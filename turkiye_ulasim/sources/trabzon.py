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
