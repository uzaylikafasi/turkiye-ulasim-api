"""Diyarbakır belediye portalının anonim ASIS köprüsü; kaynak kimliği/yönü korunur."""
import json
import re
import sqlite3
import tempfile
import time
from pathlib import Path
from datetime import datetime,timezone
import httpx
from turkiye_ulasim.gtfs import SCHEMA
BASE='https://www.diyarbakir.bel.tr'
API=BASE+'/api/transport/asis/'
DIRECTIONS={'Gidiş':(0,'G'),'Dönüş':(1,'D')}


def bootstrap(text):
    chunks=[]
    for m in re.finditer(r'self\.__next_f\.push\(',text):
        row,_=json.JSONDecoder().raw_decode(text[m.end():])
        if len(row)>1 and isinstance(row[1],str):chunks.append(row[1])
    payload=''.join(chunks);values=[]
    for key in ['initialLines','initialStations']:
        m=re.search('"'+key+'":',payload)
        if not m:raise ValueError('Diyarbakır başlangıç verisi bulunamadı')
        v,_=json.JSONDecoder().raw_decode(payload[m.end():].lstrip())
        if not isinstance(v,list) or not v:raise ValueError('Diyarbakır başlangıç listesi boş')
        values.append(v)
    lines,stations=values
    if len({x['raw']['lineNo'] for x in lines})!=len(lines) or len({x['stationId'] for x in stations})!=len(stations):raise ValueError('Diyarbakır kimlikleri tekrarlı')
    return lines,stations


def data(body,allow_missing_coordinates=False):
    if (allow_missing_coordinates and isinstance(body,dict) and body.get('items')==[]
            and body.get('raw',{}).get('isSuccess') is False
            and body['raw'].get('data') is None
            and body['raw'].get('message')=='Response Model is Empty. This LineCode not have Coordinates...'):
        return []
    if not isinstance(body,dict) or body.get('raw',{}).get('isSuccess') is not True or not isinstance(body['raw'].get('data'),list):raise ValueError('Diyarbakır servis sonucu başarısız')
    return body['raw']['data']


def position(lat,lon):
    if lat is None and lon is None:return None,None
    lat,lon=float(lat),float(lon)
    if not (35<lat<43 and 25<lon<45):raise ValueError('Diyarbakır durak koordinatı geçersiz')
    return lat,lon


def sequence(n):
    if not isinstance(n,int) or isinstance(n,bool) or n<0:raise ValueError('Diyarbakır sıra alanı geçersiz')
    return n


def build(destination,lines,stations,fetch):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent,prefix='.diyarbakir-') as folder:
        stage=Path(folder)/'data.sqlite3';db=sqlite3.connect(stage)
        try:
            db.executescript(SCHEMA);known=set();unknown_positions=0
            for s in stations:
                sid=str(int(s['stationId']));lat,lon=position(s['latitude'],s['longitude'])
                if lat is None:unknown_positions+=1
                db.execute('INSERT INTO stops VALUES (?,?,?,?)',(sid,s['name'],lat,lon));known.add(sid)
            for line in lines:
                code=line['routeCode'];lid=str(int(line['raw']['lineNo']))
                if code!=line['lineCode'] or code!=line['raw']['lineCode'].strip():raise ValueError('Diyarbakır katalog kimliği çelişkili')
                db.execute('INSERT INTO lines VALUES (?,?,?,?,?)',(lid,code,line['name'],3,code))
                for row in data(fetch(code,'line-directions')):
                    if row['lineCode'].strip()!=code or str(row['lineNo'])!=lid:raise ValueError('Diyarbakır hat kimliği eşleşmedi')
                    if row['direction'] not in DIRECTIONS:raise ValueError('Diyarbakır yön alanı değişti')
                    direction,_=DIRECTIONS[row['direction']];sid=str(int(row['durakId']))
                    if sid not in known:raise ValueError(f'Diyarbakır durak katalogda yok: {sid}')
                    db.execute('INSERT INTO line_stops VALUES (?,?,?,?)',(lid,direction,sequence(row['orderId']),sid))
                for direction,way in [(0,'G'),(1,'D')]:
                    for row in data(fetch(code,'route-coordinate',way),allow_missing_coordinates=True):
                        if row['routeCode'].strip()!=code or row['routeDirection']!=way:raise ValueError('Diyarbakır geometri hat/yön eşleşmedi')
                        lat,lon=position(row['latitude'],row['longitude'])
                        if lat is None:raise ValueError('Diyarbakır geometri koordinatı boş')
                        db.execute('INSERT INTO line_shapes VALUES (?,?,?,?,?)',(lid,direction,sequence(row['seqNbr']),lat,lon))
            # Ortak durak envanterinde yalnız bu otobüslerin kullandığı duraklar.
            db.execute('DELETE FROM stops WHERE id NOT IN (SELECT stop_id FROM line_stops)')
            if not db.execute('SELECT 1 FROM line_stops LIMIT 1').fetchone():raise ValueError('Diyarbakır bütün durak listeleri boş')
            now=datetime.now(timezone.utc).isoformat(timespec='seconds');warnings=['Resmî belediye portalındaki ASIS köprüsü kullanılır; sefer takvimi veya canlı veri sunulmaz.',f'Kaynak genel durak kataloğunda {unknown_positions} kaydın koordinatı yoktur; kullanılanlar null korunur ve yakın durak sonucuna girmez.']
            db.executemany('INSERT INTO meta VALUES (?,?)',[('calendar_end',''),('imported_at',now),('topology_updated_at',now),('topology_source',API),('warnings',json.dumps(warnings,ensure_ascii=False))]);db.commit()
        finally:db.close()
        stage.replace(destination)


def request(client,path,params=None):
    for attempt in range(3):
        time.sleep(.5+attempt)
        try:
            r=client.get(BASE+'/ulasim/canli' if path=='bootstrap' else API+path,params=params,timeout=30)
            if r.status_code in (500,502,503,504) and attempt<2:continue
            r.raise_for_status();return r.text if path=='bootstrap' else r.json()
        except httpx.TransportError:
            if attempt==2:raise


def fetch(client,code,typ,way=None):
    params={'lineCode':code} if typ=='line-directions' else {'routeCode':code,'routeDirection':way}
    return request(client,typ,params)


def update(destination,client):
    lines,stations=bootstrap(request(client,'bootstrap'))
    build(destination,lines,stations,lambda code,typ,way=None:fetch(client,code,typ,way))
