"""İETT'nin belgelenmiş SOAP servisi; kimlik doğrulaması gerektirmez.

WSDL: https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx?WSDL
Belge v1.4 saatte en fazla 100 istek belirtir. Bu süreç en fazla 90 istek yapar.
Üretimde bir worker kullanılmalı; birden çok süreç/IP tüketicisi kotayı paylaşmaz.
"""
from __future__ import annotations

import asyncio
import json
import math
import time
from collections import deque
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from xml.etree import ElementTree as ET

import httpx

from .base import LiveResult, SourceError, SourceRateLimited

BASE_URL = "https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx"
NAMESPACE = "http://tempuri.org/"
METHOD = "GetHatOtoKonum_json"
CACHE_SECONDS = 60
HOURLY_BUDGET = 90
ISTANBUL_TZ = timezone(timedelta(hours=3))


class IstanbulLive:
    def __init__(self, client: httpx.AsyncClient | None = None, clock=time.monotonic):
        self.client = client or httpx.AsyncClient(timeout=15)
        self.clock = clock
        self._cache: dict[str, tuple[float, LiveResult]] = {}
        self._requests: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def _fetch(self, code: str) -> LiveResult:
        # Kilit eşzamanlı aynı hat sorgularını da tek kaynak isteğine indirger.
        async with self._lock:
            now = self.clock()
            self._cache = {k: v for k, v in self._cache.items() if now - v[0] < CACHE_SECONDS}
            if code in self._cache:
                return replace(self._cache[code][1], cached=True)
            while self._requests and now - self._requests[0] >= 3600:
                self._requests.popleft()
            if len(self._requests) >= HOURLY_BUDGET:
                raise SourceRateLimited(max(1, math.ceil(3600 - (now - self._requests[0]))))
            self._requests.append(now)  # Hatalı istekler de kaynak kotasını tüketir.
            envelope = ET.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")
            body = ET.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
            method = ET.SubElement(body, f"{{{NAMESPACE}}}{METHOD}")
            ET.SubElement(method, f"{{{NAMESPACE}}}HatKodu").text = code
            try:
                response = await self.client.post(BASE_URL, content=ET.tostring(envelope, encoding="utf-8"),
                    headers={"Content-Type": "text/xml; charset=utf-8", "SOAPAction": f'"{NAMESPACE}{METHOD}"'})
            except httpx.HTTPError as exc:
                raise SourceError(f"İETT kaynağına ulaşılamadı: {type(exc).__name__}") from exc
            if response.status_code != 200:
                raise SourceError(f"İETT kaynağı HTTP {response.status_code} döndü")
            try:
                root = ET.fromstring(response.content)
                result = root.find(f".//{{{NAMESPACE}}}{METHOD}Result")
                if result is None or result.text is None:
                    raise ValueError("SOAP sonuç alanı yok")
                items = json.loads(result.text)
                if not isinstance(items, list) or any(not isinstance(i, dict) for i in items):
                    raise ValueError("Araç listesi bekleniyordu")
            except (ET.ParseError, ValueError) as exc:
                raise SourceError("İETT kaynağı geçersiz SOAP/JSON yanıtı döndü") from exc
            fetched = LiveResult(items)
            self._cache[code] = (self.clock(), fetched)
            return fetched

    async def vehicles(self, line_id: str, *, line: dict) -> LiveResult:
        result = await self._fetch(line["code"])
        vehicles, warnings = [], []
        dropped = stale = 0
        for item in result.data:
            # Aynı hat kodunun farklı yön/varyantları GTFS'te farklı route_id'lerdir.
            if str(item.get("hatkodu", "")) != line["code"]:
                continue
            if item.get("guzergahkodu") != line.get("source_route_code"):
                continue
            try:
                lat = float(str(item["enlem"]).replace(",", "."))
                lon = float(str(item["boylam"]).replace(",", "."))
                if not (35 < lat < 43 and 25 < lon < 45) or not item.get("kapino"):
                    raise ValueError("Geçersiz konum/araç")
            except (ValueError, KeyError):
                dropped += 1
                continue
            try:
                observed = datetime.fromisoformat(item["son_konum_zamani"]).replace(tzinfo=ISTANBUL_TZ)
                age = (datetime.now(ISTANBUL_TZ) - observed).total_seconds()
                is_stale = age > 300 or age < -60
            except (ValueError, KeyError, TypeError):
                observed, is_stale = None, True
            stale += is_stale
            vehicles.append({"id": str(item["kapino"]), "line_id": line_id,
                "source_line_code": line["code"], "source_route_code": item["guzergahkodu"],
                "source_direction": item.get("yon"), "latitude": lat, "longitude": lon,
                "observed_at": observed.isoformat() if observed else None, "stale": is_stale,
                "position_confidence": "single"})
        if dropped:
            warnings.append(f"{dropped} araç kaydı geçersiz konum/kimlik nedeniyle atlandı.")
        if stale:
            warnings.append(f"{stale} aracın kaynak konum zamanı eski veya doğrulanamıyor (stale=true).")
        return LiveResult(vehicles, warnings, result.fetched_at, result.cached)
