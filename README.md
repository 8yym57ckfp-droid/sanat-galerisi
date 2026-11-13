# Perihan Baktaş · Sanat Atölyesi

Python 3.10+ ve standart kütüphane ile çalışan sanat galerisi sitesi. Eser kataloğu, yönetim paneli, beğeniler ve arşiv içerir.

## Windows’ta çalıştırma

1. Python 3.10 veya üstünü kurun.
2. `start.bat` dosyasına çift tıklayın; açılan pencereyi açık bırakın.
3. `http://127.0.0.1:8000` adresini açın.
4. İlk kullanımda `/atolye-yonetim-8f31/setup` adresinden en az 10 karakterli yönetici parolası oluşturun.

PowerShell alternatifi: bu klasörde `python server.py` komutunu çalıştırın.

## Yönetim paneli

- **Tablolar:** eser ekleme/düzenleme, benzersiz kod, ölçü, kategori, açıklama, fiyat, indirim, görsel ve WhatsApp bağlantısı. İleri tarihli yayınlar seçilen güne kadar taslakta kalır.
- **Katalog:** ana sayfa bölümlerini seçme, beğeni sayılarını görme, kod kopyalama, satıldı işaretleme ve arşive alma.
- **Site ayarları:** atölye adı, ayrı satırlarda kategori ekleme/silme ve sosyal medya bağlantıları.

## Dosyalar ve yayınlama

- `data/site.sqlite3`: eserler, site ayarları, yönetici hesabı ve beğeniler.
- `uploads/works/`: tablo görselleri.
- `legacy-homepage.html`: özgün ana sayfa tasarımının korunmuş kopyası.
- `index.html`: sunucuyu başlatma yönergesi.

Eski yerel sipariş kayıtları varsa, bu sürüm onları silmez; sipariş özellikleri artık sitede sunulmaz.

GitHub Pages Python sunucusu ve SQLite çalıştırmadığından siteyi orada tek başına çalıştırmaz. Python destekli barındırma gerekir. Varsayılan `127.0.0.1:8000` adresi yalnızca bu bilgisayardan erişilir.

