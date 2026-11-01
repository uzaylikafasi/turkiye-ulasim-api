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


from turkiye_ulasim.sources.kentkart import normalize_arrivals

def arrival_body(city='kocaeli'):
    return json.loads((Path(__file__).parent/f'fixtures/kentkart/arrivals-{city}.json').read_text())


def arrival_stop(body):
    s=body['stopInfo'];bus=body['busList'][0]
    return {'id':s['busStopid'],'latitude':float(s['lat']),'longitude':float(s['lng']),
            'lines':[{'id':bus['routeCode'],'code':bus['displayRouteCode']}]}


@pytest.mark.parametrize('city',['kocaeli','gaziantep','sivas','edirne'])
def test_real_arrivals_minutes_stops_and_static_mapping(city):
    b=arrival_body(city);stop=arrival_stop(b);rows=normalize_arrivals(b,stop)
    first=next(x for x in rows if x['vehicle_id']==b['busList'][0]['busId'])
    assert first['eta_seconds']==int(b['busList'][0]['timeDiff'])*60
    assert first['stops_away']==int(b['busList'][0]['stopDiff'])
    assert first['line_id']==stop['lines'][0]['id'] and first['stale'] is None
    stop['lines']=[];assert all(x['line_id'] is None for x in normalize_arrivals(b,stop))
    b['busList']=[];assert normalize_arrivals(b,stop)==[]  # routeList is not live arrivals


@pytest.mark.parametrize('fault',['status','stop','buslist','row','shape','direction'])
def test_arrival_source_errors_fail_closed(fault):
    b=arrival_body();stop=arrival_stop(b)
    if fault=='status':b['result']=None
    if fault=='stop':b['stopInfo']['busStopid']='different'
    if fault=='buslist':b['busList']=None
    if fault=='row':b['busList']=[None]
    if fault=='shape':b['busList'][0]['shapeId']='other'
    if fault=='direction':b['busList'][0]['direction']='3'
    with pytest.raises(SourceError):normalize_arrivals(b,stop)


def test_arrival_unknown_values_bus_filter_and_leading_zero():
    b=arrival_body('gaziantep');stop=arrival_stop(b);r=b['busList'][0]
    r.update(timeDiff='NaN',stopDiff='2.5',lat='0',disabledPerson='unknown')
    row=normalize_arrivals(b,stop)[-1]
    assert row['eta_seconds'] is None and row['stops_away'] is None and row['latitude'] is None
    assert row['wheelchair_accessible'] is None and row['source_line_id']=='00570'
    r['timeDiff']='1e308';assert normalize_arrivals(b,stop)[-1]['eta_seconds'] is None
    for r in b['busList']:r['routeType']='6'
    assert normalize_arrivals(b,stop)==[]


@pytest.mark.asyncio
async def test_arrival_cache_identity_and_shared_vehicle_budget():
    b=arrival_body();stop=arrival_stop(b);calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=b)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        live=KentkartLive('004',c,clock=lambda:0)
        a=await live.arrivals_for_stop(stop);cached=await live.arrivals_for_stop(stop)
        assert cached.cached and cached.fetched_at==a.fetched_at and len(calls)==1
        q=calls[0].url.params;assert q['busStopId']==stop['id'] and q['region']=='004'
        changed=copy.deepcopy(stop);changed['lines']=[]
        assert (await live.arrivals_for_stop(changed)).data[0]['line_id'] is None and len(calls)==2
        live.requests.extend([0]*28)
        with pytest.raises(SourceRateLimited):await live.vehicles('41010',line={'code':'10'})
        assert (await live.arrivals_for_stop(stop)).cached
        stop['latitude']=None
        with pytest.raises(SourceUnsupported):await live.arrivals_for_stop(stop)


def test_arrivals_api_static_validation_and_capability(gtfs_db):
    from fastapi.testclient import TestClient
    from turkiye_ulasim.main import create_app
    from turkiye_ulasim.gtfs import GtfsStore
    b=arrival_body();b['stopInfo']['busStopid']='21050';calls=[]
    b['busList'][0].update(routeCode='446',displayRouteCode='446',shapeId='4460')
    def handler(r):calls.append(r);return httpx.Response(200,json=b)
    def factory():return {'kocaeli':(GtfsStore(gtfs_db),KentkartLive('004',httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        entry=next(x for x in c.get('/v1/cities').json()['data'] if x['id']=='kocaeli')
        assert entry['capabilities']['arrivals']
        assert c.get('/v1/kocaeli/stops/missing/arrivals').status_code==404 and not calls
        r=c.get('/v1/kocaeli/stops/21050/arrivals');assert r.status_code==200
        assert r.json()['data'][0]['line_id']=='446' and r.json()['meta']['live']
        assert c.get('/v1/kocaeli/stops/21050/arrivals').json()['meta']['cached'] and len(calls)==1


@pytest.mark.parametrize('city,region,line,code',[
    ('adana','003','00112','112'),('antalya','026','00080','KL08')])
@pytest.mark.asyncio
async def test_adana_antalya_real_paths_and_shared_arrivals(city,region,line,code):
    fixture_dir=Path(__file__).parent/'fixtures/kentkart';calls=[]
    def handler(r):
        calls.append(r)
        name=f'vehicles-{city}-{r.url.params["direction"]}.json' if r.url.path.endswith('pathInfo') else f'arrivals-{city}.json'
        return httpx.Response(200,json=json.loads((fixture_dir/name).read_text()))
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        live=KentkartLive(region,c)
        vehicles=await live.vehicles(line,line={'code':code})
        assert vehicles.data and all(r['line_id']==line for r in vehicles.data)
        assert (await live.vehicles(line,line={'code':code})).cached
        body=arrival_body(city);stop=arrival_stop(body);arrivals=await live.arrivals_for_stop(stop)
        assert arrivals.data and len(calls)==3 and len(live.requests)==3
        assert all(r.url.params['region']==region for r in calls)
        assert (await live.arrivals_for_stop(stop)).cached


@pytest.mark.asyncio
async def test_known_no_result_and_antalya_identity_mismatch_remain_unsupported():
    fixture_dir=Path(__file__).parent/'fixtures/kentkart'
    for filename,region,line,code in [('no-path-adana.json','003','00100','100'),
                                     ('mismatch-antalya35.json','026','00354','35')]:
        body=json.loads((fixture_dir/filename).read_text())
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,json=body))) as c:
            with pytest.raises(SourceUnsupported):await KentkartLive(region,c).vehicles(line,line={'code':code})
    body['result']={'code':3,'message':'different failure'}
    with pytest.raises(SourceError):normalize(body,'00354','35',0)
