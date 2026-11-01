import copy,json
from pathlib import Path
import httpx,pytest
from turkiye_ulasim.sources.kentkart import KentkartLive,normalize
from turkiye_ulasim.sources.base import SourceError,SourceRateLimited,SourceUnsupported
BODY=json.loads((Path(__file__).parent/'fixtures/kentkart/live004.json').read_text())


def test_real_ids_heading_and_unknown_gps_age():
    rows=normalize(BODY,'41010','10',0)
    assert len(rows)==2 and rows[0]['id']=='41253'
    assert rows[0]['direction']==0 and rows[0]['heading_degrees']==73.9
    assert rows[0]['wheelchair_accessible'] is True and rows[0]['stale'] is None
    assert normalize(BODY,'different','10',0) is None
    assert normalize(BODY,'41010','10',1) is None


@pytest.mark.parametrize('fault',['status','list','duplicate','result'])
def test_source_failure_not_empty_success(fault):
    b=copy.deepcopy(BODY)
    if fault=='result':b['result']=None
    if fault=='status':b['result']['code']=1
    if fault=='list':b['pathList'][0]['busList']={}
    if fault=='duplicate':b['pathList'].append(b['pathList'][0])
    with pytest.raises(SourceError):normalize(b,'41010','10',0)


@pytest.mark.asyncio
async def test_both_directions_cache_and_budget():
    calls=[]
    def handler(r):
        calls.append(r);b=copy.deepcopy(BODY)
        if r.url.params['direction']=='1':
            b['pathList'][0].update(direction='1',path_code='410101',busList=[])
        return httpx.Response(200,json=b)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        live=KentkartLive('004',c,clock=lambda:0)
        a=await live.vehicles('41010',line={'code':'10'});b=await live.vehicles('41010',line={'code':'10'})
        assert len(a.data)==2 and b.cached and len(calls)==2
        assert all(r.url.params['region']=='004' and r.url.params['resultType']=='010000' for r in calls)
        live.requests.extend([0]*28)
        with pytest.raises(SourceRateLimited):await live.vehicles('41011',line={'code':'11'})


@pytest.mark.asyncio
async def test_missing_mapping_and_conflicting_directions():
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,json={'result':{'code':0},'pathList':[]}))) as c:
        with pytest.raises(SourceUnsupported):await KentkartLive('004',c).vehicles('41010',line={'code':'10'})
    def handler(r):
        b=copy.deepcopy(BODY);way=r.url.params['direction'];b['pathList'][0].update(direction=way,path_code='41010'+way)
        return httpx.Response(200,json=b)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        assert (await KentkartLive('004',c).vehicles('41010',line={'code':'10'})).data==[]


def test_api_uses_local_line_before_live_source(gtfs_db):
    from fastapi.testclient import TestClient
    from turkiye_ulasim.main import create_app
    from turkiye_ulasim.gtfs import GtfsStore
    calls=[]
    def handler(r):
        calls.append(r);b=copy.deepcopy(BODY);way=r.url.params['direction']
        b['pathList'][0].update(path_code='446'+way,direction=way,displayRouteCode='446')
        if way=='1':b['pathList'][0]['busList']=[]
        return httpx.Response(200,json=b)
    def factory():return {'kocaeli':(GtfsStore(gtfs_db),KentkartLive('004',httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        assert c.get('/v1/kocaeli/lines/missing/vehicles').status_code==404 and not calls
        r=c.get('/v1/kocaeli/lines/446/vehicles');assert r.status_code==200 and len(r.json()['data'])==2
        assert r.json()['meta']['live'] and r.json()['meta']['source_kind']=='community_gtfs'
        assert c.get('/v1/kocaeli/lines/446/vehicles').json()['meta']['cached'] and len(calls)==2
