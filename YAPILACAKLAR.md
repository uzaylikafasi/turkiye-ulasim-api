# Yapılacaklar

Ortak çalışma listesi · son güncelleme: 31 Ekim 2026.

**Canlı API:** https://mithrixa.com/turkiye-ulasim-api · [Belgeler](https://mithrixa.com/turkiye-ulasim-api/docs). Günlük güncelleme ve sürekli servis kuruldu.

**Öncelik: yeni şehirler ve otobüs kapsamı.** Altyapı işleri şehir eklemeyi sürekli ertelememeli. Metro, tramvay, vapur ve şehirlerarası ulaşım sonraki aşama. Yeni kaynak bulunması ile çalışır şehir desteği farklı aşamalardır.

## Bir işi devralmak

1. Aşağıdaki iş kimliğini seç; bu dosyadaki maddenin yanına adını ve `devam ediyor` yazıp dalında paylaş. Böylece aynı iş iki kez yapılmaz. Adı yazılmamış işler alınabilir.
2. `git pull` sonrası `git switch -c feat/is-kimligi` ile dal aç. PR başlığında iş kimliğini kullan; değişikliği, doğrulamayı ve kalan sınırları yaz.
3. Testleri çalıştır. Çalışan kaynak örneğini ve lisans/kaynak bağlantısını ekle; erişim anahtarlarını, `.env`, ham trafik veya kullanıcı verisini gönderme.
4. PR birleşince kutuyu işaretle, gerekiyorsa README ve [şehir tablosunu](docs/BUYUKSEHIRLER.md) güncelle. Bekleyen işin hangi dosyadan ve komuttan devam edeceğini yaz.

Kod: `turkiye_ulasim/`; bağlayıcılar: `turkiye_ulasim/sources/`; indirme: `tools/gtfs_guncelle.py`; testler: `tests/`.

```sh
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
.venv/bin/python -m tools.gtfs_guncelle izmir konya
# İstanbul kurulumu daha büyük dosya indirir:
.venv/bin/python -m tools.gtfs_guncelle istanbul
# Mevcut Maraş API'si Pi'de 8000 kullandığı için geliştirme portu:
.venv/bin/uvicorn turkiye_ulasim.main:app --port 8010 --workers 1
```

## Tamamlananlar

- [x] **TEMEL-01:** Ortak `{data, meta}` yanıtı; kaynak, lisans ve uyarılar.
- [x] **IZM-01:** İzmir otobüs hat/durak/güzergâh + canlı araç ve varış.
- [x] **IST-01:** İstanbul resmi GTFS/CSV içe aktarma + varyanta göre SOAP araç konumu.
- [x] **KON-01:** Konya otobüs GTFS'i; tramvaylar kapsam dışında.
- [x] **VERI-01:** Atomik veri güncelleme; bozuk ithalatta önceki dosyayı koruma; arama sayfalama.
- [x] **PAYLASIM-01:** Bu ortak yapılacaklar listesi ve devralma adımları.

## Önce yapılacaklar

- [x] **KMR-01 — Kahramanmaraş ortak bağlayıcı**. Mevcut Kahramankart API'si ortak şemaya bağlandı: arama, detay, sıra, geometri, yakın durak, araç ve varış. Kaynak topluluk olarak etiketli; id:yön kimliği, alınma zamanı, kota ve önbellek var. 48 test ve dört şehirde 14 gerçek veri sorgusu geçti. Tam envanter ve eksik varış yönü KMR-02/03'te açık.
- [ ] **KMR-02 — Tam hat envanteri:** Arama sonuçları sınırlı. Kaynak bütün şehri veriyor gibi davranmadan tam hat/yön listesini elde et; güncelleme tarihi ve kapsama ölçütü ekle.
- [ ] **KMR-03 — Varıştan hatta bağlantı:** Varış yanıtında kaynak hat kimliği var, yön her kayıtta yok. Yönü tahmin etmeden ortak hat/yön kimliğine güvenilir eşleme ekle.
- [ ] **CI-01 — GitHub Actions:** [Hazır şablon](docs/templates/github-tests.yml) Python 3.11/3.12 için çevrimdışı pytest çalıştırır. **Henüz etkin değil:** şablonun workflow olarak yüklenmesi ve ilk başarılı koşumun doğrulanması gerekiyor. Depoya yazma yetkisi olan katkıcılar GitHub web arayüzünden şablonu `.github/workflows/tests.yml` olarak ekleyebilir; ilk başarılı Actions koşumundan sonra kutuyu işaretle. API kodu ve liste bu eksikten bağımsız yayımlandı.
- [x] **API-01 — Yetenek sözleşmesi:** `line_catalog`, `gtfs`, canlı araç/varış ve `source_kind` belge ve testlerle sabitlendi. Tam liste olmayan kaynak boş sorguda 422; destek olmayan uç 501; kapalı/kurulmamış kaynak 503; kaynak hatası 502.

