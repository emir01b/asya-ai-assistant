# ASYA'ya katkıda bulunma

Güncel uygulama `apps/backend` ve `apps/frontend` altındadır. Kurulum kapsamı
ve mevcut yerel ortama bağlantı için [KURULUM.md](KURULUM.md) dosyasını okuyun.

## Çalışma akışı

1. İlgili geliştirme dalından bir çalışma dalı açın.
2. Tek bir davranışı veya sorunu ele alın; bağımlı parçaları birlikte değiştirin.
3. İlgili testleri çalıştırın ve değişikliğin sınırlarını açıklayın.
4. Yalnızca ilgili dosyaları `git add -- <dosyalar>` ile stage edin; diff'i inceleyin.
5. Anlamlı commit mesajıyla kaydedin, dalınızı push edip pull request açın.

`feat:`, `fix:`, `build:` ve `docs:` önekleri kullanılabilir. Commitleri incelemesi
kolay, çalışır bütünler halinde tutun. Geçiş sırasında frontend, backend ve yerel
runtime araçlarının hangi committe bulunduğunu PR açıklamasında belirtin.

## Kontroller

Repo kökünde, hazırlanmış ortamla:

```powershell
.\scripts\test.ps1
```

Backend testleri ayrı çalıştırılabilir:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s apps/backend/tests -v
```

Frontend için `apps/frontend` içinde `npm.cmd test` ve `npm.cmd run build` kullanın.
Tarayıcı testleri çalışan frontend/backend gerektirir: `npm.cmd run test:e2e`.
Gerçek model ve fiziksel mikrofon testlerini birim testi sonuçlarından ayrı raporlayın.

API şeması değiştiğinde:

```powershell
.\.venv\Scripts\python.exe scripts\export-openapi.py
Push-Location apps\frontend
npm.cmd run types:api
npm.cmd run build
Pop-Location
```

## Veri ve bağımlılıklar

- Kişisel sesleri, konuşmaları, veritabanlarını, sertifika anahtarlarını ve `.env`
  dosyalarını commit etmeyin.
- Model ağırlıkları, Python ortamları ve `node_modules` Git dışında tutulur.
- Ana CUDA/Torch ortamını ve izole STT ortamını ayrı tutun.
- Kök `requirements.txt` API bağımlılıklarına yönlendirir; STT paketi listesi
  `apps/backend/requirements-stt.txt` dosyasındadır.
- README görüntülerinde boş veya açıkça tanımlanmış demo verileri kullanın.

## Hata bildirimi

Yeniden üretme adımlarını, beklenen/gerçek davranışı, işletim sistemi ve ilgili
paket sürümlerini yazın. Kişisel içerikleri ve gizli bilgileri loglardan çıkarın.
