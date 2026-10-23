# ASYA

Aktif geliştirme `asya-ai-assistant` reposunun `evolution/voice-studio` dalında
devam eder. React/FastAPI kaynakları eski ASYA koduyla aynı Git geçmişindedir.

## Bu bilgisayarda başlatma

Repo kökünde PowerShell ile:

```powershell
.\scripts\start-app.ps1
```

Tarayıcı adresi: **http://127.0.0.1:8000**. Geliştirme sunucuları için
`scripts/start-dev.ps1` kullanılır; frontend 5173, backend 8000 portundadır.
Başlatıcı terminalinde Ctrl+C ile durdurulur. Zaten çalışan eski sunucu varsa
önce kendi terminalinden durdurun; aynı veritabanını kullanan iki backend açmayın.

## Mevcut yerel ortam

Python/CUDA ortamları taşınabilir olmadığı için mevcut kurulum yerinde tutulur.
Bu bilgisayarda repo kökündeki `.venv`, `.venv-stt`, `data` ve `chatterbox`
Windows junction bağlantılarıyla kardeş `voice-lab` klasörüne bağlıdır.
Modeller, ses profilleri, konuşmalar, ayarlar ve sertifikalar aynı yerde kalır.
Bağlantılar ve içerikleri Git dışında tutulur. **`voice-lab` klasörünü silmeyin
veya yeniden adlandırmayın.** Uygulama kaynaklarını bundan sonra ASYA'da düzenleyin.

Bağlantılar gerektiğinde yeniden oluşturulabilir:

```powershell
.\scripts\link-local-runtime.ps1 -RuntimeRoot ..\voice-lab
```

Script var olan farklı hedeflerin üzerine yazmaz. Frontend bağımlılıkları bu
repo için ayrı kurulur:

```powershell
Push-Location apps\frontend
npm.cmd ci
npm.cmd run build
Pop-Location
```

Gereksinimler: Windows, Python 3.11, Node >=22.12.0 ve mevcut CUDA/Torch kurulumu.
Backend ek paketleri `apps/backend/requirements.txt`, izole Whisper ortamı
`apps/backend/requirements-stt.txt` içindedir. Bunlar tek başına sıfırdan AI
ortamı kurma reçetesi değildir. Başka bir bilgisayarda temiz kurulum bu aktarımda
doğrulanmadı; mevcut Torch/CUDA paketlerini topluca yükseltmeyin.

Chatterbox upstream commit'i `5de7a54aa4e5e2baadb0182dde554908b48b85c2`;
yerel pyproject değişiklikleri `../patches/chatterbox-runtime.patch` dosyasında
saklanır. Kullanılan Torch ve torchaudio 2.10.0'dır; CUDA kurulumu korunur.
Bu kayıt tam bağımlılık kilidi veya otomatik kurulum scripti değildir.

## Kullanım

- Ses kütüphanesinde izinli referans sesle profil oluşturun.
- Studio'da metinden yerel Chatterbox sesi üretin; WAV/MP3 indirin.
- Ayarlar'da çalışan LM Studio API adresini seçip modelleri tarayın.
  Varsayılan adres `http://127.0.0.1:1234/v1`; bu bilgisayardaki kayıtlı ayarlar
  mevcut veritabanından kullanılır.
- Sesli sohbette tarayıcı mikrofonu, Whisper STT, streaming LLM ve cümle bazlı
  TTS kullanılır. Yanıt sırasında mikrofon varsayılan olarak bekler.
- Offline mod mevcut model önbelleklerini kullanır; ilk model indirmesi internet ister.

Backendin GPU kuyruğu TTS ve STT işlerini sıraya alır. LM Studio ayrı çalışır.
Chatterbox çalışan segmentin ortasında durdurulamaz; iptal sonrası sonraki segment
üretilmez. Tauri/Electron masaüstü paketi ve Fish S2 entegrasyonu tamamlanmamıştır.

## Yerel ağ

```powershell
.\scripts\start-lan.ps1 -LanAddress 192.168.8.13
```

Örnek IP yerine bu bilgisayarın yerel IP adresini yazın. LAN modunda aynı ağdaki
cihazlar uygulamanın kayıtlarına erişebilir. HTTPS mikrofon erişimi için istemcide
yerel CA sertifikasına güven verilmelidir; adımlar [HTTPS rehberinde](HTTPS_ACCESS.md).

## Doğrulama

```powershell
.\scripts\check-environment.ps1
.\scripts\test.ps1
```

`test.ps1` backend testlerini, frontend testlerini ve production derlemesini
çalıştırır. Gerçek GPU/model testleri ayrıca `scripts/verify-tts.py`,
`scripts/verify-stt.py` ve `scripts/verify-live-lm.py` ile yürütülür. Tarayıcı
testleri için sunucular açıkken `apps/frontend` içinde `npm.cmd run test:e2e`
çalıştırılır. Model, fiziksel mikrofon ve ağ testleri birim testlerinden ayrıdır.

Eski Streamlit sürümü repo kökünde korunur; kendi bağımlılıklarıyla
`streamlit run main.py` üzerinden çalışır. Eski SQLite şeması yeni Store'a
doğrudan uygun değildir; eski konuşmaları içeri aktaran dönüştürücü henüz yoktur.
Mevcut ASYA konuşmaları paylaşılan `data` sayesinde kullanılmaya devam eder.
