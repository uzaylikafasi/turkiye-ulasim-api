# Büyükşehirlerde otobüs kapsamı

Öncelik otobüsler ve büyükşehirlerdir (29 Ekim 2026). Destek listesine yalnız kaynak bağlantısı, veri lisansı ve gerçek içe aktarması doğrulanan şehirler alınır. Bir mobil uygulamada canlı harita bulunması, yeniden yayımlanabilir açık API bulunduğu anlamına gelmez.

## Bu sürüm

| Şehir | Resmi kaynak | Uygulanan destek |
|---|---|---|
| İzmir | [ESHOT / İzmir açık veri](https://acikveri.bizizmir.com/dataset/toplu-ulasim-gtfs-verileri) | Otobüs GTFS + araç konumu + varış |
| İstanbul | [İETT GTFS](https://data.ibb.gov.tr/dataset/iett-gtfs-verisi), [SOAP](https://api.ibb.gov.tr/iett/FiloDurum/SeferGerceklesme.asmx?WSDL) | Otobüs GTFS + güzergâh varyantına göre araç konumu; varış yok |
| Konya | [GTFS](https://acikveri.konya.bel.tr/dataset/toplu-tasima-gtfs-verileri) | 162 otobüs hattı; dosyadaki üç tramvay hattı kapsam dışında. Kaynak Kasım 2025, canlı kaynak henüz doğrulanmadı. |

## Sıradaki araştırma

| Öncelik | Şehir | 29 Ekim 2026 kontrolü / sonraki adım |
|---|---|---|
| 1 | Ankara | EGO ve belediyenin açık veri kaynaklarında hat/durak, GTFS ve yeniden kullanım koşulları araştırılacak. Açık bağlayıcı henüz yok. |
| 2 | Bursa | Belediye ulaşım sayfaları var; açık veri portalı denemesinde sertifika doğrulanamadı. İndirilebilir veri ve lisans doğrulanacak. |
| 3 | Antalya | Resmi açık veri kaynaklarında otobüs veri seti ve lisansı araştırılacak. |
| 4 | Kocaeli | `veri.kocaeli.bel.tr/dataset/toplu-ulasim-verisi` ve CKAN uçları bu kontrolde HTTP 502 verdi. Ulaşılabilirlik, dosya ve lisans yeniden kontrol edilecek. |
| 5 | Gaziantep | [Resmi GTFS katalog sayfası](https://acikveri.gaziantep.bel.tr/dataset/toplu-ulasim-gtfs-verileri) var; portal bu kontrolde web'den 502, yerel istemciden sertifika hatası verdi. Doğrulanmış dosya indirmesi bekleniyor. |
| 6 | Kayseri, Sakarya, Kahramanmaraş | Resmi açık kaynak / yeniden kullanım koşulları doğrulanacak. Uygulamanın erişim bilgileri ortak depoya taşınmayacak. |

Bu sıra büyüklüğe ve erişilebilirliğe göre çalışma sırasıdır; nüfus sıralaması değildir. Ulaşılamayan kaynaklar ülke çapındaki kapsam iddiasına dahil edilmez. Diğer büyükşehirlerin otobüs kaynakları sonraki turda incelenecek; metro, tramvay ve vapur bu işin ardından gelir.

## Doğrulama · 29 Ekim 2026

28 çevrimdışı test geçti. Kurulu gerçek verilerle üç şehirde toplam 15 örnek uç `200` döndürdü; İstanbul'da canlı araç, İzmir'de canlı araç ve varış yanıtları doluydu. Bu kontroller bütün hatların güncel veya çalışır olduğunu kanıtlamaz.

| Şehir | Farklı hat kodu | Katalogdaki GTFS güzergâh/varyantı | İçe alınan durak |
|---|---|---|---|
| İzmir | 421 | 421 | 11.739 |
| İstanbul | 1.095 | 9.274 | 14.040 |
| Konya | 162 | 162 | 4.117 |

İstanbul'da 7 aday seferin durak sırası tutarsızdı; üç hat/yön için denenen üç aday da tutarsız olduğundan sıra yayımlanmadı. Ayrıca katalogdaki her varyantın sefer kaydı yoktur; toplam güzergâh sayısı kullanılabilir durak sırası veya aktif sefer sayısı değildir. İBB durak dosyasındaki dört bozuk kayıt ayrı resmi servisten doğrulandı.
