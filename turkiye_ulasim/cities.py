"""Kaynak türü ve veri lisansı belirtilen şehirler; resmi ve topluluk kaynakları ayrıdır."""
from __future__ import annotations

from dataclasses import dataclass, field, replace


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
    partial_feed: bool = False
    topology_region: str | None = None
    stop_coordinates: bool = True


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

# Kentkart verisinden topluluğun ürettiği GTFS: resmi belediye feed'i değildir.
for slug, name in (
    ('antalya', 'Antalya'),
    ('kocaeli', 'Kocaeli'),
    ('adana', 'Adana'),
    ('gaziantep', 'Gaziantep'),
    ('erzurum', 'Erzurum'),
    ('mardin', 'Mardin'),
    ('mugla', 'Muğla'),
    ('ordu', 'Ordu'),
    ('canakkale', 'Çanakkale'),
    ('duzce', 'Düzce'),
    ('burdur', 'Burdur'),
    ('nigde', 'Niğde'),
    ('kirklareli', 'Kırklareli'),
    ('osmaniye', 'Osmaniye'),
    ('tokat', 'Tokat'),
    ('kastamonu', 'Kastamonu'),
    ('sivas', 'Sivas'),
    ('edirne', 'Edirne'),
):
    CITIES[slug] = City(
        id=slug, name=name, operator=f"{name} · Kentkart / Egezenn GTFS",
        gtfs_url=f"https://raw.githubusercontent.com/Egezenn/kk-gtfs/main/data/{slug}.zip",
        license="Derleme/biçimlendirme CC0 1.0; alt verinin hakları Kentkart/belediyeye aittir",
        source_url="https://github.com/Egezenn/kk-gtfs",
        source_kind="community_catalog" if slug in ("sivas", "edirne") else "community_gtfs",
        partial_feed=slug in ("sivas", "edirne"),
        topology_region={"sivas": "005", "edirne": "013"}.get(slug),
        warnings=("Resmi belediye GTFS yayını değildir; Kentkart verisinden Egezenn/kk-gtfs topluluk derlemesi kullanılır.",
                  "Kaynak takvimi üretim tarihinden itibaren 60 gün olarak türetilir; takvim, kaynağın güncelliğini veya bugün çalıştığını kanıtlamaz.",
                  "Katalogdaki her hattın sıralı durak ve geometri kaydı bulunmayabilir; kaynak kapsamı kısmi olabilir.",
                  "Yalnız otobüs hatları sunulur; canlı araç/varış desteği eklenmedi. Kaynak tarife zamanları varsayımlar içerir; bu API tarife sorgusu sunmaz."),
    )

CITIES["sakarya"] = City(
    id="sakarya", name="Sakarya", operator="Sakarya Büyükşehir Belediyesi / SAKUS",
    gtfs_url="", source_url="https://sakus.sakarya.bel.tr/harita",
    license="Kaynak veri için yeniden kullanım lisansı belirtilmemiş",
    source_kind="official_service", partial_feed=True, live_vehicles=True,
    warnings=("GTFS değildir; resmî SAKUS servisinden statik katalog aktarılır.",
              "Her güzergâh ayrı hatId:routeId kimliği taşır; direction=0 güzergâhın kendi sırasıdır, gidiş/dönüş eşlemesi değildir.",
              "Bazı kaynak güzergâhlarında durak listesi boştur; desteklenmeyen durak sırası 501 döner.",
              "Canlı araç desteklenir; varış ve sefer takvimi henüz desteklenmez."),
)

CITIES["ankara"] = City(
    id="ankara", name="Ankara", operator="EGO Genel Müdürlüğü",
    gtfs_url="", source_url="https://www.ego.gov.tr/HareketSaatleri",
    license="Kaynak veri için yeniden kullanım lisansı belirtilmemiş",
    source_kind="official_service", partial_feed=True, stop_coordinates=False, live_arrivals=True, live_vehicles=True,
    warnings=("Resmî EGO sitesinin otobüs kataloğu ve yayımlanan durak listesi kullanılır; GTFS değildir.",
              "Statik durak koordinatları null; yakın durak ve güzergâh geometrisi desteklenmez. Canlı araç ve durak varışları EGO Cepte servisinden alınır.",
              "direction=0 kaynakta yayımlanan tek durak listesidir; gidiş/dönüş ayrımı doğrulanmadı."),
)