## Yeni büyükşehirler: sırayla araştır ve bağla

Her şehirde bitiş ölçütü: erişilebilir kaynak + kullanım/lisans bilgisi + gerçek dosya/yanıt + ortak şema bağlayıcısı + çevrimdışı test + README güncellemesi. Erişim veya lisans doğrulanmadıysa durumu açık yaz; destek var diye işaretleme.

- [ ] **ANK-01 — Ankara:** EGO / belediye kaynaklarından indirilebilir hat-durak veya GTFS ve kullanım koşullarını doğrula; sonra otobüsleri içe aktar.
- [ ] **BUR-01 — Bursa:** Resmi portal bağlantısı/sertifikası, BURULAŞ veri kaynağı ve yeniden kullanım bilgilerini doğrula.
- [ ] **ANT-01 — Antalya:** Resmi otobüs veri kaynağı, GTFS ve canlı veri seçeneklerini araştır.
- [ ] **KOC-01 — Kocaeli:** Açık veri portalının 502 sorunu sonrası GTFS dosyası ve lisansını tekrar doğrula; kaynağı erişilebilir olmadan tamamlandı sayma.
- [ ] **GAZ-01 — Gaziantep:** Resmi GTFS portalı ve indirme bağlantısını tekrar kontrol et; önceki kontrolde erişim/sertifika sorunu vardı.
- [ ] **KAY-01 — Kayseri:** Belediyenin GTFS/Google Maps duyurusu var; dış geliştiriciye açık dosya adresi ve lisansı ayrıca bulunacak. Duyuru, indirilebilir açık feed kanıtı değildir.
- [ ] **SAK-01 — Sakarya:** Belediye kaynakları ve canlı toplu taşıma erişimini incele; haritada görünmesi açık API sayılmaz.
- [ ] **DIGER-01 — Sonraki büyükşehir turu:** Adana, Aydın, Balıkesir, Denizli, Diyarbakır, Erzurum, Eskişehir, Hatay, Malatya, Manisa, Mardin, Mersin, Muğla, Ordu, Samsun, Şanlıurfa, Tekirdağ, Trabzon, Van için kaynak envanteri çıkar; her çalışır bağlayıcıyı ayrı iş/PR yap.

## Veri doğruluğu

- [ ] **IST-02:** İstanbul'da durak sırası tutarsız 3 hat/yönü incele; kaynağı doğrulamadan sıralama uydurma.
- [ ] **IST-03:** Katalogdaki 9.274 varyantın yalnız 2.877'sinde bu içe aktarmada durak sırası var. Seferi olmayan varyantları istemciye anlaşılır biçimde göster; toplamı aktif hat sayısı diye sunma.
- [ ] **IZM-02:** Canlı `Yon` ile GTFS yön eşlemesini gerçek örneklerle doğrula; mükerrer araç konumu seçiminin sınırlarını ölç.
- [ ] **KON-02:** Konya'nın Kasım 2025 dosyasının yenisini izle; 2030'a uzanan takvimi güncellik kanıtı sayma.

## Yayın ve bakım

- [x] **YAYIN-01:** 30 Ekim: ayrı 8010 portunda systemd servisi; https://mithrixa.com/turkiye-ulasim-api üzerinden sınırlı GET köprüsüyle yayın. Maraş servisi 8000’de korundu. [İşletim ve geri alma](deployment/README.md).
- [x] **BAKIM-01:** Günlük 04:10 (+0–5 dk) systemd timer, tek yazar kilidi, atomik ithalat, şehir bazında hata raporu ve yeniden başlatmadan SQLite yenileme eklendi. Kaynak eski veri yayımlarsa güncelleme bunu kendiliğinden güncel hale getiremez.
- [ ] **KOTA-01:** İETT tek worker'da 90 istek/saat bütçesi kullanır. Birden fazla süreç/sunucu öncesinde paylaşılan kota ve önbellek kur; aynı IP'deki diğer tüketicileri hesaba kat.
- [x] **IZLEME-01:** 30 Ekim: `/healthz`, `/readyz`, `/v1/status` eklendi. Yerel GTFS okunabilirliği, kaydedilmiş içe aktarma/takvim bilgisi ve süreçte gözlenen canlı başarı/hata durumu sunulur. Ağ sorgusu ve gizli bilgi yok; sürekli izleme kurulumu YAYIN/BAKIM işlerinde açık.
- [ ] **BELGE-01:** Çalışır küçük Python/JavaScript istemci örnekleri; boş veri ve desteklenmeyen yetenekleri nasıl ele alacağını göster.

