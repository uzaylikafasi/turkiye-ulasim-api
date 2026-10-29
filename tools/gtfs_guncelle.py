"""Şehirlerin GTFS dosyalarını indirip `data/<şehir>.sqlite3` olarak kurar.

Kullanım: python -m tools.gtfs_guncelle [izmir ...]
"""
import sys
import tempfile
from pathlib import Path

import httpx

from turkiye_ulasim import gtfs
from turkiye_ulasim.cities import CITIES
from turkiye_ulasim.main import DATA_DIR


def update(city_id: str) -> None:
    city = CITIES[city_id]
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder:
        archive = Path(folder) / "gtfs.zip"
        with httpx.stream("GET", city.gtfs_url, timeout=120, follow_redirects=True) as response:
            response.raise_for_status()
            with archive.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        gtfs.build(archive, DATA_DIR / f"{city_id}.sqlite3")
    print(f"{city.name}: {DATA_DIR / f'{city_id}.sqlite3'}")


if __name__ == "__main__":
    for name in sys.argv[1:] or CITIES:
        update(name)
