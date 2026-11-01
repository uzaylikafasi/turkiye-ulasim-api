import copy,json
from pathlib import Path
import httpx,pytest
from turkiye_ulasim.sources.ankara import normalize,AnkaraLive
from turkiye_ulasim.sources.base import SourceError,SourceRateLimited
BODY=json.loads((Path(__file__).parent/'fixtures/ego/arrivals.json').read_text())


def test_real_arrival_filters_timetable_and_preserves_source_direction():
    rows=normalize(BODY,'14043')
    assert len(rows)==1 and rows[0]['eta_seconds']==959
    assert rows[0]['source_direction']=='4' and rows[0]['line_id'] is None
    assert rows[0]['observed_at'].endswith('+03:00')


@pytest.mark.parametrize('fault',['status','identity','structure'])
def test_bad_upstream_is_not_empty_success(fault):
    body=copy.deepcopy(BODY)
    if fault=='status':body['status']='FALSE'
    if fault=='identity':body['table'][1]['secili_durak_no']='1'
    if fault=='structure':body['table']={}
    with pytest.raises(SourceError):normalize(body,'14043')


def test_passed_or_invalid_vehicles_are_not_future_arrivals():
    body=copy.deepcopy(BODY);body['table'][1]['saniye']='999999'
    assert normalize(body,'14043')==[]
    body['table'][1]['saniye']='NaN'
    assert normalize(body,'14043')==[]


@pytest.mark.asyncio
async def test_cache_and_budget():
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        source=AnkaraLive(c,clock=lambda:0)
        first=await source.arrivals('14043');second=await source.arrivals('14043')
        assert not first.cached and second.cached and len(calls)==1
        source.requests.extend([0]*29)
        with pytest.raises(SourceRateLimited):await source.arrivals('99999')
        assert len(calls)==1


def test_arrivals_api_checks_local_stop_before_upstream(tmp_path):
    from fastapi.testclient import TestClient
    from tools.ego_guncelle import parse,build
    from turkiye_ulasim.gtfs import GtfsStore
    from turkiye_ulasim.main import create_app
    html=(Path(__file__).parent/'fixtures/ego/101.html').read_text()
    dest=tmp_path/'db';build(dest,parse(html).lines,lambda _:html)
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    def factory():return {'ankara':(GtfsStore(dest),AnkaraLive(httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        assert c.get('/v1/ankara/stops/999999/arrivals').status_code==404
        assert not calls
        response=c.get('/v1/ankara/stops/14043/arrivals')
        assert response.status_code==200 and response.json()['meta']['live']
        assert len(response.json()['data'])==1 and len(calls)==1
