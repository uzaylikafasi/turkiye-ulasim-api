"""Eksik sefer dosyası yerine gerçek Kentkart hat-durak/geometri ilişkilerini doğrular.

Sefer/takvim üretmez. Çağrılar sıralı ve aralarında en az bir saniye vardır.
Yalnız aynı route_id ve yönün path_code kaydı kabul edilir.
"""
import json
import sqlite3
import time
import httpx
from datetime import datetime, timezone

URL = 'https://service.kentkart.com/rl1/web/pathInfo'


def point(row):
    lat,lon=float(row['lat']),float(row['lng'])
    if not (35<lat<43 and 25<lon<45):
        raise ValueError('Kentkart geçersiz koordinat döndürdü')
    return lat,lon


def enrich(db_path,region,client,pause=time.sleep):
    db=sqlite3.connect(db_path)
    try:
        routes=db.execute('select id,short_name from lines order by id').fetchall()
        completed=0
        for index,(line_id,code) in enumerate(routes):
            for direction in (0,1):
                pause(1)
                for attempt in range(3):
                    try:
                        response=client.get(URL,params={'region':region,'lang':'tr','direction':direction,
                                                       'displayRouteCode':code,'resultType':'101000'},timeout=20)
                    except httpx.RequestError:
                        if attempt==2:raise
                        pause(2*(attempt+1))
                        continue
                    if response.status_code in (500,502,503,504) and attempt<2:
                        pause(2*(attempt+1))
                        continue
                    response.raise_for_status()
                    break
                body=response.json()
                if not isinstance(body,dict) or str(body.get('result',{}).get('code'))!='0':
                    raise ValueError('Kentkart işlem sonucu başarısız')
                paths=body.get('pathList')
                if not isinstance(paths,list) or any(not isinstance(p,dict) for p in paths):
                    raise ValueError('Kentkart pathList biçimi değişmiş')
                matches=[p for p in paths if str(p.get('path_code'))==f'{line_id}{direction}'
                         and p.get('displayRouteCode')==code and str(p.get('direction'))==str(direction)]
                if not matches:
                    continue
                if len(matches)!=1:
                    raise ValueError('Kentkart aynı hat/yön için birden fazla aynı kimlik verdi')
                path=matches[0]
                stops,points=path.get('busStopList'),path.get('pointList')
                if not isinstance(stops,list) or not isinstance(points,list):
                    raise ValueError('Kentkart durak/geometri listesi eksik')
                seen={}
                for row in stops:
                    seq=int(row['seq']);stop_id=str(row['stopId']);lat,lon=point(row)
                    if seq in seen:
                        if seen[seq]!=stop_id:raise ValueError('Kentkart durak sırası çakışıyor')
                        continue
                    seen[seq]=stop_id
                    db.execute('INSERT INTO stops VALUES (?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name, latitude=excluded.latitude, longitude=excluded.longitude',
                               (stop_id,row['stopName'],lat,lon))
                    db.execute('INSERT INTO line_stops VALUES (?,?,?,?)',(line_id,direction,seq,stop_id))
                seen={}
                for row in points:
                    seq=int(row['seq']);position=point(row)
                    if seq in seen:
                        if seen[seq]!=position:raise ValueError('Kentkart geometri sırası çakışıyor')
                        continue
                    seen[seq]=position
                    db.execute('INSERT INTO line_shapes VALUES (?,?,?,?,?)',(line_id,direction,seq,*position))
                completed+=bool(stops or points)
            if (index+1)%10==0:print(f'Kentkart {region}: {index+1}/{len(routes)} hat kontrol edildi',flush=True)
        if not completed:raise ValueError('Kentkart kaynağından doğrulanmış topoloji alınamadı')
        warning=f'GTFS sefer dosyaları eksik; doğrulanmış sefer takvimi sunulmaz. {completed} hat/yön ilişkisi Kentkart servisinden doğrulandı; bu işlem sefer veya canlı araç verisi üretmez.'
        db.execute("UPDATE meta SET value=? WHERE key='warnings'",(json.dumps([warning],ensure_ascii=False),))
        db.executemany('INSERT OR REPLACE INTO meta VALUES (?,?)',[
            ('topology_source',URL),('topology_updated_at',datetime.now(timezone.utc).isoformat(timespec='seconds'))])
        db.commit()
        return completed
    finally:
        db.close()
