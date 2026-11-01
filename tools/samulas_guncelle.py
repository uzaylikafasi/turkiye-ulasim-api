"""SAMULAŞ herkese açık otobüs kataloğu ve hat haritaları."""
import html
import json
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from turkiye_ulasim.gtfs import SCHEMA

BASE='https://samulas.com.tr'
CATALOG=BASE+'/api/v1/lines/list_v2'


def catalog(client):
    lines=[];page=1
    while True:
        r=client.get(CATALOG,params={'page':page,'limit':100},timeout=30);r.raise_for_status();body=r.json()
        if body.get('status')!='success':raise ValueError('SAMULAŞ katalog başarısız')
        data=body['data'];paging=data['pagination']
        if paging['currentPage']!=page or not 1<=paging['totalPages']<=20:raise ValueError('SAMULAŞ sayfalama değişti')
        lines.extend(data['data'])
        if page==paging['totalPages']:break
        page+=1;time.sleep(1)
    if not lines or len(lines)!=paging['total'] or len({x['line_no'] for x in lines})!=len(lines):raise ValueError('SAMULAŞ katalog eksik/tekrarlı')
    return lines


def point(coord):
    lat,lon=map(float,coord)
    if not (35<lat<43 and 25<lon<45):raise ValueError('SAMULAŞ koordinatı geçersiz')
    return lat,lon


def parse(text,line):
    title=re.search(r'<title>(.*?)</title>',text,re.S)
    if title is None or html.unescape(title.group(1)).strip()!=line['text']+' - Samulaş':raise ValueError('SAMULAŞ hat başlığı eşleşmedi')
    scripts=re.findall(r'<script[^>]*>(.*?)</script>',text,re.S)
    scripts=[s for s in scripts if re.search(r'var routeGeoJson\s*=',s)]
    if not scripts:raise ValueError('SAMULAŞ harita verisi bulunamadı')
    # İki harita aynı veriyi gösterir; yalnız ilk kaynak kopyası içe alınır.
    s=scripts[0];m=re.search(r'var routeGeoJson\s*=\s*',s)
    geo,_=json.JSONDecoder().raw_decode(s[m.end():])
    blocks=re.split(r'var latLng\s*=\s*',s)[1:]
    stops=[]
    for b in blocks:
        coord,_=json.JSONDecoder().raw_decode(b);lat,lon=point(coord)
        m=re.search(r'title\s*=\s*"<b>([0-9]+)\s*-\s*([0-9]+)\s*-\s*(.*?)</b>"',b,re.S)
        if not m:raise ValueError('SAMULAŞ durak işareti biçimi değişti')
        stops.append((m.group(1),m.group(2)+' - '+html.unescape(m.group(3)).strip(),lat,lon))
    if not stops:raise ValueError('SAMULAŞ durak işaretleri boş')
    for marker,field in [(stops[0],'first_station'),(stops[-1],'last_station')]:
        endpoint=line.get(field)
        if endpoint and not re.match(re.escape(marker[1].split(' - ',1)[0])+r'\s*-',endpoint['station_name']):raise ValueError('SAMULAŞ başlangıç/bitiş eşleşmedi')
    return stops,geo


def build(destination,lines,fetch):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent,prefix='.samulas-') as folder:
        stage=Path(folder)/'data.sqlite3';db=sqlite3.connect(stage)
        try:
            db.executescript(SCHEMA);known={};warnings=[
                'Duraklar kaynak haritasındaki işaret sırasıyla sunulur; resmî sefer/durak-sırası dosyasıyla doğrulanmış değildir.',
                'direction=0 yayımlanan harita güzergâhıdır; ayrı gidiş/dönüş eşlemesi ve sefer takvimi sunulmaz.']
            for line in lines:
                lid=str(int(line['line_no']));stops,feature=parse(fetch(lid),line)
                db.execute('INSERT INTO lines VALUES (?,?,?,?,?)',(lid,line['text'].split(' ',1)[0],line['text'],3,str(line['route_id'])))
                for seq,stop in enumerate(stops):
                    sid,name,lat,lon=stop
                    if sid in known and known[sid]!=stop:raise ValueError('SAMULAŞ durak kimliği çelişkisi')
                    if sid not in known:db.execute('INSERT INTO stops VALUES (?,?,?,?)',stop);known[sid]=stop
                    db.execute('INSERT INTO line_stops VALUES (?,?,?,?)',(lid,0,seq,sid))
                if feature is None:
                    warnings.append(f'{lid}: kaynak geometri yok');continue
                g=feature['geometry']
                if g['type']!='MultiLineString':raise ValueError('SAMULAŞ geometri türü değişti')
                parts=g['coordinates']
                if any(not p for p in parts) or any(a[-1]!=b[0] for a,b in zip(parts,parts[1:])):
                    warnings.append(f'{lid}: kopuk geometri yayımlanmadı');continue
                for seq,coord in enumerate(p for part in parts for p in part):
                    lat,lon=point([coord[1],coord[0]])
                    db.execute('INSERT INTO line_shapes VALUES (?,?,?,?,?)',(lid,0,seq,lat,lon))
            now=datetime.now(timezone.utc).isoformat(timespec='seconds')
            db.executemany('INSERT INTO meta VALUES (?,?)',[('calendar_end',''),('imported_at',now),('topology_updated_at',now),('topology_source',BASE+'/otobusler'),('warnings',json.dumps(warnings,ensure_ascii=False))]);db.commit()
        finally:db.close()
        stage.replace(destination)


def fetch(client,lid):
    for attempt in range(3):
        time.sleep(1+attempt)
        try:
            r=client.get(BASE+'/otobus-detay/'+lid,timeout=30)
            if r.status_code in (500,502,503,504) and attempt<2:continue
            r.raise_for_status();return r.text
        except httpx.TransportError:
            if attempt==2:raise


def update(destination,client):
    build(destination,catalog(client),lambda lid:fetch(client,lid))
