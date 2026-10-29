# Türkiye Ulaşım API

Türkiye'deki şehirlerin toplu taşıma verisini tek biçimde sunan açık kaynak API. Her şehir için aynı uçlar kullanılır, yanıt biçimi de aynıdır. Uygulama yazan biri şehir başına ayrı sistem öğrenmek zorunda kalmaz.

Şu an desteklenen: **İzmir (ESHOT otobüsleri)**. Sıradakiler İstanbul (İETT) ve İzmir'in metro, tramvay, İZBAN ve vapur hatları.

## Veri ilkesi

Projeye yalnız belediyelerin **resmi açık veri** olarak yayınladığı kaynaklar girer. Bir uygulamanın kendi kullandığı uçlardan izinsiz veri çekilmez. Her yanıtın `meta` alanında kaynak, lisans ve kaynak sayfası yazar.

| Şehir | Statik veri | Canlı veri | Lisans |
|---|---|---|---|
| İzmir | [ESHOT GTFS](https://acikveri.bizizmir.com/dataset/toplu-ulasim-gtfs-verileri) | [İZTEK web servisleri](https://openfiles.izmir.bel.tr/471231/docs/iztek-WebServisKullanimDokumani_1.0.pdf) | İzmir BB Açık Veri Lisansı |

## Kurulum

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m tools.gtfs_guncelle          # GTFS'i indirip data/izmir.sqlite3 kurar (~20 sn)
.venv/bin/uvicorn turkiye_ulasim.main:app --port 8000
```

Belgeler: `http://localhost:8000/docs`

## Uçlar

| Uç | Açıklama |
|---|---|
| `GET /v1/cities` | Desteklenen şehirler, kaynak ve lisans |
| `GET /v1/{city}/lines?q=` | Hat arama (Türkçe büyük/küçük harf duyarsız) |
| `GET /v1/{city}/lines/{id}` | Hat bilgisi ve yönleri |
| `GET /v1/{city}/lines/{id}/stops?direction=0` | Sıralı duraklar |
| `GET /v1/{city}/lines/{id}/shape?direction=0` | Güzergâh `[[enlem, boylam], ...]` |
| `GET /v1/{city}/lines/{id}/vehicles` | Hattaki araçların canlı konumu |
| `GET /v1/{city}/stops/nearby?latitude=&longitude=&radius=500` | Yakındaki duraklar, mesafeye göre |
| `GET /v1/{city}/stops/{id}` | Durak ve durağa uğrayan hatlar |
| `GET /v1/{city}/stops/{id}/arrivals` | Durağa yaklaşan araçlar, kalan durak sayısına göre |

Örnek:

```sh
curl localhost:8000/v1/izmir/stops/21050/arrivals
```

```json
{
  "data": [
    {"line_id": "346", "line_name": "EVKA.5 - EGEKENT AKT.MRK", "vehicle_id": "11876", "stops_away": 4,
     "source_direction": 1, "latitude": 38.51439, "longitude": 27.05275,
     "wheelchair_accessible": true, "bike_rack": false}
  ],
  "meta": {"city": "izmir", "source": "ESHOT", "license": "İzmir Büyükşehir Belediyesi Açık Veri Lisansı",
           "source_url": "...", "live": true, "fetched_at": "2026-10-29T16:55:00+00:00", "warnings": []}
}
```

Kaynak hata verirse uç `502` döner, hata mesajı `error` alanında olur.

## Kaynak verideki bilinen sorunlar

Bunlar düzeltilmeden saklanmaz, `meta.warnings` ve alanlarla açıkça bildirilir.

- **Aynı araç birden fazla konumla geliyor (İzmir).** Bu kayıtlardan biri hareket ediyor, diğerleri eski bir konumda kalıyor ve sıraları güvenilir değil. API iki sorgu arasında yer değiştiren kaydı seçer. `position_confidence` değerleri: `single` (tek konum), `moved` (hareket eden kayıt seçildi), `ambiguous` (henüz ayırt edilemedi, ilk kayıt verildi).
- **`0,0` konumlar** atılır.
- **GTFS takvimi süresi dolmuş olabilir.** ESHOT dosyasının takvimi 2026-10-09'da bitiyor. Durum böyleyse yanıtta uyarı yer alır.
- **Canlı yön ve GTFS yönü aynı şey olmayabilir.** Canlı veri kaynağın kendi yön değerini `source_direction` alanında taşır. Bu değerin GTFS `direction_id` ile eşleştiği henüz doğrulanmadı.

## Yeni şehir eklemek

1. `turkiye_ulasim/cities.py` dosyasına şehri, GTFS adresini ve lisansını ekle.
2. `turkiye_ulasim/sources/` altına canlı veri bağlayıcısını yaz. Bağlayıcının `vehicles(line_id)` ve `arrivals(stop_id)` yöntemleri olmalı, her ikisi de `(veri, uyarılar)` döndürmeli.
3. Bağlayıcı için gerçek yanıt örnekleriyle test ekle (`tests/`).

## Test

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

## Lisans

Kod MIT lisanslı. Veri, ilgili belediyenin lisansına tabidir.
