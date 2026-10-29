import asyncio
import json
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from turkiye_ulasim.main import create_app
from turkiye_ulasim.sources.kahramanmaras import Kahramanmaras
from test_api import Clock

FIXTURES = Path(__file__).parent/'fixtures/kahramanmaras'


def load(name):
    return json.loads((FIXTURES/f'{name}.json').read_text())


def upstream(request):
    assert request.method == 'GET'
    assert request.url.host == 'mithrixa.com'
    assert 'authorization' not in request.headers
    path = request.url.path.removeprefix('/ulasim-api/v1/')
    if path == 'search':
        assert request.url.params['q'] == 'H/1'
        assert request.url.params['stops'] == 'false'
        return httpx.Response(200, json=load('search-h1'))
    if path.startswith('lines/'):
        assert request.url.params['direction'] == '1'
    return httpx.Response(200, json=load(path.replace('/','-')))


def client_for(handler=upstream, clock=None):
    bridge = Kahramanmaras(httpx.AsyncClient(transport=httpx.MockTransport(handler)), clock=clock or Clock())
    return TestClient(create_app(lambda: {'kahramanmaras': (bridge, bridge)}))


def test_search_preserves_direction_and_requires_query():
    with client_for() as client:
        assert client.get('/v1/kahramanmaras/lines').status_code == 422
        response = client.get('/v1/kahramanmaras/lines?q=H/1').json()
        h1 = [r for r in response['data'] if r['code'] == 'H/1']
        assert [(r['id'],r['source_direction']) for r in h1] == [('161:2',2),('9576:1',1)]
        assert response['meta']['source_kind'] == 'community_bridge'
        assert response['meta']['pagination']['source_limited'] is True
        assert client.get('/v1/kahramanmaras/lines?q=H/1&limit=1&offset=1').json()['data'][0]['id'] == '9576:1'
        city = next(c for c in client.get('/v1/cities').json()['data'] if c['id']=='kahramanmaras')
        assert city['available'] and city['capabilities']['vehicles'] and city['capabilities']['arrivals']
        assert not city['capabilities']['gtfs'] and not city['capabilities']['line_catalog']


def test_line_stops_shape_and_unsupported_direction():
    calls = []
    def handler(request):
        calls.append(request)
        return upstream(request)
    with client_for(handler) as client:
        detail = client.get('/v1/kahramanmaras/lines/9576:1').json()['data']
        assert detail['code']=='H/1' and detail['directions']==[0] and detail['source_direction']==1
        stops = client.get('/v1/kahramanmaras/lines/9576:1/stops?direction=0').json()['data']
        assert len(stops)==48 and stops[0]['id']=='6376'
        assert stops[0]['latitude']==37.55049
        shape = client.get('/v1/kahramanmaras/lines/9576:1/shape?direction=0').json()['data']
        assert shape[0] == [37.55049,36.91644]
        before = len(calls)
        assert client.get('/v1/kahramanmaras/lines/9576:1/stops?direction=1').json()['data']==[]
        assert len(calls)==before


def test_vehicles_reuse_detail_cache_without_inventing_measurement_time():
    calls = []
    def handler(request):
        calls.append(request)
        return upstream(request)
    with client_for(handler) as client:
        first = client.get('/v1/kahramanmaras/lines/9576:1/vehicles').json()
        again = client.get('/v1/kahramanmaras/lines/9576:1/vehicles').json()
    assert len(calls)==1
    assert first['data'][0]['line_id']=='9576:1'
    assert first['data'][0]['observed_at'] is None
    assert first['meta']['fetched_at']==load('lines-9576')['meta']['fetched_at']==again['meta']['fetched_at']
    assert again['meta']['cached'] is True


def test_stop_arrivals_and_nearby_share_common_schema():
    with client_for() as client:
        stop = client.get('/v1/kahramanmaras/stops/6968').json()['data']
        assert stop['name']=='DEMOKRASİ MEYDANI'
        assert all(line['id'] is None and line['source_id'] for line in stop['lines'])
        arrivals = client.get('/v1/kahramanmaras/stops/6968/arrivals').json()['data']
        assert arrivals and all(r['line_id'] is None and r['source_direction'] is None for r in arrivals)
        etas = [r['eta_seconds'] for r in arrivals if r['eta_seconds'] is not None]
        assert etas==sorted(etas)
        assert arrivals[0]['stops_away'] is None
        nearby = client.get('/v1/kahramanmaras/stops/nearby?latitude=37.58303&longitude=36.92657&radius=150').json()['data']
        assert nearby[0]['id']=='6968' and nearby[0]['distance_m']==0
        assert all(s['distance_m']<=150 for s in nearby)