## Sonraya bırakılanlar

- [ ] Metro, tramvay, İZBAN/banliyö, vapur ve şehirlerarası veri.
- [ ] Yolculuk planlama ve ortak tarife modeli; önce veri kapsamı ve kaynak kalitesi.

## Mevcut doğrulama

0.2.0 (`57f7cf9`): 28 test geçti; İzmir, İstanbul ve Konya'da gerçek kaynaklarla 15 örnek uç `200` döndürdü. Bu sonuç her hattın güncel veya çalışır olduğunu kanıtlamaz. Yeni işler tamamlanınca bu bölüme tarih, commit ve test sonucu ekleyin.

0.3.0: Kahramanmaraş topluluk köprüsü eklendi; 48 çevrimdışı test geçti. Dört şehirde 14 gerçek veri sorgusu 200 döndü; Maraş H/1 gidiş 48, dönüş 52 durak; Demokrasi Meydanı varışı dolu. H/1 araç listesi son kontrolde boştu; dolu araç yanıtı önceki kaynak incelemesinde ve test örneğinde doğrulandı. Sürekli ortak API yayını hâlâ açık iş.

30 Ekim: sağlık ve veri durumu uçları eklendi; 52 çevrimdışı test geçti. Kaynaklara otomatik sağlık sorgusu yapılmaz. Sürekli yayın ve otomatik güncelleme henüz kurulmadı.

30 Ekim yayın: 55 test geçti; dış adreste sağlık, veri durumu, dört şehirden veri, belgeler ve OpenAPI dahil 11 ortak API sorgusu 200 döndü. Eski Maraş API ve ana site de 200. İlk otomatik güncelleme üç GTFS şehrinde başarılı; API aynı süreçte yeni dosyaları yükledi.

## 31 Ekim: dört yeni şehir

- [x] **YENI-01:** Antalya (162 hat, 4.503 durak), Kocaeli (409, 8.597), Adana (291, 3.618), Gaziantep (162, 3.110) otobüs GTFS desteği. Egezenn/kk-gtfs topluluk derlemesi; resmi veri olarak etiketlenmez. Canlı araç/varış yok; takvim/zamanlar türetilmiş olabilir. Günlük güncelleyiciye dahil.
- [ ] **YENI-02:** Sonraki şehir: Ankara/Bursa için erişilebilir kaynak; Kentkart topluluk kapsamındaki diğer büyükşehirleri de doğrulayarak ekle.

ANT-01/KOC-01/GAZ-01 maddelerindeki resmi kaynak araştırması ayrı iş olarak açık; topluluk GTFS desteği tamamlandı. Adana için DIGER-01 kapsamında ilk statik destek tamamlandı.

## 31 Ekim · İkinci genişleme turu

- [x] **YENI-03:** Erzurum, Mardin, Muğla, Ordu, Çanakkale, Düzce, Burdur, Niğde, Kırklareli, Osmaniye ve Tokat: gerçek dosyalar içe alındı; topluluk kaynağı ve eksik kapsam açık. [Sayısal kapsam](docs/YENI_ILLER.md).
- [x] **KAYNAK-01:** Sivas/Edirne ZIP’lerinin gerçek hat/durak katalogları alındı; durak sırası ve geometri Kentkart servisinden doğrulanarak tamamlanıyor. Bu aşamada doğrulanmış sefer/takvim bilgisi sunulmaz ve üretilmez.
- [x] **KAYNAK-02:** Kastamonu nokta tekrarları incelendi; 1.429 birebir tekrar güvenle tekilleştirildi, farklı koordinatlar hâlâ reddedilir. İl desteği eklendi.
- [ ] **BUR-02:** Güncel acikyesil.bursa.bel.tr portalında GTFS araması boş; diğer otobüs hat/durak veri setlerini araştır.

Toplam 19 il; günlük güncelleme 18 GTFS kaynağını kapsar. İlçe verileri il kapsamı diye sayılmadı. Öncelik hâlâ yeni iller ve otobüs kapsamı.

Bu tur doğrulama: 70 çevrimdışı test, yeni 11 ilde 44 dış veri sorgusu başarılı. Canlı listede 19 il; tümü yapılandırılmış. Ana site ve eski Maraş API sağlık kontrolü 200.

## GitHub düzeni ve Kastamonu

