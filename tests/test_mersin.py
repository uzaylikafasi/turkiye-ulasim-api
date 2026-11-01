import copy,json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from tools.mersin_guncelle import catalog,build,rows
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
P=Path(__file__).parent/'fixtures/mersin'
CAT=json.loads((P/'catalog.json').read_text());STOPS=json.loads((P/'stops.json').read_text());SHAPE=json.loads((P/'shape.json').read_text())
def fetch(lid,typ):return STOPS if typ=='hatdurak' else SHAPE


def test_real_nested_fields_and_separate_source_directions(tmp_path):
    lines=catalog(CAT);assert [x[0] for x in lines]==['10M-G','10M-D']
    dest=tmp_path/'db';build(dest,lines,fetch)
    with TestClient(create_app(lambda:{'mersin':(GtfsStore(dest),None)})) as c:
        assert len(c.get('/v1/mersin/lines').json()['data'])==2
        assert len(c.get('/v1/mersin/lines/10M-G/stops').json()['data'])==3
        assert c.get('/v1/mersin/lines/10M-G/shape').status_code==200
        assert c.get('/v1/mersin/stops/54397').json()['data']['latitude']==36.838666
        assert c.get('/v1/mersin/lines/10M-G/vehicles').status_code==501


@pytest.mark.parametrize('fault',['field','coordinate','conflict','response'])
def test_bad_source_preserves_previous_file(tmp_path,fault):
    dest=tmp_path/'db';dest.write_bytes(b'previous')
    stops=copy.deepcopy(STOPS)
    if fault=='field':stops[0]['durak_no']=['54397']
    if fault=='coordinate':stops[0]['enlem']['0']='0'
    if fault=='conflict':stops[1]['durak_no']=stops[0]['durak_no']
    if fault=='response':stops={'error':'failed'}
    with pytest.raises((ValueError,TypeError,KeyError)):build(dest,catalog(CAT),lambda lid,typ:stops if typ=='hatdurak' else SHAPE)
    assert dest.read_bytes()==b'previous'


def test_explicit_no_data_is_empty_but_not_error_envelopes():
    assert rows(0)==[]
    with pytest.raises(ValueError):rows({'error':'failed'})
    with pytest.raises(ValueError):catalog(0)


def test_daily_update_uses_municipal_service(monkeypatch,tmp_path):
    from tools import gtfs_guncelle,mersin_guncelle
    monkeypatch.setattr(gtfs_guncelle,'DATA_DIR',tmp_path)
    monkeypatch.setattr(mersin_guncelle,'update',lambda dest,client:build(dest,catalog(CAT),fetch))
    monkeypatch.setattr(gtfs_guncelle,'download',lambda *a:pytest.fail('ZIP download'))
    gtfs_guncelle.update('mersin');assert (tmp_path/'mersin.sqlite3').exists()
