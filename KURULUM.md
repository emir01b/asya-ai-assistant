# ASYA kurulum ve çalıştırma

Yeni ASYA React/FastAPI uygulamasıdır. Eski `streamlit run main.py`, `setup.py`
ve `quick-start.sh` yolları kaldırıldı. Geçiş dalına frontend ve başlatıcılar ayrı
commitlerle eklenir; aşağıdaki komutlar bu dosyaların mevcut olduğu checkout içindir.

## Mevcut yerel ortamı kullanma

Windows'ta repo kökünden PowerShell ile:

```powershell
.\scripts\link-local-runtime.ps1 -RuntimeRoot ..\voice-lab
.\scripts\check-environment.ps1
Push-Location apps\frontend
npm.cmd ci
npm.cmd run build
Pop-Location
.\scripts\start-app.ps1
```

Bağlantı scripti `.venv`, `.venv-stt`, `data` ve `chatterbox` klasörlerini mevcut
ortama bağlar. Farklı bir hedefin üzerine yazmaz. **Bağlanan `voice-lab` klasörünü
silmeyin veya yeniden adlandırmayın.** Uygulama kaynaklarını ASYA reposunda düzenleyin.
Frontend bağımlılıkları ASYA içinde ayrıca kurulur.

Önceden çalışan sunucuyu kendi terminalinde Ctrl+C ile durdurun. Aynı veri alanıyla
iki backend çalıştırmayın. Uygulamayı http://127.0.0.1:8000 adresinden açın.

## Yeni bilgisayarda kurulum kapsamı

Python 3.11, Node.js >=22.12.0 ve uyumlu NVIDIA/CUDA/Torch ortamı gerekir.
Chatterbox ve ağırlıkları ana `.venv` ortamı için ayrıca hazırlanmalıdır.
Bu repo henüz baştan sona doğrulanmış bir temiz AI kurulum reçetesi sunmaz.

Kök `requirements.txt`, `apps/backend/requirements.txt` dosyasındaki API
paketlerine yönlendirir; tüm ses modeli bağımlılıklarını kurmaz. CUDA/Torch
ortamını bu dosyayı kullanarak yeniden kurmaya veya topluca yükseltmeye çalışmayın.
Mevcut kurulum Torch 2.10.0+cu128 kullanır.

Whisper bağımlılıkları ayrı tutulur. Ana ortam hazır olduktan sonra:

```powershell
.\scripts\setup-stt.ps1 -DownloadModel
```

Bu işlem `.venv-stt` ortamını hazırlar ve STT modelini indirir; internet ve disk
alanı gerektirir. Offline modda gerekli model dosyaları önceden indirilmiş olmalıdır.

## LM Studio

LM Studio'da Developer bölümünden API sunucusunu başlatın ve bir sohbet modeli
yükleyin. ASYA → Ayarlar içinde çalışan adresi girin, modelleri tarayın ve seçin.
Varsayılan API adresi `http://127.0.0.1:1234/v1` olur; portunuz farklıysa değiştirin.
LM Studio, ASYA'nın yönettiği bir süreç değildir.

## Geliştirme

```powershell
.\scripts\start-dev.ps1
```

Arayüz http://127.0.0.1:5173, API http://127.0.0.1:8000 adresindedir.
Test ve production derlemesi:

```powershell
.\scripts\test.ps1
```

## Yerel ağ ve mikrofon

PowerShell 7 ile, örnek IP yerine sunucu bilgisayarınızın özel IPv4 adresini kullanın:

```powershell
.\scripts\start-lan.ps1 -LanAddress 192.168.1.10
```

LAN adresi `https://192.168.1.10:8000` olur. İstemcide mikrofon için yerel CA
sertifikasına güven verilmelidir. Sertifika indirme adresi
`https://192.168.1.10:8000/api/v1/system/local-ca.crt` olur.
Mac'te Anahtar Zinciri Erişimi'nde ASYA Local CA (eski kurulumlarda Voice AI Studio
Local CA) sertifikasının SSL güvenini ayarlayıp tarayıcıyı yeniden açın.

LAN modunda aynı ağdaki cihazlar kayıtlarınıza erişebilir. Sunucu bilgisayarında
`http://127.0.0.1:8001` kullanılır. İlk güvenlik duvarı kurulumu yönetici onayı isteyebilir.

## Veri ve sorun giderme

- Veriler `data/` altında, Git dışındadır. `VOICE_DATA_DIR` alternatif konum seçer.
- `.env.example` örnektir; `.env` otomatik yüklenmez. Değişkenleri PowerShell ortamına atayın.
- LM bağlantısı yoksa API sunucusu, port ve yüklenmiş modeli kontrol edin.
- GPU belleği yetmezse LLM modelini küçültün veya Ayarlar'dan ses motorunu CPU'ya alın.
- Mikrofon için localhost veya güvenilen HTTPS bağlantısı ve tarayıcı izni gerekir.
- `scripts/diagnostics.ps1` yerel sistem/API tanılamasını gösterir.

Eski ASYA veritabanı yeni şemayla doğrudan değiştirilemez. Konuşma dönüştürücüsü
henüz uygulanmadı; eski verileri koruyun.
