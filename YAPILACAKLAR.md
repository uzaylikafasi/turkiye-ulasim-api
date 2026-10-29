# Yapılacaklar

Ortak çalışma listesi · son güncelleme: 29 Ekim 2026.

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

- [ ] **KMR-01 — Kahramanmaraş ortak bağlayıcı** · Ada, devam ediyor. Çalışan [Kahramankart API'sini](https://github.com/uzaylikafasi/kahramankart-ulasim-api) ortak şemaya bağla: hat arama, detay, sıra, geometri, yakın durak, araç ve varış. Kaynağı topluluk olarak belirt; yön/kimlik ve kaynak zamanını koru. Test ve gerçek kaynak kontrolüyle tamamlanır.
- [ ] **KMR-02 — Tam hat envanteri:** Arama sonuçları sınırlı. Kaynak bütün şehri veriyor gibi davranmadan tam hat/yön listesini elde et; güncelleme tarihi ve kapsama ölçütü ekle.
- [ ] **KMR-03 — Varıştan hatta bağlantı:** Varış yanıtında kaynak hat kimliği var, yön her kayıtta yok. Yönü tahmin etmeden ortak hat/yön kimliğine güvenilir eşleme ekle.
- [ ] **CI-01 — GitHub Actions:** Her PR'da çevrimdışı pytest. Ağdan gerçek kaynak sorguları ayrı ve isteğe bağlı olsun; test için erişim bilgisi gerektirmesin.
- [ ] **API-01 — Yetenek sözleşmesi:** Şehir başına tam liste / arama, GTFS, canlı araç, varış ve kaynak türünü belge ve testlerle sabitle. Veri yokluğu, destek yokluğu ve kaynak hatası ayrımını koru.

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

- [ ] **YAYIN-01:** Ayrı port + systemd/hosting yapılandırması, alan adı/tünel ve kaynak kotasıyla sürekli API yayını. Mevcut Maraş servisine dokunma.
- [ ] **BAKIM-01:** Otomatik veri güncelleme, başarısız indirmede eski veriyi koruma, güncelleme/sağlık raporu. Yeni dosyayı açan süreç yönetimini belirle.
- [ ] **KOTA-01:** İETT tek worker'da 90 istek/saat bütçesi kullanır. Birden fazla süreç/sunucu öncesinde paylaşılan kota ve önbellek kur; aynı IP'deki diğer tüketicileri hesaba kat.
- [ ] **IZLEME-01:** `/healthz` ve şehir başına son başarılı statik güncelleme / kaynak hata durumu; anahtar veya özel veri açığa çıkarma.
- [ ] **BELGE-01:** Çalışır küçük Python/JavaScript istemci örnekleri; boş veri ve desteklenmeyen yetenekleri nasıl ele alacağını göster.

## Sonraya bırakılanlar

- [ ] Metro, tramvay, İZBAN/banliyö, vapur ve şehirlerarası veri.
- [ ] Yolculuk planlama ve ortak tarife modeli; önce veri kapsamı ve kaynak kalitesi.

## Mevcut doğrulama

0.2.0 (`57f7cf9`): 28 test geçti; İzmir, İstanbul ve Konya'da gerçek kaynaklarla 15 örnek uç `200` döndürdü. Bu sonuç her hattın güncel veya çalışır olduğunu kanıtlamaz. Yeni işler tamamlanınca bu bölüme tarih, commit ve test sonucu ekleyin.
