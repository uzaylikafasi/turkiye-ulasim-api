# Türkiye Ulaşım API

Şehirlerin otobüs verilerini aynı uçlardan, aynı `{data, meta}` biçimiyle sunan açık kaynak API. Öncelik büyükşehirlerin otobüsleri; metro, tramvay ve vapur sonraki aşamada.

**0.2.0: İzmir, İstanbul ve Konya.** Destek, resmi kaynağın sunduğu veriye göre değişir:

| Şehir | Hat / durak / yakın durak | Güzergâh geometrisi | Canlı araç | Canlı varış | Veri lisansı |
|---|---|---|---|---|---|
| İzmir · ESHOT | Var | Var | Var | Var | İzmir BB Açık Veri Lisansı |
| İstanbul · İETT | Var | Kaynakta yok | Var | Desteklenmiyor | İBB Açık Veri Lisansı |
| Konya | Var | Var | Desteklenmiyor | Desteklenmiyor | CC BY 4.0 |

Şehirlerin kurulum durumu ve yetenekleri `/v1/cities` yanıtındaki `available` ve `capabilities` alanlarından okunur. Canlı verisi desteklenmeyen uç `501`, henüz veritabanı kurulmamış şehir `503` döner. Boş bir araç listesi başarılı bir canlı sorgunun sonucu olabilir; destek yokluğu anlamına gelmez.

## Kurulum

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m tools.gtfs_guncelle         # tüm desteklenen şehirler
# veya: .venv/bin/python -m tools.gtfs_guncelle istanbul konya
.venv/bin/uvicorn turkiye_ulasim.main:app --port 8000 --workers 1
```

Belgeler: `http://localhost:8000/docs`. Veriler `data/<şehir>.sqlite3` dosyalarındadır; dizin `ULASIM_DATA_DIR` ile değiştirilebilir. İçe aktarma geçici dosyada tamamlanır, başarıdan sonra eski veritabanının yerini alır. Bir şehir güncellenemezse diğerleri denenir; komut hata koduyla biter ve o şehrin eski verisi korunur. Açık API süreci yeni veritabanını kullanmak için yeniden başlatılmalıdır. Sürekli sunucu veya otomatik güncelleme bu depoyu indirmekle kurulmaz.

## Uçlar

| Uç | Açıklama |
|---|---|
| `GET /v1/cities` | Şehirler, kaynaklar, lisanslar, yetenekler ve kurulum durumu |
| `GET /v1/{city}/lines?q=&limit=200&offset=0` | Türkçe harf duyarsız arama; `limit` en fazla 500, `meta.pagination.has_more` devamı belirtir |
| `GET /v1/{city}/lines/{id}` | Hat ve mevcut yönleri |
| `GET /v1/{city}/lines/{id}/stops?direction=0` | Temsilci seferin sıralı durakları |
| `GET /v1/{city}/lines/{id}/shape?direction=0` | `[[enlem, boylam], ...]`; geometri yoksa boş liste ve uyarı |
| `GET /v1/{city}/lines/{id}/vehicles` | Canlı araçlar; destek yoksa `501` |
| `GET /v1/{city}/stops/nearby?latitude=&longitude=&radius=500` | En yakın 20 durak; yarıçap en fazla 3000 metre |
| `GET /v1/{city}/stops/{id}` | Durak ve temsilci seferlerde durağa uğrayan hatlar |
| `GET /v1/{city}/stops/{id}/arrivals` | Canlı varış; destek yoksa `501` |

İstanbul'da önce `/v1/istanbul/lines?q=15F` ile hat kimliğini seçin. GTFS `route_id`, görünen `15F` kodundan farklıdır; yönler ve güzergâh varyantları ayrı kimlik taşır. Canlı uç `source_route_code` ile tam varyantı eşleştirir, aynı kodun bütün araçlarını her varyanta kopyalamaz. Konya kimlikleri `1-A`, durakları `1000a` gibi alfasayısal olabilir.

```sh
curl 'localhost:8000/v1/istanbul/lines?q=15F'
curl 'localhost:8000/v1/konya/lines/1-A/stops?direction=0'
curl 'localhost:8000/v1/izmir/stops/21050/arrivals'
```

Her yanıtta `meta.city`, `source`, `license`, `source_url`, `live` ve `warnings` bulunur. Canlı yanıttaki `fetched_at`, kaynaktan alınma zamanıdır; önbellekte değişmez. `cached` önbellek kullanımını belirtir. İstanbul araçlarında ayrıca kaynağın konum zamanı `observed_at` ve beş dakikadan eski, gelecekte veya doğrulanamayan zamanlar için `stale` bulunur. Kaynak hatası `502`; İETT saatlik bütçesi dolduğunda `503` ve `Retry-After` döner.

