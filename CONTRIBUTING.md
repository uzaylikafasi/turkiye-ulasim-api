# Katkı

Öncelik yeni illerin otobüs kapsamı ve mevcut kaynakların veri kalitesidir. Açık işler [YAPILACAKLAR.md](YAPILACAKLAR.md) dosyasında iş kimlikleriyle tutulur.

## Bir işi devralma

1. Listeden bir iş seçin. Yanına adınızı ve “devam ediyor” yazıp paylaşın; aynı işi iki kişi üstlenmesin.
2. Güncel main'den `feat/is-kimligi` dalı açın.
3. Değişikliği, doğrulamayı ve kalan sınırları PR açıklamasına yazın. Birleşince listeyi güncelleyin.

```sh
.venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest -q
```

Testler kaynak servislere gitmeden çalışmalıdır. Yeni bağlayıcıda gerçek yanıt yapısını temsil eden küçük örnekler kullanın; anahtar, `.env`, ham trafik veya kullanıcı bilgisi eklemeyin.

## Yeni il ekleme

- Önce gerçek dosyayı/yanıtı indirin; yalnız alan adı veya uygulama varlığını destek saymayın.
- `turkiye_ulasim/cities.py` içinde kaynak, veri lisansı, `source_kind` ve yetenekleri belirtin.
- GTFS kaynağını `tools.gtfs_guncelle` ile içe aktarın. Otobüs dışındaki modları kapsam dışında tutun.
- Gerekirse `sources/` içine canlı bağlayıcı ekleyin. Eksik yön, zaman veya konum uydurmayın.
- `deployment/public_proxy.py` yol listesine ili ekleyin; testler public yolların açık olduğunu da doğrular.
- README, kapsam tablosu ve ortak yapılacaklar listesini güncelleyin. Katalog sayısını aktif sefer sayısı diye sunmayın.
- Canlı yayını ancak örnek uçları doğruladıktan sonra tamamlandı sayın. [İşletim belgesini](deployment/README.md) izleyin.

Yeni servisi Pi'ye kurmak veya canlıyı yeniden başlatmak, yalnız belge değişikliğinden farklı bir işlemdir; mevcut çalışma kapsamını ve sistem kayıtlarını kontrol edin.

## Test ve veri doğruluğu

Birebir aynı kaynak kayıtları güvenle tekilleştirilebilir; aynı kimlik/sırada farklı veri varsa sessizce ilk kaydı seçmeyin. Atomik içe aktarma hatasında önceki veritabanı korunmalıdır. `warnings`, kaynak türü ve belirsiz alanlar istemcilere açıkça iletilmelidir.

GitHub Actions şablonu `docs/templates/github-tests.yml` içindedir. Mevcut OAuth bağlantısında workflow yetkisi olmadığı için henüz etkin değildir; etkinleşmeden CI geçiyor rozeti eklemeyin.
