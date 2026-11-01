"""Mersin resmî ulaşım portalının anonim hat/durak/geometri servisi."""
import json
import re
import sqlite3
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx
from turkiye_ulasim.gtfs import SCHEMA
URL='https://ulasim.mersin.bel.tr/ajax/bilgi.php'


def value(row,key):
    v=row[key]
    if not isinstance(v,dict) or set(v)!={'0'} or not isinstance(v['0'],str):raise ValueError('Mersin alan biçimi değişti')
    return v['0'].strip()


def rows(body):
    if body==0:return []
    if not isinstance(body,list) or any(not isinstance(x,dict) for x in body):raise ValueError('Mersin liste yanıtı değişti')
    return body


def catalog(body):
    lines=[];seen=set()
    for r in rows(body):
        code,way=value(r,'hat_no'),value(r,'hat_yon');lid=code+'-'+way
        if not re.fullmatch(r'[0-9A-Z]+',code) or way not in ('G','D') or lid in seen:raise ValueError('Mersin hat kimliği geçersiz/tekrarlı')
        seen.add(lid);lines.append((lid,code,value(r,'hat_adi')))
    if not lines:raise ValueError('Mersin katalog boş')
    return lines


def point(row):
    lat,lon=float(value(row,'enlem')),float(value(row,'boylam'))
    if not (35<lat<43 and 25<lon<45):raise ValueError('Mersin koordinatı geçersiz')
    return lat,lon


def build(destination,lines,fetch):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent,prefix='.mersin-') as folder:
        stage=Path(folder)/'data.sqlite3';db=sqlite3.connect(stage)
        try:
            db.executescript(SCHEMA);known={};warnings=[
                'Katalogdaki hat adları durak listesinin başlangıç/bitişiyle tam örtüşmeyebilir; kaynak adları değiştirilmeden korunur.',
                'Duraklar kaynak yanıtı sırasındadır; sefer dosyasıyla doğrulanmış değildir. Yanıt hat kimliğini tekrar etmez; eşleşme katalogdaki hat/yön sorgu parametresiyledir.',
                'G/D kaynak kimliğinde korunur; direction=0 bu statik kaydın kendi sırasıdır. Statik aktarım canlı veri veya tarife içermez; canlı araçlar ayrı bağlayıcıdan sunulur.']
            for lid,code,name in lines:
                db.execute('INSERT INTO lines VALUES (?,?,?,?,?)',(lid,code,name,3,lid))
                for seq,r in enumerate(rows(fetch(lid,'hatdurak'))):
                    sid=value(r,'durak_no');lat,lon=point(r);stop=(sid,value(r,'durak_adi'),lat,lon)
                    if not sid.isdigit():raise ValueError('Mersin durak kimliği geçersiz')
                    if sid in known and known[sid]!=stop:raise ValueError(f'Mersin durak kimliği çelişkisi: {sid}')
                    if sid not in known:db.execute('INSERT INTO stops VALUES (?,?,?,?)',stop);known[sid]=stop
                    db.execute('INSERT INTO line_stops VALUES (?,?,?,?)',(lid,0,seq,sid))
                for seq,r in enumerate(rows(fetch(lid,'hatguzergah'))):
                    lat,lon=point(r);db.execute('INSERT INTO line_shapes VALUES (?,?,?,?,?)',(lid,0,seq,lat,lon))
            if not known:raise ValueError('Mersin duraklar boş')
            now=datetime.now(timezone.utc).isoformat(timespec='seconds')
            db.executemany('INSERT INTO meta VALUES (?,?)',[('calendar_end',''),('imported_at',now),('topology_updated_at',now),('topology_source',URL),('warnings',json.dumps(warnings,ensure_ascii=False))]);db.commit()
        finally:db.close()
        stage.replace(destination)


def request(client,typ,lid=None):
    data={'tipi':typ,'hatno':lid} if lid is not None else {'tipi':'hatbilgisi','aranan':'TUM'}
    for attempt in range(3):
        time.sleep(.5+attempt)
        try:
            r=client.post(URL,data=data,timeout=30)
            if r.status_code in (500,502,503,504) and attempt<2:continue
            r.raise_for_status();return r.json()
        except httpx.TransportError:
            if attempt==2:raise


def update(destination,client):
    build(destination,catalog(request(client,'hatbilgisi')),lambda lid,typ:request(client,typ,lid))
