# İl kapsamı

31 Ekim 2026 · **22 il**. Aşağıdaki sayılar içe alınan kaynak dosyalarından okunmuştur. Hat/güzergâh kaydı, aktif sefer sayısı değildir; bir ilin listede olması tam şehir kapsamı anlamına gelmez.

| İl | Hat / güzergâh kaydı | Sıralı durağı olan hat | Durak | Canlı araç / varış | Kaynak |
|---|---:|---:|---:|---|---|
| İzmir | 421 | 421 | 11739 | Var / Var | Resmi açık veri |
| İstanbul | 9274 | 2877 | 14040 | Var / Yok | Resmi açık veri |
| Konya | 162 | 154 | 4117 | Yok / Yok | Resmi açık veri |
| Kahramanmaraş | Arama | Uzak API | Uzak API | Var / Var | Topluluk köprüsü |
| Antalya | 162 | 162 | 4503 | Yok / Yok | Topluluk GTFS |
| Kocaeli | 409 | 405 | 8597 | Yok / Yok | Topluluk GTFS |
| Adana | 291 | 132 | 3618 | Yok / Yok | Topluluk GTFS |
| Gaziantep | 162 | 162 | 3110 | Yok / Yok | Topluluk GTFS |
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
| Sivas | 111 | 111 | 624 | Yok / Yok | Katalog + Kentkart servisi |
| Edirne | 23 | 23 | 392 | Yok / Yok | Katalog + Kentkart servisi |

## Sınırlar

- İstanbul'da görünen hat kodu ile GTFS varyant kimliği farklıdır. Binlerce varyant, binlerce ayrı aktif hat anlamına gelmez. Kaynak GTFS geometrisi yayımlamaz.
- Sıralı durak kaydı bulunmayan hatlarda `directions` boş olabilir. Kaynakta geometri yoksa çizgi uydurulmaz; boş liste ve uyarı döner.
- Konya kaynağı Kasım 2025 dosyasıdır; takvimin ileri tarihe uzaması güncellik kanıtı değildir.
- Kahramanmaraş tam hat kataloğu sunmaz; arama sonuçları sınırlıdır. Kaynak veri lisansı belirtilmemiştir.
- [Egezenn/kk-gtfs](https://github.com/Egezenn/kk-gtfs) topluluk derlemesinde takvim ve zamanlar türetilmiş olabilir. Derleme CC0, temel veri hakları Kentkart/belediyededir. Bu illerde canlı araç/varış desteği yoktur.

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
