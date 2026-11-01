"""Anonim EGO Cep'te durak varışları; tarife mesajları canlı araç sayılmaz."""
import asyncio
import math
import time
from collections import OrderedDict, deque
from datetime import datetime
from zoneinfo import ZoneInfo
import httpx
from .base import LiveResult, SourceError, SourceRateLimited

URL='https://egocptsrvand.ego.gov.tr/mblSrv14/service.asp'


def normalize(body,stop_id):
    if not isinstance(body,dict) or body.get('status')!='TRUE' or not isinstance(body.get('table'),list):
        raise SourceError('EGO canlı yanıt biçimi değişti veya işlem başarısız')
    rows=[];seen=set()
    for r in body['table']:
        if not isinstance(r,dict):raise SourceError('EGO varış kaydı geçersiz')
        if not r.get('arac_no') or r['arac_no']=='-':continue
        if str(r.get('secili_durak_no'))!=stop_id:raise SourceError('EGO seçili durak kimliği eşleşmedi')
        try:
            lat,lon=float(r['lat']),float(r['lng']);eta=float(r['saniye'])
            if not (35<lat<43 and 25<lon<45 and math.isfinite(eta) and 0<=eta<999999):continue
        except (KeyError,TypeError,ValueError):continue
        key=(str(r['arac_no']),str(r.get('hat_no','')))
        if key in seen:continue
        seen.add(key)
        try:observed=datetime.strptime(r['konum_tarihi'],'%d.%m.%Y %H:%M:%S').replace(tzinfo=ZoneInfo('Europe/Istanbul')).isoformat()
        except (KeyError,ValueError,TypeError):observed=None
        rows.append({'line_id':None,'source_line_id':str(r.get('hat_no','')),
                     'source_line_code':str(r.get('hat_no','')),'line_name':r.get('hat_ad'),
                     'vehicle_id':str(r['arac_no']),'source_direction':r.get('yon'),
                     'stops_away':None,'eta_seconds':eta,'source_remaining_time':r.get('sure'),
                     'latitude':lat,'longitude':lon,'observed_at':observed,
                     'wheelchair_accessible':None,'bike_rack':None})
    return sorted(rows,key=lambda r:r['eta_seconds'])


class AnkaraLive:
    def __init__(self,client=None,clock=time.monotonic):
        self.client=client or httpx.AsyncClient(timeout=15)
        self.clock=clock;self.lock=asyncio.Lock();self.cache=OrderedDict();self.requests=deque()
    async def arrivals(self,stop_id):
        async with self.lock:
            now=self.clock()
            if stop_id in self.cache:
                expires,result=self.cache[stop_id]
                if expires>now:
                    self.cache.move_to_end(stop_id)
                    return LiveResult(result.data,result.warnings,result.fetched_at,True)
                del self.cache[stop_id]
            while self.requests and now-self.requests[0]>=60:self.requests.popleft()
            if len(self.requests)>=30:raise SourceRateLimited(max(1,math.ceil(60-now+self.requests[0])),'EGO','dakikalık')
            self.requests.append(now)
            try:
                r=await self.client.get(URL,params={'FNC':'Otobusler','VER':'3.1.0','LAN':'tr','DURAK':stop_id})
                if r.status_code==429:raise SourceRateLimited(60,'EGO','dakikalık')
                r.raise_for_status();rows=normalize(r.json(),stop_id)
            except (httpx.HTTPError,ValueError) as exc:raise SourceError('EGO canlı kaynağı okunamadı') from exc
            result=LiveResult(rows,['Tarife/hareket saati mesajları canlı varışlara dahil edilmez; kaynak yön kodları ortak yönlerle eşleştirilmedi.'])
            self.cache[stop_id]=(self.clock()+20,result)
            while len(self.cache)>128:self.cache.popitem(last=False)
            return result
