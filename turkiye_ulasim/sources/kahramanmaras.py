"""Mevcut herkese açık Kahramankart API'sini ortak biçime çevirir.

Doğrudan Pallium'a bağlanmaz; erişim bilgisi gerekmez. Kaynak, resmi açık veri
olarak etiketlenmez. Hat kimlikleri id:yön içerir; eksik yön tahmin edilmez.
"""
from __future__ import annotations

import asyncio
import math
import re
import time
from collections import OrderedDict, deque
from datetime import datetime

import httpx

from ..gtfs import _distance_m
from .base import LiveResult, SourceError, SourceNotFound, SourceRateLimited, SourceUnsupported

BASE_URL = "https://mithrixa.com/ulasim-api/v1/"
LINE_ID = re.compile(r"([1-9][0-9]{0,9}):([1-3])\Z")
STOP_ID = re.compile(r"[1-9][0-9]{0,9}\Z")


def _list(data, field):
    if not isinstance(data, dict) or not isinstance(data.get(field), list):
        raise SourceError(f"Kahramanmaraş kaynağında {field} listesi bekleniyordu")
    if any(not isinstance(item, dict) for item in data[field]):
        raise SourceError(f"Kahramanmaraş kaynağında {field} kayıt biçimi değişmiş")
    return data[field]


def _position(item):
    try:
        lat, lon = float(item['latitude']), float(item['longitude'])
        return (lat, lon) if 35 < lat < 43 and 25 < lon < 45 else None
    except (ValueError, TypeError, KeyError):
        return None


def _line_record(item):
    try:
        source_id, direction = str(item['id']), int(item['direction'])
        if not STOP_ID.fullmatch(source_id) or direction not in (1, 2, 3):
            raise ValueError()
        return {'id': f'{source_id}:{direction}', 'code': str(item['code']), 'name': item['name'],
                'mode': 'bus', 'source_id': source_id, 'source_direction': direction}
    except (KeyError, ValueError, TypeError):
        raise SourceError('Kahramanmaraş hat kimliği/yön biçimi değişmiş') from None


def _stop_record(item):
    position = _position(item.get('location') or {})
    if position is None or not STOP_ID.fullmatch(str(item.get('id', ''))) or not isinstance(item.get('name'), str):
        raise SourceError('Kahramanmaraş durak biçimi/konumu değişmiş')
    return {'id': str(item['id']), 'name': item['name'], 'latitude': position[0], 'longitude': position[1],
            'code': str(item.get('code', ''))}


