"""Türkiye ulaşım API'si: her şehir aynı uçlar ve aynı `{data, meta}` biçimiyle."""
from __future__ import annotations

import os
import inspect
import asyncio
import json
import sqlite3
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from .cities import CITIES, City
from .gtfs import GtfsStore
from .sources.izmir import IzmirLive
from .sources.ankara import AnkaraLive
from .sources.diyarbakir import DiyarbakirLive
from .sources.trabzon import TrabzonLive
from .sources.istanbul import IstanbulLive
from .sources.base import SourceError, SourceRateLimited, SourceNotFound, SourceUnsupported
from .sources.kahramanmaras import Kahramanmaras

DATA_DIR = Path(os.environ.get("ULASIM_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))


def default_sources() -> dict:
    factories = {"izmir": IzmirLive, "istanbul": IstanbulLive, "ankara": AnkaraLive, "diyarbakir": DiyarbakirLive, "trabzon": TrabzonLive}
    sources = {city_id: (GtfsStore(DATA_DIR / f"{city_id}.sqlite3"),
                         factories[city_id]() if city_id in factories else None)
               for city_id, city in CITIES.items() if city.gtfs and (DATA_DIR / f"{city_id}.sqlite3").is_file()}
    if os.getenv("ULASIM_KAHRAMANMARAS_ENABLED", "1") != "0":
        bridge = Kahramanmaras()
        sources["kahramanmaras"] = (bridge, bridge)
    return sources


async def store_call(store, method, *args):
    call = getattr(store, method)
    if inspect.iscoroutinefunction(call):
        return await call(*args)
    if isinstance(store, GtfsStore):
        if not hasattr(store, "query_lock"):
            store.query_lock = asyncio.Lock()
        async with store.query_lock:
            store.refresh()
            return await run_in_threadpool(call, *args)
    return await run_in_threadpool(call, *args)


def create_app(sources_factory: Callable[[], dict] = default_sources) -> FastAPI:
    state: dict = {"observations": {}}

    @asynccontextmanager
    async def lifespan(_app):
        state["sources"] = sources_factory()
        try:
            yield
        finally:
            for store, live in state["sources"].values():
                if isinstance(store, GtfsStore):
                    store.db.close()
                if live is not None:
                    await live.client.aclose()

    app = FastAPI(title="Türkiye Ulaşım API", version="0.3.0", lifespan=lifespan)

    def city_of(city_id: str):
        if city_id not in CITIES:
            raise HTTPException(404, f"Şehir desteklenmiyor: {city_id}")
        if city_id not in state["sources"]:
            raise HTTPException(503, f"Şehrin veri kaynağı henüz kurulmadı veya kapalı: {city_id}")
        return (CITIES[city_id], *state["sources"][city_id])

    def envelope(city: City, store: GtfsStore, data, result=None, warnings=()):
        warnings = list(city.warnings) + store.warnings() + list(warnings)
        if result is not None:
            warnings.extend(result.warnings)
        if store.calendar_expired():
            warnings.append("Kaynağın GTFS takvimi süresi dolmuş; hat ve durak bilgisi eski olabilir.")
        meta = {"city": city.id, "source": city.operator, "license": city.license, "source_url": city.source_url,
                "live": result is not None, "warnings": warnings, "source_kind": city.source_kind, "partial_feed": city.partial_feed}
        if city.partial_feed:
            meta.update(dict(store.db.execute("SELECT key,value FROM meta WHERE key IN ('topology_source','topology_updated_at')")))
        if result is not None:
            meta["fetched_at"] = result.fetched_at
            meta["cached"] = result.cached
        return {"data": data, "meta": meta}

    @app.exception_handler(SourceError)
    async def source_error(_request, exc):
        parts = _request.url.path.removeprefix(_request.scope.get("root_path", "")).split("/")
        if len(parts) > 2 and parts[2] in CITIES:
            observation = state["observations"].setdefault(parts[2], {})
            observation.update(last_outcome="error", last_error_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                               last_error_type=type(exc).__name__)
        if isinstance(exc, SourceRateLimited):
            return JSONResponse(status_code=503, content={"error": str(exc)},
                                headers={"Retry-After": str(exc.retry_after)})
        status = 404 if isinstance(exc, SourceNotFound) else 501 if isinstance(exc, SourceUnsupported) else 502
        return JSONResponse(status_code=status, content={"error": str(exc)})

    def diagnostics():
        rows = []
        for city in CITIES.values():
            source = state["sources"].get(city.id)
            row = {"city": city.id, "configured": source is not None, "storage": "catalog" if city.partial_feed else "gtfs" if city.gtfs else "remote",
                   "local_status": "missing" if source is None else "configured",
                   "imported_at": None, "calendar_end": None, "calendar_expired": None,
                   "upstream_checked": False, "live_observation": dict(state["observations"].get(city.id, {}))}
            if source is not None and city.gtfs:
                try:
                    db = source[0].db
                    values = dict(db.execute("SELECT key,value FROM meta"))
                    # Temel tabloların okunabildiğini doğrula; dosya yollarını veya hata ayrıntılarını açma.
                    row.update(lines=db.execute("SELECT count(*) FROM lines").fetchone()[0],
                               stops=db.execute("SELECT count(*) FROM stops").fetchone()[0],
                               imported_at=values.get("imported_at"), calendar_end=values.get("calendar_end") or None,
                               calendar_expired=source[0].calendar_expired(), local_status="readable")
                except sqlite3.Error:
                    row["local_status"] = "error"
            rows.append(row)
        return rows

    @app.get("/healthz")
    def health():
        return {"status": "ok", "version": app.version, "upstream_checked": False}

    @app.get("/v1/status")
    async def source_status():
        try:
            update = json.loads((DATA_DIR / "update-status.json").read_text())
        except (OSError, ValueError):
            update = None
        return {"data": diagnostics(), "meta": {"upstream_checked": False, "last_update": update,
                "note": "Yerel dosya durumu ve bu süreçte gözlenen canlı sorgular; kaynaklara yeni istek yapılmaz."}}

    @app.get("/readyz")
    async def readiness():
        rows = diagnostics()
        # Hazır olma, yapılandırılmış kaynaklar ve yerel veri içindir; canlı sağlayıcı garantisi değildir.
        ready = all(r["local_status"] == "readable" for r in rows if r["storage"] != "remote")
        return JSONResponse(status_code=200 if ready else 503,
                            content={"status": "ready" if ready else "not_ready", "upstream_checked": False})

    @app.get("/v1/cities")
    def cities():
        return {"data": [asdict(c) | {"modes": list(c.modes), "available": c.id in state["sources"], "gtfs": c.gtfs and not c.partial_feed,
                        "capabilities": {"static": True, "vehicles": c.live_vehicles, "arrivals": c.live_arrivals,
                                         "stop_coordinates": c.stop_coordinates, "nearby": c.stop_coordinates,
                                         "line_catalog": c.line_catalog, "gtfs": c.gtfs and not c.partial_feed}}
                         for c in CITIES.values()],
                "meta": {}}

    @app.get("/v1/{city_id}/lines")
    async def lines(city_id: str, q: str = Query("", max_length=80),
              limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
        city, store, _ = city_of(city_id)
        if not city.line_catalog and not q.strip():
            raise HTTPException(422, "Bu şehirde tam hat kataloğu yok; q ile hat arayın (örnek: H/1)")
        data = await store_call(store, "lines", q.strip(), limit + 1, offset)
        response = envelope(city, store, data[:limit])
        response["meta"]["pagination"] = {"limit": limit, "offset": offset, "has_more": len(data) > limit,
                                             "source_limited": not city.line_catalog}
        return response

    @app.get("/v1/{city_id}/lines/{line_id}")
    async def line(city_id: str, line_id: str):
        city, store, _ = city_of(city_id)
        found = await store_call(store, "line", line_id)
        if found is None:
            raise HTTPException(404, "Hat bulunamadı")
        return envelope(city, store, found)

    @app.get("/v1/{city_id}/lines/{line_id}/stops")
    async def line_stops(city_id: str, line_id: str, direction: int = Query(0, ge=0, le=1)):
        city, store, _ = city_of(city_id)
        if await store_call(store, "line", line_id) is None:
            raise HTTPException(404, "Hat bulunamadı")
        data = await store_call(store, "line_stops", line_id, direction)
        if city.partial_feed and not data:
            raise HTTPException(501, "Bu hat/yön için doğrulanmış durak sırası bulunmuyor")
        return envelope(city, store, data)

    @app.get("/v1/{city_id}/lines/{line_id}/shape")
    async def line_shape(city_id: str, line_id: str, direction: int = Query(0, ge=0, le=1)):
        city, store, _ = city_of(city_id)
        if await store_call(store, "line", line_id) is None:
            raise HTTPException(404, "Hat bulunamadı")
        data = await store_call(store, "line_shape", line_id, direction)
        if city.partial_feed and not data:
            raise HTTPException(501, "Bu hat/yön için doğrulanmış geometri bulunmuyor")
        return envelope(city, store, data, warnings=[] if data else ["Kaynak bu hat/yön için güzergâh geometrisi içermiyor."])

    @app.get("/v1/{city_id}/lines/{line_id}/vehicles")
    async def vehicles(city_id: str, line_id: str):
        city, store, live = city_of(city_id)
        found = await store_call(store, "line", line_id)
        if found is None:
            raise HTTPException(404, "Hat bulunamadı")
        if not city.live_vehicles or live is None:
            raise HTTPException(501, "Bu şehirde açık canlı araç konumu kaynağı desteklenmiyor")
        if city.id == "istanbul" and not found.get("source_route_code"):
            raise HTTPException(501, "Kaynak bu hat için canlı eşleştirmede kullanılan güzergâh kodunu içermiyor")
        result = await live.vehicles(line_id, line=found)
        state["observations"].setdefault(city.id, {}).update(last_outcome="success", last_success_at=result.fetched_at)
        return envelope(city, store, result.data, result=result)

    @app.get("/v1/{city_id}/stops/nearby")
    async def nearby(city_id: str, latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180),
               radius: float = Query(500, gt=0, le=3000)):
        city, store, _ = city_of(city_id)
        if not city.stop_coordinates:
            raise HTTPException(501, "Kaynak durak koordinatı vermiyor; yakın durak desteklenmiyor")
        return envelope(city, store, await store_call(store, "nearby", latitude, longitude, radius))

    @app.get("/v1/{city_id}/stops/{stop_id}")
    async def stop(city_id: str, stop_id: str):
        city, store, _ = city_of(city_id)
        found = await store_call(store, "stop", stop_id)
        if found is None:
            raise HTTPException(404, "Durak bulunamadı")
        return envelope(city, store, found)

    @app.get("/v1/{city_id}/stops/{stop_id}/arrivals")
    async def arrivals(city_id: str, stop_id: str):
        city, store, live = city_of(city_id)
        found = await store_call(store, "stop", stop_id)
        if found is None:
            raise HTTPException(404, "Durak bulunamadı")
        if not city.live_arrivals or live is None:
            raise HTTPException(501, "Bu şehirde açık canlı varış kaynağı desteklenmiyor")
        result = await live.arrivals_for_stop(found) if hasattr(live, "arrivals_for_stop") else await live.arrivals(stop_id)
        state["observations"].setdefault(city.id, {}).update(last_outcome="success", last_success_at=result.fetched_at)
        return envelope(city, store, result.data, result=result)

    return app


app = create_app()
