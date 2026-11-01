from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient
from tools.ego_guncelle import parse,build
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app

HTML=(Path(__file__).parent/'fixtures/ego/101.html').read_text()


def test_actual_html_entities_and_source_order():
    p=parse(HTML)
    assert p.selected=='101'
    assert p.lines==[('101','GÖLBAŞI-HAYMANA YOLU-BAHÇELİEVLER')]
    assert p.stops[0]==(1,'14043','GÖLBAŞI HAREKET NOKTASI')
    assert len(p.stops)==3


def test_coordinate_free_catalog_api(tmp_path):
    dest=tmp_path/'ego.sqlite3';build(dest,parse(HTML).lines,lambda _:HTML)
    with TestClient(create_app(lambda:{'ankara':(GtfsStore(dest),None)})) as c:
        city=next(x for x in c.get('/v1/cities').json()['data'] if x['id']=='ankara')
        assert not city['capabilities']['nearby'] and not city['capabilities']['gtfs']
        assert c.get('/v1/ankara/lines?q=Gölbaşı').json()['data']
        stops=c.get('/v1/ankara/lines/101/stops').json()['data']
        assert len(stops)==3 and stops[0]['latitude'] is None
        assert c.get('/v1/ankara/stops/14043').json()['data']['lines'][0]['id']=='101'
        for path in ['/lines/101/shape','/lines/101/vehicles','/stops/nearby?latitude=40&longitude=32']:
            assert c.get('/v1/ankara'+path).status_code==501


@pytest.mark.parametrize('bad',[
    HTML.replace('<td>101</td>','<td>102</td>'),
    HTML.replace('<td>2<text>','<td>1<text>'),
    HTML.replace('id="hat_liste_otobus"','id="unknown"'),
    HTML.replace('<td>14043</td>','<td>invalid</td>'),
])
def test_invalid_response_preserves_database(tmp_path,bad):
    dest=tmp_path/'ego.sqlite3';dest.write_bytes(b'previous')
    with pytest.raises((ValueError,sqlite3.Error)):build(dest,parse(HTML).lines,lambda _:bad)
    assert dest.read_bytes()==b'previous'


def test_only_bus_selector_is_imported():
    assert len(parse(HTML+'<select id="hat_liste_metro"><option value="M1">Metro</option></select>').lines)==1


def test_daily_update_routes_to_ego(monkeypatch,tmp_path):
    from tools import gtfs_guncelle,ego_guncelle
    monkeypatch.setattr(gtfs_guncelle,'DATA_DIR',tmp_path)
    monkeypatch.setattr(ego_guncelle,'update',lambda dest,client:build(dest,parse(HTML).lines,lambda _:HTML))
    monkeypatch.setattr(gtfs_guncelle,'download',lambda *a:pytest.fail('ZIP download'))
    gtfs_guncelle.update('ankara')
    assert (tmp_path/'ankara.sqlite3').exists()
