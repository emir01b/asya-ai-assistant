# ASYA kurulum ve çalıştırma

Yeni ASYA React/FastAPI uygulamasıdır. Eski `streamlit run main.py`, `setup.py`
ve `quick-start.sh` yolları kaldırıldı. Geçiş dalına frontend ve başlatıcılar ayrı
commitlerle eklenir; aşağıdaki komutlar bu dosyaların mevcut olduğu checkout içindir.

## İlk kullanıcı: otomatik Windows kurulumu

Repo kökündeki **`kurulum.bat`** dosyasını çift tıklayın. Aynı kurucuyu
PowerShell'den `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\kurulum.ps1`
ile de açabilirsiniz. Yalnız bu işlem için execution policy seçilir; kalıcı sistem
politikası değiştirilmez. Yönetici olarak çalıştırmanız gerekmez.

Ön koşullar eksikse kurucu indirme bağlantısını gösterir ve değişiklik yapmadan durur:

- **Python 3.11 x64:** Bu otomatik kurulumun desteklediği sürümdür. Diğer Python
  sürümleri silinmez. [Windows indirmeleri](https://www.python.org/downloads/windows/),
  [3.11.9 x64 geleneksel kurucu](https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe).
  3.11.9 eski bir yama sürümüdür; güncel Python install manager kullanıyorsanız
  onun sunduğu güncel 3.11 yama sürümünü tercih edin. Python Launcher ve PATH
  seçeneklerini etkinleştirin; kurulumdan sonra terminali yeniden açın.
- **Node.js >=22.12.0 ve npm:** [Node.js LTS](https://nodejs.org/en/download).
- **Git:** [Git for Windows](https://git-scm.com/downloads/win).
- İnternet; tam kurulum için yaklaşık **7–10 GB indirme**, önbellekler ve paketlerin
  açılmış halleri için **en az 25 GB boş alan** önerilir. Boyutlar tahminidir;
  CPU/NVIDIA seçimi ve bağımlılık sürümleriyle değişir. Whisper da bu tahmine dahildir.

Kurucu NVIDIA kartı/sürücüsü bulunursa adını gösterir, ardından hangi donanımı
kullandığınızı sorar:

| Seçim | Kurulan Torch paketi | Çalışma şekli |
| --- | --- | --- |
| NVIDIA RTX 20/30/40/50 ve uyumlu yeni kartlar | 2.10.0, CUDA 12.8 | GPU |
| Eski NVIDIA GTX 10/16 vb. | 2.10.0, CUDA 12.6 | Uyumluluk testi geçen kartlarda GPU |
| AMD / Intel / ekran kartı yok | 2.10.0, CPU | CPU; daha yavaş |

Kart ailesi tek başına garanti değildir. Kurucu CUDA seçilince gerçek GPU hesaplaması
yapar; uyumsuz kart veya sürücüde hata verir. CPU seçeneğiyle yeniden çalıştırabilirsiniz.
Bu Windows kurucusunda AMD/Intel GPU hızlandırması sunulmaz. NVIDIA sürücüsü sistemde
hazır olmalıdır: [resmî sürücü indirme](https://www.nvidia.com/Download/index.aspx).
CUDA Toolkit veya ekran kartı sürücüsü kurulmaz; Torch'un resmî CPU/CUDA paketleri
seçilen depodan alınır. LM Studio'nun iç paketleri kopyalanmaz.

Kurucu sırasıyla:

1. Python/Node/Git'i ve ASYA portlarının boş olduğunu kontrol eder. Çalışan ASYA'yı
   kendi terminalinde Ctrl+C ile durdurun.
2. `.venv` ve `.venv-stt` oluşturur. Önceden varsa yedekleyerek yeniden oluşturma,
   mevcut Python 3.11 ortamında paketleri güncelleme veya iptal seçeneklerini sorar.
   Yedekler `.venv.backup-TARİH-...` ve `.venv-stt.backup-TARİH-...` adlarıyla kalır.
   Junction/sembolik bağlantı olan ortamları değiştirmez.
3. Chatterbox'ın `5de7a54aa4e5e2baadb0182dde554908b48b85c2` kaynak sürümünü
   resmî GitHub deposundan alır, `patches/chatterbox-runtime.patch` ile Torch ve
   torchaudio gereksinimini 2.10.0'a eşler. Farklı mevcut kaynak klasörünü ezmez.
4. Seçilen Torch/torchaudio/torchvision paketlerini, kök `requirements.txt` içeriğini
   ve ayrı ortamda `apps/backend/requirements-stt.txt` bağımlılıklarını yükler.
   `pip check`, Chatterbox V3 importu ve CPU/GPU kontrollerini çalıştırır.
5. Chatterbox'ın yalnızca kullanılan altı model dosyasını Hugging Face önbelleğine,
   Whisper large-v3-turbo modelini `data/models/stt` altına indirir. Kısa Türkçe ses
   üretip `data/setup-test.wav` dosyasına kaydeder ve bu sesi Whisper ile yazıya çevirir.
   CPU'da test ve ilk model yükleme uzun sürebilir. Test hatasında başarı bildirmez.
6. Frontend için `npm ci` ve `npm run build` çalıştırır. İlk kurulumsa cihaz ayarlarını
   seçime göre kaydeder; mevcut kayıtlı uygulama ayarlarını korur.

Kurulum sonrası `scripts/start-app.ps1` ile başlatın. Sohbet için ayrıca
[LM Studio](https://lmstudio.ai/download) API sunucusunu açıp ASYA Ayarlar ekranından
model seçin. LM Studio ve sohbet modeli bu kurucu tarafından kurulmaz.

İleri kullanım:

```powershell
# Yalnız ön koşulları kontrol et; paket, ortam veya ayar değiştirmez:
.\kurulum.ps1 -CheckOnly
# Soruları yanıtlayarak CPU kur; model indirmesini sonraya bırak:
.\kurulum.ps1 -Device CPU -SkipModels
# Python özel konumdaysa:
.\kurulum.ps1 -PythonPath 'D:\Python311\python.exe'
```

`-SkipModels` seçeneğinde ses testleri atlanır; model dosyaları henüz hazır olmadığı
için ses üretimi garanti edilmez. Modelleri almak ve test etmek için kurucuyu tekrar
çalıştırın. Mevcut ortamı güncelleme seçeneği paketleri değiştirir; korumak istediğiniz
çalışan ortamda yedekleme seçeneğini kullanın. Yedekten dönüşte yeni ortamı başka ada
taşıyın, yedeği tam eski adına geri taşıyın; sanal ortamlar farklı yolda çalıştırılmaz.

Kök `requirements.txt` artık ana ses ortamını da kapsar, fakat hazırlanmış/patch
uygulanmış `chatterbox/` kaynak klasörü ve doğru Torch seçimi gerektirir. Temiz kurulumda
önce kurucuyu kullanın. STT, modeller ve frontend tek başına pip ile kurulmuş olmaz.
Tam bir transitif bağımlılık kilidi değildir; tüm donanımlarda canlı temiz kurulum
henüz doğrulanmadı. Kurucu tamamlandığını ancak seçilen kontroller geçince söyler.

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

Yeni bilgisayarda yukarıdaki `kurulum.bat` yolunu kullanın. Hazır çalışan bir ortamda
yalnız API paketlerini güncellemek için `apps/backend/requirements.txt` kullanılır;
kök dosya tüm ana ses ortamını kapsar. Önceden doğrulanan ortam Torch 2.10.0+cu128
kullanır; kurucu CPU ve CUDA 12.6 seçeneklerini de sunar.

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
