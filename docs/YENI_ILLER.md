# Yeni il kapsamı · 31 Ekim 2026

Toplam 19 il. Bu turda 11 il eklendi. Kaynak [Egezenn/kk-gtfs](https://github.com/Egezenn/kk-gtfs) topluluk derlemesi; belediyenin resmi feed’i değildir. Derleme CC0, temel veri hakları Kentkart/belediyededir. Yalnız otobüsler; canlı araç/varış desteği yok. Kaynak takvimi ve zamanları türetilmiş olabilir.

| İl | Katalogdaki otobüs hattı | Sıralı durağı bulunan hat | Otobüs durağı |
|---|---:|---:|---:|
| Erzurum | 55 | 51 | 724 |
| Mardin | 92 | 87 | 765 |
| Muğla | 383 | 321 | 3436 |
| Ordu | 56 | 44 | 886 |
| Çanakkale | 32 | 11 | 324 |
| Düzce | 57 | 50 | 1240 |
| Burdur | 18 | 18 | 346 |
| Niğde | 10 | 1 | 24 |
| Kırklareli | 8 | 5 | 127 |
| Osmaniye | 17 | 15 | 221 |
| Tokat | 23 | 2 | 63 |

Katalog sayısı aktif sefer veya tam şehir kapsamı değildir. Sıralı durak kaydı bulunmayan hatlarda `directions` boş olabilir. Kaynakta geometri yoksa çizgi uydurulmaz; boş liste ve uyarı döner.

Eklenmeyenler: Sivas/Edirne — trips.txt eksik. Kastamonu — aynı hat/yön/nokta sırasında çakışan geometri kayıtları; içe aktarma reddedildi. Yozgat dosyası çok küçük/boş görünüyor; doğrulanmış destek sayılmaz. İlçeler il kapsamı gibi sunulmadı.

Bursa’nın güncel resmi portalı acikyesil.bursa.bel.tr; GTFS araması 31 Ekim’de sıfır veri seti döndürdü. Bu, tüm Bursa kaynaklarında veri olmadığını kanıtlamaz; otobüs hattı/durak veri setleri ayrıca araştırılacak.

Doğrulama: 70 test geçti; 11 yeni ilde hat listesi, durak sırası, geometri ve durak detayı için toplam 44 dış sorgu 200 döndürdü. Bu örnekler bütün hatların eksiksiz veya bugün çalışır olduğunu kanıtlamaz.