## Kaynaklar ve sınırlar

Yalnız resmi açık veri olarak yayımlanan kaynaklar kullanılır. Kodun MIT lisansı belediye verisinin lisansının yerini almaz; `meta` içindeki kaynak ve lisans bilgisini uygulamanızda koruyun.

- İzmir: [ESHOT GTFS](https://acikveri.bizizmir.com/dataset/toplu-ulasim-gtfs-verileri), [İZTEK servis belgesi](https://openfiles.izmir.bel.tr/471231/docs/iztek-WebServisKullanimDokumani_1.0.pdf).
- İstanbul: [İETT GTFS kataloğu](https://data.ibb.gov.tr/dataset/iett-gtfs-verisi), [İETT servis belgesi v1.4](https://data.ibb.gov.tr/dataset/367a12a3-958c-4ecf-b7e8-41b5bf3b5580/resource/5c3e950f-61e5-4713-bd6d-46d1494c745e/download/en_iett-web-service-usage-document-v.1.4.pdf), [canlı konum WSDL](https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx?WSDL).
- Konya: [GTFS kataloğu ve CC BY 4.0 lisansı](https://acikveri.konya.bel.tr/dataset/toplu-tasima-gtfs-verileri).

İstanbul CSV dosyaları CKAN kataloğundan bulunur; büyük `stop_times` ZIP'i akışla indirilir. Noktalı virgül ayracı, bozuk Türkçe metin ve binlik gruplamaya dönüşmüş koordinatlar düzeltilir. Sütunları kayan duraklar belgelenmiş `GetDurak_json` servisiyle doğrulanır; doğrulanamazsa içe aktarma başarısız olur. Kaynaktaki kimliksiz devam satırları atlanır; güzergâh kodu eksik hatlarda canlı eşleştirme `501` döner.

Bilinen sınırlar:

- **İETT saatte en fazla 100 istek kabul eder.** Bağlayıcı süreç başına 90 istek bütçesi ve hat kodu başına 60 saniye önbellek uygular; aynı anda aynı hat için tek istek gider. Hatalı istekler de sayılır. Tek worker kullanın. Birden çok süreç/sunucu veya aynı IP'deki başka tüketiciler için ortak kota gerekir. Bu sınır nedeniyle ülke ölçeğinde canlı hizmet için sağlayıcıyla ayrıca kapasite planlamak gerekir.
- **Verinin tarihi ile takvim farklıdır.** Konya kaynağı Kasım 2025'tendir, takvimi 2030'a uzanır. Eski kaynak uyarısı yanıtlarda korunur. Takvimi geçmiş dosyalar ayrıca uyarı üretir; zaman çizelgesi sorgusu sunulmaz.
- **Hat/yön başına en çok duraklı tek sefer temsilci seçilir.** En uzun üç adayda aynı sıra numarasının farklı duraklara verilmesi kontrol edilir; tutarlı aday yoksa durak sırası ve geometri uyarıyla atlanır. Alternatif dalların tümü ve hizmet takvimine göre bugün çalışıp çalışmadığı hesaplanmaz. Bir durağın hat listesi de bu temsilci seferlerle sınırlıdır. Katalogda seferi olmayan hat varyantlarında `directions` boş olabilir. Otobüs dışındaki hatlar ve yalnız onlara ait duraklar içe alınmaz.
- **İzmir aynı aracı farklı konumlarla gönderebilir.** `position_confidence`: `single` tek konum, `moved` önceki sorguya göre hareket eden kayıt, `ambiguous` ayırt edilemeyen kayıt. Bu karşılaştırma kaynağın zaman damgası kadar kesin değildir. `0,0` konumlar atılır.
- **Canlı yön, GTFS yönüyle aynı kabul edilmez.** Kaynağın yön değeri `source_direction` alanında korunur.

Büyükşehirlerin kaynak durumu ve devam sırası: [docs/BUYUKSEHIRLER.md](docs/BUYUKSEHIRLER.md).

## Yeni şehir ve test

`turkiye_ulasim/cities.py` içine resmi kaynak/lisans ve canlı yetenekleri ekleyin. Statik şehir için GTFS kaynağı yeterlidir. Canlı bağlayıcı `LiveResult` döndürür; kaynak hataları `SourceError` olur. Şehri `default_sources()` içine bağlayın; gerçek yanıt örneğiyle çevrimdışı test ekleyin.

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Kod [MIT](LICENSE) lisanslıdır.
