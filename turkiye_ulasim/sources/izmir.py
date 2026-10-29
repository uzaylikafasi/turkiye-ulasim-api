"""İzmir ESHOT canlı verisi (İZTEK açık veri web servisleri, anonim erişim).

Belge: https://openfiles.izmir.bel.tr/471231/docs/iztek-WebServisKullanimDokumani_1.0.pdf
Gözlenen kaynak davranışı (2026-10-29):
- Koordinatlar virgüllü metin ("38,49866833"); `KoorX` enlem, `KoorY` boylam.
- "0" konumlu kayıtlar geliyor.
- Hat konumlarında aynı `OtobusId` 2-3 kez gelir: biri hareket eder, diğerleri aynı yerde kalır.
  Sıra güvenilir değil. Bu yüzden önceki sorguya göre yer değiştiren kayıt canlı sayılır.
"""
from __future__ import annotations

import time

import httpx

from .base import LiveResult, SourceError

BASE_URL = "https://openapi.izmir.bel.tr/api/iztek"
# Önceki konumlar bu süreden eskiyse karşılaştırmada kullanılmaz.
MEMORY_SECONDS = 300


def _coordinate(value) -> float | None:
    try:
        number = float(str(value).replace(",", "."))
    except ValueError:
        return None
    return number if number else None


def _position(item) -> tuple[float, float] | None:
    latitude, longitude = _coordinate(item.get("KoorX")), _coordinate(item.get("KoorY"))
    if latitude is None or longitude is None or not (35 < latitude < 43 and 25 < longitude < 45):
        return None
    return latitude, longitude


class IzmirLive:
    def __init__(self, client: httpx.AsyncClient | None = None, clock=time.monotonic):
        self.client = client or httpx.AsyncClient(base_url=BASE_URL, timeout=10)
        self.clock = clock
        self._seen: dict[tuple[str, int], tuple[float, set[tuple[float, float]]]] = {}

    async def _get(self, path: str):
        try:
            response = await self.client.get(path)
        except httpx.HTTPError as exc:
            raise SourceError(f"İzmir kaynağına ulaşılamadı: {type(exc).__name__}") from exc
        if response.status_code == 204:
            return None
        if response.status_code != 200:
            raise SourceError(f"İzmir kaynağı HTTP {response.status_code} döndü")
        try:
            return response.json()
        except ValueError as exc:
            raise SourceError("İzmir kaynağı JSON dışı yanıt döndü") from exc

    async def vehicles(self, line_id: str, *, line: dict | None = None) -> LiveResult:
        body = await self._get(f"/hatotobuskonumlari/{int(line_id)}") or {}
        if body.get("HataMesaj"):
            raise SourceError(f"İzmir kaynağı: {body['HataMesaj']}")
        groups: dict[int, list[tuple[int, tuple[float, float]]]] = {}
        for item in body.get("HatOtobusKonumlari") or []:
            position = _position(item)
            if position is not None and isinstance(item.get("OtobusId"), int):
                groups.setdefault(item["OtobusId"], []).append((item.get("Yon"), position))

        now = self.clock()
        vehicles, warnings = [], []
        ambiguous = 0
        for vehicle_id, entries in groups.items():
            key = (line_id, vehicle_id)
            seen_at, previous = self._seen.get(key, (0.0, set()))
            fresh = previous if now - seen_at <= MEMORY_SECONDS else set()
            positions = {p for _, p in entries}
            if len(positions) == 1:
                direction, position = entries[0]
                confidence = "single"
            else:
                moved = [(d, p) for d, p in entries if fresh and p not in fresh]
                if len(moved) == 1:
                    (direction, position), confidence = moved[0], "moved"
                else:
                    (direction, position), confidence = entries[0], "ambiguous"
                    ambiguous += 1
            self._seen[key] = (now, positions)
            vehicles.append({"id": str(vehicle_id), "line_id": line_id, "source_direction": direction,
                             "latitude": position[0], "longitude": position[1],
                             "position_confidence": confidence})
        if ambiguous:
            warnings.append(f"{ambiguous} araç için kaynak birden fazla konum verdi; canlı olanı ayırt etmek "
                            "için ikinci bir sorgu gerekiyor (position_confidence=ambiguous).")
        return LiveResult(vehicles, warnings)

    async def arrivals(self, stop_id: str) -> LiveResult:
        body = await self._get(f"/duragayaklasanotobusler/{int(stop_id)}") or []
        arrivals = []
        for item in body:
            position = _position(item)
            arrivals.append({
                "line_id": str(item.get("HatNumarasi")),
                "line_name": item.get("HatAdi"),
                "vehicle_id": str(item.get("OtobusId")),
                "stops_away": item.get("KalanDurakSayisi"),
                "source_direction": item.get("HattinYonu"),
                "latitude": position[0] if position else None,
                "longitude": position[1] if position else None,
                "wheelchair_accessible": item.get("EngelliMi"),
                "bike_rack": item.get("BisikletAparatliMi"),
            })
        arrivals.sort(key=lambda a: a["stops_away"] if isinstance(a["stops_away"], int) else 10**6)
        return LiveResult(arrivals)
