<div align="center">

# Türkiye Ulaşım API

Türkiye’nin otobüs verileri için tek API, ortak yanıt biçimi.

**28 il · Hatlar ve duraklar · Güzergâhlar · Desteklenen şehirlerde canlı veri**

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](requirements.txt)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)](turkiye_ulasim/main.py)
[![Kod lisansı](https://img.shields.io/badge/Kod-MIT-blue)](LICENSE)

[**Canlı API belgeleri**](https://mithrixa.com/turkiye-ulasim-api/docs) · [Şehir listesi](https://mithrixa.com/turkiye-ulasim-api/v1/cities) · [Yapılacaklar](YAPILACAKLAR.md) · [Katkı rehberi](CONTRIBUTING.md)

</div>

Şehir başına farklı veri biçimleriyle uğraşmadan otobüs hatlarını arayın, durakları bulun ve güzergâhları alın. Bütün şehirler aynı uçları ve `{data, meta}` yanıtını kullanır. Her yanıtta kaynak, veri lisansı ve bilinen sınırlamalar bulunur.

## Hemen deneyin

Ana adres: `https://mithrixa.com/turkiye-ulasim-api`

```sh
# Desteklenen şehirler ve yetenekleri
curl 'https://mithrixa.com/turkiye-ulasim-api/v1/cities'

# Kocaeli otobüs hatlarında arama
curl 'https://mithrixa.com/turkiye-ulasim-api/v1/kocaeli/lines?q=10'

# İzmir'de bir durağa yaklaşan araçlar
curl 'https://mithrixa.com/turkiye-ulasim-api/v1/izmir/stops/21050/arrivals'
```

Anahtar gerektirmez. Halka açık köprüde IP başına **60 istek/dakika** sınırı vardır; kaynakların ayrıca kendi kotaları bulunur. `429` veya `503` yanıtında `Retry-After` alanını izleyin.

## Hangi şehirde ne var?

| Kapsam | Hat / durak | Durak sırası / güzergâh | Canlı araç | Canlı varış |
|---|---|---|---|---|
| İzmir | Var | Var | Var | Var |
| İstanbul | Var | Durak sırası var; geometri yok | Var | Yok |
| Kahramanmaraş | Hat arama / durak | Var | Var | Var |
| Konya ve diğer 9 il | Var | Kaynakta bulunan hatlarda | Yok | Yok |
| Antalya, Adana, Kocaeli, Gaziantep, Muğla, Ordu ve Erzurum | Var | Kaynakta bulunan hatlarda | Var | Var |
| Diyarbakır | Var | Yön bazında kaynak sırası ve mevcut geometriler | Var | Yok |
| Trabzon | Var | Kaynak güzergâhına göre durak sırası ve geometri | Var | Var |
| Mersin | Var | Kaynak hat/yön yanıtlarında | Yok | Yok |
| Samsun | Var | Kaynak harita işaretleri ve geometri | Yok | Yok |
| Ankara | Var; koordinatlar yok | Kaynak durak listesi var; geometri yok | Var | Var |
| Sakarya | Var | SAKUS kaynak güzergâhlarında | Yok | Yok |
| Sivas ve Edirne | Var | Kentkart servisinden doğrulanan hat/yönlerde | Var | Var |

**Diğer 9 il:** Burdur, Çanakkale, Düzce, Kastamonu, Kırklareli, Mardin, Niğde, Osmaniye ve Tokat.

> **Kapsam kısmi olabilir.** Bir ilin listede olması bütün hatlarının güncel veya eksiksiz olduğunu göstermez. Katalogda bulunup sefer/durak sırası olmayan hatlar vardır. Veri olmayan yerde sefer, konum veya güzergâh üretilmez.

[İl bazında sayılar ve eksikler →](docs/YENI_ILLER.md)

## Uçlar

`{city}` için `/v1/cities` yanıtındaki kimliği kullanın. Hat ve durak kimliklerini sorgu yanıtından aynen alın; görünen hat koduyla aynı olmayabilir.

| İstek | Kullanım |
|---|---|
| `/v1/cities` | Şehirler, kaynaklar ve yetenekler |
| `/v1/{city}/lines?q=&limit=200&offset=0` | Hat arama ve sayfalama |
| `/v1/{city}/lines/{id}` | Hat bilgisi ve yönleri |
| `/v1/{city}/lines/{id}/stops?direction=0` | Sıralı duraklar |
| `/v1/{city}/lines/{id}/shape?direction=0` | Güzergâh koordinatları |
| `/v1/{city}/lines/{id}/vehicles` | Canlı araç konumları |
| `/v1/{city}/stops/nearby?latitude=&longitude=&radius=500` | Yakındaki duraklar |
| `/v1/{city}/stops/{id}` | Durak bilgisi |
| `/v1/{city}/stops/{id}/arrivals` | Yaklaşan araçlar |

Bütün uçlar `GET` kullanır. Desteklenmeyen canlı veri `501`, geçici kaynak hatası `502`, kurulu olmayan/kapalı veri veya dolan kaynak bütçesi `503` döner. Boş liste, destek yokluğuyla aynı şey değildir.

[Yanıt alanları, yönler, kaynak kotaları ve örnekler →](docs/API.md)

## Yerelde çalıştırma

```sh
git clone https://github.com/uzaylikafasi/turkiye-ulasim-api.git
cd turkiye-ulasim-api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Başlamak için tek şehir yeterli; diğerlerini sonradan indirebilirsiniz
.venv/bin/python -m tools.gtfs_guncelle izmir
.venv/bin/uvicorn turkiye_ulasim.main:app --port 8010 --workers 1
```

Belgeler: `http://localhost:8010/docs`. Veriler `data/` altında tutulur. Kurmadığınız GTFS şehirleri kullanılamaz; `/readyz` bütün GTFS kaynakları hazır olmadan `503` döner. Uçların tamamını kurmak için `.venv/bin/python -m tools.gtfs_guncelle` çalıştırın.

Sivas ve Edirne kurulumu, eksik durak ilişkilerini Kentkart servisinden sırayla doğruladığı için diğer statik kaynaklardan daha uzun sürebilir. Geçerli veri ancak doğrulama tamamlandıktan sonra atomik değiştirilir.

Kahramanmaraş uzak topluluk API’sini kullanır; GTFS indirmez. `ULASIM_KAHRAMANMARAS_ENABLED=0` ile kapatılabilir. İETT kotası süreç içinde tutulduğu için **tek worker** kullanın.

## Kaynak ve veri ilkesi

- **Resmi açık veri:** İzmir, İstanbul, Konya.
- **Topluluk GTFS’i:** Diğer 16 il için [Egezenn/kk-gtfs](https://github.com/Egezenn/kk-gtfs). Belediye tarafından yayımlanmış resmi feed olarak gösterilmez. Takvim ve zamanlar türetilmiş olabilir.
- **Servisle tamamlanan katalog:** Sivas ve Edirne’de sefer dosyaları eksiktir. Hat/durak kataloğu dosyadan, doğrulanan durak sırası ve geometri Kentkart servisinden alınır; sefer/takvim üretilmez.
- **Topluluk köprüsü:** Kahramanmaraş için [Kahramankart Ulaşım API](https://github.com/uzaylikafasi/kahramankart-ulasim-api). Kaynak veri lisansı belirtilmemiştir.

Kod **[MIT](LICENSE)** lisanslıdır. Veri lisansları kaynaklara göre değişir; topluluk derlemesinin CC0 beyanı, temel verinin hak sahipliğini değiştirmez. Uygulamanızda `meta.source`, `source_url`, `license` ve `warnings` alanlarını koruyun.

## Durum ve katkı

Canlı kurulumda sürekli servis ve **günlük 04:10–04:15** veri güncellemesi vardır. Sağlık, yerel veri hazırlığı ve son güncelleme bilgisi ayrı uçlarda sunulur:

[Sağlık](https://mithrixa.com/turkiye-ulasim-api/healthz) · [Hazır olma](https://mithrixa.com/turkiye-ulasim-api/readyz) · [Veri durumu](https://mithrixa.com/turkiye-ulasim-api/v1/status)

Katkıda bulunmak isteyenler, [ortak yapılacaklar listesinden](YAPILACAKLAR.md) bir iş seçip [katkı adımlarını](CONTRIBUTING.md) izleyebilir. Öncelik **yeni iller ve otobüs kapsamı**.

- [API kullanımı ve veri sınırları](docs/API.md)
- [İl kapsamı ve eksik kaynaklar](docs/YENI_ILLER.md)
- [Büyükşehir araştırmaları](docs/BUYUKSEHIRLER.md)
- [Yayın, güncelleme ve geri alma](deployment/README.md)

Otomatik GitHub CI henüz etkin değil; hazır şablon [katkı rehberinde](CONTRIBUTING.md) belirtilmiştir. Testler yerelde çalıştırılır; sonuçları bütün canlı hatların doğrulandığı anlamına gelmez.

Sakarya, resmî SAKUS servisinden günlük katalog aktarımıyla desteklenir. Hat kimliği `2:157` gibi kaynak hat ve güzergâh kimliğini taşır. `direction=0` bu güzergâhın kendi sırasıdır; gidiş/dönüş anlamı yüklenmez. Kaynak yeniden kullanım lisansı belirtilmemiştir.

Ankara, resmî EGO sitesinin otobüs kataloğu ve durak sırasıyla desteklenir. Durak koordinatları kaynakta yoktur (`null`); yakın durak ve geometri uçları 501 döner. `direction=0` kaynakta yayımlanan tek listedir; ayrı gidiş/dönüş anlamı yüklenmez.

Ankara durak varışları EGO Cep’te servisinden alınır: `/v1/ankara/stops/14043/arrivals`. Tarife/hareket saati mesajları canlı araç sayılmaz; kalan süre ve kaynak GPS zamanı ayrı alanlardır. Canlı kaynak için 30 istek/dakika bütçe ve 20 saniye önbellek uygulanır.

Samsun, resmî SAMULAŞ otobüs kataloğu ve hat haritalarıyla desteklenir. Durak koordinatları ve yakın durak sorgusu vardır; durak listesi kaynak harita işaretlerinin sırasını korur ve sefer dosyasıyla doğrulanmış sıra iddiası taşımaz. Canlı araç/varış ve tarife sunulmaz.

Mersin, resmî ulaşım portalının hat/yön kataloğu, durak ve geometri servisiyle desteklenir. `10M-G` ve `10M-D` ayrı kayıtlardır; `direction=0` seçilen kaynak kaydının kendi listesidir. Katalogdaki hat adları gerçek başlangıç/bitişle farklılık gösterebilir; kaynak adları korunur.

Trabzon, resmî AKUS GeoJSON servisinden desteklenir. `hatId:güzergâhId` kimliği kaynak varyantlarını ayırır; `direction=0` seçilen güzergâhın kendi sırasıdır. Duraklar kaynak `sira` alanına göre sunulur, EPSG:3857 koordinatları enlem/boylama çevrilir.

Diyarbakır, belediyenin resmî ASIS köprüsünden desteklenir. İç hat numarası API kimliğidir; görünen hat kodu korunur. `direction=0` gidiş, `direction=1` dönüş olarak kaynağın yön alanına bağlanır. Geometrisi bulunmayan hat/yönlerde geometri sorgusu 501 döner.

Canlı veri örnekleri: Diyarbakır araçları `/v1/diyarbakir/lines/117/vehicles`, Trabzon durak varışları `/v1/trabzon/stops/3528/arrivals`. Diyarbakır’da `observed_at` GPS zamanı, `stale` eski konum işareti; Trabzon’da `eta_seconds` tahmini varış, `stops_away` kalan durak sayısıdır.

Trabzon canlı araçları da desteklenir: `/v1/trabzon/lines/59:94/vehicles`. Genel kaynak yanıtı tam hat/güzergâh kimliğiyle süzülür; GPS zamanı ve eski konum işareti korunur.

Ankara hat araçları: `/v1/ankara/lines/263/vehicles`. Araç ve durak varışlarında GPS zamanı, `age_seconds` ve `stale` sunulur. Varış önbelleği 20, araç önbelleği 15 saniyedir; ikisi 30 kaynak isteği/dakika bütçesini paylaşır.

Antalya, Adana, Kocaeli, Gaziantep, Sivas, Edirne, Muğla, Ordu ve Erzurum’da Kentkart canlı araç ve durak varış desteği var. Örnek: `/v1/kocaeli/lines/41010/vehicles`. Kaynak GPS ölçüm zamanı doğrulanmadığından `observed_at`, `age_seconds` ve `stale` boş döner. Varış örneği: `/v1/kocaeli/stops/80671/arrivals`; kaynak dakika tahmini saniyeye çevrilir. Statik derlemenin CC0 lisansı canlı kaynağı kapsamaz. [Ayrıntılar](docs/API.md#kentkart-canlı-araçlar).

Antalya KL08 (`00080`) ve Adana 112 (`00112`) hatlarında araç sorgusu kullanılabilir. Antalya 35 (`00354`) özel kaynak eşlemesiyle desteklenir; iki yöndeki durak sırası doğrulanmıştır. Adana’daki görev gibi servis güzergâhlarında kaynak sonuç vermeyebilir. Varış örnekleri: `/v1/antalya/stops/10017/arrivals`, `/v1/adana/stops/42077/arrivals`. Destek bütün hatların eksiksizliğini göstermez.

Muğla `/v1/mugla/lines/10001/vehicles`, Ordu `/v1/ordu/lines/00210/vehicles` ve Erzurum `/v1/erzurum/lines/10020/vehicles` canlı araç örnekleridir. Üç ilde durak varışları da vardır; GPS ölçüm saati henüz bilinmiyor.
