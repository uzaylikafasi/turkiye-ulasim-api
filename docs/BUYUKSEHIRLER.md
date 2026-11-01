# Büyükşehirlerde otobüs kapsamı

Öncelik otobüsler ve büyükşehirlerdir (29 Ekim 2026). Resmi açık veri ile topluluk köprüleri ayrı etiketlenir. Kaynak bağlantısı, mevcut veri ve erişim biçimi doğrulanır; veri lisansı belirsizse açıkça belirtilir. Bir mobil uygulamada canlı harita bulunması, yeniden yayımlanabilir açık API bulunduğu anlamına gelmez.

## Bu sürüm

| Şehir | Resmi kaynak | Uygulanan destek |
|---|---|---|
| İzmir | [ESHOT / İzmir açık veri](https://acikveri.bizizmir.com/dataset/toplu-ulasim-gtfs-verileri) | Otobüs GTFS + araç konumu + varış |
| İstanbul | [İETT GTFS](https://data.ibb.gov.tr/dataset/iett-gtfs-verisi), [SOAP](https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx?WSDL) | Otobüs GTFS + güzergâh varyantına göre araç konumu; varış yok |
| Konya | [GTFS](https://acikveri.konya.bel.tr/dataset/toplu-tasima-gtfs-verileri) | 162 otobüs hattı; dosyadaki üç tramvay hattı kapsam dışında. Kaynak Kasım 2025, canlı kaynak henüz doğrulanmadı. |
| Kahramanmaraş | [Mevcut topluluk API'si](https://mithrixa.com/ulasim-api/docs) | Hat arama, durak, sıra, geometri, yakın durak, araç ve varış; resmi açık veri olarak etiketlenmez. GTFS/tam hat envanteri yok; veri lisansı belirtilmemiş. |

## Sıradaki araştırma

| Öncelik | Şehir | 29 Ekim 2026 kontrolü / sonraki adım |
|---|---|---|
| 1 | Ankara | EGO ve belediyenin açık veri kaynaklarında hat/durak, GTFS ve yeniden kullanım koşulları araştırılacak. Açık bağlayıcı henüz yok. |
| 2 | Bursa | Belediye ulaşım sayfaları var; açık veri portalı denemesinde sertifika doğrulanamadı. İndirilebilir veri ve lisans doğrulanacak. |
| 3 | Antalya | Resmi açık veri kaynaklarında otobüs veri seti ve lisansı araştırılacak. |
| 4 | Kocaeli | `veri.kocaeli.bel.tr/dataset/toplu-ulasim-verisi` ve CKAN uçları bu kontrolde HTTP 502 verdi. Ulaşılabilirlik, dosya ve lisans yeniden kontrol edilecek. |
| 5 | Gaziantep | [Resmi GTFS katalog sayfası](https://acikveri.gaziantep.bel.tr/dataset/toplu-ulasim-gtfs-verileri) var; portal bu kontrolde web'den 502, yerel istemciden sertifika hatası verdi. Doğrulanmış dosya indirmesi bekleniyor. |
| 6 | Kayseri, Sakarya | Resmi açık kaynak / yeniden kullanım koşulları doğrulanacak. Kayseri belediyesinin GTFS entegrasyon duyurusu var; dış geliştiriciye açık feed adresi ayrıca bulunmalı. Uygulamanın erişim bilgileri ortak depoya taşınmayacak. |

Bu sıra büyüklüğe ve erişilebilirliğe göre çalışma sırasıdır; nüfus sıralaması değildir. Ulaşılamayan kaynaklar ülke çapındaki kapsam iddiasına dahil edilmez. Diğer büyükşehirlerin otobüs kaynakları sonraki turda incelenecek; metro, tramvay ve vapur bu işin ardından gelir.

## 0.2.0 doğrulaması · 29 Ekim 2026

28 çevrimdışı test geçti. Kurulu gerçek verilerle üç şehirde toplam 15 örnek uç `200` döndürdü; İstanbul'da canlı araç, İzmir'de canlı araç ve varış yanıtları doluydu. Bu kontroller bütün hatların güncel veya çalışır olduğunu kanıtlamaz.

| Şehir | Farklı hat kodu | Katalogdaki GTFS güzergâh/varyantı | İçe alınan durak |
|---|---|---|---|
| İzmir | 421 | 421 | 11.739 |
| İstanbul | 1.095 | 9.274 | 14.040 |
| Konya | 162 | 162 | 4.117 |

İstanbul'da 7 aday seferin durak sırası tutarsızdı; üç hat/yön için denenen üç aday da tutarsız olduğundan sıra yayımlanmadı. Ayrıca katalogdaki her varyantın sefer kaydı yoktur; toplam güzergâh sayısı kullanılabilir durak sırası veya aktif sefer sayısı değildir. İBB durak dosyasındaki dört bozuk kayıt ayrı resmi servisten doğrulandı.

## 0.3.0 doğrulaması · 29 Ekim 2026

48 çevrimdışı test geçti. Ortak API üzerinden dört şehirde toplam 14 gerçek veri sorgusu 200 döndü. Maraş H/1 gidişte 48, dönüşte 52 durak ve Demokrasi Meydanı'nda dolu varış yanıtı görüldü. Araç listesi bu son kontrolde boştu; daha önceki dolu gerçek araç yanıtı test örneğinde korunuyor. Boş veri yerine konum üretilmez.

Kahramanmaraş köprüsü GTFS indirmeden çalışır, doğrudan Pallium erişim bilgisi kullanmaz. Kimlik `9576:1` gibi kaynak id:yön içerir. Arama tam envanter değildir; eksik varış yönleri tahmin edilmez. Tam envanter ve varıştan hatta bağlama işleri [ortak listede](../YAPILACAKLAR.md) açık kaldı.

30 Ekim: sürekli ortak API [mithrixa.com/turkiye-ulasim-api](https://mithrixa.com/turkiye-ulasim-api/docs) adresinde yayımlandı; yerel servis 8010 portundadır. Günlük 04:10 güncelleme kuruldu ve ilk tur üç GTFS şehrinde başarıyla tamamlandı. Mevcut Maraş servisi değiştirilmedi. Diğer şehirlerin kaynak ve test işleri de [YAPILACAKLAR.md](../YAPILACAKLAR.md) üzerinden devralınabilir.

## 31 Ekim · Yeni şehirler

[Kaynak depo](https://github.com/Egezenn/kk-gtfs) üzerinden Antalya, Kocaeli, Adana ve Gaziantep eklendi. Belediye portallarının erişim sorunları sürerken erişilebilir topluluk GTFS verisi kullanıldı; kaynak türü `community_gtfs`, belediyenin resmi açık verisi olduğu iddia edilmez. Derleme/biçimlendirme CC0, temel verinin hakları Kentkart/belediyeye aittir. Takvim üretim tarihinden +60 gün olarak türetilir; bugün çalışma/güncellik garantisi değildir. Canlı araç/varış desteklenmiyor.

| Yeni şehir | Otobüs hat kaydı | Otobüslerin kullandığı durak |
|---|---|---|
| Antalya | 162 | 4.503 |
| Kocaeli | 409 | 8.597 |
| Adana | 291 | 3.618 |
| Gaziantep | 162 | 3.110 |

Toplam şehir desteği sekize çıktı. Otobüs dışındaki hatlar içe alınmadı. Her şehirde hat arama/detay, sıralı durak, geometri, durak detayı ve yakın durak uçları bulunur. Yeni şehirler günlük GTFS güncelleyicisine dahildir. Yukarıdaki resmi kaynak araştırmaları, bu topluluk desteğinden ayrı açık işlerdir.

31 Ekim ikinci tur: Erzurum, Mardin, Muğla ve Ordu dahil 11 yeni il eklendi; toplam 19 il. Kapsam ve dışarıda bırakılan kaynaklar [yeni il tablosunda](YENI_ILLER.md).

Kastamonu eklemesiyle toplam 20 il: geometri anahtar çakışmasının birebir aynı nokta tekrarından kaynaklandığı doğrulandı; tekilleştirme sonrası içe aktarma başarılı.

Sivas ve Edirne’nin eksik sefer dosyalarına rağmen, gerçek Kentkart servisinden 268 hat/yön ilişkisi doğrulandı. Toplam destek 22 il; bu iki il için geçerli GTFS/sefer takvimi iddiası kurulmaz.

## 31 Ekim · Sakarya servis doğrulaması

[Resmî SAKUS haritasının](https://sakus.sakarya.bel.tr/harita) kullandığı `sbbpublicapi.sakarya.bel.tr/api/v1/Ulasim` servisi doğrulandı. `busType=3869` ve `5731` katalogları toplam 162 kayıt döndürdü; ikisi Adaray olduğundan otobüs kapsamı 160 kayıt (159 otobüs, 1 metrobüs). Sorgu parametresi tek başına otobüs filtresi değildir; kaynak `busTypeId` alanı ayrıca filtrelenmelidir.

`route-and-busstops/2` örneğinde iki güzergâh, her birinde 39 sıralı durak ve MultiLineString geometri doğrulandı. Kaynak yönleri 220/221; ortak 0/1 yönüne karşılıkları henüz doğrulanmadı. Servis Origin/Referer başlıkları bekler. Yeniden kullanım lisansı doğrulanmadı; erişilebilir servis olması açık veri lisansı anlamına gelmez.

Tekrarlanabilir kontrol: `python -m tools.sakus_kontrol`. Bu araç yalnız katalog ve örnek güzergâhı denetler. Sakarya henüz ortak API'ye eklenmedi; yayımlanan kapsam 22 il. Sonraki iş tam katalog aktarımı, kaynak yönlerinin doğrulanması, atomik güncelleme ve uç testleridir.

## 1 Kasım · Sakarya entegrasyonu

SAKUS için atomik SQLite aktarımı ve günlük yenileme bağlandı. Kaynak güzergâh kimliği korunur; `hatId:routeId` ayrı API kaydıdır. Kaynağın 219/220/221 kodları için gidiş/dönüş anlamı tahmin edilmez. Bütün güzergâhların kendi durak sırası `direction=0` ile sunulur. Hatalı kimlik, koordinat, tekrarlı sıra veya çelişen durak güncellemeyi durdurur; eski dosya korunur. Kopuk MultiLineString parçaları sahte hatla bağlanmaz.

## 1 Kasım · Ankara resmî kaynakları

EGO HareketSaatleri sayfasında 662 otobüs hattı bulundu. Otobüs seçicisi metro/Ankaray alanlarından ayrı okunur. Her hattın sayfasındaki Hat No doğrulanır; yayımlanan durak numarası/adı/sırası alınır. Koordinat veya gidiş/dönüş anlamı üretilmez. Günlük güncelleme tamamlanmadan mevcut dosya değiştirilmez.

EGO Cep’te anonim `Otobusler` servisi 14043 durağında gerçek araç konumu, kaynak GPS zamanı ve kalan saniye döndürdü. Tarife mesajı (`arac_no=-`) ve geçmiş/geçersiz varış kayıtları filtrelenir. Endpoint keşfi [egomac kaynak açıklaması](https://github.com/byigitt/egomac) ile yapıldı; yanıtlar doğrudan [EGO servisinden](https://egocptsrvand.ego.gov.tr/mblSrv14/service.asp) doğrulandı. Kod bağımsız uygulandı. Kaynak yeniden kullanım lisansı belirtilmemiştir.

Bursa: yeni açık veri portalının 49 veri seti incelendi; bu katalogda kullanılabilir otobüs hat/durak seti bulunamadı. BursaKart web sitesi bu bağlantıdan HTTP 403 verdi. Bursa kapsamı henüz eklenmedi.

## 1 Kasım · Samsun

[Resmî SAMULAŞ otobüs sayfası](https://samulas.com.tr/otobusler) ve `api/v1/lines/list_v2` kataloğu 84 kayıt döndürdü. Hat başlığı ve ilk/son durak kimlikleriyle eşleşen harita işaretlerinden 1.560 durak ve 4.165 ilişki alındı. İşaret sırası korunur; doğrulanmış sefer sırası iddiası yok. 14 kesintisiz şekil yayımlanır; 70 çok parçalı şekil mevcut API biçiminde sunulmaz. Kaynak veri lisansı belirtilmemiştir.

Denizli portalı anonim otomatik isteğe `403 browser_check_failed` döndürdü; entegrasyon yapılmadı. Kayseri'nin herkese açık arama ucu boş ve örnek 500 sorgusunda boş liste döndürdü; kullanılabilir veri doğrulanmadı. Bu kaynaklar kapsam sayısına dahil değildir.

## 1 Kasım · Mersin resmî portalı

[Resmî hat sayfasının](https://ulasim.mersin.bel.tr/hatveguzergahlar) anonim `ajax/bilgi.php` servisi kullanılır. `tipi=hatbilgisi, aranan=TUM` 251 hat/yön kaydı döndürdü; `hatdurak` ve `hatguzergah` çağrılarında `hatno=10M-G` gibi kaynak kimliği kullanılır. Alanlar `{"0":"değer"}` sarmalayıcısından okunur; şema değişirse aktarım durur. Geçersiz hat sorgusu kaynakta 0 döndürdü.

Örnek 10M-G katalog adı ÇARŞI–TECE iken durak listesi KARACA İLYAS BAŞLANGIÇ’tan başlıyor; bu tutarsızlık gizlenmez ve adlar tahminle düzeltilmez. Durak/geometri yanıtları hat kimliğini tekrar etmez; ilişki sorgulanan katalog kodu/yönüne dayanır. Durak listesinin kaynak sırası korunur, sefer dosyasıyla doğrulanmış sıra iddiası yoktur. Canlı araç/varış henüz bağlı değildir. Kaynak veri için yeniden kullanım lisansı belirtilmemiştir.

## 1 Kasım · Trabzon

[Resmî AKUS portalı](https://ulasim.trabzon.bel.tr/) 121 otobüs hattı yayımlıyor. `Web/GetHatGeoJson` ve `Web/GetHatDurakGeoJson` kaynaklarında hat/güzergâh kimliği ve G/D, 1/2 yön alanları birlikte doğrulandı. 242 güzergâh, 4.914 durak, 13.104 sıralı ilişki alındı; her güzergâhta geometri var. Koordinatlar kaynakta EPSG:3857; enlem/boylam dönüşümünden sonra Türkiye sınırları kontrol edilir. Kaynak veri için yeniden kullanım lisansı belirtilmemiştir; canlı veri henüz eklenmedi.

## 1 Kasım · Diyarbakır

[Belediyenin canlı ulaşım sayfası](https://www.diyarbakir.bel.tr/ulasim/canli) 115 hat ve 1.060 genel durak kaydını başlangıç JSON'unda yayımlıyor. Anonim `/api/transport/asis/line-directions` kaynağı hat kodu/iç numarası, Gidiş/Dönüş, durak kimliği ve sıra veriyor. `route-coordinate` geometrisi G/D yönüne göre ayrıca eşleştirilir. Ham kodların sonundaki boşluklar temizlenir; iç boşluklar ve diğer karakterler korunur. Kaynağın açık geometri-yok mesajı haricindeki başarısız yanıtlar güncellemeyi durdurur.

Balıkesir Kart portalı bu bağlantıdan 403 döndürdü. Şanlıurfa portalının oturum açma kullanan arayüzü incelendi, kullanılabilir anonim veri doğrulanmadı. Eskişehir resmî portalının rotalar ucu başarısız sonuç, duraklar ucu boş liste döndürdü. Bu şehirler henüz kapsama eklenmedi.

## 1 Kasım · Mevcut illerde canlı destek

İl sayısı 28 kaldı. Diyarbakır resmî `live-data` kaynağından hat araçları, Trabzon `DuragaYaklasanAraclar` kaynağından durak varışları eklendi. Diyarbakır iç hat kimliği/kodu ve yön, Trabzon iç durak/QR kodu ile hat-güzergâh ilişkileri doğrulanır. Kaynakların vermediği GPS zamanı veya konumu üretilmez. Trabzon `KonumGetir` hat araç servisi bu kontrolde hata verdi; araç listesi henüz desteklenmez.

157 test geçti. Dış kontrolde Diyarbakır A1 hattında 10 gerçek araç, Trabzon 3528 iç durak kimliğinde dolu bir varış yanıtı görüldü. Tekrar sorgular önbellekten geldi; yanlış kimliklerde 404, desteklenmeyen karşı uçlarda 501 doğrulandı. Araç sayısı anlık gözlemdir.

## Trabzon araç kaynağı düzeltmesi · 1 Kasım

Önceki form isteği hatası JSON POST ile aşıldı; `Web/KonumGetir` genel araç yanıtı verir. Normalleştirilen ortak alanlar tüm güzergâhlar için 15 saniye paylaşılır, sonuç tam hat/güzergâh kimliğine süzülür. Canlı yanıtta CRS etiketi yoktur; hem derece hem metre değerleri gözlendi, Türkiye için ayrık aralıklarla yorumlanır. Bu çıkarım meta uyarısında açıkça belirtilir. GPS zamanı/güncellik ve aynı zamanlı çelişki denetimi eklendi. Personel alanları taşınmaz.

163 test ve dolu dış araç/varış yanıtları doğrulandı. Diyarbakır `station-routes` yalnız geçen hatları verir; ETA kaynağı olarak kullanılmaz. Kapsam 28 il kaldı.

## Ankara hat araçları · mevcut desteği tamamlama

EGO Cep’te `FNC=Otobus&HAT=263` çağrısı DURAK parametresi olmadan gerçek araç döndürdü. Hat kimliği/kodu doğrulanır; tarife mesajı araç sayılmaz. Kaynağın durak seçilmeden ürettiği saniye alanı araç uç noktasında ETA olarak sunulmaz. Araç ve varış GPS zamanlarına yaş/eski konum işareti eklendi. Hız/pusula açısı ayrı; yon=3/4 değerlerinin ortak karşılığı tahmin edilmez.

171 test ve dış kontroller geçti: 263 hattında iki gerçek araç, cache ve eski servisler doğrulandı. Örnek durak varışı son kontrolde boştu; bu destek yokluğu anlamına gelmez. İl sayısı 28 kaldı. Statik Ankara koordinat/geometri eksikleri sürüyor.

## 1 Kasım · Kentkart canlı araç tamamlama

Kocaeli 004, Gaziantep 028, Sivas 005 ve Edirne 013 bölgeleri anonim pathInfo kaynağıyla doğrulandı. Örnek hatlarda sırasıyla 2, 8, 6 ve 1 araç gözlendi; bunlar anlık örneklerdir, tüm hatların kapsamını kanıtlamaz. Yerel hat kimliği + kaynak yönü tam eşleştirilir. GPS ölçüm zamanı doğrulanmadığı için güncellik iddiası kurulmaz. Canlı lisansı belirtilmemiştir; statik derleme CC0 kapsamı ayrı tutulur. 179 test geçti. Antalya kimlik uyuşmazlığı nedeniyle etkinleştirilmedi; il sayısı 28 kaldı.
