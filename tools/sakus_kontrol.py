"""SAKUS kaynağını kontrol eder; henüz ortak API'ye veri yayımlamaz."""
import json
import httpx

BASE = 'https://sbbpublicapi.sakarya.bel.tr/api/v1/Ulasim'
HEADERS = {'Origin': 'https://sakus.sakarya.bel.tr',
           'Referer': 'https://sakus.sakarya.bel.tr/'}
BUS_TYPES = {6904, 6907, 7354, 7355}


def catalog(client):
    lines = {}
    for group in (3869, 5731):
        response = client.get(BASE, params={'busType': group})
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, list):
            raise ValueError('SAKUS katalog yanıtı liste değil')
        for row in body:
            # Kaynak sorgusu raylı hatları da döndürebilir.
            if row['busTypeId'] not in BUS_TYPES:
                continue
            key = row['id']
            if key in lines and lines[key] != row:
                raise ValueError('Çelişen SAKUS hat kimliği')
            lines[key] = row
    if not lines:
        raise ValueError('SAKUS otobüs kataloğu boş')
    return list(lines.values())


def check_route(client, line_id):
    response = client.get(f'{BASE}/route-and-busstops/{line_id}')
    response.raise_for_status()
    body = response.json()
    if body['lineId'] != line_id:
        raise ValueError('SAKUS hat kimliği eşleşmedi')
    results = []
    for route in body['routes']:
        orders = set()
        for stop in route['busStops']:
            if stop['order'] in orders:
                raise ValueError('Tekrarlanan durak sırası')
            orders.add(stop['order'])
            geometry = stop['busStopGeometry']
            lon, lat = geometry['coordinates']
            if geometry['type'] != 'Point' or not (25 < lon < 45 and 35 < lat < 43):
                raise ValueError('Geçersiz durak koordinatı')
        results.append({'route_id': route['routeId'],
                        'source_direction': route['routeTypeId'],
                        'stops': len(orders),
                        'geometry_type': (route.get('routeGeometry') or {}).get('type')})
    return results


def main():
    with httpx.Client(headers=HEADERS, timeout=25) as client:
        lines = catalog(client)
        sample = next(row for row in lines if row['id'] == 2)
        print(json.dumps({'bus_lines': len(lines), 'sample_line': sample['id'],
                          'routes': check_route(client, sample['id']),
                          'published': False}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
