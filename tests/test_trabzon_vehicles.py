import copy,json
from datetime import datetime
from pathlib import Path
import httpx,pytest
from turkiye_ulasim.sources.trabzon import TrabzonLive,normalize_vehicles
from turkiye_ulasim.sources.base import SourceError,SourceRateLimited
BODY=json.loads((Path(__file__).parent/'fixtures/trabzon/vehicles.json').read_text())
NOW=datetime.fromisoformat('2026-11-01T12:00:00+03:00')


def test_real_projected_vehicle_fields_and_privacy():
    b=copy.deepcopy(BODY);b['SonucData'][0].update(Tarih='01.11.2026 11:59:40',SoforAdSoyad='private',SoforGsm='private')
    rows,_=normalize_vehicles(b,NOW);r=rows[0]
    assert r['line_id']=='59:94' and r['source_line_code']=='208-B'
    assert 40<r['latitude']<42 and 39<r['longitude']<41
    assert r['source_coordinate_system']=='EPSG:4326'
    assert r['age_seconds']==20 and r['stale'] is False
    assert 'Sofor' not in str(rows) and 'private' not in str(rows)


def test_old_invalid_future_and_duplicate_measurements():
    b=copy.deepcopy(BODY);r=b['SonucData'][0];r['Tarih']='01.11.2026 11:00:00'
    rows,_=normalize_vehicles(b,NOW);assert rows[0]['stale'] is True
    r['Tarih']='01.01.0001 00:00:00';assert normalize_vehicles(b,NOW)[0][0]['observed_at'] is None
    r['Tarih']='01.11.2026 15:00:00';assert normalize_vehicles(b,NOW)[0][0]['stale'] is None
    r['KonumX']='NaN';assert len(normalize_vehicles(b,NOW)[0])==2
    b=copy.deepcopy(BODY);b['SonucData'][0]['Tarih']='01.11.2026 11:59:00'
    r=dict(b['SonucData'][0],Tarih='01.11.2026 11:59:40',KonumX='39.71')
    b['SonucData'].append(r);rows,_=normalize_vehicles(b,NOW);assert len(rows)==3 and rows[0]['longitude']==39.71
    b['SonucData'].append(dict(r,KonumX='39.72'))
    assert len(normalize_vehicles(b,NOW)[0])==2


@pytest.mark.asyncio
async def test_global_feed_is_cached_but_filtered_for_each_variant():
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        live=TrabzonLive(c,clock=lambda:0)
        a=await live.vehicles('59:94',line={'code':'208-B'})
        b=await live.vehicles('20:57',line={'code':'128'})
        missing=await live.vehicles('1:36',line={'code':'103'})
        assert len(a.data)==1 and a.data[0]['line_id']=='59:94'
        assert len(b.data)==1 and b.data[0]['line_id']=='20:57' and b.cached
        assert missing.data==[] and missing.cached and len(calls)==1
        assert calls[0].method=='POST' and json.loads(calls[0].content)=={}
        with pytest.raises(SourceError):await live.vehicles('59:94',line={'code':'wrong'})


@pytest.mark.asyncio
async def test_business_failure_and_rate_limit_are_not_empty_success():
    for response,expected in [(httpx.Response(200,json={'SonucDurum':False,'SonucData':None}),SourceError),(httpx.Response(429),SourceRateLimited)]:
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:response)) as c:
            with pytest.raises(expected):await TrabzonLive(c).vehicles('59:94',line={'code':'208-B'})
    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,json=BODY))) as c:
        live=TrabzonLive(c,clock=lambda:0);live.requests.extend([0]*30)
        with pytest.raises(SourceRateLimited):await live.vehicles('59:94',line={'code':'208-B'})


def test_live_api_only_publishes_the_requested_variant(tmp_path):
    from fastapi.testclient import TestClient
    from tools.trabzon_guncelle import catalog,build
    from turkiye_ulasim.gtfs import GtfsStore
    from turkiye_ulasim.main import create_app
    from test_trabzon import HTML,fetch
    dest=tmp_path/'db';build(dest,catalog(HTML),fetch)
    body=copy.deepcopy(BODY);body['SonucData'][0].update(HatId=1,GuzergahId=36,HatKod='103')
    def factory():return {'trabzon':(GtfsStore(dest),TrabzonLive(httpx.AsyncClient(transport=httpx.MockTransport(lambda _:httpx.Response(200,json=body)))))}
    with TestClient(create_app(factory)) as c:
        r=c.get('/v1/trabzon/lines/1:36/vehicles');assert r.status_code==200
        assert len(r.json()['data'])==1 and r.json()['data'][0]['line_id']=='1:36'
        assert c.get('/v1/trabzon/lines/1:39/vehicles').json()['data']==[]


def test_mixed_observed_coordinate_formats_are_explicit():
    b=copy.deepcopy(BODY)
    b['SonucData'][1].update(KonumX='4422323.732244811',KonumY='5013661.1388476975')
    rows,_=normalize_vehicles(b,NOW)
    assert rows[0]['source_coordinate_system']=='EPSG:4326'
    assert rows[1]['source_coordinate_system']=='EPSG:3857'
    assert all(40<r['latitude']<42 and 39<r['longitude']<41 for r in rows)
