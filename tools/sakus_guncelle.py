"""SAKUS gerçek güzergâhlarını atomik yerel kataloğa aktarır; sefer üretmez."""
import json
import sqlite3
import tempfile
import time
import httpx
from datetime import datetime, timezone
from pathlib import Path

from turkiye_ulasim.gtfs import SCHEMA
from .sakus_kontrol import BASE, HEADERS, catalog


def point(geometry):
    if geometry['type'] != 'Point':
        raise ValueError('SAKUS durak geometrisi Point değil')
    lon, lat = map(float, geometry['coordinates'])
    if not (25 < lon < 45 and 35 < lat < 43):
        raise ValueError('SAKUS koordinatı geçersiz')
    return lat, lon


def build(destination, lines, fetch):
    """Kaynak routeId kimliği korunur; 0 güzergâhın kendi sırasıdır, gidiş iddiası değildir."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent, prefix='.sakus-') as folder:
        staged = Path(folder) / 'catalog.sqlite3'
        db = sqlite3.connect(staged)
        try:
            db.executescript(SCHEMA)
            stops = {}
            warnings = ['Her kaynak güzergâhı ayrı hat kimliğidir (hatId:routeId); direction=0 yalnız bu güzergâhın kaynak sırasıdır, gidiş/dönüş eşlemesi değildir.',
                        'Sefer takvimi ve canlı araç/varış verisi sunulmaz.']
            for line in lines:
                body = fetch(line['id'])
                if body['lineId'] != line['id'] or body['typeValueId'] != line['busTypeId']:
                    raise ValueError('SAKUS hat kimliği/türü eşleşmedi')
                routes = body['routes']
                if not routes:
                    db.execute('INSERT INTO lines VALUES (?,?,?,?,?)',
                               (str(line['id']), line.get('lineNumber') or '', line.get('name') or '', 3, str(line['id'])))
                    warnings.append(f"{line['id']}: kaynakta güzergâh yok")
                for route in routes:
                    key = f"{line['id']}:{route['routeId']}"
                    db.execute('INSERT INTO lines VALUES (?,?,?,?,?)',
                               (key, line.get('lineNumber') or '', route.get('routeName') or line.get('name') or '', 3, str(line['id'])))
                    for stop in route['busStops']:
                        lat, lon = point(stop['busStopGeometry'])
                        sid = str(stop['id'])
                        value = (sid, stop.get('name') or '', lat, lon)
                        if sid in stops and stops[sid] != value:
                            raise ValueError(f'Çelişen SAKUS durağı: {sid}')
                        if sid not in stops:
                            db.execute('INSERT INTO stops VALUES (?,?,?,?)', value)
                            stops[sid] = value
                        seq = int(stop['order'])
                        if seq < 0 or seq != stop['order']:
                            raise ValueError('Geçersiz durak sırası')
                        db.execute('INSERT INTO line_stops VALUES (?,?,?,?)', (key, 0, seq, sid))
                    geometry = route.get('routeGeometry')
                    if not geometry:
                        continue
                    if geometry['type'] != 'MultiLineString':
                        raise ValueError('Beklenmeyen SAKUS güzergâh geometrisi')
                    segments = geometry['coordinates']
                    if any(not s for s in segments) or any(a[-1] != b[0] for a,b in zip(segments, segments[1:])):
                        warnings.append(f'{key}: kopuk geometri yayımlanmadı')
                        continue
                    for seq, coord in enumerate(c for segment in segments for c in segment):
                        lat, lon = point({'type': 'Point', 'coordinates': coord})
                        db.execute('INSERT INTO line_shapes VALUES (?,?,?,?,?)', (key, 0, seq, lat, lon))
            if not stops:
                raise ValueError('SAKUS durak verisi boş')
            now = datetime.now(timezone.utc).isoformat(timespec='seconds')
            db.executemany('INSERT INTO meta VALUES (?,?)', [
                ('calendar_end',''), ('imported_at',now), ('topology_updated_at',now),
                ('topology_source',BASE), ('warnings',json.dumps(warnings,ensure_ascii=False))])
            db.commit()
        finally:
            db.close()
        staged.replace(destination)


def update(destination, client, pause=time.sleep):
    client.headers.update(HEADERS)
    lines = catalog(client)
    def fetch(line_id):
        for attempt in range(3):
            pause(1 + attempt)
            try:
                response = client.get(f'{BASE}/route-and-busstops/{line_id}', timeout=30)
                if response.status_code in (500,502,503,504) and attempt < 2:
                    continue
                response.raise_for_status()
                return response.json()
            except httpx.TransportError:
                if attempt == 2:
                    raise
    build(destination, lines, fetch)
