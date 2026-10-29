"""Türkiye ulaşım API'si: her şehir aynı uçlar ve aynı `{data, meta}` biçimiyle."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .cities import CITIES, City
from .gtfs import GtfsStore
from .sources.izmir import IzmirLive
from .sources.istanbul import IstanbulLive
from .sources.base import SourceError, SourceRateLimited

DATA_DIR = Path(os.environ.get("ULASIM_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))


def default_sources() -> dict:
    factories = {"izmir": IzmirLive, "istanbul": IstanbulLive}
    return {city_id: (GtfsStore(DATA_DIR / f"{city_id}.sqlite3"),
                      factories[city_id]() if city_id in factories else None)
            for city_id in CITIES if (DATA_DIR / f"{city_id}.sqlite3").is_file()}


def create_app(sources_factory: Callable[[], dict] = default_sources) -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(_app):
        state["sources"] = sources_factory()
        try:
            yield
        finally:
            for store, live in state["sources"].values():
                store.db.close()
                if live is not None:
                    await live.client.aclose()

    app = FastAPI(title="Türkiye Ulaşım API", version="0.2.0", lifespan=lifespan)

    def city_of(city_id: str):
        if city_id not in CITIES:
            raise HTTPException(404, f"Şehir desteklenmiyor: {city_id}")
        if city_id not in state["sources"]:
            raise HTTPException(503, f"Şehrin GTFS verisi henüz kurulmadı: {city_id}")
        return (CITIES[city_id], *state["sources"][city_id])

    def envelope(city: City, store: GtfsStore, data, result=None, warnings=()):
        warnings = list(city.warnings) + store.warnings() + list(warnings)
        if result is not None:
            warnings.extend(result.warnings)
        if store.calendar_expired():
            warnings.append("Kaynağın GTFS takvimi süresi dolmuş; hat ve durak bilgisi eski olabilir.")
        meta = {"city": city.id, "source": city.operator, "license": city.license, "source_url": city.source_url,
                "live": result is not None, "warnings": warnings}
        if result is not None:
            meta["fetched_at"] = result.fetched_at
            meta["cached"] = result.cached
        return {"data": data, "meta": meta}

    @app.exception_handler(SourceError)
    async def source_error(_request, exc):
        if isinstance(exc, SourceRateLimited):
            return JSONResponse(status_code=503, content={"error": str(exc)},
                                headers={"Retry-After": str(exc.retry_after)})
        return JSONResponse(status_code=502, content={"error": str(exc)})

    @app.get("/v1/cities")
    def cities():
        return {"data": [asdict(c) | {"modes": list(c.modes), "available": c.id in state["sources"],
                        "capabilities": {"static": True, "vehicles": c.live_vehicles, "arrivals": c.live_arrivals}}
                         for c in CITIES.values()],
                "meta": {}}

    @app.get("/v1/{city_id}/lines")
    def lines(city_id: str, q: str = Query("", max_length=80),
              limit: int = Query(200, ge=1, le=500), offset: int = Query(0, ge=0)):
        city, store, _ = city_of(city_id)
        data = store.lines(q.strip(), limit + 1, offset)
        response = envelope(city, store, data[:limit])
        response["meta"]["pagination"] = {"limit": limit, "offset": offset, "has_more": len(data) > limit}
        return response

    @app.get("/v1/{city_id}/lines/{line_id}")
    def line(city_id: str, line_id: str):
        city, store, _ = city_of(city_id)
        found = store.line(line_id)
        if found is None:
            raise HTTPException(404, "Hat bulunamadı")
        return envelope(city, store, found)

    @app.get("/v1/{city_id}/lines/{line_id}/stops")
    def line_stops(city_id: str, line_id: str, direction: int = Query(0, ge=0, le=1)):
        city, store, _ = city_of(city_id)
        if store.line(line_id) is None:
            raise HTTPException(404, "Hat bulunamadı")
        return envelope(city, store, store.line_stops(line_id, direction))

    @app.get("/v1/{city_id}/lines/{line_id}/shape")
    def line_shape(city_id: str, line_id: str, direction: int = Query(0, ge=0, le=1)):
        city, store, _ = city_of(city_id)
        if store.line(line_id) is None:
            raise HTTPException(404, "Hat bulunamadı")
        data = store.line_shape(line_id, direction)
        return envelope(city, store, data, warnings=[] if data else ["Kaynak bu hat/yön için güzergâh geometrisi içermiyor."])

    @app.get("/v1/{city_id}/lines/{line_id}/vehicles")
    async def vehicles(city_id: str, line_id: str):
        city, store, live = city_of(city_id)
        found = store.line(line_id)
        if found is None:
            raise HTTPException(404, "Hat bulunamadı")
        if not city.live_vehicles or live is None:
            raise HTTPException(501, "Bu şehirde açık canlı araç konumu kaynağı desteklenmiyor")
        if city.id == "istanbul" and not found.get("source_route_code"):
            raise HTTPException(501, "Kaynak bu hat için canlı eşleştirmede kullanılan güzergâh kodunu içermiyor")
        result = await live.vehicles(line_id, line=found)
        return envelope(city, store, result.data, result=result)

    @app.get("/v1/{city_id}/stops/nearby")
    def nearby(city_id: str, latitude: float = Query(ge=-90, le=90), longitude: float = Query(ge=-180, le=180),
               radius: float = Query(500, gt=0, le=3000)):
        city, store, _ = city_of(city_id)
        return envelope(city, store, store.nearby(latitude, longitude, radius))

    @app.get("/v1/{city_id}/stops/{stop_id}")
    def stop(city_id: str, stop_id: str):
        city, store, _ = city_of(city_id)
        found = store.stop(stop_id)
        if found is None:
            raise HTTPException(404, "Durak bulunamadı")
        return envelope(city, store, found)

    @app.get("/v1/{city_id}/stops/{stop_id}/arrivals")
    async def arrivals(city_id: str, stop_id: str):
        city, store, live = city_of(city_id)
        if store.stop(stop_id) is None:
            raise HTTPException(404, "Durak bulunamadı")
        if not city.live_arrivals or live is None:
            raise HTTPException(501, "Bu şehirde açık canlı varış kaynağı desteklenmiyor")
        result = await live.arrivals(stop_id)
        return envelope(city, store, result.data, result=result)

    return app


app = create_app()
