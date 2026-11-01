# Pi yayını ve günlük güncelleme

Canlı temel adres: **https://mithrixa.com/turkiye-ulasim-api**; [belgeler](https://mithrixa.com/turkiye-ulasim-api/docs).

- `turkiye-ulasim.service`: 127.0.0.1:8010, tek worker, 300 MB bellek sınırı; oturum açılmadan çalışması için user linger gerekir.
- `turkiye-ulasim-update.timer`: her gün 04:10 Europe/Istanbul, 0–5 dakika rastgele gecikme. Makine kapalıysa sonraki açılışta kaçırılan iş çalışır.
- `turkiye-ulasim-update.service`: sırayla 21 ZIP kaynağını ve Sakarya SAKUS / Ankara EGO / Samsun SAMULAŞ / Mersin ulaşım kataloglarını günceller; 750 MB, %50 CPU, 60 dakika sınırı. Anahtar veya ücretli model çağrısı yok.

```sh
mkdir -p ~/.config/systemd/user
cp deployment/turkiye-ulasim*.service deployment/turkiye-ulasim*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now turkiye-ulasim.service turkiye-ulasim-update.timer
systemctl --user start turkiye-ulasim-update.service
systemctl --user list-timers turkiye-ulasim-update.timer
journalctl --user -u turkiye-ulasim-update.service -n 30
```

Manuel güncelleme: `.venv/bin/python -m tools.yenile`. `data/.update.lock` başka zamanlayıcıyla aynı anda yazmayı önler. Başarısız şehrin eski veritabanı korunur; diğer şehirler denenir, iş hata koduyla biter. Sonuç `data/update-status.json` ve `/v1/status` içindeki `meta.last_update` alanında bulunur. İş yarıda kesilirse rapor `running` kalabilir; systemd günlükleri ve zaman damgasıyla birlikte değerlendirin.

GTFS dosyaları atomik değişir. Sonraki veri sorgusu yeni dosyanın inode değerini görüp SQLite bağlantısını yeniler. Okuma işlemleri şehir başına kilitlenir; aynı API süreci ve İETT kota/önbellek durumu korunur. Sağlık uçları tek başına dosya yenilemeyi tetiklemez; veri sorgusundan sonra güncel bağlantı durumunu gösterir. Yeni kod yüklerken servisi yeniden başlatmak hâlâ gerekir; İETT kotasının süreçle sınırlı olduğunu hesaba katın.

## Dış erişim

`public_proxy.py`, mevcut Mithrixa web sunucusunun GET işleyicisine `proxy_ulasim(handler)` olarak bağlanır. Sabit 127.0.0.1:8010 hedefine gider; yalnız belirtilen API yollarını açar. Swagger/OpenAPI `/turkiye-ulasim-api` kökünü kullanır. IP başına 60/dakika, toplam 180/dakika, en fazla sekiz eşzamanlı istek ve 4 MB yanıt sınırı vardır. `Retry-After` korunur. Anahtar veya yetkilendirme başlığı aktarılmaz.

Pi'de web sunucusu `~/mithrixa-bio-yeni/sunucu.py`, port 8080'dir. Ortak proxy, mevcut Maraş proxy'sinden önce kontrol edilir. Eski Maraş `transport_proxy.py` sembolik bağlantısı gerçek `~/kahramankart-ulasim-api/deployment/transport_proxy.py` dosyasını göstermelidir; vault içindeki eski yola işaret eden bağlantı 30 Ekim'de düzeltildi. Yeni ortak API, 8000 portundaki Maraş servisini değiştirmez.

Servis ve zamanlayıcı `~/merkez/sistemler.yaml` içinde kayıtlıdır. Bu makineye özgü web entegrasyonu ve merkez kaydı başka makinede otomatik kurulmaz.

## Geri alma

Ortak API'yi kapatmak için `systemctl --user disable --now turkiye-ulasim.service turkiye-ulasim-update.timer` kullanın. Çalışan güncelleme varsa ayrıca `systemctl --user stop turkiye-ulasim-update.service`. Bu işlem Maraş servisini durdurmaz. Web işleyicisindeki `proxy_ulasim` bağlantısı ayrıca kaldırılabilir; sadece ortak API kapalıysa köprü 502 döner.

Sivas/Edirne ZIP’lerinde sefer dosyaları eksiktir; güncelleyici gerçek Kentkart hat/yön ilişkilerini kontrollü, sıralı çağrılarla tamamlar. Dosya hedefiyle aynı dosya sisteminde staging kullanılır; servis başarısız olursa eski dosya korunur. Bu kaynaklar için sefer/takvim üretilmez ve durum uçları storage=catalog gösterir.

Ankara ve Mersin gibi kayıt başına sorgu gerektiren kaynaklar sıralı ve beklemeli yenilenir. Kaynak sayısı arttığı için zaman aşımı 60 dakikadır; hata halinde eski şehir dosyası korunur.
