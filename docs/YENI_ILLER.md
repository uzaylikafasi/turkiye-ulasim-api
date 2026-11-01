# İl kapsamı

1 Kasım 2026 · **28 il**. Aşağıdaki sayılar içe alınan kaynak dosyalarından okunmuştur. Hat/güzergâh kaydı, aktif sefer sayısı değildir; bir ilin listede olması tam şehir kapsamı anlamına gelmez.

| İl | Hat / güzergâh kaydı | Sıralı durağı olan hat | Durak | Canlı araç / varış | Kaynak |
|---|---:|---:|---:|---|---|
| İzmir | 421 | 421 | 11739 | Var / Var | Resmi açık veri |
| İstanbul | 9274 | 2877 | 14040 | Var / Yok | Resmi açık veri |
| Konya | 162 | 154 | 4117 | Yok / Yok | Resmi açık veri |
| Kahramanmaraş | Arama | Uzak API | Uzak API | Var / Var | Topluluk köprüsü |
| Antalya | 162 | 162 | 4503 | Yok / Yok | Topluluk GTFS |
| Kocaeli | 409 | 405 | 8597 | Var / Yok | Topluluk GTFS |
| Adana | 291 | 132 | 3618 | Yok / Yok | Topluluk GTFS |
| Gaziantep | 162 | 162 | 3110 | Var / Yok | Topluluk GTFS |
| Erzurum | 55 | 51 | 724 | Yok / Yok | Topluluk GTFS |
| Mardin | 92 | 87 | 765 | Yok / Yok | Topluluk GTFS |
| Muğla | 383 | 321 | 3436 | Yok / Yok | Topluluk GTFS |
| Ordu | 56 | 44 | 886 | Yok / Yok | Topluluk GTFS |
| Çanakkale | 32 | 11 | 324 | Yok / Yok | Topluluk GTFS |
| Düzce | 57 | 50 | 1240 | Yok / Yok | Topluluk GTFS |
| Burdur | 18 | 18 | 346 | Yok / Yok | Topluluk GTFS |
| Niğde | 10 | 1 | 24 | Yok / Yok | Topluluk GTFS |
| Kırklareli | 8 | 5 | 127 | Yok / Yok | Topluluk GTFS |
| Osmaniye | 17 | 15 | 221 | Yok / Yok | Topluluk GTFS |
| Tokat | 23 | 2 | 63 | Yok / Yok | Topluluk GTFS |
| Kastamonu | 27 | 23 | 91 | Yok / Yok | Topluluk GTFS |
| Sivas | 111 | 111 | 624 | Var / Yok | Katalog + Kentkart servisi |
| Edirne | 23 | 23 | 392 | Var / Yok | Katalog + Kentkart servisi |
| Sakarya | 301 güzergâh (160 hat) | 206 | 2.581 | Yok / Yok | Resmî SAKUS servisi |
| Ankara | 662 | 662 | 10.744 | Var / Var | Resmî EGO sitesi + Cep’te servisi |
| Samsun | 84 | 84 harita işaret listesi | 1.560 | Yok / Yok | Resmî SAMULAŞ kataloğu/haritası |
| Mersin | 251 hat/yön | 245 kaynak listesi | 4.856 | Yok / Yok | Resmî ulaşım portalı |
| Trabzon | 242 güzergâh (121 hat) | 242 | 4.914 | Var / Var | Resmî AKUS GeoJSON |
| Diyarbakır | 115 | 115 (210 yön) | 991 | Var / Yok | Resmî belediye ASIS köprüsü |

## Sınırlar

