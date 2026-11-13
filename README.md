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

## Render’da yayınlama

Bu proje Python sunucusu ve yönetim paneli çalıştırdığı için Render’da **Web Service** olarak yayınlanır; **Static Site** seçilmez.

1. Projenin GitHub’daki `sanat-galerisi` deposunda `server.py`, `static/`, `uploads/` ve HTML dosyalarının bulunduğunu doğrulayın. `main` dalındaki değişiklikler Render’a otomatik dağıtılabilir.
2. Render’da **New → Web Service** seçin, GitHub hesabınızı bağlayın ve `8yym57ckfp-droid/sanat-galerisi` deposunu seçin. Root Directory alanını boş bırakın.
3. Build Command olarak `pip install -r requirements.txt`, Start Command olarak `python server.py` girin.
4. Kalıcı eser ve görsel saklamak için ücretli Web Service’e bir disk bağlayın. Mount Path `/var/data` olsun ve Environment bölümüne `GALLERY_DATA_DIR=/var/data` ekleyin. Disk olmadan Render yeniden başlatma ve dağıtımlarında veriler silinebilir. Bu uygulama Render’ın verdiği `PORT` değerini ve dış bağlantı için `0.0.0.0` adresini otomatik kullanır.
5. İlk dağıtım **Live** olduktan sonra sitenin adresini açın ve `/atolye-yonetim-8f31/setup` sayfasından en az 10 karakterli yönetici parolası belirleyin. Yönetim giriş adresi `/atolye-yonetim-8f31/login` olur.

Yerel `data/site.sqlite3` ve `uploads/works/` GitHub’a dahil edilmez. Bu nedenle Render’daki ilk kurulumda mevcut yerel eser kataloğu otomatik aktarılmaz; yayınlandıktan sonra yönetim panelinden eserleri ve görsellerini yükleyin veya önce katalog verisini ayrıca taşıyın.

GitHub Pages Python sunucusu ve SQLite çalıştırmadığından siteyi orada tek başına çalıştırmaz. Python destekli barındırma gerekir. Varsayılan `127.0.0.1:8000` adresi yalnızca bu bilgisayardan erişilir.

