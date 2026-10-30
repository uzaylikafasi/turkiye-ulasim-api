import io
import json
import shutil
import sqlite3
from fastapi.testclient import TestClient
from turkiye_ulasim.gtfs import GtfsStore
from turkiye_ulasim.main import create_app
from tools import yenile
from deployment import public_proxy


def test_atomic_refresh_without_restarting_application(gtfs_db):
    store=GtfsStore(gtfs_db)
    with TestClient(create_app(lambda:{'izmir':(store,None)})) as client:
        first=client.get('/v1/izmir/lines/446').json()['data']['name']
        replacement=gtfs_db.with_suffix('.next')
        shutil.copyfile(gtfs_db,replacement)
        with sqlite3.connect(replacement) as db:
            db.execute("UPDATE lines SET long_name='YENİ HAT' WHERE id='446'")
        replacement.replace(gtfs_db)
        assert client.get('/v1/izmir/lines/446').json()['data']['name']=='YENİ HAT'
        assert first!='YENİ HAT'


def test_update_failure_is_recorded_and_other_cities_continue(tmp_path,monkeypatch):
    monkeypatch.setattr(yenile,'DATA_DIR',tmp_path)
    calls=[]
    def update(city):
        calls.append(city)
        if city=='istanbul':
            raise ValueError('private internal path must not be published')
    monkeypatch.setattr(yenile,'update',update)
    assert yenile.run()==1
    report=json.loads((tmp_path/'update-status.json').read_text())
    assert calls==['izmir','istanbul','konya']
    assert report['status']=='partial_failure'
    assert report['cities']['konya']['status']=='success'
    assert 'private' not in str(report)


def test_public_proxy_only_allows_specific_paths():
    for path in ['/v1/cities','/readyz','/v1/kahramanmaras/lines/9576:1/vehicles']:
        assert public_proxy.PATH.fullmatch(path)
    for path in ['/v1/../secret','/admin','/v1/izmir/lines/%2e%2e','/v1/ankara/lines']:
        assert not public_proxy.PATH.fullmatch(path)
