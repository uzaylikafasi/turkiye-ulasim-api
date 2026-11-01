import copy,json
from pathlib import Path
from datetime import datetime
import httpx,pytest
from turkiye_ulasim.sources.diyarbakir import normalize,DiyarbakirLive
from turkiye_ulasim.sources.base import SourceError,SourceRateLimited
BODY=json.loads((Path(__file__).parent/'fixtures/diyarbakir/live.json').read_text())
NOW=datetime.fromisoformat('2026-11-01T09:23:00+03:00')


def test_real_vehicle_direction_is_not_heading_and_private_fields_are_dropped():
    b=copy.deepcopy(BODY);b['raw']['data'][0].update(driver='private',totalRevenue=123)
    rows,warnings=normalize(b,'117','A1',NOW)
    assert len(rows)==2 and rows[0]['source_direction']=='D' and rows[0]['direction']==1
    assert rows[0]['heading_degrees']==245 and rows[0]['age_seconds']==19
    assert rows[0]['stale'] is False and rows[0]['observed_at'].endswith('+03:00')
    assert 'driver' not in str(rows) and 'totalRevenue' not in str(rows)


def test_old_missing_future_and_invalid_coordinates_are_distinct():
    b=copy.deepcopy(BODY);b['raw']['data'][0]['date']='2026-11-01T09:00:00'
    b['raw']['data'][1]['date']='invalid'
    rows,warnings=normalize(b,'117','A1',NOW)
    assert rows[0]['stale'] is True and rows[1]['stale'] is None
    assert any('eski' in w for w in warnings)
    b['raw']['data'][1]['date']='2026-11-01T12:00:00'
    assert normalize(b,'117','A1',NOW)[0][1]['observed_at'] is None
    b['raw']['data'][0]['latitude']=0
    assert len(normalize(b,'117','A1',NOW)[0])==1


@pytest.mark.parametrize('fault',['status','identity','code','json'])
def test_upstream_failure_is_not_empty_success(fault):
    b=copy.deepcopy(BODY)
    if fault=='status':b['raw']['isSuccess']=False
    if fault=='identity':b['raw']['data'][0]['routeNo']=999
    if fault=='code':b['raw']['data'][0]['routeCode']='A2'
    if fault=='json':b['raw']['data']={}
    with pytest.raises(SourceError):normalize(b,'117','A1',NOW)


def test_duplicate_vehicle_uses_latest_and_equal_time_conflict_is_omitted():
    b=copy.deepcopy(BODY);r=copy.deepcopy(b['raw']['data'][0]);r['date']='2026-11-01T09:22:50';r['latitude']=37.94
    b['raw']['data'].append(r)
    rows,_=normalize(b,'117','A1',NOW)
    assert len(rows)==2 and rows[0]['latitude']==37.94
    r2=dict(r,latitude=37.95);b['raw']['data'].append(r2)
    assert len(normalize(b,'117','A1',NOW)[0])==1


@pytest.mark.asyncio
async def test_cache_budget_and_retry_after():
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        source=DiyarbakirLive(c,clock=lambda:0)
        a=await source.vehicles('117',line={'code':'A1'});b=await source.vehicles('117',line={'code':'A1'})
        assert not a.cached and b.cached and len(calls)==1
        source.requests.extend([0]*29)
        with pytest.raises(SourceRateLimited):await source.vehicles('118',line={'code':'A2'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(429,headers={'Retry-After':'42'}))) as c:
        with pytest.raises(SourceRateLimited) as e:await DiyarbakirLive(c).vehicles('117',line={'code':'A1'})
        assert e.value.retry_after==42


def test_live_api_checks_static_line_and_exposes_observation(tmp_path):
    from fastapi.testclient import TestClient
    from tools.diyarbakir_guncelle import bootstrap,build
    from turkiye_ulasim.gtfs import GtfsStore
    from turkiye_ulasim.main import create_app
    from test_diyarbakir import HTML,fetch
    dest=tmp_path/'db';build(dest,*bootstrap(HTML),fetch);calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    def factory():return {'diyarbakir':(GtfsStore(dest),DiyarbakirLive(httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        assert c.get('/v1/diyarbakir/lines/missing/vehicles').status_code==404 and not calls
        response=c.get('/v1/diyarbakir/lines/117/vehicles').json()
        assert response['meta']['live'] and len(response['data'])==2
        assert c.get('/v1/diyarbakir/lines/117/vehicles').json()['meta']['cached']
        assert len(calls)==1
