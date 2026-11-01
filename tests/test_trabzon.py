import copy,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tools.trabzon_guncelle import catalog,build,point
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
P=Path(__file__).parent/'fixtures/trabzon'
HTML=(P/'catalog.html').read_text()
BODIES={t:json.loads((P/(t+'.json')).read_text()) for t in ['GetHatGeoJson','GetHatDurakGeoJson']}
def fetch(lid,typ):return BODIES[typ]


def test_real_identity_direction_and_mercator_projection(tmp_path):
    lines=catalog(HTML);assert lines[0][:2]==(1,'103')
    dest=tmp_path/'db';build(dest,lines,fetch)
    with TestClient(create_app(lambda:{'trabzon':(GtfsStore(dest),None)})) as c:
        data=c.get('/v1/trabzon/lines').json()['data']
        assert {x['id'] for x in data}=={'1:36','1:39'}
        stops=c.get('/v1/trabzon/lines/1:39/stops').json()['data'];assert len(stops)==2
        assert 40<stops[0]['latitude']<42 and 39<stops[0]['longitude']<41
        assert c.get('/v1/trabzon/lines/1:36/shape').status_code==200
        assert c.get('/v1/trabzon/lines/1:36/vehicles').status_code==501


@pytest.mark.parametrize('fault',['identity','direction','route','projection','sequence'])
def test_invalid_geojson_preserves_old_file(tmp_path,fault):
    bodies=copy.deepcopy(BODIES);f=bodies['GetHatDurakGeoJson']['features'][0];p=f['properties']
    if fault=='identity':p['hat_id']=999
    if fault=='direction':p['yon_str']='G'
    if fault=='route':p['hat_guzergah_id']=999
    if fault=='projection':f['geometry']['crs']['properties']['name']='EPSG:4326'
    if fault=='sequence':p['sira']=-1
    dest=tmp_path/'db';dest.write_bytes(b'previous')
    with pytest.raises(ValueError):build(dest,catalog(HTML),lambda lid,typ:bodies[typ])
    assert dest.read_bytes()==b'previous'


def test_mercator_known_point_and_invalid_position():
    g={'crs':{'properties':{'name':'EPSG:3857'}}}
    lat,lon=point(g,[4452779.631730943,4865942.279503175])
    assert lat==pytest.approx(40,abs=.000001)
    assert lon==pytest.approx(40,abs=.000001)
    with pytest.raises(ValueError):point(g,[float('inf'),0])


def test_daily_updater_selects_geojson_source(monkeypatch,tmp_path):
    from tools import gtfs_guncelle,trabzon_guncelle
    monkeypatch.setattr(gtfs_guncelle,'DATA_DIR',tmp_path)
    monkeypatch.setattr(trabzon_guncelle,'update',lambda dest,client:build(dest,catalog(HTML),fetch))
    monkeypatch.setattr(gtfs_guncelle,'download',lambda *a:pytest.fail('ZIP download'))
    gtfs_guncelle.update('trabzon');assert (tmp_path/'trabzon.sqlite3').exists()
