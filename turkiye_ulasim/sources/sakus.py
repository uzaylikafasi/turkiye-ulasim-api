"""SAKUS araçları: belediye hat kimliği ve kaynak güzergâhı birlikte korunur."""
import asyncio
import math
import time
from collections import OrderedDict, deque
import httpx
from .base import LiveResult, SourceError, SourceRateLimited, SourceUnsupported

URL = 'https://sbbpublicapi.sakarya.bel.tr/api/v1/VehicleTracking'
HEADERS = {'Origin': 'https://sakus.sakarya.bel.tr', 'Referer': 'https://sakus.sakarya.bel.tr/'}


def normalize(body, parent, code):
    if not isinstance(body, list):
        raise SourceError('SAKUS araç şeması değişti')
    known, conflicts = {}, set()
    for row in body:
        if not isinstance(row, dict) or str(row.get('lineId')) != parent or row.get('lineNumber') != code:
            raise SourceError('SAKUS araç hat kimliği/kodu eşleşmedi')
        route, vehicle = str(row.get('routeId', '')), str(row.get('busNumber', ''))
        if not route.isdigit() or int(route) <= 0 or not vehicle.isdigit() or int(vehicle) <= 0:
            raise SourceError('SAKUS araç/güzergâh kimliği geçersiz')
        try:
            location = row['location']
            if location['type'] != 'Point' or len(location['coordinates']) != 2:
                raise ValueError()
            lon, lat = map(float, location['coordinates'])
            if not (35 < lat < 43 and 25 < lon < 45):
                continue
        except (TypeError, KeyError, ValueError):
            continue
        heading = row.get('headingDegree')
        heading = heading if isinstance(heading, (int, float)) and not isinstance(heading, bool) and math.isfinite(heading) and 0 <= heading < 360 else None
        item = {'id': vehicle, 'line_id': parent + ':' + route, 'source_line_id': parent,
                'source_route_id': route, 'source_direction': None, 'direction': None,
                'latitude': lat, 'longitude': lon, 'heading_degrees': heading,
                'observed_at': None, 'age_seconds': None, 'stale': None, 'position_confidence': 'single'}
        if vehicle in known and known[vehicle] != item:
            conflicts.add(vehicle)
        else:
            known[vehicle] = item
    return [item for key, item in known.items() if key not in conflicts], len(conflicts)


class SakusLive:
    def __init__(self, client=None, clock=time.monotonic):
        self.client = client or httpx.AsyncClient(timeout=15)
        self.clock = clock
        self.lock = asyncio.Lock()
        self.cache = OrderedDict()
        self.requests = deque()

    async def vehicles(self, line_id, *, line):
        parts = line_id.split(':')
        if len(parts) != 2 or any(not p.isdigit() or int(p) <= 0 for p in parts) or line.get('source_route_code') != parts[0]:
            raise SourceUnsupported('SAKUS kaynak hat/güzergâh eşlemesi eksik')
        parent, _ = parts
        key = (parent, line['code'])
        async with self.lock:
            now = self.clock()
            result = None
            if key in self.cache:
                expires, saved = self.cache[key]
                if expires > now:
                    self.cache.move_to_end(key)
                    result = LiveResult(saved.data, saved.warnings, saved.fetched_at, True)
                else:
                    del self.cache[key]
            if result is None:
                while self.requests and now - self.requests[0] >= 60:
                    self.requests.popleft()
                if len(self.requests) >= 30:
                    raise SourceRateLimited(max(1, math.ceil(60 - now + self.requests[0])), 'SAKUS', 'dakikalık')
                self.requests.append(now)
                try:
                    response = await self.client.get(URL, params={'LineId': parent}, headers=HEADERS)
                    if response.status_code == 429:
                        raise SourceRateLimited(60, 'SAKUS', 'dakikalık')
                    response.raise_for_status()
                    rows, conflicts = normalize(response.json(), parent, line['code'])
                except (httpx.HTTPError, ValueError) as exc:
                    raise SourceError('SAKUS araç kaynağı okunamadı') from exc
                result = LiveResult(rows, [
                    'Belediye LineId ile ASIS kimliği farklıdır; araçlar tam hatId:routeId kimliğine süzülür. Gidiş/dönüş anlamı tahmin edilmez.',
                    'Kaynak GPS ölçüm zamanı vermiyor; observed_at/age_seconds/stale null, fetched_at yalnız sorgu zamanıdır.',
                    'Kaynak etaS bir sonraki durağa aittir; hat araç yanıtı durak varış tahmini sunmaz. Kaynak yeniden kullanım lisansı belirtilmemiştir.',
                    f'{conflicts} aynı araç için çelişkili güzergâh/konum kaydı yayımlanmadı.'])
                self.cache[key] = (self.clock() + 15, result)
                while len(self.cache) > 128:
                    self.cache.popitem(last=False)
            return LiveResult([r for r in result.data if r['line_id'] == line_id], result.warnings, result.fetched_at, result.cached)
