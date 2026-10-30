"""Günlük GTFS güncellemesi; tek yazar, şehir bazında hata ve atomik durum raporu."""
import fcntl
import json
import os
from datetime import datetime, timezone

from .gtfs_guncelle import update, DATA_DIR, CITIES


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def run():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with (DATA_DIR/'.update.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('Başka bir güncelleme çalışıyor.')
            return 1
        report = {'started_at': now(), 'status': 'running', 'cities': {}}
        def save():
            path = DATA_DIR/'update-status.tmp'
            path.write_text(json.dumps(report, ensure_ascii=False))
            os.replace(path, DATA_DIR/'update-status.json')
        save()
        for city in CITIES.values():
            if not city.gtfs:
                continue
            try:
                update(city.id)
                report['cities'][city.id] = {'status': 'success', 'finished_at': now()}
            except Exception as exc:
                # Günlükte ayrıntı, kamu raporunda yalnız hata türü.
                print(f'{city.id}: güncelleme başarısız ({type(exc).__name__})', flush=True)
                report['cities'][city.id] = {'status': 'error', 'error_type': type(exc).__name__, 'finished_at': now()}
            save()
        failed = any(r['status']=='error' for r in report['cities'].values())
        report.update(status='partial_failure' if failed else 'success', finished_at=now())
        save()
        return int(failed)


if __name__ == '__main__':
    raise SystemExit(run())
