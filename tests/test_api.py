from datetime import date

import httpx
from fastapi.testclient import TestClient

from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
from turkiye_ulasim.sources.izmir import BASE_URL, IzmirLive


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def make_client(gtfs_db, handler, clock=None):
    live = IzmirLive(httpx.AsyncClient(base_url=BASE_URL, transport=httpx.MockTransport(handler)),
                     clock=clock or Clock())
    return TestClient(create_app(lambda: {"izmir": (GtfsStore(gtfs_db), live)}))


def no_upstream(request):
    raise AssertionError(f"kaynağa gitmemeliydi: {request.url}")


def test_gtfs_keeps_the_longest_trip_per_direction_and_its_shape(gtfs_db):
    store = GtfsStore(gtfs_db)
    assert [s["id"] for s in store.line_stops("446", 0)] == ["21056", "21050"]
    assert [s["id"] for s in store.line_stops("446", 1)] == ["21050"]
    assert store.line_shape("446", 0) == [[38.515, 27.0534], [38.5123, 27.0513]]
    assert store.line("446")["directions"] == [0, 1]
    assert store.calendar_expired(date(2026, 10, 29)) and not store.calendar_expired(date(2026, 10, 1))


def test_line_search_folds_turkish_case(gtfs_db):
    with make_client(gtfs_db, no_upstream) as client:
        assert [l["id"] for l in client.get("/v1/izmir/lines?q=ışıkkent").json()["data"]] == ["90"]
        assert [l["id"] for l in client.get("/v1/izmir/lines?q=iskele").json()["data"]] == ["446"]


def test_stop_lists_its_lines_and_nearby_is_sorted(gtfs_db):
    with make_client(gtfs_db, no_upstream) as client:
        stop = client.get("/v1/izmir/stops/21050").json()["data"]
        assert [l["id"] for l in stop["lines"]] == ["446"]
        near = client.get("/v1/izmir/stops/nearby?latitude=38.5124&longitude=27.0514&radius=1000").json()["data"]
        assert [s["id"] for s in near] == ["21050", "21056"]
        assert near[0]["distance_m"] < near[1]["distance_m"]


def test_vehicles_parse_comma_decimals_and_drop_zero_positions(gtfs_db):
    def handler(request):
        assert request.url.path == "/api/iztek/hatotobuskonumlari/446"
        return httpx.Response(200, json={"HataMesaj": "", "HatOtobusKonumlari": [
            {"OtobusId": 1, "Yon": 0, "KoorX": "38,49866833", "KoorY": "27,056685"},
            {"OtobusId": 2, "Yon": 1, "KoorX": "0", "KoorY": "0"},
        ]})

    with make_client(gtfs_db, handler) as client:
        body = client.get("/v1/izmir/lines/446/vehicles").json()
    assert body["data"] == [{"id": "1", "line_id": "446", "source_direction": 0, "latitude": 38.49866833,
                             "longitude": 27.056685, "position_confidence": "single"}]
    assert body["meta"]["live"] is True and "fetched_at" in body["meta"]


def test_duplicate_vehicle_picks_the_entry_that_moved(gtfs_db):
    stale = {"OtobusId": 7, "Yon": 0, "KoorX": "38,3918", "KoorY": "27,15354333"}
    polls = iter([
        [stale, {"OtobusId": 7, "Yon": 0, "KoorX": "38,47055", "KoorY": "27,08509"}],
        [{"OtobusId": 7, "Yon": 0, "KoorX": "38,47073", "KoorY": "27,08526"}, stale],
    ])
    clock = Clock()

    def handler(request):
        return httpx.Response(200, json={"HataMesaj": "", "HatOtobusKonumlari": next(polls)})

    with make_client(gtfs_db, handler, clock) as client:
        first = client.get("/v1/izmir/lines/446/vehicles").json()
        assert first["data"][0]["position_confidence"] == "ambiguous"
        assert first["meta"]["warnings"]
        clock.now += 15
        second = client.get("/v1/izmir/lines/446/vehicles").json()["data"][0]
    assert second["position_confidence"] == "moved"
    assert (second["latitude"], second["longitude"]) == (38.47073, 27.08526)


def test_arrivals_are_sorted_by_stops_away(gtfs_db):
    def handler(request):
        assert request.url.path == "/api/iztek/duragayaklasanotobusler/21050"
        return httpx.Response(200, json=[
            {"KalanDurakSayisi": 11, "HattinYonu": 1, "KoorY": "27,05", "KoorX": "38,52", "EngelliMi": True,
             "BisikletAparatliMi": False, "HatNumarasi": 346, "HatAdi": "EVKA.5 - EGEKENT", "OtobusId": 11876},
            {"KalanDurakSayisi": 2, "HattinYonu": 0, "KoorY": "0", "KoorX": "0", "EngelliMi": False,
             "BisikletAparatliMi": True, "HatNumarasi": 446, "HatAdi": "EVKA.5 - BOSTANLI", "OtobusId": 1706},
        ])

    with make_client(gtfs_db, handler) as client:
        data = client.get("/v1/izmir/stops/21050/arrivals").json()["data"]
    assert [(a["line_id"], a["stops_away"]) for a in data] == [("446", 2), ("346", 11)]
    assert data[0]["latitude"] is None and data[1]["wheelchair_accessible"] is True


def test_source_failures_become_502(gtfs_db):
    def handler(request):
        return httpx.Response(500, text="boom")

    with make_client(gtfs_db, handler) as client:
        response = client.get("/v1/izmir/lines/446/vehicles")
    assert response.status_code == 502 and "HTTP 500" in response.json()["error"]


def test_bad_input_never_reaches_source(gtfs_db):
    with make_client(gtfs_db, no_upstream) as client:
        for path in ("/v1/unknown-city/lines", "/v1/izmir/lines/999/vehicles", "/v1/izmir/lines/abc/vehicles",
                     "/v1/izmir/stops/99999/arrivals", "/v1/izmir/lines/446/stops?direction=2",
                     "/v1/izmir/stops/nearby?latitude=91&longitude=27"):
            assert client.get(path).status_code in (404, 422), path


def test_line_pagination_exposes_remaining_results(gtfs_db):
    with make_client(gtfs_db, no_upstream) as client:
        first = client.get('/v1/izmir/lines?limit=1').json()
        second = client.get('/v1/izmir/lines?limit=1&offset=1').json()
        assert first['meta']['pagination']['has_more'] is True
        assert second['meta']['pagination']['has_more'] is False
        assert first['data'][0]['id'] != second['data'][0]['id']
        assert client.get('/v1/izmir/lines?limit=501').status_code == 422