class Kahramanmaras:
    """Statik yöntemleri de async olan uzak kaynak; küçük önbellek ve dakika bütçesi."""
    def __init__(self, client: httpx.AsyncClient | None = None, clock=time.monotonic):
        self.client = client or httpx.AsyncClient(timeout=15)
        self.clock = clock
        self._cache: OrderedDict[tuple, tuple[float, dict]] = OrderedDict()
        self._lock = asyncio.Lock()
        self._requests = deque()

    def warnings(self):
        return []

    def calendar_expired(self):
        return False  # Bu kaynak GTFS takvimi sunmaz.

    async def _get(self, path, params=None, ttl=15):
        params = params or {}
        key = (path, tuple(sorted(params.items())))
        async with self._lock:
            now = self.clock()
            if key in self._cache:
                expires, payload = self._cache[key]
                if expires > now:
                    self._cache.move_to_end(key)
                    return {'data': payload['data'], 'meta': payload['meta'] | {'cached': True}}
                del self._cache[key]
            while self._requests and now - self._requests[0] >= 60:
                self._requests.popleft()
            if len(self._requests) >= 60:
                raise SourceRateLimited(max(1, math.ceil(60 - now + self._requests[0])), 'Kahramanmaraş', 'dakikalık')
            self._requests.append(now)
            try:
                response = await self.client.get(BASE_URL + path, params=params)
            except httpx.HTTPError as exc:
                raise SourceError(f'Kahramanmaraş kaynağına ulaşılamadı: {type(exc).__name__}') from exc
            if response.status_code == 404:
                raise SourceNotFound('Kahramanmaraş kaynağında kayıt bulunamadı')
            if response.status_code == 429:
                try:
                    retry = min(3600, max(1, int(response.headers.get('Retry-After', 15))))
                except ValueError:
                    retry = 15
                raise SourceRateLimited(retry, 'Kahramanmaraş', 'dakikalık')
            if response.status_code != 200:
                raise SourceError(f'Kahramanmaraş kaynağı HTTP {response.status_code} döndü')
            try:
                payload = response.json()
                if not isinstance(payload, dict) or 'data' not in payload or not isinstance(payload.get('meta'), dict):
                    raise ValueError()
                fetched_at = payload['meta']['fetched_at']
                if not isinstance(fetched_at, str) or datetime.fromisoformat(fetched_at).tzinfo is None:
                    raise ValueError()
                if isinstance(payload['data'], dict) and str(payload['data'].get('processInfo', 1)) != '1':
                    raise ValueError()
            except (ValueError, KeyError, TypeError):
                raise SourceError('Kahramanmaraş kaynağının JSON/metadata biçimi değişmiş') from None
            self._cache[key] = (self.clock() + ttl, payload)
            while len(self._cache) > 256:
                self._cache.popitem(last=False)
            return payload

    @staticmethod
    def _parts(line_id):
        match = LINE_ID.fullmatch(line_id)
        return (match[1], int(match[2])) if match else None

    @staticmethod
    def _unresolved_line(item):
        # StopLines ve arrivals yön vermiyor: tıklanabilir kimlik uydurma.
        return {'id': None, 'code': str(item.get('lineCode', '')), 'name': item.get('name'), 'mode': 'bus',
                'source_id': str(item.get('lineId', '')), 'source_direction': None}

    async def lines(self, query='', limit=200, offset=0):
        payload = await self._get('search', {'q': query, 'stops': 'false', 'lines': 'true'}, ttl=60)
        rows = _list(payload['data'], 'busLines')
        return [_line_record(row) for row in rows if str(row.get('lineType')) == '1'][offset:offset+limit]

    async def line(self, line_id):
        parts = self._parts(line_id)
        if parts is None:
            return None
        source_id, direction = parts
        payload = await self._get(f'lines/{source_id}', {'direction': direction})
        info = payload['data'].get('busLineInfo') if isinstance(payload['data'], dict) else None
        if not isinstance(info, dict) or str(info.get('id')) != source_id or info.get('lineType') != 'Otobus':
            raise SourceError('Kahramanmaraş hat detay biçimi/kimliği değişmiş')
        line = _line_record(info | {'direction': direction})
        # Gidiş=1/Dönüş=2 ortak 0/1'e çevrilir; kaynak 3'ün anlamı doğrulanmadı.
        return line | {'directions': [direction-1] if direction in (1, 2) else []}

    def _direction(self, line_id, direction):
        parts = self._parts(line_id)
        if parts is None:
            raise SourceNotFound('Hat bulunamadı')
        if parts[1] == 3:
            raise SourceUnsupported('Kaynağın 3 yön değerinin ortak 0/1 karşılığı doğrulanmadı')
        return parts if direction == parts[1]-1 else None

    async def line_stops(self, line_id, direction):
        parts = self._direction(line_id, direction)
        if parts is None:
            return []
        payload = await self._get(f'lines/{parts[0]}/stops', {'direction': parts[1]}, ttl=300)
        rows = _list(payload['data'], 'lineStops')
        try:
            rows = sorted(rows, key=lambda item: int(item['sequenceNo']))
        except (KeyError, TypeError, ValueError):
            raise SourceError('Kahramanmaraş durak sırası biçimi değişmiş') from None
        return [_stop_record(row) for row in rows]

    async def line_shape(self, line_id, direction):
        parts = self._direction(line_id, direction)
        if parts is None:
            return []
        payload = await self._get(f'lines/{parts[0]}/shape', {'direction': parts[1]}, ttl=300)
        positions = [_position(row) for row in _list(payload['data'], 'lineCoordinates')]
        if any(p is None for p in positions):
            raise SourceError('Kahramanmaraş güzergâhında geçersiz koordinat')
        return [list(p) for p in positions]

    async def stop(self, stop_id):
        if not STOP_ID.fullmatch(stop_id):
            return None
        payload = await self._get(f'stops/{stop_id}')
        if not isinstance(payload['data'], dict):
            raise SourceError('Kahramanmaraş durak detay biçimi değişmiş')
        stop = _stop_record(payload['data'] | {'id': stop_id})
        lines = await self._get(f'stops/{stop_id}/lines', ttl=300)
        return stop | {'lines': [self._unresolved_line(r) for r in _list(lines['data'], 'stopLines')]}

    async def nearby(self, latitude, longitude, radius_m, limit=20):
        payload = await self._get('stops/nearby', {'latitude': latitude, 'longitude': longitude}, ttl=30)
        stops = []
        for row in _list(payload['data'], 'nearestStops'):
            stop = _stop_record({'id': row.get('busStopId'), 'name': row.get('busStopName'),
                                 'code': row.get('busStopCode'), 'location': row})
            distance = _distance_m(latitude, longitude, stop['latitude'], stop['longitude'])
            if distance <= radius_m:
                stops.append(stop | {'distance_m': round(distance)})
        return sorted(stops, key=lambda s: s['distance_m'])[:limit]

    async def vehicles(self, line_id, *, line):
        source_id, direction = self._parts(line_id)
        payload = await self._get(f'lines/{source_id}', {'direction': direction})
        info = payload['data'].get('busLineInfo') if isinstance(payload['data'], dict) else None
        if not isinstance(info, dict) or str(info.get('id')) != source_id:
            raise SourceError('Kahramanmaraş canlı hat kimliği biçimi değişmiş')
        vehicles, dropped = [], 0
        for row in _list(info, 'liveBuses'):
            position = _position(row.get('location') or {})
            if position is None or not (row.get('busNo') or row.get('plate')):
                dropped += 1
                continue
            vehicles.append({'id': str(row.get('busNo') or row['plate']), 'line_id': line_id,
                'source_direction': direction, 'latitude': position[0], 'longitude': position[1],
                'observed_at': None, 'position_confidence': 'single'})
        warnings = ['Kaynak GPS ölçüm zamanı vermiyor; fetched_at yalnız API verisinin alınma zamanıdır.']
        if dropped:
            warnings.append(f'{dropped} geçersiz araç konumu atlandı.')
        return LiveResult(vehicles, warnings, payload['meta']['fetched_at'], bool(payload['meta'].get('cached')))

    async def arrivals(self, stop_id):
        payload = await self._get(f'stops/{stop_id}')
        arrivals = []
        for row in _list(payload['data'], 'buses'):
            position = _position(row.get('busLocation') or {})
            eta = row.get('timeToStop')
            eta = eta if isinstance(eta, (int, float)) and not isinstance(eta, bool) and math.isfinite(eta) and eta >= 0 else None
            arrivals.append({'line_id': None, 'source_line_id': str(row.get('lineId', '')),
                'source_line_code': row.get('busCode'), 'line_name': row.get('busName'),
                'vehicle_id': row.get('plate'), 'source_direction': None, 'stops_away': None,
                'eta_seconds': eta, 'source_remaining_time': row.get('remaining_time'),
                'latitude': position[0] if position else None, 'longitude': position[1] if position else None,
                'wheelchair_accessible': None, 'bike_rack': None})
        arrivals.sort(key=lambda a: a['eta_seconds'] if a['eta_seconds'] is not None else math.inf)
        return LiveResult(arrivals, ['Kaynak varışlarda yön ve kalan durak sayısı vermiyor; hat/yön kimliği tahmin edilmedi.'],
                          payload['meta']['fetched_at'], bool(payload['meta'].get('cached')))
