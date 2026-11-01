"""Trabzon resmî AKUS GeoJSON kaynaklarını atomik kataloğa aktarır."""
import html
import json
import math
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from turkiye_ulasim.gtfs import SCHEMA
BASE='https://ulasim.trabzon.bel.tr'


def catalog(text):
    matches=re.findall(r'<a href="/Web/Mobil\?hatIdler=([0-9]+)"\s+class="tbb-hat-link">\s*<span[^>]*data-hat-kod="([^"]+)">.*?</span>\s*<span class="tbb-hat-name">(.*?)</span>',text,re.S)
    lines=[(int(i),html.unescape(code).strip(),html.unescape(name).strip()) for i,code,name in matches]
    if not lines or len({r[0] for r in lines})!=len(lines):raise ValueError('Trabzon katalog boş/tekrarlı')
    return lines


def features(body):
    if not isinstance(body,dict) or body.get('type')!='FeatureCollection' or not isinstance(body.get('features'),list):raise ValueError('Trabzon GeoJSON koleksiyonu değişti')
    return body['features']


def point(geometry,coord):
    if geometry.get('crs',{}).get('properties',{}).get('name')!='EPSG:3857':raise ValueError('Trabzon koordinat sistemi değişti')
    x,y=map(float,coord)
    if not (math.isfinite(x) and math.isfinite(y) and abs(x)<21000000 and abs(y)<21000000):raise ValueError('Trabzon koordinatı geçersiz')
    lon=math.degrees(x/6378137);lat=math.degrees(math.atan(math.sinh(y/6378137)))
    if not (35<lat<43 and 25<lon<45):raise ValueError('Trabzon koordinatı Türkiye dışında')
    return lat,lon


def identity(props,line):
    if props['hat_id']!=line[0] or str(props['hat_kod'])!=line[1]:raise ValueError('Trabzon hat kimliği eşleşmedi')
    if props['yon_str'] not in ('G','D') or str(props['yon'])!={'G':'1','D':'2'}[props['yon_str']]:raise ValueError('Trabzon yön alanları çelişkili')


def build(destination,lines,fetch):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent,prefix='.trabzon-') as folder:
        stage=Path(folder)/'data.sqlite3';db=sqlite3.connect(stage)
        try:
            db.executescript(SCHEMA);known={};warnings=['Her hatId:güzergâhId ayrı kayıttır; direction=0 bu kaynak güzergâhının kendi sırasını ifade eder. Sefer takvimi ve canlı veri sunulmaz.']
            for line in lines:
                route_features=features(fetch(line[0],'GetHatGeoJson'));stop_features=features(fetch(line[0],'GetHatDurakGeoJson'));routes={}
                for f in route_features:
                    p=f['properties'];identity(p,line);rid=int(p['id']);key=f'{line[0]}:{rid}'
                    if rid in routes:raise ValueError('Trabzon güzergâh kimliği tekrarlı')
                    routes[rid]=p
                    db.execute('INSERT INTO lines VALUES (?,?,?,?,?)',(key,line[1],line[2]+' / '+p['ad'],3,str(line[0])))
                    g=f['geometry']
                    if g['type']!='LineString':raise ValueError('Trabzon geometri türü değişti')
                    for seq,coord in enumerate(g['coordinates']):
                        lat,lon=point(g,coord);db.execute('INSERT INTO line_shapes VALUES (?,?,?,?,?)',(key,0,seq,lat,lon))
                if not routes:
                    db.execute('INSERT INTO lines VALUES (?,?,?,?,?)',(str(line[0]),line[1],line[2],3,str(line[0])))
                    warnings.append(f'{line[0]}: kaynakta güzergâh yok')
                for f in stop_features:
                    p=f['properties'];identity(p,line);rid=int(p['hat_guzergah_id'])
                    if rid not in routes or p['yon_str']!=routes[rid]['yon_str']:raise ValueError('Trabzon durak güzergâhı eşleşmedi')
                    g=f['geometry']
                    if g['type']!='Point':raise ValueError('Trabzon durak geometrisi değişti')
                    lat,lon=point(g,g['coordinates']);sid=str(int(p['durak_id']));stop=(sid,p['ad'],lat,lon)
                    if sid in known and known[sid]!=stop:raise ValueError(f'Trabzon durak kimliği çelişkisi: {sid}')
                    if sid not in known:db.execute('INSERT INTO stops VALUES (?,?,?,?)',stop);known[sid]=stop
                    seq=p['sira']
                    if not isinstance(seq,int) or seq<0:raise ValueError('Trabzon durak sırası geçersiz')
                    db.execute('INSERT INTO line_stops VALUES (?,?,?,?)',(f'{line[0]}:{rid}',0,seq,sid))
            if not known:raise ValueError('Trabzon duraklar boş')
            now=datetime.now(timezone.utc).isoformat(timespec='seconds')
            db.executemany('INSERT INTO meta VALUES (?,?)',[('calendar_end',''),('imported_at',now),('topology_updated_at',now),('topology_source',BASE),('warnings',json.dumps(warnings,ensure_ascii=False))]);db.commit()
        finally:db.close()
        stage.replace(destination)


def request(client,name,lid=None):
    for attempt in range(3):
        time.sleep(.5+attempt)
        try:
            r=client.get(BASE+('/Web/'+name if lid is not None else '/'),params={'hatIdler':lid} if lid is not None else {},timeout=30)
            if r.status_code in (500,502,503,504) and attempt<2:continue
            r.raise_for_status();return r.json() if lid is not None else r.text
        except httpx.TransportError:
            if attempt==2:raise


def update(destination,client):
    build(destination,catalog(request(client,'')),lambda lid,name:request(client,name,lid))
