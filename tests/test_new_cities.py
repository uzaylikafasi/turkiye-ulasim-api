import pytest
from fastapi.testclient import TestClient
from turkiye_ulasim.cities import CITIES
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
from deployment.public_proxy import PATH


@pytest.mark.parametrize('city',[c.id for c in CITIES.values() if c.source_kind=='community_gtfs'])
def test_community_bus_cities_have_honest_capabilities_and_public_routes(city,gtfs_db):
    with TestClient(create_app(lambda:{city:(GtfsStore(gtfs_db),None)})) as client:
        listing=client.get('/v1/cities').json()['data']
        entry=next(c for c in listing if c['id']==city)
        assert entry['available'] and entry['source_kind']=='community_gtfs'
        assert entry['capabilities']['gtfs']
        assert entry['capabilities']['vehicles'] == (city in ('kocaeli','gaziantep'))
        data=client.get(f'/v1/{city}/lines/446').json()
        assert data['data']['mode']=='bus' and data['meta']['source_kind']=='community_gtfs'
        assert data['meta']['warnings']
        assert client.get(f'/v1/{city}/lines/446/vehicles').status_code==501
        assert client.get(f'/v1/{city}/stops/21050/arrivals').status_code==501
        assert PATH.fullmatch(f'/v1/{city}/lines/446/stops')
