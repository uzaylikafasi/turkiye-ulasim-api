# API kullanımı ve kaynak ayrıntıları

Şehirlerin otobüs verilerini aynı uçlardan, aynı `{data, meta}` biçimiyle sunan açık kaynak API. Öncelik büyükşehirlerin otobüsleri; metro, tramvay ve vapur sonraki aşamada.

**28 il destekleniyor.** İzmir, İstanbul, Konya, Kahramanmaraş; Antalya, Kocaeli, Adana, Gaziantep; Erzurum, Mardin, Muğla, Ordu, Çanakkale, Düzce, Burdur, Niğde, Kırklareli, Osmaniye, Tokat, Kastamonu, Sivas, Edirne, Sakarya, Ankara, Samsun, Mersin, Trabzon ve Diyarbakır. Destek, kaynağın sunduğu veriye göre değişir:

| Şehir | Hat / durak / yakın durak | Güzergâh geometrisi | Canlı araç | Canlı varış | Veri lisansı |
|---|---|---|---|---|---|
| İzmir · ESHOT | Var | Var | Var | Var | İzmir BB Açık Veri Lisansı |
| İstanbul · İETT | Var | Kaynakta yok | Var | Desteklenmiyor | İBB Açık Veri Lisansı |
| Konya | Var | Var | Desteklenmiyor | Desteklenmiyor | CC BY 4.0 |
| Kahramanmaraş · topluluk köprüsü | Arama / durak / yakın durak | Var | Var | Var | Kaynak veri lisansı belirtilmemiş |
| Antalya, Adana · topluluk GTFS | Var | Var | Desteklenmiyor | Desteklenmiyor | Derleme CC0; alt veri hakları Kentkart/belediyede |
| Kocaeli, Gaziantep · topluluk GTFS + Kentkart canlı | Var | Kaynakta bulunan hatlarda | Var | Desteklenmiyor | Statik derleme CC0; canlı lisansı belirtilmemiş |

