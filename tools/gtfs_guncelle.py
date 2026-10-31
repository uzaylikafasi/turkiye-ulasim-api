"""Resmi GTFS zip veya CKAN CSV kaynaklarını atomik SQLite veritabanına dönüştürür."""
from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sqlite3
import tempfile
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

import httpx

from turkiye_ulasim import gtfs
from turkiye_ulasim.cities import CITIES
from turkiye_ulasim.main import DATA_DIR


def download(client: httpx.Client, url: str, target: Path) -> None:
    """Kesilen aktarmayı Range ile sürdürür; sunucu Range'i yok sayarsa baştan başlar."""
    for attempt in range(4):
        offset = target.stat().st_size if target.exists() else 0
        try:
            with client.stream("GET", url, headers={"Range": f"bytes={offset}-"} if offset else {}) as response:
                response.raise_for_status()
                if response.status_code == 206:
                    content_range = response.headers.get("Content-Range", "")
                    if not content_range.startswith(f"bytes {offset}-"):
                        raise ValueError("Kaynak beklenmeyen dosya aralığı döndü")
                with target.open("ab" if offset and response.status_code == 206 else "wb") as handle:
                    for chunk in response.iter_bytes():
                        handle.write(chunk)
            return
        except (httpx.TransportError, httpx.HTTPStatusError):
            if attempt == 3:
                raise


def repair_ibb_stops(client: httpx.Client, path: Path) -> None:
    """Sütunları kayan İBB duraklarını ayrı, belgelenmiş durak servisiyle doğrular."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle, delimiter=";")
        header = next(reader)
        records = list(reader)
    repaired = []
    repairs = 0
    for row in records:
        item = dict(zip(header, row))
        try:
            lat = gtfs._coordinate(item["stop_lat"], ibb_csv=True)
            lon = gtfs._coordinate(item["stop_lon"], ibb_csv=True)
            if not 35 < lat < 43 or not 25 < lon < 45:
                raise ValueError("Geçersiz konum")
        except (ValueError, KeyError):
            repairs += 1
            if repairs > 10:
                raise ValueError("İBB kaynağında 10'dan fazla bozuk durak; kaynak şeması incelenmeli")
            namespace = "http://tempuri.org/"
            envelope = ET.Element("{http://schemas.xmlsoap.org/soap/envelope/}Envelope")
            body = ET.SubElement(envelope, "{http://schemas.xmlsoap.org/soap/envelope/}Body")
            method = ET.SubElement(body, f"{{{namespace}}}GetDurak_json")
            ET.SubElement(method, f"{{{namespace}}}DurakKodu").text = item["stop_code"]
            response = client.post("https://api.ibb.gov.tr/iett/UlasimAnaVeri/HatDurakGuzergah.asmx",
                content=ET.tostring(envelope, encoding="utf-8"), headers={"Content-Type": "text/xml; charset=utf-8",
                "SOAPAction": '"http://tempuri.org/GetDurak_json"'})
            response.raise_for_status()
            node = ET.fromstring(response.content).find(f".//{{{namespace}}}GetDurak_jsonResult")
            data = json.loads(node.text) if node is not None and node.text else []
            found = next((r for r in data if str(r.get("SDURAKKODU")) == item["stop_code"]), None)
            point = re.fullmatch(r"POINT\s*\(\s*([\d.]+)\s+([\d.]+)\s*\)", found.get("KOORDINAT", "")) if found else None
            if point is None:
                raise ValueError(f"İBB bozuk durak resmi servisten doğrulanamadı: {item['stop_code']}")
            lon, lat = map(float, point.groups())
            item["stop_name"] = found["SDURAKADI"]
        repaired.append([item["stop_id"], item["stop_name"], lat, lon])
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["stop_id", "stop_name", "stop_lat", "stop_lon"])
        writer.writerows(repaired)
    print(f"İBB durakları: koordinat biçimi düzeltildi, {repairs} bozuk satır resmi servisten doğrulandı.")


def catalog_archive(client: httpx.Client, catalog_url: str, folder: Path) -> Path:
    response = client.get(catalog_url)
    response.raise_for_status()
    body = response.json()
    if not body.get("success"):
        raise ValueError("CKAN kataloğu veri setini döndürmedi")
    resources = body["result"]["resources"]
    archive_path = folder / "gtfs.zip"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name in ("routes", "stops", "trips", "stop_times", "calendar"):
            matches = [r for r in resources if r.get("name", "").casefold() == name]
            matches.sort(key=lambda r: r.get("format", "").upper() != "ZIP")
            if not matches:
                raise ValueError(f"CKAN kaynağı eksik: {name}")
            resource = matches[0]
            local = folder / name
            download(client, resource["url"], local)
            if resource.get("format", "").upper() == "ZIP":
                with zipfile.ZipFile(local) as source:
                    members = [n for n in source.namelist() if Path(n).name.lower() in (f"{name}.txt", f"{name}.csv")]
                    if len(members) != 1:
                        raise ValueError(f"ZIP içinde tek {name} dosyası bekleniyordu")
                    with source.open(members[0]) as src, archive.open(f"{name}.txt", "w") as dst:
                        import shutil
                        shutil.copyfileobj(src, dst)
            else:
                if name == "stops":
                    repair_ibb_stops(client, local)
                archive.write(local, f"{name}.txt")
    return archive_path


def update(city_id: str) -> None:
    city = CITIES[city_id]
    if not city.gtfs:
        print(f"{city.name}: GTFS kaynağı yok; uzak bağlayıcı kullanılır, içe aktarma gerekmiyor.")
        return
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as folder, httpx.Client(timeout=120, follow_redirects=True) as client:
        folder = Path(folder)
        if city.catalog_url:
            archive = catalog_archive(client, city.catalog_url, folder)
        else:
            archive = folder / "gtfs.zip"
            download(client, city.gtfs_url, archive)
        destination = DATA_DIR / f"{city_id}.sqlite3"
        if city.partial_feed and city.topology_region:
            from .kentkart_topology import enrich
            # Son değişim her zaman hedefle aynı dosya sisteminde atomik olsun.
            with tempfile.TemporaryDirectory(dir=DATA_DIR, prefix=".topology-") as stage_dir:
                staged = Path(stage_dir) / "staged.sqlite3"
                gtfs.build(archive, staged, allow_partial=True)
                enrich(staged, city.topology_region, client)
                staged.replace(destination)
        else:
            gtfs.build(archive, destination, ibb_csv=city_id == "istanbul", allow_partial=city.partial_feed)
    print(f"{city.name}: {DATA_DIR / f'{city_id}.sqlite3'}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cities", nargs="*", metavar="CITY", help=f"Şehirler: {', '.join(CITIES)}; varsayılan tümü")
    args = parser.parse_args()
    unknown = set(args.cities) - CITIES.keys()
    if unknown:
        parser.error(f"Bilinmeyen şehir: {', '.join(sorted(unknown))}")
    failed = False
    for name in args.cities or [c.id for c in CITIES.values() if c.gtfs]:
        try:
            update(name)
        except (httpx.HTTPError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError, sqlite3.Error) as exc:
            print(f"{CITIES[name].name}: güncellenemedi ({exc}); önceki veritabanı korundu.")
            failed = True
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
