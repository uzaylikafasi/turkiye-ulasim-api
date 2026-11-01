"""ATUS anonim hat formu; GTFS kodu kaynak seçenek etiketiyle eşleştirilir."""
import asyncio
import json
import math
import re
import time
from collections import OrderedDict, deque
from html.parser import HTMLParser
import httpx
from .base import LiveResult, SourceError, SourceRateLimited, SourceUnsupported
URL='https://atus.konya.bel.tr/atus/hattaki-araclar'


class Form(HTMLParser):
    def __init__(self):
        super().__init__();self.csrf=[];self.options=[];self.select=False;self.option=None
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='input' and 'csrf' in a.get('class','').split() and a.get('name') and a.get('value'):
            self.csrf.append((a['name'],a['value']))
        if tag=='select':self.select=a.get('name')=='hatIsmi'
        if tag=='option' and self.select:self.option=[a.get('value',''),'']
    def handle_data(self,data):
        if self.option is not None:self.option[1]+=data
    def handle_endtag(self,tag):
        if tag=='option' and self.option is not None:self.options.append(self.option);self.option=None
        if tag=='select':self.select=False


class Text(HTMLParser):
    def __init__(self):super().__init__();self.parts=[]
    def handle_data(self,data):self.parts.append(data)


def form_data(text,code):
    parser=Form();parser.feed(text)
    matches=[v for v,label in parser.options if label.strip().split(maxsplit=1)[:1]==[code] and v]
    if len(parser.csrf)!=1:raise SourceError('ATUS anonim formu/oturum alanı bulunamadı')
    if not matches:raise SourceUnsupported('ATUS formunda bu yerel hat kodu bulunamadı')
    if len(matches)!=1:raise SourceError('ATUS kaynak hat etiketi tekrarlı')
    return {parser.csrf[0][0]:parser.csrf[0][1],'hatIsmi':matches[0]}


def js_value(text,name):
    matches=list(re.finditer(r'\bvar\s+'+name+r'\s*=\s*',text))
    if len(matches)!=1:raise SourceError('ATUS yanıtında hat/araç alanı bulunamadı veya tekrarlı')
    try:return json.JSONDecoder().raw_decode(text[matches[0].end():])[0]
    except (ValueError,TypeError) as exc:raise SourceError('ATUS araç JSON alanı değişti') from exc


def normalize(text,line_id,source_code):
    if js_value(text,'data')!=source_code:raise SourceError('ATUS yanıt kaynak hat kodu eşleşmedi')
    title=js_value(text,'hatBilgi');body=js_value(text,'hatAraclar')
    if not isinstance(title,str) or title.split(maxsplit=1)[:1]!=[line_id] or not isinstance(body,list):
        raise SourceError('ATUS yerel hat etiketi/araç şeması eşleşmedi')
    known={};conflicts=set()
    for r in body:
        if not isinstance(r,dict) or not isinstance(r.get('aciklama'),str):raise SourceError('ATUS araç açıklaması değişti')
        parser=Text();parser.feed(r['aciklama']);description=' '.join(' '.join(parser.parts).split())
        vehicle=re.search(r'Araç\s+No\s*:\s*([0-9]+)\b',description)
        if not description.startswith(source_code+'-') or not vehicle:raise SourceError('ATUS araç hat kodu/kimliği eşleşmedi')
        try:
            lat,lon=float(r['kor']['lat']),float(r['kor']['lng'])
            if not (35<lat<43 and 25<lon<45):continue
        except (KeyError,TypeError,ValueError):continue
        try:heading=float(r.get('yon'))
        except (TypeError,ValueError):heading=None
        item={'id':vehicle[1],'line_id':line_id,'source_route_id':source_code,'direction':None,'source_direction':None,
              'latitude':lat,'longitude':lon,'heading_degrees':heading if heading is not None and math.isfinite(heading) and 0<=heading<360 else None,
              'observed_at':None,'age_seconds':None,'stale':None,'position_confidence':'single'}
        if vehicle[1] in known and known[vehicle[1]]!=item:conflicts.add(vehicle[1])
        else:known[vehicle[1]]=item
    return [r for key,r in known.items() if key not in conflicts],len(conflicts)


class KonyaLive:
    def __init__(self,client=None,clock=time.monotonic):
        self.client=client or httpx.AsyncClient(timeout=20,follow_redirects=True);self.clock=clock
        self.lock=asyncio.Lock();self.cache=OrderedDict();self.requests=deque()

    async def request(self,method,**kwargs):
        now=self.clock()
        while self.requests and now-self.requests[0]>=60:self.requests.popleft()
        if len(self.requests)>=30:raise SourceRateLimited(max(1,math.ceil(60-now+self.requests[0])),'ATUS','dakikalık')
        self.requests.append(now)
        try:
            response=await self.client.request(method,URL,**kwargs)
            if response.status_code==429:raise SourceRateLimited(60,'ATUS','dakikalık')
            response.raise_for_status();return response.text
        except httpx.HTTPError as exc:raise SourceError('ATUS kaynağı okunamadı') from exc

    async def vehicles(self,line_id,*,line):
        if line_id!=line['code']:raise SourceUnsupported('ATUS yerel hat kimliği/kodu eşleşmiyor')
        async with self.lock:
            now=self.clock()
            if line_id in self.cache:
                expires,result=self.cache[line_id]
                if expires>now:
                    self.cache.move_to_end(line_id);return LiveResult(result.data,result.warnings,result.fetched_at,True)
                del self.cache[line_id]
            form=await self.request('GET');data=form_data(form,line['code'])
            page=await self.request('POST',data=data)
            rows,conflicts=normalize(page,line_id,data['hatIsmi'])
            result=LiveResult(rows,[
                'GTFS hat kodu resmî ATUS form etiketiyle eşleştirilir; yanıtın kaynak ve yerel hat kodları ayrıca doğrulanır. Harf/sayı dönüşümü tahmin edilmez.',
                'Kaynak yon pusula açısıdır, güzergâh yönü değildir. GPS ölçüm saati yok; observed_at/age_seconds/stale null, fetched_at sorgu zamanıdır.',
                'Canlı kaynak: '+URL+'. ATUS canlı verisinin yeniden kullanım lisansı belirtilmemiştir; statik GTFS CC BY 4.0 lisansı canlı veriye uygulanmaz.',
                f'{conflicts} aynı araç için çelişkili konum kaydı yayımlanmadı.'])
            self.cache[line_id]=(self.clock()+15,result)
            while len(self.cache)>128:self.cache.popitem(last=False)
            return result
