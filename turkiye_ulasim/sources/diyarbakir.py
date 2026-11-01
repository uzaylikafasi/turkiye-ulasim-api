"""Diyarbakır belediye ASIS köprüsünün canlı araç konumları."""
import asyncio
import math
import time
from collections import OrderedDict,deque
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import httpx
from .base import LiveResult,SourceError,SourceRateLimited
URL='https://www.diyarbakir.bel.tr/api/transport/asis/live-data'
STALE_SECONDS=300


def normalize(body,line_id,code,now=None):
    if not isinstance(body,dict) or body.get('raw',{}).get('isSuccess') is not True or not isinstance(body['raw'].get('data'),list):
        raise SourceError('Diyarbakır canlı servis sonucu başarısız veya şema değişti')
    now=now or datetime.now(timezone.utc)
    vehicles={};ambiguous=set();invalid=0
    for r in body['raw']['data']:
        if not isinstance(r,dict):raise SourceError('Diyarbakır araç kaydı değişti')
        if str(r.get('routeNo'))!=line_id or str(r.get('routeCode','')).strip()!=code:
            raise SourceError('Diyarbakır canlı hat kimliği eşleşmedi')
        try:
            lat,lon=float(r['latitude']),float(r['longitude'])
            if not (35<lat<43 and 25<lon<45):raise ValueError()
            vid=str(r.get('validatorNo') or r.get('plate') or '').strip()
            if not vid:raise ValueError()
        except (KeyError,TypeError,ValueError):invalid+=1;continue
        try:
            observed=datetime.fromisoformat(r['date'])
            if observed.tzinfo is None:observed=observed.replace(tzinfo=ZoneInfo('Europe/Istanbul'))
            age=(now-observed).total_seconds()
            if age < -120:observed=None;age=None
        except (KeyError,TypeError,ValueError):observed=None;age=None
        way=r.get('routeDriction')
        speed=r.get('speed');heading=r.get('direction')
        item={'id':vid,'line_id':line_id,'source_direction':way if way in ('G','D') else None,
              'direction':{'G':0,'D':1}.get(way),'latitude':lat,'longitude':lon,
              'observed_at':observed.isoformat() if observed else None,
              'age_seconds':round(max(0,age)) if age is not None else None,
              'stale':age>STALE_SECONDS if age is not None else None,
              'speed_kmh':speed if isinstance(speed,(int,float)) and not isinstance(speed,bool) and math.isfinite(speed) and speed>=0 else None,
              'heading_degrees':heading if isinstance(heading,(int,float)) and not isinstance(heading,bool) and math.isfinite(heading) and 0<=heading<360 else None,
              'position_confidence':'single'}
        previous=vehicles.get(vid)
        if previous:
            oldtime=datetime.fromisoformat(previous['observed_at']) if previous['observed_at'] else None
            if observed and (oldtime is None or observed>oldtime):
                vehicles[vid]=item;ambiguous.discard(vid)
            elif observed==oldtime and (lat,lon)!=(previous['latitude'],previous['longitude']):ambiguous.add(vid)
        else:vehicles[vid]=item
    rows=[r for vid,r in vehicles.items() if vid not in ambiguous]
    warnings=['Saat dilimi içermeyen kaynak GPS zamanı Europe/Istanbul kabul edilir; fetched_at sorgu zamanıdır. 300 saniyeden eski GPS kaydı stale=true olarak korunur.']
    stale=sum(r['stale'] is True for r in rows);unknown=sum(r['observed_at'] is None for r in rows)
    if stale:warnings.append(f'{stale} araç konumu 300 saniyeden eski.')
    if unknown:warnings.append(f'{unknown} aracın güvenilir GPS zamanı yok; güncelliği doğrulanamadı.')
    if invalid or ambiguous:warnings.append(f'{invalid} geçersiz, {len(ambiguous)} aynı zamanlı çelişkili araç kaydı yayımlanmadı.')
    return rows,warnings


class DiyarbakirLive:
    def __init__(self,client=None,clock=time.monotonic):
        self.client=client or httpx.AsyncClient(timeout=15)
        self.clock=clock;self.lock=asyncio.Lock();self.cache=OrderedDict();self.requests=deque()
    async def vehicles(self,line_id,*,line):
        code=line.get('source_route_code') or line['code']
        key=(line_id,code)
        async with self.lock:
            now=self.clock()
            if key in self.cache:
                expires,result=self.cache[key]
                if expires>now:
                    self.cache.move_to_end(key)
                    return LiveResult(result.data,result.warnings,result.fetched_at,True)
                del self.cache[key]
            while self.requests and now-self.requests[0]>=60:self.requests.popleft()
            if len(self.requests)>=30:raise SourceRateLimited(max(1,math.ceil(60-now+self.requests[0])),'Diyarbakır','dakikalık')
            self.requests.append(now)
            try:
                r=await self.client.get(URL,params={'routeCode':code})
                if r.status_code==429:
                    try:retry=min(3600,max(1,int(r.headers.get('Retry-After',60))))
                    except ValueError:retry=60
                    raise SourceRateLimited(retry,'Diyarbakır','dakikalık')
                r.raise_for_status();data,warnings=normalize(r.json(),line_id,code)
            except (httpx.HTTPError,ValueError) as exc:raise SourceError('Diyarbakır canlı kaynağı okunamadı') from exc
            result=LiveResult(data,warnings);self.cache[key]=(self.clock()+15,result)
            while len(self.cache)>128:self.cache.popitem(last=False)
            return result
