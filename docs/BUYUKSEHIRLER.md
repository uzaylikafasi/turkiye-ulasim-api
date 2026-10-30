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
