"""Anonim Kentkart pathInfo araçları; bölge/hat/yön kimliği birlikte doğrulanır."""
import asyncio
import math
import time
from collections import OrderedDict,deque
import httpx
from .base import LiveResult,SourceError,SourceRateLimited,SourceUnsupported
URL='https://service.kentkart.com/rl1/web/pathInfo'
ARRIVALS_URL='https://service.kentkart.com/rl1/web/nearest/bus'


def normalize(body,line_id,code,direction):
    if (isinstance(body,dict) and isinstance(body.get('result'),dict)
        and str(body['result'].get('code'))=='3' and body['result'].get('message')=='Sonuç Bulunamadı'
        and body.get('pathList') in (None,[])):
        return None
    if not isinstance(body,dict) or not isinstance(body.get('result'),dict) or str(body['result'].get('code'))!='0' or not isinstance(body.get('pathList'),list):
        raise SourceError('Kentkart işlem sonucu başarısız veya şema değişti')
    paths=[p for p in body['pathList'] if isinstance(p,dict) and str(p.get('path_code'))==line_id+str(direction)
           and p.get('displayRouteCode')==code and str(p.get('direction'))==str(direction)]
    if len(paths)>1:raise SourceError('Kentkart hat/yön kimliği tekrarlı')
    if not paths:return None
    buses=paths[0].get('busList')
    if not isinstance(buses,list):raise SourceError('Kentkart araç listesi değişti')
    rows=[]
    for r in buses:
        if not isinstance(r,dict):raise SourceError('Kentkart araç kaydı değişti')
        try:
            lat,lon=float(r['lat']),float(r['lng']);vid=str(r['busId']).strip()
            if not vid or not (35<lat<43 and 25<lon<45):continue
        except (ValueError,TypeError,KeyError):continue
        try:heading=float(r.get('bearing'))
        except (ValueError,TypeError):heading=None
        rows.append({'id':vid,'line_id':line_id,'source_direction':str(direction),'direction':direction,
                     'latitude':lat,'longitude':lon,'observed_at':None,'age_seconds':None,'stale':None,
                     'heading_degrees':heading if heading is not None and math.isfinite(heading) and 0<=heading<360 else None,
                     'wheelchair_accessible':{'0':False,'1':True}.get(str(r.get('disabledPerson'))),
                     'bike_rack':{'0':False,'1':True}.get(str(r.get('bike'))),'position_confidence':'single'})
    return rows


def nonnegative(value):
    if value is None or isinstance(value,bool):return None
    try:number=float(value)
    except (TypeError,ValueError):return None
    return number if math.isfinite(number) and number>=0 else None


def normalize_arrivals(body,stop):
    if (not isinstance(body,dict) or not isinstance(body.get('result'),dict)
        or str(body['result'].get('code'))!='0' or not isinstance(body.get('busList'),list)
        or not isinstance(body.get('stopInfo'),dict)
        or str(body['stopInfo'].get('busStopid'))!=stop['id']):
        raise SourceError('Kentkart varış sonucu/şeması veya durak kimliği eşleşmedi')
    known={(r['id'],r['code']) for r in stop['lines']};rows=[]
    for r in body['busList']:
        if not isinstance(r,dict):raise SourceError('Kentkart varış kaydı değişti')
        # Teleferik/raylı kayıtları otobüs olarak yayımlama.
        if str(r.get('routeType'))!='3':continue
        route=r.get('routeCode');way=r.get('direction');code=r.get('displayRouteCode');vid=r.get('busId')
        if (not isinstance(route,str) or not route or str(way) not in ('0','1')
            or not isinstance(code,str) or not code or not isinstance(vid,str) or not vid.strip()
            or str(r.get('shapeId'))!=route+str(way)):
            raise SourceError('Kentkart varış hat/yön kimliği geçersiz')
        minutes=nonnegative(r.get('timeDiff'));count=nonnegative(r.get('stopDiff'))
        try:
            lat,lon=float(r['lat']),float(r['lng'])
            if not (35<lat<43 and 25<lon<45):lat=lon=None
        except (KeyError,ValueError,TypeError):lat=lon=None
        rows.append({'line_id':route if (route,code) in known else None,'source_line_id':route,
                     'source_line_code':code,'source_route_id':r['shapeId'],'line_name':r.get('displayName'),
                     'vehicle_id':vid,'source_direction':str(way),'direction':int(way),
                     'eta_seconds':round(minutes*60) if minutes is not None and math.isfinite(minutes*60) else None,
                     'stops_away':int(count) if count is not None and count.is_integer() else None,
                     'latitude':lat,'longitude':lon,'observed_at':None,'age_seconds':None,'stale':None,
                     'wheelchair_accessible':{'0':False,'1':True}.get(str(r.get('disabledPerson'))),
                     'bike_rack':{'0':False,'1':True}.get(str(r.get('bike')))})
    return sorted(rows,key=lambda r:r['eta_seconds'] if r['eta_seconds'] is not None else math.inf)


