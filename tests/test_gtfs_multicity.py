import copy
import csv
import io
import zipfile

import pytest
from fastapi.testclient import TestClient

from conftest import FILES
from turkiye_ulasim import gtfs
from turkiye_ulasim.main import create_app


def write_feed(path, files, delimiter=',', prefix=''):
    with zipfile.ZipFile(path, 'w') as archive:
        for name, rows in files.items():
            buffer = io.StringIO()
            csv.writer(buffer, delimiter=delimiter).writerows(rows)
            archive.writestr(prefix + name, '\ufeff' + buffer.getvalue())


def test_mixed_feed_excludes_trams_and_their_stops(tmp_path):
    files = copy.deepcopy(FILES)
    files['routes.txt'].append(['tram', 'T1', 'Tramvay', '0'])
    files['trips.txt'].append(['tram', '1', 'tram-trip', '0', ''])
    files['stop_times.txt'].append(['tram-trip', '10:00:00', '10:00:00', '10123', '1'])
    archive, db = tmp_path/'feed.zip', tmp_path/'feed.sqlite3'
    write_feed(archive, files, prefix='nested/')
    gtfs.build(archive, db)
    store = gtfs.GtfsStore(db)
    assert store.line('tram') is None
    assert store.stop('10123') is None
    assert store.line('446')['mode'] == 'bus'
    with TestClient(create_app(lambda: {'konya': (store, None)})) as client:
        assert client.get('/v1/konya/lines/446/vehicles').status_code == 501
        assert client.get('/v1/konya/stops/21050/arrivals').status_code == 501
        assert client.get('/v1/konya/lines/446/stops').status_code == 200


def test_ibb_semicolon_encoding_and_coordinates(tmp_path):
    files = copy.deepcopy(FILES)
    files['routes.txt'][0].append('route_code')
    files['routes.txt'][1] = ['446', '15F', 'KADIKÃ–Y - EÄ\x9eÄ°TÄ°M', '3', '15F_G_D0']
    files['routes.txt'][2].append('90_G_D0')
    files['stops.txt'][1][2:] = ['410.191.700.005.564', '286.843.529.999.755']
    archive, db = tmp_path/'feed.zip', tmp_path/'feed.sqlite3'
    write_feed(archive, files, delimiter=';')
    gtfs.build(archive, db, ibb_csv=True)
    store = gtfs.GtfsStore(db)
    assert store.line('446')['name'] == 'KADIKÖY - EĞİTİM'
    assert store.line('446')['source_route_code'] == '15F_G_D0'
    stop = store.stop('21050')
    assert stop['latitude'] == 41.0191700005564
    assert stop['longitude'] == 28.6843529999755
    store.db.close()


def test_failed_build_preserves_previous_database_and_removes_temporary(tmp_path, gtfs_db):
    before = gtfs_db.read_bytes()
    broken = tmp_path / 'broken.zip'
    write_feed(broken, {'routes.txt': FILES['routes.txt']})
    with pytest.raises(ValueError, match='eksik'):
        gtfs.build(broken, gtfs_db)
    assert gtfs_db.read_bytes() == before
    assert list(tmp_path.glob('*.tmp')) == []


def test_calendar_dates_without_calendar(tmp_path):
    from datetime import date
    files = copy.deepcopy(FILES)
    del files['calendar.txt']
    files['calendar_dates.txt'] = [['service_id', 'date', 'exception_type'], ['1','20261231','1'], ['1','20300101','2']]
    archive, db = tmp_path/'feed.zip', tmp_path/'feed.sqlite3'
    write_feed(archive, files)
    gtfs.build(archive, db)
    store = gtfs.GtfsStore(db)
    assert not store.calendar_expired(date(2026,12,31))
    assert store.calendar_expired(date(2027,1,1))
    store.db.close()


def test_conflicting_stop_sequence_uses_another_trip(tmp_path):
    files = copy.deepcopy(FILES)
    # En uzun sefer aynı sırada iki farklı durak taşıyor; kısa sefer seçilmeli.
    files['stop_times.txt'].append(['uzun', '07:05:00', '07:05:00', '21056', '2'])
    archive, db = tmp_path/'feed.zip', tmp_path/'feed.sqlite3'
    write_feed(archive, files)
    gtfs.build(archive, db)
    store = gtfs.GtfsStore(db)
    assert [s['id'] for s in store.line_stops('446', 0)] == ['21050']
    assert any('aday sefer atlandı' in w for w in store.warnings())
    store.db.close()


def test_all_conflicting_candidates_omit_route_order_with_warning(tmp_path):
    files = copy.deepcopy(FILES)
    files['trips.txt'] = [files['trips.txt'][0]] + [['446','1',f'bad-{i}','0','s1'] for i in range(3)]
    files['stop_times.txt'] = [files['stop_times.txt'][0]] + [
        [f'bad-{i}','07:00:00','07:00:00',stop,'1'] for i in range(3) for stop in ('21050','21056')]
    archive, db = tmp_path/'feed.zip', tmp_path/'feed.sqlite3'
    write_feed(archive, files)
    gtfs.build(archive, db)
    store = gtfs.GtfsStore(db)
    assert store.line_stops('446',0) == []
    assert store.line_shape('446',0) == []
    assert any('üç aday sefer de tutarsız' in w for w in store.warnings())
    store.db.close()


def test_identical_shape_points_are_deduplicated(tmp_path):
    files=copy.deepcopy(FILES)
    files['shapes.txt'].append(files['shapes.txt'][1][:])
    archive,db=tmp_path/'feed.zip',tmp_path/'feed.sqlite3'
    write_feed(archive,files)
    gtfs.build(archive,db)
    store=gtfs.GtfsStore(db)
    assert len(store.line_shape('446',0))==2
    assert any('birebir aynı güzergâh' in w for w in store.warnings())
    store.db.close()


def test_conflicting_shape_coordinates_preserve_existing_database(tmp_path,gtfs_db):
    files=copy.deepcopy(FILES)
    files['shapes.txt'].append(['s1','39.0','27.0534','1'])
    archive=tmp_path/'conflict.zip'
    write_feed(archive,files)
    before=gtfs_db.read_bytes()
    with pytest.raises(ValueError,match='farklı koordinatlar'):
        gtfs.build(archive,gtfs_db)
    assert gtfs_db.read_bytes()==before
