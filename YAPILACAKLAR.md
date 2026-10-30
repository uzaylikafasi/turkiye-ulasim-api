# Yapılacaklar

Ortak çalışma listesi · son güncelleme: 30 Ekim 2026.

**Canlı API:** https://mithrixa.com/turkiye-ulasim-api · [Belgeler](https://mithrixa.com/turkiye-ulasim-api/docs). Günlük güncelleme ve sürekli servis kuruldu.

**Öncelik: otobüsler, önce büyükşehirler.** Metro, tramvay, vapur ve şehirlerarası ulaşım sonraki aşama. Yeni kaynak bulunması ile çalışır şehir desteği farklı aşamalardır.

## Bir işi devralmak

1. Aşağıdaki iş kimliğini seç; bu dosyadaki maddenin yanına adını ve `devam ediyor` yazıp dalında paylaş. Böylece aynı iş iki kez yapılmaz. Adı yazılmamış işler alınabilir; Samet'e otomatik görev atanmadı.
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

- [x] **KMR-01 — Kahramanmaraş ortak bağlayıcı** · Ada tamamladı. Mevcut Kahramankart API'si ortak şemaya bağlandı: arama, detay, sıra, geometri, yakın durak, araç ve varış. Kaynak topluluk olarak etiketli; id:yön kimliği, alınma zamanı, kota ve önbellek var. 48 test ve dört şehirde 14 gerçek veri sorgusu geçti. Tam envanter ve eksik varış yönü KMR-02/03'te açık.
- [ ] **KMR-02 — Tam hat envanteri:** Arama sonuçları sınırlı. Kaynak bütün şehri veriyor gibi davranmadan tam hat/yön listesini elde et; güncelleme tarihi ve kapsama ölçütü ekle.
- [ ] **KMR-03 — Varıştan hatta bağlantı:** Varış yanıtında kaynak hat kimliği var, yön her kayıtta yok. Yönü tahmin etmeden ortak hat/yön kimliğine güvenilir eşleme ekle.
- [ ] **CI-01 — GitHub Actions:** [Hazır şablon](docs/templates/github-tests.yml) Python 3.11/3.12 için çevrimdışı pytest çalıştırır. **Henüz etkin değil:** mevcut OAuth bağlantısı `workflow` yetkisi olmadığı için GitHub yüklemeyi reddetti. Samet veya Ömer GitHub web arayüzünden şablonu `.github/workflows/tests.yml` olarak ekleyebilir; ilk başarılı Actions koşumundan sonra kutuyu işaretle. API kodu ve liste bu eksikten bağımsız yayımlandı.
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
