# API kullanımı ve kaynak ayrıntıları

Şehirlerin otobüs verilerini aynı uçlardan, aynı `{data, meta}` biçimiyle sunan açık kaynak API. Öncelik büyükşehirlerin otobüsleri; metro, tramvay ve vapur sonraki aşamada.

**22 il destekleniyor.** İzmir, İstanbul, Konya, Kahramanmaraş; Antalya, Kocaeli, Adana, Gaziantep; Erzurum, Mardin, Muğla, Ordu, Çanakkale, Düzce, Burdur, Niğde, Kırklareli, Osmaniye, Tokat, Kastamonu, Sivas ve Edirne. Destek, kaynağın sunduğu veriye göre değişir:

| Şehir | Hat / durak / yakın durak | Güzergâh geometrisi | Canlı araç | Canlı varış | Veri lisansı |
|---|---|---|---|---|---|
| İzmir · ESHOT | Var | Var | Var | Var | İzmir BB Açık Veri Lisansı |
| İstanbul · İETT | Var | Kaynakta yok | Var | Desteklenmiyor | İBB Açık Veri Lisansı |
| Konya | Var | Var | Desteklenmiyor | Desteklenmiyor | CC BY 4.0 |
| Kahramanmaraş · topluluk köprüsü | Arama / durak / yakın durak | Var | Var | Var | Kaynak veri lisansı belirtilmemiş |
| Antalya, Kocaeli, Adana, Gaziantep · topluluk GTFS | Var | Var | Desteklenmiyor | Desteklenmiyor | Derleme CC0; alt veri hakları Kentkart/belediyede |

