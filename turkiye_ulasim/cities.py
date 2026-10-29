"""Desteklenen şehirler. Yeni şehir: GTFS adresi + canlı bağlayıcı + lisans bilgisi.

Yalnız resmi açık veri yayınlayan kaynaklar buraya girer. Uygulamaların kendi uçlarından
(izin alınmadan) çekilen veri bu projede yayınlanmaz.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class City:
    id: str
    name: str
    operator: str
    gtfs_url: str
    license: str
    source_url: str
    modes: tuple[str, ...] = field(default=("bus",))


CITIES = {
    "izmir": City(
        id="izmir",
        name="İzmir",
        operator="ESHOT",
        gtfs_url="https://www.eshot.gov.tr/gtfs/bus-eshot-gtfs.zip",
        license="İzmir Büyükşehir Belediyesi Açık Veri Lisansı",
        source_url="https://acikveri.bizizmir.com/dataset/toplu-ulasim-gtfs-verileri",
    ),
}
