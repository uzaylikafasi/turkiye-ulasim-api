import httpx
from fastapi.testclient import TestClient
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
from turkiye_ulasim.sources.izmir import IzmirLive


def test_health_does_not_claim_readiness_or_call_upstream():
    with TestClient(create_app(lambda:{})) as client:
        assert client.get('/healthz').json()['status']=='ok'
        assert client.get('/readyz').status_code==503
        rows=client.get('/v1/status').json()['data']
        assert all(not r['upstream_checked'] for r in rows)
        assert all(r['local_status']=='missing' for r in rows)


def test_status_reports_import_time_calendar_and_local_readability(gtfs_db):
    with TestClient(create_app(lambda:{c:(GtfsStore(gtfs_db),None) for c in ('izmir','istanbul','konya')})) as client:
        assert client.get('/readyz').status_code==200
        row=client.get('/v1/status').json()['data'][0]
        assert row['local_status']=='readable' and row['imported_at']
        assert row['calendar_end']=='20261009'
        assert row['lines']==2
        assert '/home/' not in str(row)


def test_broken_database_is_not_ready_and_hides_internal_error(gtfs_db):
    store=GtfsStore(gtfs_db)
    store.db.close()
    with TestClient(create_app(lambda:{'izmir':(store,None)})) as client:
        row=client.get('/v1/status').json()['data'][0]
        assert row['local_status']=='error'
        assert client.get('/readyz').status_code==503
        assert 'Cannot operate' not in str(row)


def test_status_tracks_observed_live_error_then_success(gtfs_db):
    calls=[]
    def handler(request):
        calls.append(request)
        return httpx.Response(500) if len(calls)==1 else httpx.Response(200,json={'HatOtobusKonumlari':[]})
    live=IzmirLive(httpx.AsyncClient(base_url="https://openapi.izmir.bel.tr/api/iztek", transport=httpx.MockTransport(handler)))
    with TestClient(create_app(lambda:{'izmir':(GtfsStore(gtfs_db),live)})) as client:
        assert client.get('/v1/izmir/lines/446/vehicles').status_code==502
        row=client.get('/v1/status').json()['data'][0]['live_observation']
        assert row['last_outcome']=='error' and row['last_error_type']=='SourceError'
        assert client.get('/v1/izmir/lines/446/vehicles').status_code==200
        row=client.get('/v1/status').json()['data'][0]['live_observation']
        assert row['last_outcome']=='success' and row['last_success_at']
        assert row['last_error_at']
    assert len(calls)==2