Kahramanmaraş, [Kahramankart Ulaşım API’sinin](https://github.com/uzaylikafasi/kahramankart-ulasim-api) herkese açık köprüsünü kullanır. `source_kind=community_bridge` ile işaretlenir; GTFS ve tam hat kataloğu sunmaz. İzmir, İstanbul ve Konya `official_open_data` kaynaklarıdır. Diğer 16 il [Egezenn/kk-gtfs](https://github.com/Egezenn/kk-gtfs) topluluk derlemesini kullanır (`community_gtfs`); resmi belediye yayını değildir. Kaynaktaki takvim ve ara durak zamanları türetilmiştir; takvim verinin güncel olduğunun kanıtı değildir. Yalnız otobüsler alınır, canlı araç/varış sunulmaz.

Şehirlerin kurulum durumu ve yetenekleri `/v1/cities` yanıtındaki `available` ve `capabilities` alanlarından okunur; `available` kaynağın yapılandırıldığını belirtir, anlık sağlık kontrolü değildir. `capabilities.line_catalog` tam hat listesini, `gtfs` statik GTFS desteğini belirtir. Canlı verisi desteklenmeyen uç `501`, henüz veritabanı kurulmamış şehir `503` döner. Boş bir araç listesi başarılı bir canlı sorgunun sonucu olabilir; destek yokluğu anlamına gelmez.

**Ortak geliştirme:** [Yapılacaklar ve işi devralma](../YAPILACAKLAR.md).

## Kurulum

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m tools.gtfs_guncelle         # tüm desteklenen şehirler
# veya: .venv/bin/python -m tools.gtfs_guncelle istanbul konya
.venv/bin/uvicorn turkiye_ulasim.main:app --port 8010 --workers 1
```

Canlı API: **https://mithrixa.com/turkiye-ulasim-api** · [Canlı belgeler](https://mithrixa.com/turkiye-ulasim-api/docs) · [Yayın ve bakım](../deployment/README.md).

Yerel belgeler: `http://localhost:8010/docs`. Örneklerde yerel sunucu için 8010 portu kullanılır. GTFS verileri `data/<şehir>.sqlite3` dosyalarındadır; dizin `ULASIM_DATA_DIR` ile değiştirilebilir. Kahramanmaraş için içe aktarma veya erişim anahtarı gerekmez; uzak API kullanılır. Köprü `ULASIM_KAHRAMANMARAS_ENABLED=0` ile kapatılabilir. Varsayılan GTFS güncellemesi 21 statik ZIP kaynağını indirir. İçe aktarma geçici dosyada tamamlanır, başarıdan sonra eski veritabanının yerini alır. Bir şehir güncellenemezse diğerleri denenir; komut hata koduyla biter ve o şehrin eski verisi korunur. Çalışan API sonraki veri sorgusunda yeni dosyayı sunucuyu yeniden başlatmadan yükler. Canlı kurulumda sürekli servis ve günlük 04:10 güncellemesi bulunur; yalnız depoyu indirmek bu servisleri başka makinede kurmaz.

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
curl 'localhost:8010/v1/istanbul/lines?q=15F'
curl 'localhost:8010/v1/konya/lines/1-A/stops?direction=0'
curl 'localhost:8010/v1/izmir/stops/21050/arrivals'
```

Her yanıtta `meta.city`, `source`, `license`, `source_url`, `live` ve `warnings` bulunur. Canlı yanıttaki `fetched_at`, kaynaktan alınma zamanıdır; önbellekte değişmez. `cached` önbellek kullanımını belirtir. İstanbul araçlarında ayrıca kaynağın konum zamanı `observed_at` ve beş dakikadan eski, gelecekte veya doğrulanamayan zamanlar için `stale` bulunur. Kaynak hatası `502`; İETT saatlik bütçesi dolduğunda `503` ve `Retry-After` döner.

## Kahramanmaraş kullanımı

```sh
curl 'localhost:8010/v1/kahramanmaras/lines?q=H%2F1'
curl 'localhost:8010/v1/kahramanmaras/lines/9576:1/stops?direction=0'
curl 'localhost:8010/v1/kahramanmaras/lines/9576:1/vehicles'
curl 'localhost:8010/v1/kahramanmaras/stops/6968/arrivals'
```

Hat kimliği **kaynak kimliği:yön** biçimindedir: `9576:1` ve `161:2` farklı kayıtlardır. Aramadan dönen kimliği aynen kullanın. Kaynak gidiş=1/dönüş=2, ortak durak/geometri sorgularında sırasıyla `direction=0/1` olur; `source_direction` özgün değeri korur. Kaynak yön=3 için 0/1 karşılığı henüz doğrulanmadığından sıra/geometri sorgusu `501` döner.

Kaynak tam hat listesini yayımlamadığı için boş `q` ile `/lines` sorgusu `422` döner. Arama sonuçları sınırlıdır; `meta.pagination.source_limited=true`, dönen arama kümesinin şehir envanteri olmadığını belirtir. `has_more` yalnız dönen küme içindeki sayfalamaya aittir.

Varış ve durak-hat kayıtlarında yön yoksa ortak `line_id` / `id` **null** kalır; özgün kimlik `source_line_id` / `source_id` içinde korunur. Varışlarda kaynak saniye tahmini `eta_seconds`, özgün yazı `source_remaining_time` alanındadır; `stops_away` bilinmiyorsa null kalır. `distanceToStop` alanının birimi doğrulanmadığından metre diye sunulmaz. Araç GPS ölçüm zamanı verilmez: `observed_at=null`; `fetched_at` veri alınma zamanıdır.

Köprüde kısa süreli, en fazla 256 yanıtlık önbellek, eşzamanlı sorgu birleştirme ve süreç başına dakikada 60 kaynak isteği bütçesi vardır. İki canlı sorgu arasında en az 15 saniye bırakın. Aynı IP’de başka tüketiciler varsa kaynağın kendi sınırı daha erken uygulanabilir. Üst kaynak veya yerel bütçe sınırında `503` ve `Retry-After` döner.

## Kaynaklar ve sınırlar

Resmi açık veri kaynakları ile topluluk köprüleri `source_kind` alanında ayrılır. Kahramanmaraş’ın kaynak veri lisansı doğrulanmış değildir; MIT ifadesi yalnız bağlayıcı koduna aittir. Kodun MIT lisansı belediye verisinin lisansının yerini almaz; `meta` içindeki kaynak ve lisans bilgisini uygulamanızda koruyun.

- İzmir: [ESHOT GTFS](https://acikveri.bizizmir.com/dataset/toplu-ulasim-gtfs-verileri), [İZTEK servis belgesi](https://openfiles.izmir.bel.tr/471231/docs/iztek-WebServisKullanimDokumani_1.0.pdf).
- İstanbul: [İETT GTFS kataloğu](https://data.ibb.gov.tr/dataset/iett-gtfs-verisi), [İETT servis belgesi v1.4](https://data.ibb.gov.tr/dataset/367a12a3-958c-4ecf-b7e8-41b5bf3b5580/resource/5c3e950f-61e5-4713-bd6d-46d1494c745e/download/en_iett-web-service-usage-document-v.1.4.pdf), [canlı konum WSDL](https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx?WSDL).
- Konya: [GTFS kataloğu ve CC BY 4.0 lisansı](https://acikveri.konya.bel.tr/dataset/toplu-tasima-gtfs-verileri).
- Kahramanmaraş: [topluluk API belgesi](https://mithrixa.com/ulasim-api/docs), [kaynak kodu](https://github.com/uzaylikafasi/kahramankart-ulasim-api). Ortak bağlayıcı doğrudan Pallium’a bağlanmaz; erişim bilgisi taşımaz.

İstanbul CSV dosyaları CKAN kataloğundan bulunur; büyük `stop_times` ZIP'i akışla indirilir. Noktalı virgül ayracı, bozuk Türkçe metin ve binlik gruplamaya dönüşmüş koordinatlar düzeltilir. Sütunları kayan duraklar belgelenmiş `GetDurak_json` servisiyle doğrulanır; doğrulanamazsa içe aktarma başarısız olur. Kaynaktaki kimliksiz devam satırları atlanır; güzergâh kodu eksik hatlarda canlı eşleştirme `501` döner.

Bilinen sınırlar:

- **İETT saatte en fazla 100 istek kabul eder.** Bağlayıcı süreç başına 90 istek bütçesi ve hat kodu başına 60 saniye önbellek uygular; aynı anda aynı hat için tek istek gider. Hatalı istekler de sayılır. Tek worker kullanın. Birden çok süreç/sunucu veya aynı IP'deki başka tüketiciler için ortak kota gerekir. Bu sınır nedeniyle ülke ölçeğinde canlı hizmet için sağlayıcıyla ayrıca kapasite planlamak gerekir.
- **Verinin tarihi ile takvim farklıdır.** Konya kaynağı Kasım 2025'tendir, takvimi 2030'a uzanır. Eski kaynak uyarısı yanıtlarda korunur. Takvimi geçmiş dosyalar ayrıca uyarı üretir; zaman çizelgesi sorgusu sunulmaz.
- **Hat/yön başına en çok duraklı tek sefer temsilci seçilir.** En uzun üç adayda aynı sıra numarasının farklı duraklara verilmesi kontrol edilir; tutarlı aday yoksa durak sırası ve geometri uyarıyla atlanır. Alternatif dalların tümü ve hizmet takvimine göre bugün çalışıp çalışmadığı hesaplanmaz. Bir durağın hat listesi de bu temsilci seferlerle sınırlıdır. Katalogda seferi olmayan hat varyantlarında `directions` boş olabilir. Otobüs dışındaki hatlar ve yalnız onlara ait duraklar içe alınmaz.
- **İzmir aynı aracı farklı konumlarla gönderebilir.** `position_confidence`: `single` tek konum, `moved` önceki sorguya göre hareket eden kayıt, `ambiguous` ayırt edilemeyen kayıt. Bu karşılaştırma kaynağın zaman damgası kadar kesin değildir. `0,0` konumlar atılır.
- **Canlı yön, GTFS yönüyle aynı kabul edilmez.** Kaynağın yön değeri `source_direction` alanında korunur.

Büyükşehirlerin kaynak durumu ve devam sırası: [docs/BUYUKSEHIRLER.md](BUYUKSEHIRLER.md).

## Yeni şehir ve test

`turkiye_ulasim/cities.py` içine kaynak türü, veri lisansı ve canlı yetenekleri ekleyin. Doğrulanmamış kaynağı resmi açık veri olarak etiketlemeyin. Statik şehir için GTFS kaynağı yeterlidir. Canlı bağlayıcı `LiveResult` döndürür; kaynak hataları `SourceError` olur. Şehri `default_sources()` içine bağlayın; gerçek yanıt örneğiyle çevrimdışı test ekleyin.

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

GitHub Actions için [hazır test şablonu](templates/github-tests.yml) vardır. Henüz etkin değildir. GitHub web arayüzünden `.github/workflows/tests.yml` olarak eklenince her PR ve main push’unda Python 3.11 / 3.12 ile çevrimdışı testleri çalıştırır. Testler gerçek servisleri çağırmaz; canlı kontroller ayrı yapılır.

Kod [MIT](../LICENSE) lisanslıdır.

## Sağlık ve veri durumu

- `/healthz`: uygulama ayakta mı? Verinin tam veya canlı kaynağın erişilebilir olduğunu söylemez.
- `/readyz`: 21 statik ZIP kaynağının dosyaları ve temel tabloları okunabiliyorsa 200; eksik/bozuksa 503. İsteğe bağlı Maraş köprüsü bu yerel koşula dahil değildir.
- `/v1/status`: şehir başına yapılandırma, dosya okunabilirliği, `imported_at`, takvim bitişi/süresi ve bu süreçte gözlenen son canlı başarı/hata bilgisi.

Bu uçlar kaynağa ağ isteği yapmaz ve kota tüketmez; `upstream_checked=false` kalır. Konya gibi uzun takvimli eski kaynakların güncel olduğunu kanıtlamaz. Eski veritabanında içe aktarma zamanı yoksa null gösterilir. Canlı gözlemler yeniden başlatmada sıfırlanır; hata mesajı, anahtar ve yerel dosya yolu yayımlanmaz. Canlı kurulumda sürekli API servisi ve günlük güncelleme bulunur; kurulum ve sınırlar [yayın belgesindedir](../deployment/README.md). Sağlık uçları dış sağlayıcının erişilebilirliğini kendiliğinden test etmez.

31 Ekim yeni otobüs kapsamı: Antalya 162 hat/4.503 durak; Kocaeli 409/8.597; Adana 291/3.618; Gaziantep 162/3.110. Bunlar kaynak dosyasından alınan katalog sayılarıdır, bugün aktif sefer sayısı değildir. Kaynak: [topluluk veri deposu](https://github.com/Egezenn/kk-gtfs).

Yeni 11 ilin hat/durak sayıları ve kısmi kapsamı: [il kapsam tablosu](YENI_ILLER.md). Eksik kaynaklar çalışır destek olarak sayılmadı.

## Sivas ve Edirne: eksik dosyayı gerçek servisle tamamlama

Bu iki kaynağın ZIP dosyasında `trips.txt` ve `stop_times.txt` yoktur. Hat ve durak katalogları doğrulanır; ardından Kentkart `pathInfo` servisinden aynı hat kimliği, görünen kod ve yönle eşleşen durak sırası / geometri alınır. Farklı hat veya yön yanıtı kullanılmaz. Sefer, saat veya hizmet takvimi üretilmez.

Bu yüzden `partial_feed=true`, `source_kind=community_catalog`, `capabilities.gtfs=false` kalır. Doğrulanmış hat/yönde durak ve geometri uçları çalışır; bulunmayan ilişkide 501 döner. `directions` yalnız kaydedilmiş yönleri gösterir. `meta.topology_source` ve `topology_updated_at`, ilişkilerin kaynağını ve doğrulama zamanını belirtir. Kaynakta olmayan durak-hat bağlantısı tahmin edilmez.

Güncelleyici çağrılar arasında en az bir saniye bırakır. Servis/doğrulama başarısız olursa önceki dosya korunur; yarım sonuç canlıya geçirilmez. Yerel dosya ve sağlayıcı verisi farklı tarihlerden gelebilir; bu veri bugün çalışma veya tam kapsam garantisi değildir.
