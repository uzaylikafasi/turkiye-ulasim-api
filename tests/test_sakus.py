import copy
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tools.sakus_guncelle import build
from tools.sakus_kontrol import catalog
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
import httpx

BODY = json.loads((Path(__file__).parent/'fixtures/sakus/line2.json').read_text())
LINES = [{'id':2,'busTypeId':6907,'lineNumber':'1','name':'SAKARYAPARK'}]


def test_catalog_excludes_rail_even_when_bus_query_returns_it():
    rows = LINES + [dict(LINES[0], id=51, busTypeId=6905)]
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=rows))) as c:
        assert catalog(c) == LINES


def test_actual_routes_keep_distinct_ids_and_api_capabilities(tmp_path):
    dest=tmp_path/'data.sqlite3'
    build(dest,LINES,lambda _:BODY)
    with TestClient(create_app(lambda:{'sakarya':(GtfsStore(dest),None)})) as c:
        city=next(x for x in c.get('/v1/cities').json()['data'] if x['id']=='sakarya')
        assert city['available'] and not city['gtfs']
        assert city['source_kind']=='official_service'
        assert {x['id'] for x in c.get('/v1/sakarya/lines').json()['data']}=={'2:157','2:158'}
        assert len(c.get('/v1/sakarya/lines/2:157/stops').json()['data'])==2
        assert c.get('/v1/sakarya/lines/2:158/shape').status_code==200
        assert c.get('/v1/sakarya/lines/2:157/vehicles').status_code==501


@pytest.mark.parametrize('fault',['identity','coordinate','sequence','conflict','network'])
def test_failed_import_preserves_previous_database(tmp_path,fault):
    dest=tmp_path/'data.sqlite3';dest.write_bytes(b'previous')
    body=copy.deepcopy(BODY)
    if fault=='identity':body['lineId']=999
    if fault=='coordinate':body['routes'][0]['busStops'][0]['busStopGeometry']['coordinates']=[0,0]
    if fault=='sequence':body['routes'][0]['busStops'][1]['order']=body['routes'][0]['busStops'][0]['order']
    if fault=='conflict':body['routes'][1]['busStops'][0]['id']=body['routes'][0]['busStops'][0]['id']
    def fetch(_):
        if fault=='network':raise httpx.ReadTimeout('timeout')
        return body
    with pytest.raises(Exception):build(dest,LINES,fetch)
    assert dest.read_bytes()==b'previous'
    assert not list(tmp_path.glob('.sakus-*'))


def test_disconnected_geometry_is_not_joined(tmp_path):
    body=copy.deepcopy(BODY)
    body['routes'][0]['routeGeometry']['coordinates'].append([[31,41],[31.1,41.1]])
    dest=tmp_path/'data.sqlite3';build(dest,LINES,lambda _:body)
    s=GtfsStore(dest)
    assert s.line_stops('2:157',0)
    assert s.line_shape('2:157',0)==[]
    assert any('kopuk' in w for w in s.warnings())
    s.db.close()


def test_daily_updater_uses_service_without_zip(monkeypatch,tmp_path):
    from tools import gtfs_guncelle
    from tools import sakus_guncelle
    monkeypatch.setattr(gtfs_guncelle,'DATA_DIR',tmp_path)
    calls=[]
    def update(dest,client):
        calls.append(dest)
        build(dest,LINES,lambda _:BODY)
    monkeypatch.setattr(sakus_guncelle,'update',update)
    monkeypatch.setattr(gtfs_guncelle,'download',lambda *a:pytest.fail('ZIP download'))
    gtfs_guncelle.update('sakarya')
    assert calls==[tmp_path/'sakarya.sqlite3']
    assert calls[0].is_file()


def test_null_source_names_remain_searchable(tmp_path):
    lines=[dict(LINES[0],lineNumber=None,name=None)]
    body=copy.deepcopy(BODY);body['routes'][0]['routeName']=None
    dest=tmp_path/'data.sqlite3';build(dest,lines,lambda _:body)
    s=GtfsStore(dest)
    assert len(s.lines())==2 and s.lines()[0]['code']==''
    s.db.close()
