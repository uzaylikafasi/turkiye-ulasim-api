import copy,json,sqlite3
from pathlib import Path
import httpx,pytest
from turkiye_ulasim.sources.sakus import SakusLive,normalize
from turkiye_ulasim.sources.base import SourceError,SourceUnsupported,SourceRateLimited
BODY=json.loads((Path(__file__).parent/'fixtures/sakus/vehicles-50.json').read_text())
LINE={'code':'M1','source_route_code':'50'}


def test_real_geojson_variants_unknown_time_and_fields():
    rows,conflicts=normalize(BODY,'50','M1')
    assert len(rows)==4 and not conflicts
    assert {r['source_route_id'] for r in rows}=={'802','803'}
    assert rows[0]['latitude']==40.773163 and rows[0]['longitude']==30.395058
    assert rows[0]['stale'] is None and rows[0]['direction'] is None
    assert 'etaS' not in rows[0] and 'plate' not in rows[0]


@pytest.mark.parametrize('fault',['schema','line','code','route'])
def test_source_schema_and_identity_fail_closed(fault):
    b=copy.deepcopy(BODY)
    if fault=='schema':b={}
    if fault=='line':b[0]['lineId']=5
    if fault=='code':b[0]['lineNumber']='other'
    if fault=='route':b[0]['routeId']=None
    with pytest.raises(SourceError):normalize(b,'50','M1')


def test_conflicting_vehicle_and_invalid_coordinates_are_omitted():
    b=copy.deepcopy(BODY);r=copy.deepcopy(b[0]);r['routeId']=803;b.append(r)
    b[1]['location']['coordinates']=[0,0]
    rows,conflicts=normalize(b,'50','M1')
    assert conflicts==1 and len(rows)==2 and all(r['id']!='3' for r in rows)


@pytest.mark.asyncio
async def test_parent_cache_is_shared_between_variants_and_budget():
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        source=SakusLive(client,clock=lambda:0)
        a=await source.vehicles('50:802',line=LINE);b=await source.vehicles('50:803',line=LINE)
        assert len(a.data)==1 and len(b.data)==3 and b.cached and len(calls)==1
        assert calls[0].url.params['LineId']=='50' and 'AsisId' not in calls[0].url.params
        assert calls[0].headers['Origin']=='https://sakus.sakarya.bel.tr'
        source.requests.extend([0]*29)
        with pytest.raises(SourceRateLimited):await source.vehicles('5:86',line={'code':'4','source_route_code':'5'})
        with pytest.raises(SourceUnsupported):await source.vehicles('50',line=LINE)


def test_api_uses_exact_local_variant(gtfs_db):
    from fastapi.testclient import TestClient
    from turkiye_ulasim.main import create_app
    from turkiye_ulasim.gtfs import GtfsStore
    with sqlite3.connect(gtfs_db) as db:
        db.executemany('insert into lines values (?,?,?,?,?)',[(f'50:{r}','M1','M1',3,'50') for r in ['802','803']])
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    def factory():return {'sakarya':(GtfsStore(gtfs_db),SakusLive(httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        assert c.get('/v1/sakarya/lines/missing/vehicles').status_code==404 and not calls
        assert len(c.get('/v1/sakarya/lines/50:802/vehicles').json()['data'])==1
        b=c.get('/v1/sakarya/lines/50:803/vehicles').json()
        assert len(b['data'])==3 and b['meta']['cached'] and len(calls)==1
        assert c.get('/v1/sakarya/stops/21050/arrivals').status_code==501
