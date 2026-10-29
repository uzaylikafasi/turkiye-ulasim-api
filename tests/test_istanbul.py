from pathlib import Path
from xml.etree import ElementTree as ET

import httpx
import pytest
from fastapi.testclient import TestClient

from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
from turkiye_ulasim.sources.istanbul import BASE_URL, HOURLY_BUDGET, IstanbulLive
from test_api import Clock, no_upstream

FIXTURE = (Path(__file__).parent / 'fixtures/iett-vehicles.xml').read_bytes()


def client_for(db, handler, clock=None):
    import sqlite3
    connection = sqlite3.connect(db)
    connection.execute("INSERT INTO lines VALUES ('route-15F','15F','BEYKOZ - KADIKÖY',3,'15F_G_D0')")
    connection.execute("INSERT INTO lines VALUES ('route-15F-return','15F','KADIKÖY - BEYKOZ',3,'15F_D_D0')")
    connection.commit()
    connection.close()
    store = GtfsStore(db)
    source = IstanbulLive(httpx.AsyncClient(transport=httpx.MockTransport(handler)), clock=clock or Clock())
    return TestClient(create_app(lambda: {'istanbul': (store, source)}))


def test_soap_line_code_and_route_variant_filter_and_cache(gtfs_db):
    calls = []
    def handler(request):
        calls.append(request)
        assert str(request.url) == BASE_URL
        root = ET.fromstring(request.content)
        assert root.find('.//{http://tempuri.org/}HatKodu').text == '15F'
        assert request.headers['soapaction'] == '"http://tempuri.org/GetHatOtoKonum_json"'
        return httpx.Response(200, content=FIXTURE)
    with client_for(gtfs_db, handler) as client:
        first = client.get('/v1/istanbul/lines/route-15F/vehicles').json()
        second = client.get('/v1/istanbul/lines/route-15F-return/vehicles').json()
        again = client.get('/v1/istanbul/lines/route-15F/vehicles').json()
    assert len(calls) == 1
    assert [v['id'] for v in first['data']] == ['M2563']
    assert [v['id'] for v in second['data']] == ['M2592', 'M2593']
    vehicle = first['data'][0]
    assert vehicle['line_id'] == 'route-15F' and vehicle['source_line_code'] == '15F'
    assert vehicle['latitude'] == 41.1421463333333
    assert vehicle['observed_at'] == '2026-10-29T20:01:59+03:00'
    assert first['meta']['cached'] is False and again['meta']['cached'] is True
    assert again['meta']['fetched_at'] == first['meta']['fetched_at']


def test_cache_expires_after_60_seconds(gtfs_db):
    calls = []
    clock = Clock()
    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=FIXTURE)
    with client_for(gtfs_db, handler, clock) as client:
        assert client.get('/v1/istanbul/lines/route-15F/vehicles').status_code == 200
        clock.now += 59
        assert client.get('/v1/istanbul/lines/route-15F/vehicles').json()['meta']['cached'] is True
        clock.now += 1
        assert client.get('/v1/istanbul/lines/route-15F/vehicles').json()['meta']['cached'] is False
    assert len(calls) == 2


def test_budget_shared_across_codes():
    import asyncio
    from turkiye_ulasim.sources.base import SourceRateLimited
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=FIXTURE)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            source = IstanbulLive(transport, clock=Clock())
            for n in range(HOURLY_BUDGET):
                await source.vehicles(str(n), line={'code': str(n), 'source_route_code': 'x'})
            with pytest.raises(SourceRateLimited) as exc:
                await source.vehicles('extra', line={'code': 'extra', 'source_route_code': 'x'})
            assert 1 <= exc.value.retry_after <= 3600
    asyncio.run(run())
    assert len(calls) == HOURLY_BUDGET


@pytest.mark.parametrize('status,body', [(500, b'error'), (200, b'<broken'),
    (200, b'<root/>'), (200, b'<GetHatOtoKonum_jsonResult xmlns="http://tempuri.org/">{}</GetHatOtoKonum_jsonResult>')])
def test_source_schema_and_http_errors_become_502(gtfs_db, status, body):
    with client_for(gtfs_db, lambda request: httpx.Response(status, content=body)) as client:
        response = client.get('/v1/istanbul/lines/route-15F/vehicles')
    assert response.status_code == 502


def test_unavailable_arrivals_and_unknown_routes_never_call_source(gtfs_db):
    with client_for(gtfs_db, no_upstream) as client:
        assert client.get('/v1/istanbul/stops/21050/arrivals').status_code == 501
        assert client.get('/v1/istanbul/lines/missing/vehicles').status_code == 404
        assert client.get('/v1/istanbul/lines/missing/stops').status_code == 404
        assert client.get('/v1/istanbul/lines/missing/shape').status_code == 404
        cities = {c['id']: c for c in client.get('/v1/cities').json()['data']}
        assert cities['istanbul']['capabilities'] == {'static': True, 'vehicles': True, 'arrivals': False}
        assert cities['konya']['available'] is False
        assert client.get('/v1/konya/lines').status_code == 503


def test_concurrent_same_code_polls_share_one_request():
    import asyncio
    calls = []
    def handler(request):
        calls.append(request)
        return httpx.Response(200, content=FIXTURE)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as transport:
            source = IstanbulLive(transport, clock=Clock())
            results = await asyncio.gather(*(source.vehicles('1', line={'code':'15F','source_route_code':'15F_G_D0'}) for _ in range(12)))
            assert sum(not r.cached for r in results) == 1
    asyncio.run(run())
    assert len(calls) == 1


def test_invalid_positions_are_dropped_and_missing_time_is_marked_stale(gtfs_db):
    import json
    root = ET.fromstring(FIXTURE)
    node = root.find('.//{http://tempuri.org/}GetHatOtoKonum_jsonResult')
    item = json.loads(node.text)[0]
    item.pop('son_konum_zamani')
    node.text = json.dumps([item, item | {'kapino':'invalid', 'enlem':'0','boylam':'0'},
                            item | {'kapino':'nan', 'enlem':'NaN'}])
    with client_for(gtfs_db, lambda request: httpx.Response(200, content=ET.tostring(root))) as client:
        body = client.get('/v1/istanbul/lines/route-15F/vehicles').json()
    assert len(body['data']) == 1
    assert body['data'][0]['stale'] is True and body['data'][0]['observed_at'] is None
    assert any('2 araç kaydı' in w for w in body['meta']['warnings'])
