"""GTFS statik verisini küçük bir SQLite dosyasına indirger.

Bir şehrin bütün `stop_times.txt` dosyası (İzmir'de 2 milyon satır) tutulmaz. Her hat ve yön için
en çok durağa uğrayan sefer temsilci seçilir; durak sırası ve güzergâh yalnız o seferden alınır.
Tarife sorguları bu yüzden ilk sürümde yok.
"""
from __future__ import annotations

import csv
import io
import math
import sqlite3
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE lines (id TEXT PRIMARY KEY, short_name TEXT, long_name TEXT, route_type INTEGER);
CREATE TABLE stops (id TEXT PRIMARY KEY, name TEXT, latitude REAL, longitude REAL);
CREATE TABLE line_stops (line_id TEXT, direction INTEGER, sequence INTEGER, stop_id TEXT,
                         PRIMARY KEY (line_id, direction, sequence));
CREATE INDEX line_stops_stop ON line_stops (stop_id);
CREATE TABLE line_shapes (line_id TEXT, direction INTEGER, sequence INTEGER, latitude REAL, longitude REAL,
                          PRIMARY KEY (line_id, direction, sequence));
"""


def _rows(archive: zipfile.ZipFile, name: str):
    with archive.open(name) as raw:
        yield from csv.DictReader(io.TextIOWrapper(raw, encoding="utf-8-sig", newline=""))


def build(zip_path: Path, db_path: Path) -> None:
    """GTFS zip'inden veritabanını baştan kurar; yarım kalan kurulum eski dosyayı bozmaz."""
    temporary = db_path.with_suffix(".tmp")
    temporary.unlink(missing_ok=True)
    db = sqlite3.connect(temporary)
    db.executescript(SCHEMA)
    with zipfile.ZipFile(zip_path) as archive:
        db.executemany("INSERT INTO lines VALUES (?,?,?,?)", (
            (r["route_id"], r.get("route_short_name", ""), r.get("route_long_name", ""), int(r.get("route_type") or 3))
            for r in _rows(archive, "routes.txt")))
        db.executemany("INSERT INTO stops VALUES (?,?,?,?)", (
            (r["stop_id"], r["stop_name"], float(r["stop_lat"]), float(r["stop_lon"]))
            for r in _rows(archive, "stops.txt")))

        trips = {r["trip_id"]: (r["route_id"], int(r.get("direction_id") or 0), r.get("shape_id", ""))
                 for r in _rows(archive, "trips.txt")}
        counts = Counter(r["trip_id"] for r in _rows(archive, "stop_times.txt"))
        chosen: dict[tuple[str, int], str] = {}
        for trip_id, count in counts.items():
            if trip_id not in trips:
                continue
            key = trips[trip_id][:2]
            if key not in chosen or count > counts[chosen[key]]:
                chosen[key] = trip_id
        wanted = {trip_id: key for key, trip_id in chosen.items()}
        db.executemany("INSERT INTO line_stops VALUES (?,?,?,?)", (
            (*wanted[r["trip_id"]], int(r["stop_sequence"]), r["stop_id"])
            for r in _rows(archive, "stop_times.txt") if r["trip_id"] in wanted))

        shapes = {}
        for trip_id, key in wanted.items():
            if trips[trip_id][2]:
                shapes.setdefault(trips[trip_id][2], []).append(key)
        if shapes and "shapes.txt" in archive.namelist():
            db.executemany("INSERT INTO line_shapes VALUES (?,?,?,?,?)", (
                (*key, int(r["shape_pt_sequence"]), float(r["shape_pt_lat"]), float(r["shape_pt_lon"]))
                for r in _rows(archive, "shapes.txt") for key in shapes.get(r["shape_id"], ())))

        ends = [r["end_date"] for r in _rows(archive, "calendar.txt")] if "calendar.txt" in archive.namelist() else []
        db.execute("INSERT INTO meta VALUES ('calendar_end', ?)", (max(ends) if ends else "",))
    db.commit()
    db.close()
    temporary.replace(db_path)


@dataclass(frozen=True)
class Stop:
    id: str
    name: str
    latitude: float
    longitude: float