Kahramanmaraş, [Kahramankart Ulaşım API’sinin](https://github.com/uzaylikafasi/kahramankart-ulasim-api) herkese açık köprüsünü kullanır. `source_kind=community_bridge` ile işaretlenir; GTFS ve tam hat kataloğu sunmaz. İzmir, İstanbul ve Konya `official_open_data` kaynaklarıdır. Diğer 16 il [Egezenn/kk-gtfs](https://github.com/Egezenn/kk-gtfs) topluluk derlemesini kullanır (`community_gtfs`); resmi belediye yayını değildir. Kaynaktaki takvim ve ara durak zamanları türetilmiştir; takvim verinin güncel olduğunun kanıtı değildir. Yalnız otobüsler alınır. Bu 16 ilin Kocaeli ve Gaziantep kaynaklarında ayrıca Kentkart canlı araç desteği vardır; varış desteği yoktur.

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

## Sakarya: resmî servis kataloğu

Kaynak türü `official_service`, `partial_feed=true`, `gtfs=false`. Günlük aktarım SAKUS hat/durak/güzergâh servisinden yapılır; takvim veya sefer üretilmez. Yeniden kullanım lisansı belirtilmemiştir.

`/v1/sakarya/lines?q=1` ile arayın; `/v1/sakarya/lines/2:157/stops?direction=0` ve `/v1/sakarya/lines/2:157/shape?direction=0` örneklerdir. Her `hatId:routeId` ayrı güzergâhtır. Tek `direction=0` o güzergâhın kaynak sırasını ifade eder; kaynak 219/220/221 yön kodları gidiş/dönüş diye tahmin edilmez. Güzergâhı olmayan katalog kayıtlarında yalnız hat kimliği bulunur. Kopuk çok parçalı şekiller birleştirilerek sahte bağlantı üretilmez; geometri yoksa 501 dönülür. Canlı araç/varış 501 döner.

## Ankara: EGO otobüs kataloğu

`source_kind=official_service`, `gtfs=false`, `partial_feed=true`. Kaynak: https://www.ego.gov.tr/HareketSaatleri . Yeniden kullanım lisansı belirtilmemiştir. `/v1/ankara/lines?q=Gölbaşı`, `/v1/ankara/lines/101/stops?direction=0`, `/v1/ankara/stops/14043` örnek sorgulardır.

`capabilities.stop_coordinates=false`, `capabilities.nearby=false`; durakların latitude/longitude alanları null'dır. Yakın durak ve geometri desteklenmez (501). Canlı araçlar ve durak varışları desteklenir. Kaynakta tek liste yayımlanır; direction=0 bu sırayı korur, gidiş/dönüş eşlemesi değildir. Günlük aktarım tek dosyayı atomik değiştirir; kimlik, durak sırası veya kaynak şeması hatasında eski veri korunur.

`/v1/ankara/stops/14043/arrivals` EGO Cep’te servisindeki gerçek araç kayıtlarını döndürür. `arac_no=-` tarife mesajları, geçersiz konumlar ve geçiş tamamlandı anlamındaki 999999 süre değeri dahil edilmez. `eta_seconds` kaynak saniye alanıdır; `observed_at` kaynak GPS zamanı (Europe/Istanbul), `fetched_at` sorgulama zamanıdır. `line_id=null`; kaynak hat kodu `source_line_id` ve yön kodu `source_direction` alanında korunur. Kaynak yön kodlarının ortak yönlere karşılığı tahmin edilmez. 20 saniye önbellek, 30 kaynak isteği/dakika sınırı vardır.

## Samsun: SAMULAŞ otobüs haritaları

`source_kind=official_service`, `partial_feed=true`, `gtfs=false`. Kaynak: https://samulas.com.tr/otobusler . Yeniden kullanım lisansı belirtilmemiştir. `/v1/samsun/lines?q=8`, `/v1/samsun/lines/390/stops`, `/v1/samsun/stops/9542` örnek sorgulardır.

Hat kimliği SAMULAŞ `line_no` alanıdır; hat kodu görünen metnin başındaki koddan alınır. Durak kimliği harita etiketindeki iç kimliktir; görünen durak numarası adın başında korunur. Aynı görünen numara farklı konumlarda kullanıldığı için anahtar olarak kullanılmaz. Koordinat aynı işaretten alınır. İşaret sırası korunur; sefer/durak-sırası dosyasıyla doğrulanmış değildir. `direction=0` yayımlanan haritadır; ayrı gidiş/dönüş anlamı yüklenmez. Kopuk MultiLineString parçaları bağlanmaz ve bu kayıtların geometrisi 501 döner. Canlı araç/varış 501 döner.

## Mersin: kaynak hat/yön kayıtları

Resmî portal: https://ulasim.mersin.bel.tr/hatveguzergahlar . `source_kind=official_service`, `partial_feed=true`, `gtfs=false`; yeniden kullanım lisansı belirtilmemiştir. Örnekler: `/v1/mersin/lines?q=10M`, `/v1/mersin/lines/10M-G/stops`, `/v1/mersin/lines/10M-G/shape`, `/v1/mersin/stops/54397`.

Kaynak `hat_no` ve `hat_yon` birlikte kimliktir. `direction=0` bu kaydın kendi sırasını korur; ayrı kayıttaki dönüş listesiyle birleştirilmez. Durak sırası kaynağın yanıt sırasıdır, sefer dosyasıyla doğrulanmadı. Katalog adları durak listesinin başlangıç/bitişiyle tam örtüşmeyebilir. Yanıt hat kimliğini tekrar etmez; ilişki katalogdaki kod/yönün sorgulanmasına dayanır. Kaynak 0 döndürürse veri yoktur; eksik durak/geometri 501 döner. Canlı araç/varış sunulmaz.

## Trabzon: AKUS GeoJSON

Kaynak https://ulasim.trabzon.bel.tr/ ; `source_kind=official_service`, `partial_feed=true`, `gtfs=false`. Yeniden kullanım lisansı belirtilmemiştir. `/v1/trabzon/lines?q=103`, `/v1/trabzon/lines/1:36/stops`, `/v1/trabzon/lines/1:39/shape` örneklerdir.

Her hat/güzergâh ayrı kimlik taşır. G/D yön alanları ve 1/2 kaynak yön numaraları birlikte doğrulanır; farklı varyantlar birleştirilmez. `direction=0` yalnız seçilen güzergâhın kendi sırasıdır. Duraklarda `durak_id` iç kimliği kullanılır. Sıra kaynağın `sira` alanıdır. Kaynağın EPSG:3857 koordinatları WGS84 enlem/boylama çevrilir; beklenmeyen koordinat sistemi aktarımı durdurur. Canlı araçlar ve durak varışları desteklenir; sefer takvimi desteklenmez.

## Diyarbakır: resmî belediye ASIS köprüsü

Kaynak https://www.diyarbakir.bel.tr/ulasim/canli ; `source_kind=official_service`, `partial_feed=true`, `gtfs=false`. Lisans belirtilmemiştir. `/v1/diyarbakir/lines?q=A1`, `/v1/diyarbakir/lines/117/stops?direction=0`, `/v1/diyarbakir/lines/117/shape?direction=1` örneklerdir.

API kimliği kaynağın `lineNo` iç numarasıdır, görünen kod `code` alanında korunur. Kaynak Gidiş/Dönüş listeleri 0/1 yönlerine çevrilir; `lineCode`, `lineNo`, durak kimliği ve sıra birlikte doğrulanır. Geometrinin `routeCode` ve G/D yönü ayrıca eşleştirilir. Kaynak genel durak envanterinden yalnız içe alınan otobüslerin kullandığı duraklar yayımlanır. Koordinatsız duraklar null kalır ve yakın durak sonucuna girmez.

Kaynak `Response Model is Empty. This LineCode not have Coordinates...` mesajıyla geometri yokluğunu bildirebilir; yalnız bu açık yanıt boş geometri sayılır. Diğer başarısız sonuçlar aktarımı durdurur ve eski dosya korunur. Eksik geometri 501; canlı araçlar desteklenir, durak varışları henüz desteklenmez. Başlangıç verisi resmî sayfanın JSON parçalarından okunur, JavaScript çalıştırılmaz.

## Diyarbakır canlı araçlar ve Trabzon varışları

`/v1/diyarbakir/lines/117/vehicles` kaynağın hat kodu ve iç numarasını birlikte doğrular. Araçlarda `source_direction=G/D`, ortak `direction=0/1` alanıdır; `heading_degrees` aracın pusula açısıdır ve yön kodu yerine kullanılmaz. `speed_kmh` kaynak hızıdır. `observed_at` GPS zamanı, `age_seconds` sorgu anındaki yaşı, `stale` 300 saniyeden eski kaydı gösterir. Saat dilimi olmayan kaynak zamanı Europe/Istanbul kabul edilir; bu varsayım meta uyarısında belirtilir. Geçersiz/belirsiz GPS zamanı null, gelecekte 120 saniyeden uzak zaman bilinmeyen sayılır. Aynı aracın en yeni ölçümü seçilir; aynı zamanda çelişen konumlar çıkarılır. Yalnız ortak araç alanları yayımlanır.

`/v1/trabzon/stops/3528/arrivals` iç durak kimliğini kaynağın `DurakQrKod=1032` koduna eşler. `stops/{id}` yanıtı `code` alanında QR kodunu sunar. `eta_seconds` kaynak tahmini, `stops_away` kalan durak sayısıdır. GPS konumu/zamanı yoktur; `observed_at`, latitude/longitude null kalır. `line_id` yalnız durakta doğrulanmış yerel hatId:güzergâhId ilişkisi varsa doldurulur; aksi halde null ve kaynak kimlikleri ayrı korunur.

İki canlı kaynakta 15 saniye önbellek ve 30 kaynak isteği/dakika vardır. `cached=true` yanıtında GPS yaşı orijinal `fetched_at` anına aittir. Kaynak hatası boş başarıya dönüştürülmez. Trabzon hat araç listesi de desteklenir; konum servisi JSON POST ile doğrulandı.

### Trabzon araç konumları

`/v1/trabzon/lines/59:94/vehicles` resmî `Web/KonumGetir` uç noktasını JSON POST (`{}`) ile kullanır. Form isteklerinde görülen hata, JSON biçiminde düzelir. Genel araç yanıtı 15 saniye boyunca kaynak başına paylaşılır; her sorgu kendi hatId:güzergâhId kaydına süzülür ve görünen hat kodu ayrıca eşleştirilir. Başka hatlara ait araçlar sonuca karışmaz. Kaynak yanıtı dışındaki filonun kapsamı doğrulanmaz; boş liste tüm şehirde araç olmadığı anlamına gelmez.

KonumX/KonumY yanıtlarında hem WGS84 derece hem EPSG:3857 metre değerleri gözlendi. Canlı yanıtta CRS etiketi yoktur. Gözlenen biçimler Türkiye için birbiriyle örtüşmeyen değer aralıklarıyla yorumlanır ve dönüştürülür; `source_coordinate_system` hangi biçimin okunduğunu belirtir. Aralık dışı konumlar çıkarılır. API enlem/boylam sunar. Sabit araç kimliği PlakaKod'dur; ölçüm Id alanı araç kimliği yapılmaz. `observed_at` kaynak Tarih alanıdır (Europe/Istanbul), `age_seconds` sorgu anındaki yaşı, `stale` 300 saniyeden eski konum işaretidir. Tarih bilinmiyor/sentinel/120 saniyeden fazla gelecekte ise zaman ve stale null kalır. En yeni kayıt seçilir; aynı araç/zamanda çelişkili konum veya hat kaydı yayımlanmaz. Ortak alanlar dışındaki ham kaynak alanları aktarılmaz. Varış ve araç sorguları 30/dakika kaynak bütçesini paylaşır.

Diyarbakır için kontrol edilen `station-routes` ucu yalnız geçen hatları döndürür; bu listeden ETA türetilmez ve varış desteği henüz açılmaz.

### Ankara hat araçları ve GPS güncelliği

`/v1/ankara/lines/263/vehicles` EGO Cep’te `FNC=Otobus&HAT=263` çağrısını durak parametresi olmadan kullanır. Yerel hat kodu/kimliği ile kaynağın hat_no/hat_kod alanları eşleştirilir. Tarife mesajları (`arac_no=-`) araç listesine alınmaz. Araç yanıtı varış süresi sunmaz; durak sorgusu yapılmadığı için kaynak `saniye` alanı bu uçta kullanılmaz. Geçmiş/geçilmiş varış işareti gerçek konumu araç listesinden çıkarma nedeni değildir.

GPS `konum_tarihi` Europe/Istanbul kabul edilir. `observed_at` kaynak zamanı, `age_seconds` sorgu anındaki yaş, `stale` 300 saniyeden eski konumu gösterir. Bilinmeyen/sentinel veya 120 saniyeden uzak gelecek zaman null kalır. En yeni kayıt seçilir; aynı araçta aynı zamanlı çelişen konumlar çıkarılır. Hız ve pusula açısı ayrı alanlardır; kaynak yon=3/4 gibi değerler ortak 0/1 yönü diye tahmin edilmez (`direction=null`).

Aynı GPS güncellik alanları Ankara varışlarına da eklendi. 15 saniye araç, 20 saniye varış önbelleği ve ortak 30 kaynak isteği/dakika bütçesi vardır. Önbellekte yaş alanı orijinal fetched_at anına aittir. Statik durak koordinatı ve geometri eksikleri devam eder; araç konumu durak koordinatı olarak kullanılmaz.

## Kentkart canlı araçlar

Kocaeli (`004`), Gaziantep (`028`), Sivas (`005`) ve Edirne (`013`) bölgelerinde [Kentkart pathInfo](https://service.kentkart.com/rl1/web/pathInfo) kaynağı kullanılır. Örnekler:

- `/v1/kocaeli/lines/41010/vehicles`
- `/v1/gaziantep/lines/00010/vehicles`
- `/v1/sivas/lines/10010/vehicles`
- `/v1/edirne/lines/22011/vehicles`

Hat kimliklerini arama sonucundan baştaki sıfırları koruyarak alın. Her sorguda iki yön ayrı istenir; kaynak `path_code = line_id + direction`, görünen hat kodu ve yön birlikte doğrulanır. Eşleşmeyen hat 501, başarısız kaynak 502 döner. Bir yön eşleşmezse yalnız doğrulanan yön uyarıyla sunulur. Aynı araç için çelişen yön/konum kayıtları yayımlanmaz. Boş araç listesi doğrulanmış hatta o anda araç görülmediğini belirtir.

Önbellek 15 saniye, şehir başına kaynak bütçesi dakikada 30 istektir; önbellek dışındaki hat sorgusu iki kaynak isteği tüketir. Kaynak sınırı 503 ve `Retry-After` döndürür. Tek süreç kullanın; birden çok süreçte ortak kota gerekir.

Kaynak GPS ölçüm zamanı doğrulanmadığından `observed_at`, `age_seconds`, `stale` null döner; `fetched_at` yalnız sorgu zamanıdır. Pusula açısı hat yönünden ayrıdır. Erişilebilirlik ve bisiklet taşıma alanları yalnız kaynak 0/1 verdiğinde doldurulur. Durak varış tahmini üretilmez.

Yanıttaki `source_kind`, `source` ve `license` statik şehir kaynağını tanımlar; canlı kaynağın adresi ve lisans belirsizliği uyarılarda ayrıca belirtilir. Statik derlemenin CC0 lisansı canlı Kentkart verisini kapsamaz. Antalya’da yerel/kaynak hat kimliği uyuşmadığı için canlı yetenek açılmadı. Diğer Kentkart şehirlerine destek otomatik yayılmaz.
