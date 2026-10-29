"""Türkiye ulaşım API'si: her şehir aynı uçlar ve aynı `{data, meta}` biçimiyle."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .cities import CITIES, City
from .gtfs import GtfsStore
from .sources.izmir import IzmirLive, SourceError

DATA_DIR = Path(os.environ.get("ULASIM_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))


def default_sources() -> dict:
    return {"izmir": (GtfsStore(DATA_DIR / "izmir.sqlite3"), IzmirLive())}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def create_app(sources_factory: Callable[[], dict] = default_sources) -> FastAPI:
    state: dict = {}

    @asynccontextmanager
    async def lifespan(_app):
        state["sources"] = sources_factory()
        yield
        for _, live in state["sources"].values():
            await live.client.aclose()

    app = FastAPI(title="Türkiye Ulaşım API", version="0.1.0", lifespan=lifespan)

    def city_of(city_id: str) -> tuple[City, GtfsStore, IzmirLive]:
        if city_id not in CITIES or city_id not in state["sources"]:
            raise HTTPException(404, f"Şehir desteklenmiyor: {city_id}")
        return (CITIES[city_id], *state["sources"][city_id])

    def envelope(city: City, store: GtfsStore, data, live: bool = False, warnings=()):
        warnings = list(warnings)
        if store.calendar_expired():
            warnings.append("Kaynağın GTFS takvimi süresi dolmuş; hat ve durak bilgisi eski olabilir.")
        meta = {"city": city.id, "source": city.operator, "license": city.license, "source_url": city.source_url,
                "live": live, "warnings": warnings}
        if live:
            meta["fetched_at"] = _now()
        return {"data": data, "meta": meta}

    @app.exception_handler(SourceError)
    async def source_error(_request, exc):
        return JSONResponse(status_code=502, content={"error": str(exc)})

    @app.get("/v1/cities")
    def cities():
        return {"data": [asdict(c) | {"modes": list(c.modes)} for c in CITIES.values() if c.id in state["sources"]],
                "meta": {}}

    @app.get("/v1/{city_id}/lines")
    def lines(city_id: str, q: str = Query("", max_length=80)):
        city, store, _ = city_of(city_id)
        return envelope(city, store, store.lines(q.strip()))

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
        return envelope(city, store, store.line_stops(line_id, direction))

    @app.get("/v1/{city_id}/lines/{line_id}/shape")
    def line_shape(city_id: str, line_id: str, direction: int = Query(0, ge=0, le=1)):
        city, store, _ = city_of(city_id)
        return envelope(city, store, store.line_shape(line_id, direction))

    @app.get("/v1/{city_id}/lines/{line_id}/vehicles")
    async def vehicles(city_id: str, line_id: str):
        city, store, live = city_of(city_id)
        if not line_id.isdigit() or store.line(line_id) is None:
            raise HTTPException(404, "Hat bulunamadı")
        data, warnings = await live.vehicles(line_id)
        return envelope(city, store, data, live=True, warnings=warnings)

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
        if not stop_id.isdigit() or store.stop(stop_id) is None:
            raise HTTPException(404, "Durak bulunamadı")
        data, warnings = await live.arrivals(stop_id)
        return envelope(city, store, data, live=True, warnings=warnings)

    return app


app = create_app()
