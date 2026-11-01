"""EGO resmî HTML kataloğu ve yayımlanan durak sırası; koordinat üretmez."""
from html.parser import HTMLParser
import json
import re
import sqlite3
import tempfile
import time
from pathlib import Path
from datetime import datetime, timezone
import httpx
from turkiye_ulasim.gtfs import SCHEMA

URL = 'https://www.ego.gov.tr/HareketSaatleri'


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.bus=False; self.option=None; self.text=[]; self.lines=[]
        self.route=False; self.cell=False; self.cells=[]; self.stops=[]
    def handle_starttag(self,tag,attrs):
        a=dict(attrs)
        if tag=='select':self.bus=a.get('id')=='hat_liste_otobus'
        if tag=='option' and self.bus:self.option=a.get('value');self.text=[]
        if tag=='table':self.route='route-table' in a.get('class','').split()
        if tag=='tr' and self.route:self.cells=[]
        if tag=='td' and self.route:self.cell=True;self.text=[]
    def handle_data(self,data):
        if self.option is not None or self.cell:self.text.append(data)
    def handle_endtag(self,tag):
        if tag=='option' and self.option is not None:
            if self.option!='0':
                code=self.option
                if not re.fullmatch(r'[0-9]+(?:-[0-9]+)?',code):raise ValueError('EGO otobüs kodu değişti')
                name=''.join(self.text).strip()
                self.lines.append((code,re.sub(r'^\([^)]*\)\s*-\s*','',name)))
            self.option=None
        if tag=='select':self.bus=False
        if tag=='td' and self.cell:self.cells.append(''.join(self.text).strip());self.cell=False
        if tag=='tr' and self.route and self.cells:
            if len(self.cells)!=4:raise ValueError('EGO durak tablosu değişti')
            seq,sid,name,address=self.cells
            if not seq.isdigit() or not sid.isdigit() or not name:raise ValueError('EGO durak satırı geçersiz')
            self.stops.append((int(seq),sid,name))
        if tag=='table':self.route=False


def parse(text):
    p=Page();p.feed(text)
    match=re.search(r'<td[^>]*>Hat No</td>\s*<td[^>]*>:</td>\s*<td[^>]*>([^<]+)</td>',text)
    p.selected=match.group(1).strip() if match else None
    if not p.lines or len(set(x[0] for x in p.lines))!=len(p.lines):raise ValueError('EGO katalog boş/tekrarlı')
    if len(set(x[0] for x in p.stops))!=len(p.stops):raise ValueError('EGO durak sırası tekrarlı')
    return p


def build(destination,lines,fetch):
    destination=Path(destination);destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent,prefix='.ego-') as folder:
        staged=Path(folder)/'catalog.sqlite3';db=sqlite3.connect(staged)
        try:
            db.executescript(SCHEMA)
            names={};empty=0
            for code,name in lines:
                p=parse(fetch(code))
                if p.selected != code or (code,name) not in p.lines:raise ValueError('EGO katalog aktarım sırasında değişti')
                db.execute('INSERT INTO lines VALUES (?,?,?,?,?)',(code,code,name,3,code))
                if not p.stops:empty+=1
                for seq,sid,sname in p.stops:
                    if sid in names and names[sid]!=sname:raise ValueError(f'EGO durak adı çelişkisi: {sid}')
                    if sid not in names:
                        db.execute('INSERT INTO stops VALUES (?,?,NULL,NULL)',(sid,sname));names[sid]=sname
                    db.execute('INSERT INTO line_stops VALUES (?,?,?,?)',(code,0,seq,sid))
            if not names:raise ValueError('EGO bütün durak listeleri boş')
            now=datetime.now(timezone.utc).isoformat(timespec='seconds')
            warnings=['Kaynak durak koordinatı ve geometri vermiyor; konumlar null, yakın durak ve şekil desteklenmez.',
                      'direction=0 yayımlanan tek durak listesidir; gidiş/dönüş ayrımı doğrulanmadı.',f'{empty} hattın kaynak durak listesi boş.']
            db.executemany('INSERT INTO meta VALUES (?,?)',[('calendar_end',''),('imported_at',now),('topology_updated_at',now),('topology_source',URL),('warnings',json.dumps(warnings,ensure_ascii=False))])
            db.commit()
        finally:db.close()
        staged.replace(destination)


def request(client,code=None):
    for attempt in range(3):
        time.sleep(.5+attempt)
        try:
            r=client.get(URL,timeout=30) if code is None else client.post(URL,data={'hat_no1':code,'hat_no2':'0','hat_no3':'0'},timeout=30)
            if r.status_code in (500,502,503,504) and attempt<2:continue
            r.raise_for_status();return r.text
        except httpx.TransportError:
            if attempt==2:raise


def update(destination,client):
    lines=parse(request(client)).lines
    build(destination,lines,lambda code:request(client,code))
