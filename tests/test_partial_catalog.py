import copy
import pytest
from fastapi.testclient import TestClient
from conftest import FILES
from test_gtfs_multicity import write_feed
from turkiye_ulasim import gtfs
from turkiye_ulasim.main import create_app


def partial_files():
    files=copy.deepcopy(FILES)
    del files['trips.txt']
    del files['stop_times.txt']
    return files


def test_partial_import_requires_opt_in_and_does_not_invent_links(tmp_path):
    archive,db=tmp_path/'partial.zip',tmp_path/'catalog.sqlite3'
    write_feed(archive,partial_files())
    with pytest.raises(ValueError,match='eksik'):
        gtfs.build(archive,db)
    gtfs.build(archive,db,allow_partial=True)
    s=gtfs.GtfsStore(db)
    assert len(s.lines())==2 and s.stop('21050')
    assert s.line('446')['directions']==[]
    assert s.line_stops('446',0)==[] and s.line_shape('446',0)==[]
    assert s.stop('21050')['lines']==[] and s.warnings()
    assert not s.calendar_expired()
    s.db.close()


def test_partial_mixed_modes_cannot_claim_bus_stops(tmp_path):
    files=partial_files()
    files['routes.txt'].append(['rail','T1','Tram','0'])
    archive,db=tmp_path/'mixed.zip',tmp_path/'db.sqlite3'
    write_feed(archive,files)
    with pytest.raises(ValueError,match='ayrılamıyor'):
        gtfs.build(archive,db,allow_partial=True)
    assert not db.exists()


@pytest.mark.parametrize('city',['sivas','edirne'])
def test_partial_city_capabilities_and_unsupported_topology(city,tmp_path):
    archive,db=tmp_path/'partial.zip',tmp_path/'catalog.sqlite3'
    write_feed(archive,partial_files())
    gtfs.build(archive,db,allow_partial=True)
    with TestClient(create_app(lambda:{city:(gtfs.GtfsStore(db),None)})) as client:
        row=next(r for r in client.get('/v1/cities').json()['data'] if r['id']==city)
        assert row['partial_feed'] and not row['capabilities']['gtfs'] and not row['gtfs']
        assert row['source_kind']=='community_catalog'
        assert client.get(f'/v1/{city}/lines').status_code==200
        stop=client.get(f'/v1/{city}/stops/21050').json()
        assert stop['meta']['partial_feed'] and stop['data']['lines']==[]
        assert client.get(f'/v1/{city}/lines/446/stops').status_code==501
        assert client.get(f'/v1/{city}/lines/446/shape').status_code==501
        assert client.get(f'/v1/{city}/lines/446/vehicles').status_code==501
