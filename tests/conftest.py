import csv
import io
import zipfile
from pathlib import Path

import pytest

from turkiye_ulasim import gtfs

FILES = {
    "agency.txt": [["agency_id", "agency_name", "agency_url", "agency_timezone"], ["1", "Eshot", "http://x", "Europe/Istanbul"]],
    "routes.txt": [["route_id", "route_short_name", "route_long_name", "route_type"],
                   ["446", "446", "EVKA 5 - BOSTANLI İSKELE", "3"], ["90", "90", "IŞIKKENT - KONAK", "3"]],
    "stops.txt": [["stop_id", "stop_name", "stop_lat", "stop_lon"],
                  ["21050", "Münevver Öğretmen Ortaokulu", "38.5123", "27.0513"],
                  ["21056", "İlkevler", "38.515", "27.0534"], ["10123", "Basmane Ptt", "38.4224", "27.1415"]],
    "trips.txt": [["route_id", "service_id", "trip_id", "direction_id", "shape_id"],
                  ["446", "1", "kisa", "0", "s1"], ["446", "1", "uzun", "0", "s1"], ["446", "1", "donus", "1", ""]],
    "stop_times.txt": [["trip_id", "arrival_time", "departure_time", "stop_id", "stop_sequence"],
                       ["kisa", "06:00:00", "06:00:00", "21050", "1"],
                       ["uzun", "07:00:00", "07:00:00", "21056", "1"], ["uzun", "07:05:00", "07:05:00", "21050", "2"],
                       ["donus", "08:00:00", "08:00:00", "21050", "1"]],
    "shapes.txt": [["shape_id", "shape_pt_lat", "shape_pt_lon", "shape_pt_sequence"],
                   ["s1", "38.515", "27.0534", "1"], ["s1", "38.5123", "27.0513", "2"]],
    "calendar.txt": [["service_id", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
                      "start_date", "end_date"], ["1", "1", "1", "1", "1", "1", "0", "0", "20260101", "20261009"]],
}


@pytest.fixture
def gtfs_db(tmp_path: Path) -> Path:
    archive = tmp_path / "gtfs.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        for name, rows in FILES.items():
            buffer = io.StringIO()
            csv.writer(buffer).writerows(rows)
            zf.writestr(name, "﻿" + buffer.getvalue())
    db = tmp_path / "izmir.sqlite3"
    gtfs.build(archive, db)
    return db
