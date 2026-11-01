"""Trabzon AKUS durak varışları; iç durak kimliği QR koduyla karıştırılmaz."""
import asyncio
import math
import time
from collections import OrderedDict,deque
import httpx
from .base import LiveResult,SourceError,SourceRateLimited,SourceUnsupported
URL='https://ulasim.trabzon.bel.tr/Web/DuragaYaklasanAraclar'


def normalize(body,stop):
    if not isinstance(body,dict) or body.get('SonucDurum') is not True or not isinstance(body.get('SonucData'),list):
        raise SourceError('Trabzon varış servisi başarısız veya şema değişti')
    rows=[];known={r['id'] for r in stop['lines']}
    for r in body['SonucData']:
        if not isinstance(r,dict) or str(r.get('DurakQrKod'))!=stop['code']:
            raise SourceError('Trabzon varış durağı eşleşmedi')
        try:
            hid,rid=int(r['HatId']),int(r['HatGuzergahId'])
            if hid<=0 or rid<=0:raise ValueError()
        except (KeyError,ValueError,TypeError):raise SourceError('Trabzon varış hat kimliği geçersiz') from None
        key=f'{hid}:{rid}';eta=r.get('VarisSuresiSn');count=r.get('KalanDurakAdet')
        eta=eta if isinstance(eta,(int,float)) and not isinstance(eta,bool) and math.isfinite(eta) and eta>=0 else None
        count=count if isinstance(count,int) and not isinstance(count,bool) and count>=0 else None
        rows.append({'line_id':key if key in known else None,'source_line_id':str(hid),
                     'source_route_id':str(rid),'source_line_code':r.get('HatKod'),'line_name':r.get('HatAd'),
                     'vehicle_id':r.get('PlakaKod'),'source_direction':r.get('YonStr'),
                     'eta_seconds':eta,'stops_away':count,'latitude':None,'longitude':None,
                     'observed_at':None,'wheelchair_accessible':None,'bike_rack':None})
    return sorted(rows,key=lambda r:r['eta_seconds'] if r['eta_seconds'] is not None else math.inf)


class TrabzonLive:
    def __init__(self,client=None,clock=time.monotonic):
        self.client=client or httpx.AsyncClient(timeout=15);self.clock=clock
        self.lock=asyncio.Lock();self.cache=OrderedDict();self.requests=deque()
    async def arrivals_for_stop(self,stop):
        code=stop.get('code')
        if not code:raise SourceUnsupported('Trabzon durak QR eşlemesi henüz güncellenmedi')
        key=(stop['id'],code)
        async with self.lock:
            now=self.clock()
            if key in self.cache:
                expires,result=self.cache[key]
                if expires>now:
                    self.cache.move_to_end(key);return LiveResult(result.data,result.warnings,result.fetched_at,True)
                del self.cache[key]
            while self.requests and now-self.requests[0]>=60:self.requests.popleft()
            if len(self.requests)>=30:raise SourceRateLimited(max(1,math.ceil(60-now+self.requests[0])),'Trabzon','dakikalık')
            self.requests.append(now)
            try:
                r=await self.client.get(URL,params={'qrDurakKod':code})
                if r.status_code==429:raise SourceRateLimited(60,'Trabzon','dakikalık')
                r.raise_for_status();rows=normalize(r.json(),stop)
            except (httpx.HTTPError,ValueError) as exc:raise SourceError('Trabzon varış kaynağı okunamadı') from exc
            result=LiveResult(rows,['Kaynak araç GPS konumu ve ölçüm zamanı vermiyor; fetched_at sorgu zamanıdır. Tahmini varış süresi kaynak tarafından hesaplanır.'])
            self.cache[key]=(self.clock()+15,result)
            while len(self.cache)>128:self.cache.popitem(last=False)
            return result


    async def vehicles(self,line_id,*,line):
        # Genel kaynağı tüm güzergâhlar paylaşır; yalnız normalleştirilmiş alanlar önbelleğe girer.
        key=('vehicles',)
        async with self.lock:
            now=self.clock();result=None
            if key in self.cache:
                expires,saved=self.cache[key]
                if expires>now:
                    self.cache.move_to_end(key);result=LiveResult(saved.data,saved.warnings,saved.fetched_at,True)
                else:del self.cache[key]
            if result is None:
                while self.requests and now-self.requests[0]>=60:self.requests.popleft()
                if len(self.requests)>=30:raise SourceRateLimited(max(1,math.ceil(60-now+self.requests[0])),'Trabzon','dakikalık')
                self.requests.append(now)
                try:
                    response=await self.client.post(VEHICLES_URL,json={})
                    if response.status_code==429:raise SourceRateLimited(60,'Trabzon','dakikalık')
                    response.raise_for_status();rows,warnings=normalize_vehicles(response.json())
                except (httpx.HTTPError,ValueError) as exc:raise SourceError('Trabzon araç kaynağı okunamadı') from exc
                result=LiveResult(rows,warnings);self.cache[key]=(self.clock()+15,result)
                while len(self.cache)>128:self.cache.popitem(last=False)
            rows=[r for r in result.data if r['line_id']==line_id]
            if any(str(r['source_line_code'])!=line['code'] for r in rows):raise SourceError('Trabzon canlı hat kodu eşleşmedi')
            return LiveResult(rows,result.warnings,result.fetched_at,result.cached)


