<div align="center">

# Türkiye Ulaşım API

Türkiye’nin otobüs verileri için tek API, ortak yanıt biçimi.

**20 il · Hatlar ve duraklar · Güzergâhlar · Desteklenen şehirlerde canlı veri**

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
| Konya ve diğer 16 il | Var | Kaynakta bulunan hatlarda | Yok | Yok |

**Diğer 16 il:** Adana, Antalya, Burdur, Çanakkale, Düzce, Erzurum, Gaziantep, Kastamonu, Kırklareli, Kocaeli, Mardin, Muğla, Niğde, Ordu, Osmaniye ve Tokat.

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

Kahramanmaraş uzak topluluk API’sini kullanır; GTFS indirmez. `ULASIM_KAHRAMANMARAS_ENABLED=0` ile kapatılabilir. İETT kotası süreç içinde tutulduğu için **tek worker** kullanın.

## Kaynak ve veri ilkesi

- **Resmi açık veri:** İzmir, İstanbul, Konya.
- **Topluluk GTFS’i:** Diğer 16 il için [Egezenn/kk-gtfs](https://github.com/Egezenn/kk-gtfs). Belediye tarafından yayımlanmış resmi feed olarak gösterilmez. Takvim ve zamanlar türetilmiş olabilir.
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