@pytest.mark.parametrize('path', ['lines/missing','lines/9576','lines/9576:9','stops/abc','stops/0','stops/0/arrivals'])
def test_bad_identifiers_do_not_reach_source(path):
    def fail(request):
        raise AssertionError('unexpected source request')
    with client_for(fail) as client:
        assert client.get('/v1/kahramanmaras/'+path).status_code==404


@pytest.mark.parametrize('response', [httpx.Response(500),httpx.Response(200,text='not-json'),
    httpx.Response(200,json={'data':{},'meta':{}}),
    httpx.Response(200,json={'data':{'processInfo':0},'meta':{'fetched_at':'2026-10-29T00:00:00+00:00'}})])
def test_source_errors_return_502(response):
    with client_for(lambda request: response) as client:
        assert client.get('/v1/kahramanmaras/lines?q=H/1').status_code==502


def test_remote_rate_limit_preserves_retry_after():
    with client_for(lambda request: httpx.Response(429,headers={'Retry-After':'25'})) as client:
        response = client.get('/v1/kahramanmaras/lines?q=H/1')
    assert response.status_code==503 and response.headers['retry-after']=='25'
    assert 'Kahramanmaraş' in response.json()['error']


def test_cache_expiry_and_concurrent_polls():
    calls=[]
    clock=Clock()
    def handler(request):
        calls.append(request)
        return upstream(request)
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            bridge=Kahramanmaras(client,clock=clock)
            results=await asyncio.gather(*(bridge.lines('H/1') for _ in range(10)))
            assert all(len(r)==10 for r in results)
            assert len(calls)==1
            clock.now+=60
            await bridge.lines('H/1')
            assert len(calls)==2
    asyncio.run(run())


def test_direction_three_is_not_guessed():
    payload=load('lines-9576')
    def handler(request):
        assert request.url.params['direction']=='3'
        return httpx.Response(200,json=payload)
    with client_for(handler) as client:
        detail=client.get('/v1/kahramanmaras/lines/9576:3').json()['data']
        assert detail['directions']==[]
        assert client.get('/v1/kahramanmaras/lines/9576:3/stops').status_code==501


def test_minute_budget_shared_across_different_queries():
    from turkiye_ulasim.sources.base import SourceRateLimited
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(200,json=load('search-h1'))
    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            bridge=Kahramanmaras(client,clock=Clock())
            for i in range(60):
                await bridge.lines(str(i))
            with pytest.raises(SourceRateLimited) as exc:
                await bridge.lines('one-more')
            assert exc.value.retry_after==60
    asyncio.run(run())
    assert len(calls)==60


def test_bridge_can_be_disabled_without_needing_a_database(monkeypatch,tmp_path):
    import turkiye_ulasim.main as main
    monkeypatch.setattr(main,'DATA_DIR',tmp_path)
    monkeypatch.setenv('ULASIM_KAHRAMANMARAS_ENABLED','0')
    with TestClient(create_app()) as client:
        city=next(c for c in client.get('/v1/cities').json()['data'] if c['id']=='kahramanmaras')
        assert city['available'] is False
        assert client.get('/v1/kahramanmaras/lines?q=H/1').status_code==503
    monkeypatch.setenv('ULASIM_KAHRAMANMARAS_ENABLED','1')
    with TestClient(create_app()) as client:
        city=next(c for c in client.get('/v1/cities').json()['data'] if c['id']=='kahramanmaras')
        assert city['available'] is True


def test_gtfs_update_does_not_attempt_empty_bridge_feed(monkeypatch,capsys):
    from tools import gtfs_guncelle
    def fail(*args,**kwargs):
        raise AssertionError('GTFS bridge download attempted')
    monkeypatch.setattr(gtfs_guncelle,'download',fail)
    gtfs_guncelle.update('kahramanmaras')
    assert 'içe aktarma gerekmiyor' in capsys.readouterr().out
