import copy,json,sqlite3
from pathlib import Path
import httpx,pytest
from turkiye_ulasim.sources.mersin import MersinLive,normalize
from turkiye_ulasim.sources.base import SourceError,SourceUnsupported,SourceRateLimited
FIXTURES=Path(__file__).parent/'fixtures/mersin'
BODY=json.loads((FIXTURES/'vehicles-10M-G.json').read_text())


def test_real_nested_coordinates_accessibility_and_unknown_gps():
    rows,n=normalize(BODY,'10M-G')
    assert len(rows)==2 and not n and rows[0]['latitude']==36.82671333
    assert rows[0]['wheelchair_accessible'] is True and rows[0]['bike_rack'] is False
    assert rows[0]['observed_at'] is None and rows[0]['direction'] is None
    assert rows[0]['source_direction']=='G' and len(rows[0]['id'])==20
    assert BODY[0]['arac_no']['0'] not in str(rows) and 'sefer_saat' not in str(rows)
    assert normalize([], '10M-G')==([],0)


@pytest.mark.parametrize('body',[0,'0',None,{},[{'arac_no':{'0':'x'}}]])
def test_ambiguous_zero_or_schema_is_not_empty_success(body):
    with pytest.raises(SourceError):normalize(body,'10M-G')


def test_duplicate_conflict_invalid_position_and_unknown_flags():
    b=copy.deepcopy(BODY);extra=copy.deepcopy(b[0]);extra['enlem']['0']='36.9';b.append(extra)
    rows,n=normalize(b,'10M-G');assert n==1 and len(rows)==1
    b=copy.deepcopy(BODY);b[0]['enlem']['0']='NaN';b[1]['bisiklet_aparati']={'0':'unknown'}
    rows,n=normalize(b,'10M-G');assert len(rows)==1 and rows[0]['bike_rack'] is None


@pytest.mark.asyncio
async def test_exact_post_cache_separate_directions_quota_and_mapping():
    calls=[]
    def handler(r):
        calls.append(r);return httpx.Response(200,json=BODY)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        source=MersinLive(c,clock=lambda:0)
        def line(key):return {'code':'10M','source_route_code':key}
        a=await source.vehicles('10M-G',line=line('10M-G'))
        assert (await source.vehicles('10M-G',line=line('10M-G'))).cached and len(calls)==1
        b=await source.vehicles('10M-D',line=line('10M-D'));assert not b.cached and len(calls)==2
        assert calls[0].method=='POST' and b'hatno=10M-G' in calls[0].content and b'tipi=hattakiaraclar' in calls[0].content
        source.requests.extend([0]*28)
        with pytest.raises(SourceRateLimited):await source.vehicles('26M-G',line={'code':'26M','source_route_code':'26M-G'})
        with pytest.raises(SourceUnsupported):await source.vehicles('10M',line=line('10M-G'))


def test_api_validates_local_line_before_upstream(gtfs_db):
    from fastapi.testclient import TestClient
    from turkiye_ulasim.main import create_app
    from turkiye_ulasim.gtfs import GtfsStore
    with sqlite3.connect(gtfs_db) as db:db.execute('insert into lines values (?,?,?,?,?)',('10M-G','10M','Mersin',3,'10M-G'))
    calls=[]
    def handler(r):calls.append(r);return httpx.Response(200,json=BODY)
    def factory():return {'mersin':(GtfsStore(gtfs_db),MersinLive(httpx.AsyncClient(transport=httpx.MockTransport(handler))))}
    with TestClient(create_app(factory)) as c:
        assert c.get('/v1/mersin/lines/missing/vehicles').status_code==404 and not calls
        r=c.get('/v1/mersin/lines/10M-G/vehicles');assert r.status_code==200 and len(r.json()['data'])==2
        assert c.get('/v1/mersin/lines/10M-G/vehicles').json()['meta']['cached']
        assert c.get('/v1/mersin/stops/21050/arrivals').status_code==501
