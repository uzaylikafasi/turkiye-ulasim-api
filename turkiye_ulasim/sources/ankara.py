"""Anonim EGO Cep'te araç ve durak varışları; tarife mesajları araç sayılmaz."""
import asyncio
import math
import time
from collections import OrderedDict, deque
from datetime import datetime,timezone
from zoneinfo import ZoneInfo
import httpx
from .base import LiveResult, SourceError, SourceRateLimited

URL='https://egocptsrvand.ego.gov.tr/mblSrv14/service.asp'


def observation(value,now):
    try:
        observed=datetime.strptime(value,'%d.%m.%Y %H:%M:%S').replace(tzinfo=ZoneInfo('Europe/Istanbul'))
        age=(now-observed).total_seconds()
        if observed.year<2000 or age < -120:return None,None,None
        return observed.isoformat(),round(max(0,age)),age>300
    except (TypeError,ValueError):return None,None,None


def normalize(body,stop_id,now=None):
    now=now or datetime.now(timezone.utc)
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
        observed,age,stale=observation(r.get('konum_tarihi'),now)
        rows.append({'line_id':None,'source_line_id':str(r.get('hat_no','')),
                     'source_line_code':str(r.get('hat_no','')),'line_name':r.get('hat_ad'),
                     'vehicle_id':str(r['arac_no']),'source_direction':r.get('yon'),
                     'stops_away':None,'eta_seconds':eta,'source_remaining_time':r.get('sure'),
                     'latitude':lat,'longitude':lon,'observed_at':observed,'age_seconds':age,'stale':stale,
                     'wheelchair_accessible':None,'bike_rack':None})
    return sorted(rows,key=lambda r:r['eta_seconds'])


def number(value,maximum=None):
    if isinstance(value,bool):return None
    try:v=float(value)
    except (ValueError,TypeError):return None
    return v if math.isfinite(v) and v>=0 and (maximum is None or v<maximum) else None


def normalize_vehicles(body,line_id,now=None):
    if not isinstance(body,dict) or body.get('status')!='TRUE' or not isinstance(body.get('table'),list):
        raise SourceError('EGO araç yanıtı başarısız veya şema değişti')
    now=now or datetime.now(timezone.utc);vehicles={};ambiguous=set();invalid=0
    for r in body['table']:
        if not isinstance(r,dict):raise SourceError('EGO araç kaydı değişti')
        if not r.get('arac_no') or r['arac_no']=='-':continue
        if str(r.get('hat_no',''))!=line_id or str(r.get('hat_kod',line_id))!=line_id:
            raise SourceError('EGO araç hat kimliği eşleşmedi')
        try:
            lat,lon=float(r['lat']),float(r['lng'])
            if not (35<lat<43 and 25<lon<45):raise ValueError()
        except (KeyError,TypeError,ValueError):invalid+=1;continue
        observed,age,stale=observation(r.get('konum_tarihi'),now);vid=str(r['arac_no'])
        item={'id':vid,'line_id':line_id,'source_direction':r.get('yon'),'direction':None,
              'latitude':lat,'longitude':lon,'observed_at':observed,'age_seconds':age,'stale':stale,
              'speed_kmh':number(r.get('hiz')),'heading_degrees':number(r.get('aci'),360),
              'position_confidence':'single'}
        previous=vehicles.get(vid)
        if previous:
            dt=datetime.fromisoformat(observed) if observed else None
            old=datetime.fromisoformat(previous['observed_at']) if previous['observed_at'] else None
            if dt and (old is None or dt>old):vehicles[vid]=item;ambiguous.discard(vid)
            elif dt==old and (lat,lon)!=(previous['latitude'],previous['longitude']):ambiguous.add(vid)
        else:vehicles[vid]=item
    rows=[item for vid,item in vehicles.items() if vid not in ambiguous]
    warnings=['Tarife mesajları araç değildir; kaynağın yon kodu ortak 0/1 yönlerine eşleştirilmedi.',
              'GPS zamanı Europe/Istanbul kabul edilir; 300 saniyeden eski kayıt stale=true, güvenilir zamanı olmayan kayıt stale=null olur. Kaynak kapsamı dönen hat araçlarıyla sınırlıdır.']
    if invalid or ambiguous:warnings.append(f'{invalid} geçersiz, {len(ambiguous)} aynı zamanlı çelişkili araç kaydı yayımlanmadı.')
    return rows,warnings


class AnkaraLive:
    def __init__(self,client=None,clock=time.monotonic):
        self.client=client or httpx.AsyncClient(timeout=15)
        self.clock=clock;self.lock=asyncio.Lock();self.cache=OrderedDict();self.requests=deque()

    async def _call(self,key,params,transform,ttl):
        async with self.lock:
            now=self.clock()
            if key in self.cache:
                expires,result=self.cache[key]
                if expires>now:
                    self.cache.move_to_end(key)
                    return LiveResult(result.data,result.warnings,result.fetched_at,True)
                del self.cache[key]
            while self.requests and now-self.requests[0]>=60:self.requests.popleft()
            if len(self.requests)>=30:raise SourceRateLimited(max(1,math.ceil(60-now+self.requests[0])),'EGO','dakikalık')
            self.requests.append(now)
            try:
                r=await self.client.get(URL,params={'VER':'3.1.0','LAN':'tr',**params})
                if r.status_code==429:
                    try:retry=min(3600,max(1,int(r.headers.get('Retry-After',60))))
                    except ValueError:retry=60
                    raise SourceRateLimited(retry,'EGO','dakikalık')
                r.raise_for_status();rows,warnings=transform(r.json())
            except (httpx.HTTPError,ValueError) as exc:raise SourceError('EGO canlı kaynağı okunamadı') from exc
            result=LiveResult(rows,warnings);self.cache[key]=(self.clock()+ttl,result)
            while len(self.cache)>128:self.cache.popitem(last=False)
            return result

    async def arrivals(self,stop_id):
        return await self._call(('arrivals',stop_id),{'FNC':'Otobusler','DURAK':stop_id},
            lambda body:(normalize(body,stop_id),['Tarife/hareket saati mesajları canlı varışlara dahil edilmez; kaynak yön kodları ortak yönlerle eşleştirilmedi.',
                'GPS zamanı Europe/Istanbul kabul edilir; age_seconds/stale sorgu anındaki GPS güncelliğidir.']),20)

    async def vehicles(self,line_id,*,line):
        if line['code']!=line_id:raise SourceError('EGO yerel hat kimliği/kodu eşleşmedi')
        return await self._call(('vehicles',line_id),{'FNC':'Otobus','HAT':line_id},
            lambda body:normalize_vehicles(body,line_id),15)
