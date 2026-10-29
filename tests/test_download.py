import csv
import io
import json
import zipfile

import httpx
import pytest

from tools.gtfs_guncelle import catalog_archive, download
from turkiye_ulasim.gtfs import GtfsStore, build


class Interrupted(httpx.SyncByteStream):
    def __iter__(self):
        yield b'abc'
        raise httpx.ReadError('connection closed')


def test_download_resumes_an_interrupted_transfer(tmp_path):
    calls = []
    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return httpx.Response(200, stream=Interrupted())
        assert request.headers['range'] == 'bytes=3-'
        return httpx.Response(206, content=b'def', headers={'Content-Range': 'bytes 3-5/6'})
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        path = tmp_path/'file'
        download(client, 'https://example.org/file', path)
    assert path.read_bytes() == b'abcdef'


def test_ignored_range_restarts_file_instead_of_appending(tmp_path):
    path = tmp_path/'file'
    path.write_bytes(b'old-partial')
    with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b'complete'))) as client:
        download(client, 'https://example.org/file', path)
    assert path.read_bytes() == b'complete'


def test_ibb_catalog_csv_zip_and_authoritative_stop_repair(tmp_path):
    # Kaynakta tırnaklanmamış noktalı virgül isim sütununu kaydırıyor.
    resources = {
        'routes': 'route_id;route_short_name;route_long_name;route_type;route_code\n1;15F;KADIKÃ–Y;3;15F_G_D0\n',
        'stops': 'stop_id;stop_code;stop_name;stop_desc;stop_lat;stop_lon;location_type;\n5;291671;FAKÜLTE; İKTİSAT;direction: METRO;4,10E+13;2,91E+12;0;\n',
        'trips': 'trip_id;route_id;service_id;direction_id\n9;1;1;0\n',
        'calendar': 'service_id;start_date;end_date\n1;20260101;20261231\n',
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, 'w') as archive:
        archive.writestr('folder/stop_times.csv', 'trip_id;stop_id;stop_sequence\n9;5;1\n')
    entries = [{'name': name, 'format': 'CSV', 'url': 'https://example.org/'+name} for name in resources]
    entries.append({'name': 'stop_times', 'format': 'ZIP', 'url': 'https://example.org/times.zip'})
    def handler(request):
        if request.url.path == '/catalog':
            return httpx.Response(200, json={'success': True, 'result': {'resources': entries}})
        if request.url.path == '/times.zip':
            return httpx.Response(200, content=buffer.getvalue())
        if request.method == 'POST':
            assert b'291671' in request.content
            payload = json.dumps([{'SDURAKKODU':291671, 'SDURAKADI':'FAKÜLTE; İKTİSAT', 'KOORDINAT':'POINT (29.1 41.1)'}])
            return httpx.Response(200, text=f'<root><GetDurak_jsonResult xmlns="http://tempuri.org/">{payload}</GetDurak_jsonResult></root>')
        return httpx.Response(200, text=resources[request.url.path.lstrip('/')])
    with httpx.Client(transport=httpx.MockTransport(handler)) as client:
        archive = catalog_archive(client, 'https://example.org/catalog', tmp_path)
    db = tmp_path/'db.sqlite3'
    build(archive, db, ibb_csv=True)
    store = GtfsStore(db)
    assert store.line('1')['name'] == 'KADIKÖY'
    assert store.stop('5')['name'] == 'FAKÜLTE; İKTİSAT'
    assert store.stop('5')['latitude'] == 41.1
    store.db.close()
