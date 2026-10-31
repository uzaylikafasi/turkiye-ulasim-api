import json
from pathlib import Path
import httpx
import pytest
from turkiye_ulasim.gtfs import build,GtfsStore
from tools.kentkart_topology import enrich
from test_gtfs_multicity import write_feed


def catalog(tmp_path):
    archive,db=tmp_path/'catalog.zip',tmp_path/'catalog.sqlite3'
    write_feed(archive,{'routes.txt':[['route_id','route_short_name','route_long_name','route_type'],['10010','1-A','Bus','3']],
                       'stops.txt':[['stop_id','stop_name','stop_lat','stop_lon'],['1','Stop','39.71','37.02']]})
    build(archive,db,allow_partial=True)
    return db


def payload(direction):
    return json.loads((Path(__file__).parent/f'fixtures/kentkart/sivas-{direction}.json').read_text())


def test_real_stop_order_and_shape_are_imported_without_trips(tmp_path):
    db=catalog(tmp_path)
    calls=[]
    def handler(request):
        calls.append(request)
        assert request.url.params['region']=='005'
        assert request.url.params['displayRouteCode']=='1-A'
        assert request.url.params['resultType']=='101000'
        assert 'authorization' not in request.headers
        return httpx.Response(200,json=payload(int(request.url.params['direction'])))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert enrich(db,'005',client,pause=lambda n:None)==2
    s=GtfsStore(db)
    assert s.line('10010')['directions']==[0,1]
    assert s.line_stops('10010',0)[0]['id']=='1'
    assert len(s.line_stops('10010',0))==3 and len(s.line_shape('10010',1))==3
    assert s.stop('1')['lines'][0]['id']=='10010'
    assert len(calls)==2 and not s.calendar_expired()
    assert s.db.execute("select value from meta where key='topology_source'").fetchone()[0].startswith('https:')
    s.db.close()


def test_wrong_path_identity_is_not_accepted(tmp_path):
    db=catalog(tmp_path)
    body=payload(0);body['pathList'][0]['path_code']='wrong-route'
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(200,json=body))) as client:
        with pytest.raises(ValueError,match='alınamadı'):
            enrich(db,'005',client,pause=lambda n:None)
    s=GtfsStore(db)
    assert s.line_stops('10010',0)==[]
    s.db.close()


def test_topology_failure_rolls_back_partial_changes(tmp_path):
    db=catalog(tmp_path)
    def handler(request):
        return httpx.Response(200,json=payload(0)) if request.url.params['direction']=='0' else httpx.Response(500)
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(httpx.HTTPStatusError):enrich(db,'005',client,pause=lambda n:None)
    s=GtfsStore(db)
    assert s.line_stops('10010',0)==[]
    s.db.close()


def test_updater_keeps_old_database_when_topology_source_fails(tmp_path,monkeypatch):
    import shutil
    from tools import gtfs_guncelle,kentkart_topology
    original=catalog(tmp_path)
    data=tmp_path/'data';data.mkdir()
    target=data/'sivas.sqlite3';shutil.copyfile(original,target)
    before=target.read_bytes()
    monkeypatch.setattr(gtfs_guncelle,'DATA_DIR',data)
    monkeypatch.setattr(gtfs_guncelle,'download',lambda client,url,dest:shutil.copyfile(tmp_path/'catalog.zip',dest))
    def fail(*args,**kwargs):raise ValueError('source unavailable')
    monkeypatch.setattr(kentkart_topology,'enrich',fail)
    with pytest.raises(ValueError):gtfs_guncelle.update('sivas')
    assert target.read_bytes()==before
    assert not list(data.glob('.topology-*'))


def test_transient_provider_503_is_retried(tmp_path):
    db=catalog(tmp_path);calls=[]
    def handler(request):
        calls.append(request)
        if len(calls)==1:return httpx.Response(503)
        return httpx.Response(200,json=payload(int(request.url.params['direction'])))
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        assert enrich(db,'005',client,pause=lambda n:None)==2
    assert len(calls)==3