def _distance_m(lat1, lon1, lat2, lon2) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    a = (math.sin((p2 - p1) / 2) ** 2
         + math.cos(p1) * math.cos(p2) * math.sin(math.radians(lon2 - lon1) / 2) ** 2)
    return 6371000 * 2 * math.asin(math.sqrt(a))


class GtfsStore:
    def __init__(self, db_path: Path):
        self.db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
        self.db.row_factory = sqlite3.Row

    def calendar_expired(self, today: date | None = None) -> bool:
        row = self.db.execute("SELECT value FROM meta WHERE key='calendar_end'").fetchone()
        end = row["value"] if row else ""
        return bool(end) and end < (today or date.today()).strftime("%Y%m%d")

    def lines(self, query: str = "", limit: int = 200) -> list[dict]:
        # SQLite LIKE Türkçe büyük/küçük harfi bilmez; eşleşme Python'da yapılır.
        needle = _fold(query)
        rows = self.db.execute("SELECT * FROM lines ORDER BY CAST(short_name AS INTEGER), short_name")
        return [_line(r) for r in rows if needle in _fold(r["short_name"] + " " + r["long_name"])][:limit]

    def line(self, line_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM lines WHERE id=?", (line_id,)).fetchone()
        if row is None:
            return None
        directions = [r[0] for r in self.db.execute(
            "SELECT DISTINCT direction FROM line_stops WHERE line_id=? ORDER BY direction", (line_id,))]
        return {**_line(row), "directions": directions}

    def line_stops(self, line_id: str, direction: int) -> list[dict]:
        rows = self.db.execute(
            "SELECT s.* FROM line_stops ls JOIN stops s ON s.id = ls.stop_id "
            "WHERE ls.line_id=? AND ls.direction=? ORDER BY ls.sequence", (line_id, direction))
        return [_stop(r) for r in rows]

    def line_shape(self, line_id: str, direction: int) -> list[list[float]]:
        rows = self.db.execute(
            "SELECT latitude, longitude FROM line_shapes WHERE line_id=? AND direction=? ORDER BY sequence",
            (line_id, direction))
        return [[r[0], r[1]] for r in rows]

    def stop(self, stop_id: str) -> dict | None:
        row = self.db.execute("SELECT * FROM stops WHERE id=?", (stop_id,)).fetchone()
        if row is None:
            return None
        lines = self.db.execute(
            "SELECT DISTINCT l.* FROM line_stops ls JOIN lines l ON l.id = ls.line_id WHERE ls.stop_id=? "
            "ORDER BY CAST(l.short_name AS INTEGER), l.short_name", (stop_id,))
        return {**_stop(row), "lines": [_line(r) for r in lines]}

    def nearby(self, latitude: float, longitude: float, radius_m: float, limit: int = 20) -> list[dict]:
        # Önce kaba bir kutu, sonra gerçek mesafe: 11 bin durakta tam tarama gerekmez.
        dlat = radius_m / 111_320
        dlon = radius_m / (111_320 * max(math.cos(math.radians(latitude)), 0.01))
        rows = self.db.execute(
            "SELECT * FROM stops WHERE latitude BETWEEN ? AND ? AND longitude BETWEEN ? AND ?",
            (latitude - dlat, latitude + dlat, longitude - dlon, longitude + dlon))
        found = []
        for r in rows:
            distance = _distance_m(latitude, longitude, r["latitude"], r["longitude"])
            if distance <= radius_m:
                found.append({**_stop(r), "distance_m": round(distance)})
        return sorted(found, key=lambda s: s["distance_m"])[:limit]


def _fold(text: str) -> str:
    return text.replace("I", "ı").replace("İ", "i").casefold()


def _line(row) -> dict:
    return {"id": row["id"], "code": row["short_name"], "name": row["long_name"], "mode": _MODES.get(row["route_type"], "other")}


def _stop(row) -> dict:
    return {"id": row["id"], "name": row["name"], "latitude": row["latitude"], "longitude": row["longitude"]}


_MODES = {0: "tram", 1: "metro", 2: "rail", 3: "bus", 4: "ferry", 5: "cable_tram", 6: "aerial_lift", 7: "funicular", 11: "trolleybus"}