VEHICLES_URL='https://ulasim.trabzon.bel.tr/Web/KonumGetir'


def normalize_vehicles(body,now=None):
    from datetime import datetime,timezone
    from zoneinfo import ZoneInfo
    if not isinstance(body,dict) or body.get('SonucDurum') is not True or not isinstance(body.get('SonucData'),list):
        raise SourceError('Trabzon araç servisi başarısız veya şema değişti')
    now=now or datetime.now(timezone.utc)
    latest={};ambiguous=set();invalid=0
    for r in body['SonucData']:
        if not isinstance(r,dict):raise SourceError('Trabzon araç kaydı değişti')
        try:
            hid,rid=int(r['HatId']),int(r['GuzergahId']);vid=str(r['PlakaKod']).strip()
            x,y=float(r['KonumX']),float(r['KonumY'])
            if hid<=0 or rid<=0 or not vid or not (math.isfinite(x) and math.isfinite(y) and abs(x)<21000000 and abs(y)<21000000):raise ValueError()
            if 25<x<45 and 35<y<43:
                lon,lat=x,y;source_crs='EPSG:4326'
            else:
                lon=math.degrees(x/6378137);lat=math.degrees(math.atan(math.sinh(y/6378137)));source_crs='EPSG:3857'
            if not (35<lat<43 and 25<lon<45):raise ValueError()
        except (KeyError,TypeError,ValueError):invalid+=1;continue
        try:
            observed=datetime.strptime(r['Tarih'],'%d.%m.%Y %H:%M:%S').replace(tzinfo=ZoneInfo('Europe/Istanbul'))
            age=(now-observed).total_seconds()
            if observed.year<2000 or age < -120:observed=None;age=None
        except (KeyError,TypeError,ValueError):observed=None;age=None
        way=r.get('HatYon');speed=r.get('Hiz');heading=r.get('Aci')
        item={'id':vid,'line_id':f'{hid}:{rid}','source_line_code':r.get('HatKod'),
              'source_direction':way if way in ('G','D') else None,
              'direction':0 if way=='G' else 1 if way=='D' else None,
              'latitude':lat,'longitude':lon,'source_coordinate_system':source_crs,'observed_at':observed.isoformat() if observed else None,
              'age_seconds':round(max(0,age)) if age is not None else None,'stale':age>300 if age is not None else None,
              'speed_kmh':speed if isinstance(speed,(int,float)) and not isinstance(speed,bool) and math.isfinite(speed) and speed>=0 else None,
              'heading_degrees':heading if isinstance(heading,(int,float)) and not isinstance(heading,bool) and math.isfinite(heading) and 0<=heading<360 else None,
              'position_confidence':'single'}
        previous=latest.get(vid)
        if previous:
            old=datetime.fromisoformat(previous['observed_at']) if previous['observed_at'] else None
            if observed and (old is None or observed>old):latest[vid]=item;ambiguous.discard(vid)
            elif observed==old and (item['line_id'],lat,lon)!=(previous['line_id'],previous['latitude'],previous['longitude']):ambiguous.add(vid)
        else:latest[vid]=item
    rows=[item for vid,item in latest.items() if vid not in ambiguous]
    warnings=['Genel kaynak yanıtı hatId:güzergâhId ile süzülür; kaynak yanıtı dışındaki araçların kapsamı doğrulanmaz.',
              'Canlı yanıtta CRS etiketi yoktur; gözlenen derece/metre biçimleri Türkiye için ayrık değer aralıklarıyla yorumlanır.',
              'Kaynak GPS zamanı Europe/Istanbul kabul edilir; fetched_at sorgu zamanıdır. 300 saniyeden eski konum stale=true, güvenilir zamanı olmayan konum stale=null olur.']
    if invalid or ambiguous:warnings.append(f'{invalid} geçersiz, {len(ambiguous)} aynı zamanlı çelişkili araç kaydı yayımlanmadı.')
    return rows,warnings
