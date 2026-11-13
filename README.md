# Perihan Baktaş · Sanat Atölyesi

Özel sipariş akışı ve yönetim paneli olan, Python 3.10+ ile çalışan sanat galerisi sitesi. Harici Python paketi gerekmez; SQLite veritabanı standart Python kurulumu içinde gelir.

## Windows'ta çalıştırma

1. Python 3.10 veya üstünü kurun.
2. `start.bat` dosyasına çift tıklayın. Açılan siyah pencere sunucuyu çalıştırır; pencereyi kapatmayın.
3. Tarayıcıda `http://127.0.0.1:8000` adresini açın.
4. İlk kullanımda `http://127.0.0.1:8000/atolye-yonetim-8f31/setup` adresine gidip en az 10 karakterli yönetici parolası belirleyin.

PowerShell alternatifi: bu klasörde `python server.py` komutunu çalıştırın.

## Sipariş süreci

1. Müşteri `Özel Sipariş` sayfasında JPG, PNG veya WEBP görselini (en fazla 8 MB) yükler; adı, soyadı, ülke kodlu telefonu, adresi, şehri, ülkesi, posta kodu ve notunu ekleyip talebini gönderir.
2. Sistem `PB-XXXXXX` biçiminde bir referans kodu üretir. Görsel ve talep Yönetim → Özel Siparişler bölümüne düşer.
3. Yönetici fiyatı ve tahmini hazırlık gününü girip teklifi kaydeder.
4. Müşteri `Sipariş Sorgula` sayfasında kodunu girer; teklifi kabul edebilir, reddedebilir veya kendi fiyat karşı teklifini gönderebilir. Karşı teklifler yönetim panelinde görünür.

## Yönetim paneli

- **Özel siparişler:** referans kodu, görsel, müşteri iletişim/adres bilgileri ve not; fiyat/süre teklifi oluşturma ve müşteri karşı tekliflerini görüntüleme. Kabul, ret ve karşı teklif durumları renkli etiketlerle ayrılır.
- **Tablolar:** eser ekleme ve düzenleme; benzersiz PB kodu, genişlik × yükseklik ölçüsü, kategori, açıklama, fiyat, indirimli fiyat, görsel, beğeni sayısı ve WhatsApp bağlantısı. Yayın tarihi ilerideyse eser o güne kadar taslakta kalır.
- **Katalog:** kategori kutularından seçim, öne çıkanları seçme, beğeni sayısını görme, eser kodunu kopyalama, satıldı işareti koyma ve eserleri arşive alma.
- **Site ayarları:** atölye adı, ayrı satırlarda eklenip silinebilen kategoriler, WhatsApp, Instagram, TikTok ve Telegram bağlantıları.

## Saklama ve yayınlama

- `data/site.sqlite3`: yönetici hesabı, eserler, ayarlar, sipariş kayıtları ve eser beğenileri. Bu dosyayı ve `uploads/` klasörünü düzenli yedekleyin.
- Eser kartlarındaki kalp ve beğeni sayısı tüm kart görünümlerinde eşzamanlı güncellenir; beğeni aynı tarayıcıdan tekrar ziyaret edildiğinde korunur ve tekrar tıklanarak geri alınabilir.
- `uploads/requests/`: müşteri referans görselleri. `uploads/works/`: tablo görselleri.
- `static/siparis-ornek.jfif`: örnek özel sipariş görseli.
- `legacy-homepage.html`: önceki tek dosyalı ana sayfanın özgün kopyasıdır ve sunucu ana sayfada aynen gösterir. Sipariş ve yönetim bağlantıları ana sayfanın üzerinde küçük bir kısayol şeridinde yer alır.
- `index.html`: klasörü doğrudan açtığınızda sunucuyu nasıl başlatacağınızı gösterir. Sipariş sistemi için `start.bat` üzerinden sunucuyu çalıştırın.

Site müşteriler tarafından internetten kullanılacaksa bu Python projesi Python çalıştırabilen bir sunucuya yüklenmelidir. GitHub Pages Python sunucusu ve SQLite çalıştırmadığı için sipariş sistemi orada tek başına çalışmaz. Barındırma adresine göre HTTPS, sunucu yedekleri ve `GALLERY_HOST`/`GALLERY_PORT` ayarlarını yapılandırın. Varsayılan adres yalnızca bu bilgisayardan erişilebilen `127.0.0.1:8000`'dır.