class KentkartLive:
    def __init__(self,region,client=None,clock=time.monotonic):
        self.region=region;self.client=client or httpx.AsyncClient(timeout=15);self.clock=clock
        self.lock=asyncio.Lock();self.cache=OrderedDict();self.requests=deque()
    async def vehicles(self,line_id,*,line):
        key=('vehicles',line_id,line['code'])
        async with self.lock:
            now=self.clock()
            if key in self.cache:
                expires,result=self.cache[key]
                if expires>now:
                    self.cache.move_to_end(key);return LiveResult(result.data,result.warnings,result.fetched_at,True)
                del self.cache[key]
            rows=[];missing=[]
            for direction in (0,1):
                body=await self.request(URL,{'direction':direction,'displayRouteCode':line['code'],'resultType':'010000'})
                part=normalize(body,line_id,line['code'],direction)
                if part is None:missing.append(direction)
                else:rows.extend(part)
            if len(missing)==2:raise SourceUnsupported('Kentkart kaynağında bu hat için doğrulanmış kimlik/yön bulunamadı')
            known={};conflicts=set()
            for row in rows:
                vid=row['id']
                if vid in known and known[vid]!=row:conflicts.add(vid)
                else:known[vid]=row
            warnings=['Kaynak doğrulanmış GPS ölçüm zamanı vermiyor; observed_at/age_seconds/stale null, fetched_at yalnız sorgu zamanıdır.',
                      'Statik topluluk GTFS ile canlı Kentkart servisi ayrı kaynaklardır; canlı eşleşme kaynak hat kimliği ve yönüyle doğrulanır.',
                      'Canlı kaynak: '+URL+'. Canlı verinin yeniden kullanım lisansı belirtilmemiştir; statik derlemenin CC0 lisansı canlı veriye uygulanmaz.']
            if missing:warnings.append(f'{missing} yönleri için kaynak kimliği eşleşmedi; yalnız doğrulanan yön sunulur.')
            if conflicts:warnings.append(f'{len(conflicts)} aynı araç için çelişkili yön/konum yayımlanmadı.')
            result=LiveResult([r for vid,r in known.items() if vid not in conflicts],warnings)
            self.cache[key]=(self.clock()+15,result)
            while len(self.cache)>128:self.cache.popitem(last=False)
            return result


    async def request(self,url,params):
        # Araç ve varış çağrıları aynı kilit altında aynı şehir bütçesini tüketir.
        now=self.clock()
        while self.requests and now-self.requests[0]>=60:self.requests.popleft()
        if len(self.requests)>=30:raise SourceRateLimited(max(1,math.ceil(60-now+self.requests[0])),'Kentkart','dakikalık')
        self.requests.append(now)
        try:
            response=await self.client.get(url,params={'region':self.region,'lang':'tr',**params})
            if response.status_code==429:raise SourceRateLimited(60,'Kentkart','dakikalık')
            response.raise_for_status();return response.json()
        except (httpx.HTTPError,ValueError) as exc:raise SourceError('Kentkart canlı kaynağı okunamadı') from exc

    async def arrivals_for_stop(self,stop):
        try:
            lat,lon=float(stop['latitude']),float(stop['longitude'])
            if not (35<lat<43 and 25<lon<45):raise ValueError()
        except (KeyError,TypeError,ValueError):raise SourceUnsupported('Kentkart varış sorgusu için durak koordinatı yok') from None
        key=('arrivals',stop['id'],lat,lon,tuple(sorted((r['id'],r['code']) for r in stop['lines'])))
        async with self.lock:
            now=self.clock()
            if key in self.cache:
                expires,result=self.cache[key]
                if expires>now:
                    self.cache.move_to_end(key);return LiveResult(result.data,result.warnings,result.fetched_at,True)
                del self.cache[key]
            body=await self.request(ARRIVALS_URL,{'accuracy':'0','lat':lat,'lng':lon,'busStopId':stop['id']})
            result=LiveResult(normalize_arrivals(body,stop),[
                'Tahmini varış kaynak timeDiff dakika alanından saniyeye çevrilir; stopDiff kalan durak sayısıdır. routeList tarife bilgileri canlı araç sayılmaz.',
                'GPS ölçüm zamanı bilinmiyor; observed_at/age_seconds/stale null, fetched_at yalnız sorgu zamanıdır. Yerel durak-hat ilişkisi yoksa line_id null kalır.',
                'Canlı kaynak: '+ARRIVALS_URL+'. Yeniden kullanım lisansı belirtilmemiştir; statik derleme CC0 lisansı canlı veriyi kapsamaz.'])
            self.cache[key]=(self.clock()+15,result)
            while len(self.cache)>128:self.cache.popitem(last=False)
            return result
