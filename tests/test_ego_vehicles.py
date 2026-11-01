import copy,json
from pathlib import Path
from datetime import datetime
import httpx,pytest
from turkiye_ulasim.sources.ankara import normalize_vehicles,normalize,AnkaraLive
from turkiye_ulasim.sources.base import SourceError,SourceRateLimited
P=Path(__file__).parent/'fixtures/ego'
BODY=json.loads((P/'vehicles263.json').read_text())
NOW=datetime.fromisoformat('2026-11-01T09:36:20+03:00')


def test_real_hat_response_excludes_timetable_and_preserves_unknown_direction():
    rows,warnings=normalize_vehicles(BODY,'263',NOW)
    assert len(rows)==2 and rows[0]['id']=='13-216'
    assert rows[0]['age_seconds']==61 and rows[0]['stale'] is False
    assert rows[1]['stale'] is True
    assert rows[0]['source_direction']=='4' and rows[0]['direction'] is None
    assert all('eta_seconds' not in r for r in rows)


@pytest.mark.parametrize('fault',['identity','code','status','schema'])
def test_source_identity_or_failure_is_not_empty_success(fault):
    b=copy.deepcopy(BODY)
    if fault=='identity':b['table'][1]['hat_no']='220'
    if fault=='code':b['table'][1]['hat_kod']='220'
    if fault=='status':b['status']='FALSE'
    if fault=='schema':b['table']={}
    with pytest.raises(SourceError):normalize_vehicles(b,'263',NOW)


def test_gps_unknown_invalid_and_latest_conflicting_records():
    b=copy.deepcopy(BODY);b['table'][1]['konum_tarihi']='01.01.0001 00:00:00'
    assert normalize_vehicles(b,'263',NOW)[0][0]['stale'] is None
    b['table'][1]['konum_tarihi']='01.11.2026 12:00:00'
    assert normalize_vehicles(b,'263',NOW)[0][0]['observed_at'] is None
    b=copy.deepcopy(BODY);r=dict(b['table'][1],konum_tarihi='01.11.2026 09:36:10',lat='40.001')
    b['table'].append(r);rows,_=normalize_vehicles(b,'263',NOW)
    assert len(rows)==2 and rows[0]['latitude']==40.001
    b['table'].append(dict(r,lat='40.002'))
    assert len(normalize_vehicles(b,'263',NOW)[0])==1
    b=copy.deepcopy(BODY);b['table'][1]['lat']='NaN'
    assert len(normalize_vehicles(b,'263',NOW)[0])==1


@pytest.mark.asyncio
async def test_vehicle_call_has_no_stop_parameter_and_shares_source_budget():
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        live=AnkaraLive(c,clock=lambda:0)
        a=await live.vehicles('263',line={'code':'263'});b=await live.vehicles('263',line={'code':'263'})
        assert a.data and b.cached and len(calls)==1
        assert calls[0].url.params['FNC']=='Otobus' and 'DURAK' not in calls[0].url.params
        live.requests.extend([0]*29)
        with pytest.raises(SourceRateLimited):await live.arrivals('263')
        with pytest.raises(SourceError):await live.vehicles('263',line={'code':'wrong'})


def test_vehicle_api_validates_static_line_and_capabilities(tmp_path):
    from tools.ego_guncelle import parse,build
    from turkiye_ulasim.gtfs import GtfsStore
    from turkiye_ulasim.main import create_app
    from fastapi.testclient import TestClient
    html=(P/'263.html').read_text();dest=tmp_path/'db';build(dest,parse(html).lines,lambda _:html);calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    def factory():return {'ankara':(GtfsStore(dest),AnkaraLive(httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        assert c.get('/v1/ankara/lines/missing/vehicles').status_code==404 and not calls
        r=c.get('/v1/ankara/lines/263/vehicles');assert r.status_code==200 and len(r.json()['data'])==2
        assert c.get('/v1/ankara/lines/263/vehicles').json()['meta']['cached'] and len(calls)==1
        city=next(x for x in c.get('/v1/cities').json()['data'] if x['id']=='ankara')
        assert city['capabilities']['vehicles'] and city['capabilities']['arrivals']
        assert not city['capabilities']['nearby']
