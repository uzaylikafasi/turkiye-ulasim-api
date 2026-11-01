"""Sabit yerel hedefe, GET ile sınırlı halka açık köprü."""
import http.client
import json
import re
import threading
import time
from collections import deque

PREFIX = '/turkiye-ulasim-api'
PATH = re.compile(r'/(?:healthz|readyz|docs|openapi\.json|v1/(?:cities|status|(?:izmir|istanbul|konya|kahramanmaras|antalya|kocaeli|adana|gaziantep|erzurum|mardin|mugla|ordu|canakkale|duzce|burdur|nigde|kirklareli|osmaniye|tokat|kastamonu|sivas|edirne|sakarya|ankara|samsun)/(?:lines(?:/[A-Za-z0-9:_-]{1,80}(?:/(?:stops|shape|vehicles))?)?|stops/(?:nearby|[0-9A-Za-z_-]{1,40}(?:/arrivals)?))))\Z')
_lock = threading.Lock()
_slots = threading.BoundedSemaphore(8)
_ips = {}
_total = deque()


def proxy_ulasim(handler):
    path, _, query = handler.path.partition('?')
    if path != PREFIX and not path.startswith(PREFIX+'/'):
        return False
    target = path[len(PREFIX):] or '/docs'
    def reply(status, data, kind='application/json', retry=None):
        handler.send_response(status)
        handler.send_header('Content-Type', kind)
        handler.send_header('Cache-Control', 'no-store')
        handler.send_header('Access-Control-Allow-Origin', '*')
        handler.send_header('Content-Length', str(len(data)))
        if retry:
            handler.send_header('Retry-After', retry)
        handler.end_headers()
        handler.wfile.write(data)
    if handler.command != 'GET' or not PATH.fullmatch(target) or len(query)>2048:
        reply(404, b'{"error":"NOT_FOUND"}')
        return True
    ip = (handler.headers.get('CF-Connecting-IP') or handler.client_address[0])[:64]
    with _lock:
        now = time.monotonic()
        for key in list(_ips):
            if not _ips[key] or _ips[key][-1] <= now-60:
                del _ips[key]
        mine = _ips.setdefault(ip, deque())
        for queue in (mine, _total):
            while queue and queue[0] <= now-60:
                queue.popleft()
        allowed = len(mine)<60 and len(_total)<180
        if allowed:
            mine.append(now)
            _total.append(now)
    if not allowed or not _slots.acquire(blocking=False):
        reply(429, b'{"error":"RATE_LIMITED"}', retry='15')
        return True
    connection = http.client.HTTPConnection('127.0.0.1', 8010, timeout=25)
    try:
        try:
            connection.request('GET', target + ('?'+query if query else ''), headers={'Accept':'application/json'})
            response = connection.getresponse()
            data = response.read(4_000_001)
            kind = response.getheader('Content-Type','')
            if len(data)>4_000_000 or not ('application/json' in kind or target=='/docs' and 'text/html' in kind):
                raise ValueError()
            if target!='/docs':
                json.loads(data)
            retry = response.getheader('Retry-After','')
            reply(response.status, data, kind, retry if retry.isdigit() else None)
        except (OSError, ValueError, http.client.HTTPException):
            reply(502,b'{"error":"API_UNAVAILABLE"}')
    finally:
        connection.close()
        _slots.release()
    return True