- [x] **BELGE-02:** README canlı bağlantılar, yetenek tablosu, hızlı deneme ve kurulumla yeniden düzenlendi; teknik ayrıntılar docs/API.md, katkı CONTRIBUTING.md içinde.
- Kastamonu doğrulaması: 1.429 nokta birebir aynı koordinat tekrarı; güvenle tekilleştirildi. Farklı koordinat çakışması hâlâ reddedilir. 27 hat / 23 sıralı hat / 91 durak ile toplam 20 il. Önceki kaynak hata notu bu incelemeyle düzeltildi.

Güncel toplam: 20 il, 19 GTFS kaynağı + Maraş köprüsü. Sivas/Edirne ve diğer yeni il araştırmaları açık.

## Servis üzerinden eksik veri

- [x] **KENT-01:** Sivas/Edirne için Kentkart pathInfo ilişkileri; katı hat/yön eşlemesi, sıralı çağrı, kaynak zamanı ve atomik güncelleme.
- [ ] **KENT-02:** Aynı doğrulama yöntemini diğer eksik şehir/katalog ilişkilerine uygula; her sağlayıcının şeması ayrı doğrulanacak. Canlı konum ve varış için ayrıca gerçek yanıt örneği gerekir.

Genel durum ve iş listesinde kişiye özel açıklamalar kullanılmaz.

Güncel toplam 22 il: Sivas 111 hat / 222 doğrulanmış yön / 624 durak; Edirne 23 / 46 / 392. 82 test ve 14 dış veri sorgusu geçti.

### Sakarya · doğrulanan yeni kaynak
- [x] Resmî SAKUS kataloğu: 160 otobüs/metrobüs kaydı; raylı kayıtlar ayrıldı.
- [x] Örnek hattın iki güzergâhında 39'ar durak ve geometri doğrulandı.
- [x] 160 hat tarandı; 301 kaynak güzergâhı, 206 sıralı güzergâh ve 2.581 durak aktarıldı. Atomik aktarım ve günlük güncelleme bağlı. Gidiş/dönüş tahmini yerine kaynak güzergâh kimliği korundu.
- [x] Ortak API testleri: 92 test geçti; Sakarya ile kapsam 23 il.
- [ ] Kaynakta boş olan 95 güzergâhın duraklarını ve kopuk `74:305` geometrisini tamamlayacak doğrulanmış kaynak araştır.
- [ ] Sakarya canlı araç/varış bağlantısı.

1 Kasım yayın kontrolü: şehir listesi 23 ve tümü kullanılabilir; Sakarya hat/durak/geometri/yakın durak uçları, ana site ve eski Maraş sağlığı doğrulandı. Canlı araç desteklenmediği için 501 döner.

## Ankara · 1 Kasım yayını

- [x] EGO sitesindeki 662 otobüs hattının tamamını ve 10.744 durağı içe aktar.
- [x] 52.228 kaynak sırasını koru; seçili Hat No doğrulaması ve atomik günlük yenileme.
- [x] EGO Cep’te durak varışları; gerçek araç/tarife ayrımı, kaynak zamanı, 20 saniye önbellek ve 30 istek/dakika bütçesi.
- [x] 107 test ve dış API kontrolleri; toplam 24 il.
- [ ] Ankara durak koordinatlarını resmî kaynakla doğrula; yakın durak/geometriyi tamamla.
- [ ] Ankara hat araç listesi ve kaynak yönlerinin anlamını ayrıca doğrula.
- [ ] Bursa: portalda kullanılabilir hat/durak seti bulunamadı, BursaKart HTTP 403; erişilebilir resmî kaynak araştır.

Güncel kapsam: 24 il. Ankara’da statik koordinat yok; canlı varış kaydı içindeki araç konumu durak koordinatı olarak kullanılmaz.

## Samsun · 1 Kasım

- [x] Resmî SAMULAŞ kataloğundaki 84 otobüs kaydını doğrula.
- [x] 1.560 durak, 4.165 harita işareti ilişkisi ve 14 kesintisiz geometriyi aktar; günlük atomik yenilemeyi bağla.
- [x] Aynı görünen durak numarasının farklı konumlarda kullanılması: iç kimlikleri koru ve regresyon testi ekle.
- [x] 115 test; kaynak harita sırası ile sefer sırasının farkını belgelerde açıkla.
- [ ] 70 çok parçalı geometri için ortak API'de parça yapısını koruyan biçim tasarla.
- [ ] Doğrulanmış sefer/durak sırası ve canlı araç/varış kaynağı.

Güncel kapsam 25 il. Denizli portal API'si 403 otomatik erişim reddi veriyor; bağlanmadı. Kayseri hat araması bu kontrolde boş yanıt döndürdü; doğrulanmış veri olmadan eklenmedi.
