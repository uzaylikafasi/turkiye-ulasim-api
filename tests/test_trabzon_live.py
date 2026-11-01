import copy,json
from pathlib import Path
import httpx,pytest
from turkiye_ulasim.sources.trabzon import normalize,TrabzonLive
from turkiye_ulasim.sources.base import SourceError,SourceRateLimited,SourceUnsupported
BODY=json.loads((Path(__file__).parent/'fixtures/trabzon/arrivals.json').read_text())
STOP={'id':'3528','code':'1032','lines':[{'id':'13:26'}]}


def test_real_qr_arrivals_do_not_invent_gps_or_unmapped_line_ids():
    rows=normalize(BODY,STOP)
    assert rows and rows[0]['stops_away']==1 and rows[0]['eta_seconds']==167
    assert rows[0]['line_id']=='13:26' and rows[1]['line_id'] is None
    assert all(x['observed_at'] is None and x['latitude'] is None for x in rows)


@pytest.mark.parametrize('fault',['failure','identity','schema'])
def test_bad_result_is_not_empty_success(fault):
    body=copy.deepcopy(BODY)
    if fault=='failure':body['SonucDurum']=False
    if fault=='identity':body['SonucData'][0]['DurakQrKod']='999'
    if fault=='schema':body['SonucData']={}
    with pytest.raises(SourceError):normalize(body,STOP)


def test_negative_or_nonfinite_eta_is_unknown():
    body=copy.deepcopy(BODY)
    body['SonucData'][0]['VarisSuresiSn']=float('nan');body['SonucData'][0]['KalanDurakAdet']=-1
    row=next(x for x in normalize(body,STOP) if x['source_line_id']=='13')
    assert row['eta_seconds'] is None and row['stops_away'] is None


@pytest.mark.asyncio
async def test_cache_budget_and_missing_qr_mapping():
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        live=TrabzonLive(client,clock=lambda:0)
        with pytest.raises(SourceUnsupported):await live.arrivals_for_stop({'id':'3528'})
        a=await live.arrivals_for_stop(STOP);b=await live.arrivals_for_stop(STOP)
        assert not a.cached and b.cached and len(calls)==1 and calls[0].url.params['qrDurakKod']=='1032'
        live.requests.extend([0]*29)
        with pytest.raises(SourceRateLimited):await live.arrivals_for_stop(dict(STOP,code='1060'))


def test_api_uses_persisted_qr_mapping_and_validates_local_stop(tmp_path):
    from fastapi.testclient import TestClient
    from tools.trabzon_guncelle import build,catalog
    from turkiye_ulasim.gtfs import GtfsStore
    from turkiye_ulasim.main import create_app
    from test_trabzon import HTML,fetch
    dest=tmp_path/'db';build(dest,catalog(HTML),fetch);calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    def factory():return {'trabzon':(GtfsStore(dest),TrabzonLive(httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        assert c.get('/v1/trabzon/stops/missing/arrivals').status_code==404 and not calls
        assert c.get('/v1/trabzon/stops/3528').json()['data']['code']=='1032'
        r=c.get('/v1/trabzon/stops/3528/arrivals')
        assert r.status_code==200 and r.json()['meta']['live'] and r.json()['data']
        assert c.get('/v1/trabzon/stops/3528/arrivals').json()['meta']['cached']
        assert len(calls)==1


@pytest.mark.asyncio
async def test_same_qr_code_does_not_reuse_another_stops_line_mapping():
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        live=TrabzonLive(client)
        a=await live.arrivals_for_stop(STOP)
        b=await live.arrivals_for_stop(dict(STOP,id='other',lines=[]))
        assert a.data[0]['line_id']=='13:26' and b.data[0]['line_id'] is None
        assert len(calls)==2
