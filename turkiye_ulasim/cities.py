"""Kaynak türü ve veri lisansı belirtilen şehirler; resmi ve topluluk kaynakları ayrıdır."""
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
    live_vehicles: bool = False
    live_arrivals: bool = False
    catalog_url: str | None = None
    warnings: tuple[str, ...] = ()
    source_kind: str = "official_open_data"
    line_catalog: bool = True
    gtfs: bool = True


CITIES = {
    "izmir": City(
        id="izmir",
        name="İzmir",
        operator="ESHOT",
        gtfs_url="https://www.eshot.gov.tr/gtfs/bus-eshot-gtfs.zip",
        license="İzmir Büyükşehir Belediyesi Açık Veri Lisansı",
        source_url="https://acikveri.bizizmir.com/dataset/toplu-ulasim-gtfs-verileri",
        live_vehicles=True,
        live_arrivals=True,
    ),
    "istanbul": City(
        id="istanbul",
        name="İstanbul",
        operator="İETT",
        gtfs_url="",
        license="İstanbul Büyükşehir Belediyesi Açık Veri Lisansı",
        source_url="https://data.ibb.gov.tr/dataset/iett-gtfs-verisi",
        catalog_url="https://data.ibb.gov.tr/api/3/action/package_show?id=iett-gtfs-verisi",
        live_vehicles=True,
        warnings=("İETT GTFS kaynağında güzergâh varyantları ayrı hat kimlikleri taşır; canlı konumlar güzergâh koduyla eşleştirilir.",
                  "Kaynağın bozuk Türkçe kodlaması içe aktarımda onarılır; GTFS şekil verisi yayımlanmıyor."),
    ),
    "konya": City(
        id="konya",
        name="Konya",
        operator="Konya Büyükşehir Belediyesi",
        gtfs_url="https://acikveri.konya.bel.tr/dataset/c2e034e6-e015-49c6-8eec-6e2f7de9c105/resource/ec944ecd-1c1f-4687-a7f6-fcf2dc5bb5db/download/gtfs_11_2025.zip",
        license="Creative Commons Atıf 4.0 Uluslararası (CC BY 4.0)",
        source_url="https://acikveri.konya.bel.tr/dataset/toplu-tasima-gtfs-verileri",
        warnings=("Kaynak Kasım 2025 dosyasıdır; takvimin 2030'a uzanması verinin güncel olduğunu kanıtlamaz.",),
    ),
    "kahramanmaras": City(
        id="kahramanmaras",
        name="Kahramanmaraş",
        operator="Pallium / Kahramankart · topluluk köprüsü",
        gtfs_url="",
        license="Kaynak veri lisansı belirtilmemiş; bağlayıcı kodu MIT",
        source_url="https://mithrixa.com/ulasim-api/docs",
        live_vehicles=True,
        live_arrivals=True,
        source_kind="community_bridge",
        line_catalog=False,
        gtfs=False,
        warnings=("Resmi açık veri kaynağı değildir; mevcut Kahramankart topluluk API'si kullanılır. Kaynak veri lisansı doğrulanmadı.",
                  "Hatlar yalnız q ile aranır; kaynak sonuçları sınırlıdır, bütün şehir envanteri değildir.",
                  "Hat kimliği kaynak kimliği:yön biçimindedir (9576:1). Varış ve durak-hat kayıtlarında yön yoksa ortak hat kimliği null kalır.",),
    ),
}
