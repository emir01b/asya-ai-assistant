# Tauri / Electron'a geçiş

Mevcut teslim, React production build'ini FastAPI'nin aynı localhost origin'i
üzerinden sunar. Masaüstü kabuğuna dönüşüm için uygulama mantığının yeniden
yazılması gerekmez. Bu dosya paketleme planıdır; native uygulama üretilmiş değildir.

1. Kullanıcının seçeceği Tauri 2 veya Electron ile kabuk oluşturun.
2. Python backend'i tek sidecar process olarak başlatın; health başarılı olduktan
   sonra webview açın. Model yüklemesini açılışın ön koşulu yapmayın.
3. Üretimde tahmin edilemeyen localhost portu ve oturum başına erişim anahtarı
   kullanın. Origin listesini, API base adresini ve WebSocket adresini kabuğun
   seçilen origin'ine göre yapılandırın. Şimdiki sabit origin listesi browser
   geliştirme/yerel üretim içindir.
4. DB ve kişisel sesleri OneDrive/workspace yerine işletim sisteminin uygulama
   veri dizinine taşıma seçeneği sunun; önce yedek alın, geçişi doğrulayın.
5. Chatterbox, CUDA, torch ve Whisper paketlerini tek bir devasa executable içine
   körlemesine gömmeyin. GPU runtime/ayrı STT worker kurulumu için sürümlü bir
   kurulum ve tanılama akışı hazırlayın. LM Studio harici servis olarak kalsın.
6. Webview2 mikrofon, AudioWorklet/PCM, Web Audio ve ses çıkışı yeteneklerini gerçek
   Windows cihazında test edin. Tauri izinlerini yalnızca gerekli sidecar ve
   localhost bağlantılarına açın; Electron'da context isolation/sandbox açık olsun.
7. Çıkışta yeni istekleri durdurun, çalışan segmenti bekleyin ve yalnızca uygulamanın
   başlattığı process'leri kapatın. Kod imzalama, installer ve güncelleme testleri ekleyin.

Kabuğun seçimi Python inference performansını tek başına değiştirmez. Dağıtım
boyutu, mikrofon uyumu ve process yönetimi kararın temel ölçütleridir.
