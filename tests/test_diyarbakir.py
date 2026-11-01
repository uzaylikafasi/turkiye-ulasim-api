import copy,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tools.diyarbakir_guncelle import bootstrap,build
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
P=Path(__file__).parent/'fixtures/diyarbakir'
HTML=(P/'bootstrap.html').read_text()
BODIES={k:json.loads((P/(k+'.json')).read_text()) for k in ['directions','G','D']}
def fetch(code,typ,way=None):return BODIES['directions' if typ=='line-directions' else way]


def test_actual_bootstrap_and_direction_specific_api(tmp_path):
    lines,stops=bootstrap(HTML);dest=tmp_path/'db';build(dest,lines,stops,fetch)
    with TestClient(create_app(lambda:{'diyarbakir':(GtfsStore(dest),None)})) as c:
        line=c.get('/v1/diyarbakir/lines/117').json()['data']
        assert line['code']=='A1' and line['directions']==[0,1]
        assert len(c.get('/v1/diyarbakir/lines/117/stops?direction=1').json()['data'])==2
        assert c.get('/v1/diyarbakir/lines/117/shape?direction=0').status_code==200
        assert c.get('/v1/diyarbakir/lines/117/vehicles').status_code==501


@pytest.mark.parametrize('fault',['identity','direction','shape','result','missingstop'])
def test_invalid_source_preserves_file(tmp_path,fault):
    bodies=copy.deepcopy(BODIES);row=bodies['directions']['raw']['data'][0]
    if fault=='identity':row['lineNo']=999
    if fault=='direction':row['direction']='unknown'
    if fault=='shape':bodies['G']['raw']['data'][0]['routeDirection']='D'
    if fault=='result':bodies['G']['raw']['isSuccess']=False
    if fault=='missingstop':row['durakId']=99999
    dest=tmp_path/'db';dest.write_bytes(b'previous');lines,stops=bootstrap(HTML)
    with pytest.raises(ValueError):build(dest,lines,stops,lambda code,typ,way=None:bodies['directions' if typ=='line-directions' else way])
    assert dest.read_bytes()==b'previous'


def test_null_station_coordinate_is_preserved(tmp_path):
    lines,stops=bootstrap(HTML);stops[0]['latitude']=None;stops[0]['longitude']=None
    dest=tmp_path/'db';build(dest,lines,stops,fetch);s=GtfsStore(dest)
    assert s.stop(stops[0]['stationId'])['latitude'] is None;s.db.close()


def test_daily_update_uses_municipal_bridge(monkeypatch,tmp_path):
    from tools import gtfs_guncelle,diyarbakir_guncelle
    monkeypatch.setattr(gtfs_guncelle,'DATA_DIR',tmp_path)
    monkeypatch.setattr(diyarbakir_guncelle,'update',lambda dest,client:build(dest,*bootstrap(HTML),fetch))
    monkeypatch.setattr(gtfs_guncelle,'download',lambda *a:pytest.fail('ZIP download'))
    gtfs_guncelle.update('diyarbakir');assert (tmp_path/'diyarbakir.sqlite3').exists()


def test_only_explicit_missing_coordinates_message_is_empty():
    from tools.diyarbakir_guncelle import data
    body={'raw':{'isSuccess':False,'message':'Response Model is Empty. This LineCode not have Coordinates...','data':None},'items':[]}
    assert data(body,allow_missing_coordinates=True)==[]
    with pytest.raises(ValueError):data(body)
    body['raw']['message']='upstream failure'
    with pytest.raises(ValueError):data(body,allow_missing_coordinates=True)


def test_padding_in_raw_line_codes_does_not_change_identity(tmp_path):
    lines,stops=bootstrap(HTML);lines[0]['raw']['lineCode']+=' '
    bodies=copy.deepcopy(BODIES)
    for row in bodies['directions']['raw']['data']:row['lineCode']+=' '
    for way in ['G','D']:
        for row in bodies[way]['raw']['data']:row['routeCode']+=' '
    dest=tmp_path/'db'
    build(dest,lines,stops,lambda code,typ,way=None:bodies['directions' if typ=='line-directions' else way])
    assert dest.exists()
