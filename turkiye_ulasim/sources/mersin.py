"""Mersin resmî portalının tam hat/yön koduyla sorgulanan canlı araçları."""
import asyncio
import hashlib
import math
import time
from collections import OrderedDict, deque
import httpx
from .base import LiveResult, SourceError, SourceRateLimited, SourceUnsupported
URL='https://ulasim.mersin.bel.tr/ajax/bilgi.php'


def value(row,key,optional=False):
    field=row.get(key)
    if field is None and optional:return None
    if not isinstance(field,dict) or set(field)!={'0'} or not isinstance(field['0'],str):
        raise SourceError('Mersin araç alanı şeması değişti')
    return field['0']


def normalize(body,line_id):
    if not isinstance(body,list):
        raise SourceError('Mersin kaynak yanıtında araç yokluğu ve servis hatası ayırt edilemiyor')
    known={};conflicts=set()
    for row in body:
        if not isinstance(row,dict):raise SourceError('Mersin araç kaydı değişti')
        vehicle=value(row,'arac_no').strip()
        if not vehicle:raise SourceError('Mersin araç kimliği eksik')
        lat_text,lon_text=value(row,'enlem'),value(row,'boylam')
        try:
            lat,lon=float(lat_text),float(lon_text)
            if not (35<lat<43 and 25<lon<45):continue
        except ValueError:continue
        # Kaynak cihaz adresini yayımlamadan kararlı, şehre bağlı araç kimliği.
        key=hashlib.sha256(('mersin:'+vehicle).encode()).hexdigest()[:20]
        item={'id':key,'line_id':line_id,'source_route_id':line_id,
              'source_direction':line_id.rsplit('-',1)[1],'direction':None,
              'latitude':lat,'longitude':lon,'observed_at':None,'age_seconds':None,'stale':None,
              'wheelchair_accessible':{'true':True,'false':False}.get(value(row,'engelli_uyumu',True)),
              'bike_rack':{'true':True,'false':False}.get(value(row,'bisiklet_aparati',True)),
              'position_confidence':'single'}
        if key in known and known[key]!=item:conflicts.add(key)
        else:known[key]=item
    return [r for key,r in known.items() if key not in conflicts],len(conflicts)


class MersinLive:
    def __init__(self,client=None,clock=time.monotonic):
        self.client=client or httpx.AsyncClient(timeout=15);self.clock=clock
        self.lock=asyncio.Lock();self.cache=OrderedDict();self.requests=deque()

    async def vehicles(self,line_id,*,line):
        if line.get('source_route_code')!=line_id or not line_id.endswith(('-G','-D')) or line_id[:-2]!=line['code']:
            raise SourceUnsupported('Mersin tam kaynak hat/yön eşlemesi eksik')
        async with self.lock:
            now=self.clock()
            if line_id in self.cache:
                expires,result=self.cache[line_id]
                if expires>now:
                    self.cache.move_to_end(line_id);return LiveResult(result.data,result.warnings,result.fetched_at,True)
                del self.cache[line_id]
            while self.requests and now-self.requests[0]>=60:self.requests.popleft()
            if len(self.requests)>=30:raise SourceRateLimited(max(1,math.ceil(60-now+self.requests[0])),'Mersin','dakikalık')
            self.requests.append(now)
            try:
                response=await self.client.post(URL,data={'hatno':line_id,'tipi':'hattakiaraclar'})
                if response.status_code==429:raise SourceRateLimited(60,'Mersin','dakikalık')
                response.raise_for_status();rows,conflicts=normalize(response.json(),line_id)
            except (httpx.HTTPError,ValueError) as exc:raise SourceError('Mersin araç kaynağı okunamadı') from exc
            result=LiveResult(rows,[
                'Kaynak hat/yön kimliğini yanıtta tekrarlamaz; eşleme yerelde doğrulanmış tam hatno sorgusuna dayanır. direction null, source_direction özgün G/D değeridir.',
                'Kaynak GPS ölçüm zamanı vermiyor; sefer_saat ölçüm zamanı değildir. observed_at/age_seconds/stale null, fetched_at sorgu zamanıdır.',
                'Araç kimliği kaynak cihaz adresinin şehre bağlı SHA-256 özetinin ilk 20 karakteridir; plaka/cihaz adresi yayımlanmaz. Kaynak yeniden kullanım lisansı belirtilmemiştir.',
                f'{conflicts} aynı araç için çelişkili konum kaydı yayımlanmadı.'])
            self.cache[line_id]=(self.clock()+15,result)
            while len(self.cache)>128:self.cache.popitem(last=False)
            return result
