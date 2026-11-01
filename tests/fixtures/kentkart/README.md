# Kentkart örnekleri

`live004.json`: 1 Kasım 2026, Kocaeli bölge 004, hat 10, yön 0 için gerçek anonim pathInfo yanıtı. Kaynak: https://service.kentkart.com/rl1/web/pathInfo?region=004&lang=tr&direction=0&displayRouteCode=10&resultType=010000

Yalnız test için gereken hat/yön kimlikleri, sonuç kodu ve iki aracın kimlik, koordinat, pusula, erişilebilirlik/bisiklet alanları tutuldu. Kaynak ölçüm saati doğrulanmadı. Diğer testlerde yön/kimlik değişiklikleri ve hata durumları sentetiktir. Bu örnek tüm şehir/hat kapsamını kanıtlamaz; canlı kaynağın yeniden kullanım lisansı belirtilmemiştir.

`arrivals-{kocaeli,gaziantep,sivas,edirne}.json`: 1 Kasım 2026 anonim `web/nearest/bus` yanıtları. Bölgeler 004/028/005/013; duraklar 80671/11734/475/20041 ve durak koordinatlarıyla çağrıldı. Kaynak https://service.kentkart.com/rl1/web/nearest/bus . GPS ölçüm zamanı yoktur. Plaka ve ilgisiz alanlar çıkarıldı; routeList’ten bir tarife örneği bırakıldı. Dakika birimi m.kentkart.com durak ekranında timeDiff + BUSSTOPDETAIL_STOPS_MINUTES gösterimiyle doğrulandı. Dört gerçek yanıtta süre, kalan durak ve kimlik eşlemesi test edilir; hata senaryoları sentetiktir.

Antalya/Adana turu (1 Kasım 2026): `vehicles-{antalya,adana}-{0,1}.json` pathInfo KL08/112 iki yön gerçek yanıtları; plaka ve ilgisiz alanlar çıkarıldı. `arrivals-{antalya,adana}.json`: 10017/42077 durakları, lat/lng yerel durak koordinatları; anonim nearest/bus gerçek yanıtları. `no-path-adana.json`: 100 görev hattı açık code=3 Sonuç Bulunamadı. `mismatch-antalya35.json`: görünen 35, path_code 000350, yerel kimlik 00354; doğrulanmış eşleme olmadan uyuşmazlık reddi test edilir. Bu kaynaklar tüm hatların çalıştığını kanıtlamaz.

Muğla/Ordu/Erzurum (1 Kasım 2026): vehicles-{şehir}-{0,1} gerçek pathInfo yanıtları; bölgeler 010/031/038, kodlar 1-9/21/B2. Muğla ve Erzurum yön 1 açık sonuç-yoktur. arrivals-{şehir} durak 70134/40140/10148 gerçek nearest/bus yanıtları. Plakalar ve ilgisiz alanlar çıkarıldı.

vehicles-antalya35-{0,1}: 026/35 pathInfo gerçek yanıtı; iki yönün 62/65 busStopList kaydı doğrulama kanıtı olarak korundu. Yerel 00354 yön durak dizileri, kaynak 000350/000351 dizileriyle 1 Kasım kontrolünde birebir aynıydı. arrivals-antalya35: 11985 durağında routeCode 00354 ve shapeId 000350 gerçek birlikteliği. Eşleme yalnız bu hat/bölgede uygulanır; kimlikler tahminle dönüştürülmez.
