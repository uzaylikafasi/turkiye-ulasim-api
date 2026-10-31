"""GTFS statik verisini küçük bir SQLite dosyasına indirger.

Bir şehrin bütün `stop_times.txt` dosyası (İzmir'de 2 milyon satır) tutulmaz. Her hat ve yön için
en çok durağa uğrayan sefer temsilci seçilir; durak sırası ve güzergâh yalnız o seferden alınır.
Tarife sorguları bu yüzden ilk sürümde yok.
"""
from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE lines (id TEXT PRIMARY KEY, short_name TEXT, long_name TEXT, route_type INTEGER, source_route_code TEXT);
CREATE TABLE stops (id TEXT PRIMARY KEY, name TEXT, latitude REAL, longitude REAL);
CREATE TABLE line_stops (line_id TEXT, direction INTEGER, sequence INTEGER, stop_id TEXT,
                         PRIMARY KEY (line_id, direction, sequence));
CREATE INDEX line_stops_stop ON line_stops (stop_id);
CREATE TABLE line_shapes (line_id TEXT, direction INTEGER, sequence INTEGER, latitude REAL, longitude REAL,
                          PRIMARY KEY (line_id, direction, sequence));
"""


def _member(archive: zipfile.ZipFile, name: str) -> str | None:
    matches = [n for n in archive.namelist() if Path(n).name.lower() == name.lower()]
    if len(matches) > 1:
        raise ValueError(f"GTFS dosyası birden çok kez bulundu: {name}")
    return matches[0] if matches else None


def _rows(archive: zipfile.ZipFile, name: str):
    member = _member(archive, name)
    if member is None:
        raise ValueError(f"GTFS dosyası eksik: {name}")
    with archive.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", newline="")
        header = text.readline()
        delimiter = ";" if header.count(";") > header.count(",") else ","
        import itertools
        yield from csv.DictReader(itertools.chain([header], text), delimiter=delimiter)


def _repair_text(value: str) -> str:
    """İBB routes.csv'deki UTF-8'in Windows-1252 olarak kaydedilmesini geri alır."""
    if not any(c in value for c in ("Ã", "Ä", "Å", "Â")):
        return value
    try:
        # Windows-1252'de tanımsız C1 karakterleri kaynakta aynen korunmuş.
        raw = b"".join(bytes([ord(c)]) if ord(c) < 256 else c.encode("cp1252") for c in value)
        return raw.decode("utf-8")
    except (UnicodeError, ValueError):
        return value


def _coordinate(value: str, *, ibb_csv: bool) -> float:
    if ibb_csv and value.count(".") > 1:
        digits = value.replace(".", "")
        if not digits.isdigit():
            raise ValueError(f"Geçersiz İBB koordinatı: {value}")
        # İBB CSV ondalık noktayı kaybedip binlik gruplama uyguluyor.
        value = digits[:2] + "." + digits[2:]
    return float(value)


def build(zip_path: Path, db_path: Path, *, bus_only: bool = True, ibb_csv: bool = False) -> None:
    """Atomik kurulum; hat/yön başına temsilci sefer. Yalnız otobüsler içe alınır."""
    import tempfile
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=db_path.parent, suffix=".tmp", delete=False) as handle:
        temporary = Path(handle.name)
    db = sqlite3.connect(temporary)
    try:
        db.executescript(SCHEMA)
        with zipfile.ZipFile(zip_path) as archive:
            routes = []
            for r in _rows(archive, "routes.txt"):
                if not r.get("route_id"):
                    continue  # İBB CSV boş ve kimliksiz devam satırları içeriyor.
                kind = int(r.get("route_type") or 3)
                if bus_only and kind != 3 and not 700 <= kind < 800:
                    continue
                routes.append((r["route_id"], r.get("route_short_name", ""),
                               _repair_text(r.get("route_long_name", "")) if ibb_csv else r.get("route_long_name", ""),
                               kind, r.get("route_code", "")))
            if not routes:
                raise ValueError("GTFS içinde desteklenen otobüs hattı yok")
            db.executemany("INSERT INTO lines VALUES (?,?,?,?,?)", routes)
            route_ids = {r[0] for r in routes}
            trips = {r["trip_id"]: (r["route_id"], int(r.get("direction_id") or 0), r.get("shape_id", ""))
                     for r in _rows(archive, "trips.txt") if r["route_id"] in route_ids}
            counts = Counter()
            bus_stops = set()
            for r in _rows(archive, "stop_times.txt"):
                if r["trip_id"] in trips:
                    counts[r["trip_id"]] += 1
                    bus_stops.add(r["stop_id"])
            if not bus_stops:
                raise ValueError("GTFS otobüs seferleri için durak sırası içermiyor")
            for r in _rows(archive, "stops.txt"):
                if r["stop_id"] not in bus_stops:
                    continue
                lat = _coordinate(r["stop_lat"], ibb_csv=ibb_csv)
                lon = _coordinate(r["stop_lon"], ibb_csv=ibb_csv)
                if not (35 < lat < 43 and 25 < lon < 45):
                    raise ValueError(f"GTFS durak koordinatı Türkiye sınırları dışında: {r['stop_id']}")
                db.execute("INSERT INTO stops VALUES (?,?,?,?)", (r["stop_id"], r["stop_name"], lat, lon))
            # Bozuk bir temsilci bütün şehri durdurmasın: her hat/yönün en uzun üç
            # adayını tek taramada doğrula. Aynı sırada farklı durak varsa seferi atla.
            candidates: dict[tuple[str, int], list[str]] = {}
            for trip_id in sorted(counts, key=counts.get, reverse=True):
                key = trips[trip_id][:2]
                group = candidates.setdefault(key, [])
                if len(group) < 3:
                    group.append(trip_id)
            selected = {trip_id: {} for group in candidates.values() for trip_id in group}
            invalid = set()
            for r in _rows(archive, "stop_times.txt"):
                if r["trip_id"] not in selected:
                    continue
                stops = selected[r["trip_id"]]
                sequence = int(r["stop_sequence"])
                if sequence in stops and stops[sequence] != r["stop_id"]:
                    invalid.add(r["trip_id"])
                stops[sequence] = r["stop_id"]
            chosen = {key: next((t for t in group if t not in invalid), None) for key, group in candidates.items()}
            omitted = sum(t is None for t in chosen.values())
            wanted = {trip_id: key for key, trip_id in chosen.items() if trip_id is not None}
            db.executemany("INSERT INTO line_stops VALUES (?,?,?,?)", (
                (*key, sequence, stop_id) for trip_id, key in wanted.items()
                for sequence, stop_id in selected[trip_id].items()))
            import_warnings = []
            if invalid:
                import_warnings.append(f"Kaynakta aynı sırada farklı duraklar içeren {len(invalid)} aday sefer atlandı.")
            if omitted:
                import_warnings.append(f"{omitted} hat/yön için üç aday sefer de tutarsız; durak sırası ve geometri yayımlanmadı.")
            missing = db.execute("SELECT 1 FROM line_stops ls LEFT JOIN stops s ON s.id=ls.stop_id WHERE s.id IS NULL LIMIT 1").fetchone()
            if missing:
                raise ValueError("GTFS seferi bilinmeyen bir durağa başvuruyor")
            shapes = {}
            for trip_id, key in wanted.items():
                if trips[trip_id][2]:
                    shapes.setdefault(trips[trip_id][2], []).append(key)
            if shapes and _member(archive, "shapes.txt"):
                seen_points = {}
                duplicate_points = 0
                def shape_records():
                    nonlocal duplicate_points
                    for r in _rows(archive, "shapes.txt"):
                        keys = shapes.get(r["shape_id"], ())
                        if not keys:
                            continue
                        sequence = int(r["shape_pt_sequence"])
                        identity = (r["shape_id"], sequence)
                        position = (float(r["shape_pt_lat"]), float(r["shape_pt_lon"]))
                        if identity in seen_points:
                            if seen_points[identity] != position:
                                raise ValueError("GTFS aynı güzergâh/nokta sırasında farklı koordinatlar içeriyor")
                            duplicate_points += 1
                            continue
                        seen_points[identity] = position
                        for key in keys:
                            yield (*key, sequence, *position)
                db.executemany("INSERT INTO line_shapes VALUES (?,?,?,?,?)", shape_records())
                if duplicate_points:
                    import_warnings.append(f"{duplicate_points} birebir aynı güzergâh noktası tekrarı tekilleştirildi.")
            ends = [r["end_date"] for r in _rows(archive, "calendar.txt")] if _member(archive, "calendar.txt") else []
            if _member(archive, "calendar_dates.txt"):
                ends.extend(r["date"] for r in _rows(archive, "calendar_dates.txt") if r["exception_type"] == "1")
            db.executemany("INSERT INTO meta VALUES (?,?)", [
                ("calendar_end", max(ends) if ends else ""),
                ("imported_at", datetime.now(timezone.utc).isoformat(timespec="seconds")),
                ("warnings", json.dumps(import_warnings, ensure_ascii=False)),
            ])
        db.commit()
        db.close()
        temporary.replace(db_path)
    finally:
        db.close()
        temporary.unlink(missing_ok=True)


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
        self.path = db_path
        self.file_id = db_path.stat().st_ino
        self.db = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, check_same_thread=False)
        self.db.row_factory = sqlite3.Row

    def refresh(self):
        if self.path.stat().st_ino != self.file_id:
            replacement = GtfsStore(self.path)
            self.db.close()
            self.db, self.file_id = replacement.db, replacement.file_id

    def warnings(self) -> list[str]:
        row = self.db.execute("SELECT value FROM meta WHERE key='warnings'").fetchone()
        return json.loads(row["value"]) if row else []

    def calendar_expired(self, today: date | None = None) -> bool:
        row = self.db.execute("SELECT value FROM meta WHERE key='calendar_end'").fetchone()
        end = row["value"] if row else ""
        return bool(end) and end < (today or date.today()).strftime("%Y%m%d")

    def lines(self, query: str = "", limit: int = 200, offset: int = 0) -> list[dict]:
        # SQLite LIKE Türkçe büyük/küçük harfi bilmez; eşleşme Python'da yapılır.
        needle = _fold(query)
        rows = self.db.execute("SELECT * FROM lines ORDER BY CAST(short_name AS INTEGER), short_name")
        from itertools import islice
        return [_line(r) for r in islice((r for r in rows if needle in _fold(r["short_name"] + " " + r["long_name"])),
                                         offset, offset + limit)]

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
    result = {"id": row["id"], "code": row["short_name"], "name": row["long_name"],
              "mode": "bus" if 700 <= row["route_type"] < 800 else _MODES.get(row["route_type"], "other")}
    if "source_route_code" in row.keys() and row["source_route_code"]:
        result["source_route_code"] = row["source_route_code"]
    return result


def _stop(row) -> dict:
    return {"id": row["id"], "name": row["name"], "latitude": row["latitude"], "longitude": row["longitude"]}


_MODES = {0: "tram", 1: "metro", 2: "rail", 3: "bus", 4: "ferry", 5: "cable_tram", 6: "aerial_lift", 7: "funicular", 11: "trolleybus"}
