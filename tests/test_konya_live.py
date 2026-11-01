from pathlib import Path
import httpx,pytest
from turkiye_ulasim.sources.konya import KonyaLive,form_data,normalize
from turkiye_ulasim.sources.base import SourceError,SourceUnsupported,SourceRateLimited
PAGE=(Path(__file__).parent/'fixtures/konya/vehicles-1A.html').read_text()
FORM='<input class="csrf" name="csrf_key" value="synthetic"><select name="hatIsmi"><option value="1-0">1-A HOCAFAKIH</option><option value="1-1">1-B OTHER</option></select>'


def test_real_vehicles_html_text_identity_and_heading():
    rows,n=normalize(PAGE,'1-A','1-0');assert len(rows)==2 and not n
    assert rows[0]['id']=='322' and rows[0]['latitude']==37.837333
    assert rows[0]['heading_degrees']==241 and rows[0]['direction'] is None and rows[0]['stale'] is None


@pytest.mark.parametrize('fault',['source','title','vehicle','schema'])
def test_identity_and_schema_fail_closed(fault):
    page=PAGE
    if fault=='source':page=page.replace('var data = "1-0"','var data = "1-1"')
    if fault=='title':page=page.replace('1-A HOCAFAKIH','1-B HOCAFAKIH')
    if fault=='vehicle':page=page.replace('Araç No','Other')
    if fault=='schema':page='<html>challenge or login</html>'
    with pytest.raises(SourceError):normalize(page,'1-A','1-0')


def test_form_unique_label_and_no_guessed_letter_mapping():
    assert form_data(FORM,'1-A')['hatIsmi']=='1-0'
    with pytest.raises(SourceUnsupported):form_data(FORM,'1-C')
    with pytest.raises(SourceError):form_data(FORM.replace('</select>','<option value="other">1-A DUPLICATE</option></select>'),'1-A')
    with pytest.raises(SourceError):form_data('<html>404</html>','1-A')


@pytest.mark.asyncio
async def test_form_post_cache_and_shared_http_budget():
    calls=[]
    def handler(r):
        calls.append(r);return httpx.Response(200,text=FORM if r.method=='GET' else PAGE)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        source=KonyaLive(c,clock=lambda:0)
        a=await source.vehicles('1-A',line={'code':'1-A'});assert len(a.data)==2
        assert calls[0].method=='GET' and calls[1].method=='POST' and b'hatIsmi=1-0' in calls[1].content
        assert b'csrf_key=synthetic' in calls[1].content
        assert (await source.vehicles('1-A',line={'code':'1-A'})).cached and len(calls)==2
        source.requests.extend([0]*28)
        with pytest.raises(SourceRateLimited):await source.vehicles('1-B',line={'code':'1-B'})


def test_api_local_line_validation(gtfs_db):
    import sqlite3
    from fastapi.testclient import TestClient
    from turkiye_ulasim.main import create_app
    from turkiye_ulasim.gtfs import GtfsStore
    with sqlite3.connect(gtfs_db) as db:db.execute('insert into lines values (?,?,?,?,?)',('1-A','1-A','Konya',3,''))
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,text=FORM if r.method=='GET' else PAGE)
    def factory():return {'konya':(GtfsStore(gtfs_db),KonyaLive(httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        assert c.get('/v1/konya/lines/missing/vehicles').status_code==404 and not calls
        r=c.get('/v1/konya/lines/1-A/vehicles');assert r.status_code==200 and len(r.json()['data'])==2
        assert r.json()['meta']['live'] and c.get('/v1/konya/lines/1-A/vehicles').json()['meta']['cached']
        assert c.get('/v1/konya/stops/21050/arrivals').status_code==501