CITIES["samsun"] = City(
    id="samsun", name="Samsun", operator="SAMULAŞ",
    gtfs_url="", source_url="https://samulas.com.tr/otobusler",
    license="Kaynak veri için yeniden kullanım lisansı belirtilmemiş",
    source_kind="official_service", partial_feed=True,
    warnings=("Resmî SAMULAŞ otobüs kataloğu ve hat haritası kullanılır; GTFS değildir.",
              "Duraklar kaynak haritasının işaret sırasındadır; doğrulanmış sefer/durak sırası değildir.",
              "direction=0 yayımlanan haritadır; canlı araç/varış ve sefer takvimi sunulmaz."),
)

CITIES["mersin"] = City(
    id="mersin", name="Mersin", operator="Mersin Büyükşehir Belediyesi",
    gtfs_url="", source_url="https://ulasim.mersin.bel.tr/hatveguzergahlar",
    license="Kaynak veri için yeniden kullanım lisansı belirtilmemiş",
    source_kind="official_service", partial_feed=True,
    warnings=("Resmî ulaşım portalının hat/yön kataloğu kullanılır; GTFS değildir.",
              "Hat adı ve durak listesinin başlangıç/bitişi farklı olabilir; kaynak adları korunur.",
              "direction=0 kaynak hat/yön kaydının kendi sırasıdır; sefer dosyasıyla doğrulanmadı. Canlı araç/varış desteklenmez."),
)

CITIES["trabzon"] = City(
    id="trabzon", name="Trabzon", operator="Trabzon Büyükşehir Belediyesi / AKUS",
    gtfs_url="", source_url="https://ulasim.trabzon.bel.tr/",
    license="Kaynak veri için yeniden kullanım lisansı belirtilmemiş",
    source_kind="official_service", partial_feed=True, live_arrivals=True, live_vehicles=True,
    warnings=("Resmî AKUS hat/durak GeoJSON servisi kullanılır; GTFS değildir.",
              "Her hatId:güzergâhId ayrı kayıttır; direction=0 seçilen güzergâhın kendi sırasıdır.",
              "Statik koordinatlar EPSG:3857'den çevrilir; canlı araçta kaynak koordinat biçimi ayrıca belirtilir. Araç ve varış desteklenir; sefer takvimi sunulmaz."),
)

CITIES["diyarbakir"] = City(
    id="diyarbakir", name="Diyarbakır", operator="Diyarbakır Büyükşehir Belediyesi / ASIS köprüsü",
    gtfs_url="", source_url="https://www.diyarbakir.bel.tr/ulasim/canli",
    license="Kaynak veri için yeniden kullanım lisansı belirtilmemiş",
    source_kind="official_service", partial_feed=True, live_vehicles=True,
    warnings=("Resmî belediye portalının ASIS köprüsü kullanılır; GTFS değildir.",
              "Gidiş=0, dönüş=1 kaynak yön bilgisiyle eşleştirilir. Konumu eksik duraklar null korunur.",
              "Canlı araç konumu desteklenir; durak varışı ve sefer takvimi henüz desteklenmez."),
)

# Canlı eşleşmesi doğrudan servis yanıtlarıyla doğrulanan bölgeler.
KENTKART_LIVE_REGIONS = {"kocaeli":"004", "gaziantep":"028", "sivas":"005", "edirne":"013", "adana":"003", "antalya":"026", "mugla":"010", "ordu":"031", "erzurum":"038", "mardin":"032", "tokat":"039", "canakkale":"007", "duzce":"036", "burdur":"017", "nigde":"023", "kirklareli":"027", "osmaniye":"033", "kastamonu":"025"}
for city_id in KENTKART_LIVE_REGIONS:
    city=CITIES[city_id]
    CITIES[city_id]=replace(city,live_vehicles=True,live_arrivals=True,warnings=tuple(
        w.replace("canlı araç/varış desteği eklenmedi", "canlı araç ve varış desteği var") for w in city.warnings))