- İstanbul'da görünen hat kodu ile GTFS varyant kimliği farklıdır. Binlerce varyant, binlerce ayrı aktif hat anlamına gelmez. Kaynak GTFS geometrisi yayımlamaz.
- Sıralı durak kaydı bulunmayan hatlarda `directions` boş olabilir. Kaynakta geometri yoksa çizgi uydurulmaz; boş liste ve uyarı döner.
- Konya kaynağı Kasım 2025 dosyasıdır; takvimin ileri tarihe uzaması güncellik kanıtı değildir.
- Kahramanmaraş tam hat kataloğu sunmaz; arama sonuçları sınırlıdır. Kaynak veri lisansı belirtilmemiştir.
- [Egezenn/kk-gtfs](https://github.com/Egezenn/kk-gtfs) topluluk derlemesinde takvim ve zamanlar türetilmiş olabilir. Derleme CC0, temel veri hakları Kentkart/belediyededir. Kocaeli ve Gaziantep’te ayrıca Kentkart canlı araç desteği vardır; diğer topluluk GTFS illerinde canlı araç, bu grubun tamamında varış desteği henüz yoktur.

## Kastamonu düzeltmesi

Önceki içe aktarma, tekrar eden nokta anahtarları nedeniyle başarısız olmuştu. Kaynağın incelenmesinde 1.429 kaydın **birebir aynı koordinat tekrarı** olduğu doğrulandı. Bunlar tekilleştirilerek Kastamonu eklendi. Aynı nokta sırasında farklı koordinat varsa içe aktarma hâlâ reddedilir ve eski veritabanı korunur.

## Henüz eklenmeyen kaynaklar

- Sivas/Edirne ZIP dosyalarında sefer dosyaları hâlâ eksik; iki il artık katalog ve gerçek Kentkart hat-durak/geometri ilişkileriyle destekleniyor. Sefer/takvim üretilmiyor. Sivas 222, Edirne 46 yön doğrulandı.
- Yozgat: indirilebilir dosya çok küçük/boş görünüyor; doğrulanmış destek sayılmadı.
- İlçeler, il kapsamı gibi sayılmadı.
- Bursa'nın güncel resmi portalında GTFS araması sıfır sonuç verdi. Bu, tüm Bursa kaynaklarında veri olmadığını kanıtlamaz; diğer hat/durak veri setleri araştırılacak.

## Doğrulama

Önceki 11 il turunda 70 test ve 44 dış sorgu geçmişti. Kastamonu ve nokta tekilleştirme testleriyle güncel yerel test sayısı 73. Örnek uç kontrolleri bütün hatların eksiksiz veya bugün çalışır olduğunu kanıtlamaz.

Güncel test sonucu: 82 test geçti. Sivas ve Edirne gerçek servis doğrulamasıyla eklendi; kaynak alınma zamanı API yanıtındaki topology_updated_at alanında bulunur.

Servis tamamlama turu: 82 test ve Sivas/Edirne üzerinde 14 dış veri sorgusu başarılı. İki ilin doğrulanan yön toplamı 268; eksik tarife veya canlı araç verisi varmış gibi sunulmadı.

1 Kasım: Sakarya için 160 hat tarandı, 301 kaynak güzergâhı ve 2.581 durak alındı. 206 güzergâhta sıralı durak var; 95 güzergâhın kaynak durak listesi boş. Kopuk geometri içeren `74:305` için şekil yayımlanmadı. 92 çevrimdışı test geçti.

1 Kasım Ankara turu: 662 hattın tamamında yayımlanan durak sırası doğrulandı; 10.744 farklı durak ve 52.228 hat-durak kaydı. Statik durak koordinatları kaynakta bulunmuyor; null sunulur. Yakın durak/geometri desteklenmez. Durak varışları ayrı EGO Cep’te servisinden alınır, tarife mesajları filtrelenir. 107 çevrimdışı test geçti.

Samsun: 84 otobüs katalog kaydı, 1.560 durak ve 4.165 hat-durak işareti. İşaret sırası sefer dosyasıyla doğrulanmış değildir. Kesintisiz 14 hattın geometrisi yayımlanır; 70 hattın çok parçalı geometrisi mevcut tek çizgi biçimine dönüştürülmez ve 501 döner. Aynı görünen durak numarası iki ayrı konumda bulunduğu için iç durak kimlikleri korunur. 115 test geçti.

Mersin: 251 hat/yön kaydı, 4.856 durak ve 16.847 ilişki. 245 kayıtta kaynak durak listesi, 241 kayıtta geometri var; kalan 6/10 kayıtta ilgili uç 501 döner. Katalog adı ve durak listesi arasında bilinen başlangıç/bitiş farkı vardır. 122 test geçti.

Trabzon: 121 hat, 242 ayrı kaynak güzergâhı, 4.914 durak ve 13.104 sıralı ilişki. 242 güzergâhın tamamında kaynak sırası ve geometri var. Hat/güzergâh kimliği, G/D yön kodu ve 1/2 yön numarası birlikte doğrulanır. EPSG:3857 koordinatları enlem/boylama çevrilir. 130 test geçti.

Diyarbakır: 115 hat, 991 kullanılan durak ve 5.266 sıralı ilişki; 210 yönde durak sırası var. 73 hattın 123 yönünde geometri mevcut; 42 hatta geometri yok. Genel katalogdaki koordinatsız tek durak içe alınan otobüs ilişkilerinde kullanılmadı. 140 test geçti.

Mevcut il tamamlama turu: Diyarbakır canlı araç konumları, Trabzon durak varışları eklendi. İstek başına 15 saniye önbellek ve kaynak başına 30/dakika bütçe. Diyarbakır GPS zamanı/güncellik işareti sunar; Trabzon varış kaynağı GPS konumu/zamanı sunmaz. İl sayısı 28.

Trabzon canlı tamamlama: konum servisi JSON POST ile doğrulandı ve araç listeleri açıldı. İl sayısı 28 kaldı; Trabzon artık hem araç hem varış verisi sunar.

Ankara tamamlama: hat araçları açıldı; mevcut varışlar da GPS yaşı/eski konum alanlarıyla tamamlandı. Statik durak koordinatı ve geometri henüz yok. İl sayısı 28 olarak korundu.

1 Kasım Kentkart canlı tamamlama: Kocaeli, Gaziantep, Sivas ve Edirne araç desteği açıldı. Tam hat/yön kimliği doğrulanır; GPS ölçüm zamanı bilinmediği için güncellik alanları null kalır. Varış desteği yok. 179 çevrimdışı test geçti; kapsam 28 il.
