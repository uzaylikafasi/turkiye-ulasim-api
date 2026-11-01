import json
import sqlite3
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tools.samulas_guncelle import parse,build,catalog
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
import httpx
P=Path(__file__).parent/'fixtures/samulas'
LINE=json.loads((P/'catalog.json').read_text());HTML=(P/'390.html').read_text()


def test_real_markers_and_api(tmp_path):
    stops,geo=parse(HTML,LINE)
    assert stops[0][1].startswith('10052 - ') and stops[-1][1].startswith('10031 - ')
    dest=tmp_path/'db';build(dest,[LINE],lambda _:HTML)
    with TestClient(create_app(lambda:{'samsun':(GtfsStore(dest),None)})) as c:
        assert c.get('/v1/samsun/lines/390').status_code==200
        assert len(c.get('/v1/samsun/lines/390/stops').json()['data'])==2
        assert c.get('/v1/samsun/lines/390/shape').status_code==200
        assert c.get('/v1/samsun/stops/nearby?latitude=41.294762&longitude=36.333906').json()['data']
        assert c.get('/v1/samsun/lines/390/vehicles').status_code==501


@pytest.mark.parametrize('bad',[
 HTML.replace('<title>','<title>WRONG '),
 HTML.replace('[41.294762, 36.333906]','[0, 0]'),
 HTML.replace('9542 - 10052','9542 - 99999'),
 HTML.replace('var routeGeoJson','var changed'),
])
def test_schema_or_identity_failure_preserves_old_database(tmp_path,bad):
    dest=tmp_path/'db';dest.write_bytes(b'previous')
    with pytest.raises((ValueError,KeyError,sqlite3.Error)):build(dest,[LINE],lambda _:bad)
    assert dest.read_bytes()==b'previous'


def test_pagination_requires_complete_catalog():
    body={'status':'success','data':{'data':[LINE],'pagination':{'currentPage':1,'totalPages':1,'total':2}}}
    with httpx.Client(transport=httpx.MockTransport(lambda _:httpx.Response(200,json=body))) as c:
        with pytest.raises(ValueError,match='eksik'):catalog(c)


def test_daily_updater_uses_samulas(monkeypatch,tmp_path):
    from tools import gtfs_guncelle,samulas_guncelle
    monkeypatch.setattr(gtfs_guncelle,'DATA_DIR',tmp_path)
    monkeypatch.setattr(samulas_guncelle,'update',lambda dest,client:build(dest,[LINE],lambda _:HTML))
    monkeypatch.setattr(gtfs_guncelle,'download',lambda *a:pytest.fail('ZIP download'))
    gtfs_guncelle.update('samsun')
    assert (tmp_path/'samsun.sqlite3').exists()


def test_reused_display_stop_number_does_not_merge_internal_ids(tmp_path):
    line=dict(LINE,last_station=dict(LINE['last_station'],station_name='10052 - OTHER'))
    text=HTML.replace('10031 - DEFTERDARLIK','10052 - OTHER')
    dest=tmp_path/'db';build(dest,[line],lambda _:text)
    s=GtfsStore(dest)
    assert len(s.line_stops('390',0))==2
    assert s.stop('9542')['latitude']!=s.stop('9752')['latitude']
    s.db.close()
