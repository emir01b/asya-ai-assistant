# 🇹🇷 KURULUM KILAVUZU

ASYA - Akıllı Sesli Yapay Zeka Asistanı için detaylı Türkçe kurulum kılavuzu.

## 📋 Sistem Gereksinimleri

### Minimum Gereksinimler
- **İşletim Sistemi**: macOS 10.15+, Ubuntu 20.04+, Windows 10+
- **Python**: 3.11 veya üstü
- **RAM**: 8GB (AI modeli için)
- **Depolama**: 10GB boş alan
- **İnternet**: Kurulum sırasında gerekli

### Önerilen Sistem
- **RAM**: 16GB
- **SSD**: Hızlı okuma/yazma için
- **Mikrofon**: Kaliteli ses girişi için
- **Hoparlör/Kulaklık**: Ses çıkışı için

## 🚀 Hızlı Kurulum

### 1. Projeyi İndirin

```bash
# Git ile klonlama
git clone https://github.com/[kullaniciadi]/asya-ai-assistant.git
cd asya-ai-assistant

# ZIP dosyası ile
# GitHub'dan "Download ZIP" seçeneğini kullanın
# İndirdiğiniz dosyayı çıkarın ve klasöre girin
```

### 2. Otomatik Kurulum

```bash
# Kurulum scriptini çalıştırın
python3 setup.py
```

Bu script otomatik olarak:
- ✅ Python sanal ortamı oluşturur
- ✅ Gerekli paketleri kurar
- ✅ Sistem bağımlılıklarını kontrol eder
- ✅ Ollama'yı kurar ve yapılandırır
- ✅ AI modelini indirir
- ✅ Başlatma scripti oluşturur

### 3. Uygulamayı Başlatın

```bash
# Otomatik oluşan script ile
./start.sh

# Veya manuel olarak
source venv/bin/activate
streamlit run main.py
```

## 🔧 Manuel Kurulum (Adım Adım)

### Adım 1: Python Sanal Ortamı

```bash
# Sanal ortam oluştur
python3 -m venv venv

# Sanal ortamı aktif et
# macOS/Linux:
source venv/bin/activate

# Windows:
venv\Scripts\activate
```

### Adım 2: Python Paketleri

```bash
# requirements.txt'ten kur
pip install -r requirements.txt

# Manuel kurulum
pip install streamlit>=1.28.1
pip install faster-whisper>=1.0.0
pip install sounddevice>=0.4.0
pip install speechrecognition>=3.10.0
pip install edge-tts>=6.1.9
pip install ollama>=0.1.7
pip install pydub>=0.25.1
pip install requests>=2.25.1
```

### Adım 3: Sistem Bağımlılıkları

#### 🍎 macOS (Homebrew)

```bash
# Homebrew yükleyin (eğer yoksa)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Gerekli paketleri kurun
brew install ollama
brew install ffmpeg
brew install portaudio
```

#### 🐧 Linux (Ubuntu/Debian)

```bash
# Sistem paketlerini güncelle
sudo apt update && sudo apt upgrade -y

# Ollama kurulumu
curl -fsSL https://ollama.ai/install.sh | sh

# Diğer bağımlılıklar
sudo apt install -y \
    ffmpeg \
    portaudio19-dev \
    python3-dev \
    build-essential \
    pulseaudio \
    alsa-utils
```

#### 🪟 Windows

```powershell
# Chocolatey ile (PowerShell Admin)
choco install ollama
choco install ffmpeg

# Veya manuel indirme:
# 1. Ollama: https://ollama.ai/download
# 2. FFmpeg: https://ffmpeg.org/download.html
# 3. Microsoft C++ Build Tools
```

### Adım 4: Ollama Yapılandırması

```bash
# Ollama servisini başlat
ollama serve

# Yeni terminal açın ve modeli indirin
ollama pull llama3.2:latest

# Model durumunu kontrol edin
ollama list
```

### Adım 5: Test ve Başlatma

```bash
# Sistem testini çalıştır
python test_components.py

# Streamlit uygulamasını başlat
streamlit run main.py
```

## 🔍 Kurulum Sorunları ve Çözümleri

### Problem 1: Python Versiyon Hatası

```bash
# Python versiyonunu kontrol edin
python3 --version

# Eğer 3.11'den düşükse:
# macOS: brew install python@3.13
# Ubuntu: sudo apt install python3.13
# Windows: python.org'dan indirin
```

### Problem 2: Pip Modül Hatası

```bash
# Pip'i güncelleyin
python3 -m pip install --upgrade pip

# Sanal ortamı yeniden oluşturun
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Problem 3: Ollama Bağlantı Sorunu

```bash
# Ollama servis durumunu kontrol et
ps aux | grep ollama

# Port kontrol
lsof -i :11434

# Servisi yeniden başlat
# macOS: brew services restart ollama
# Linux: sudo systemctl restart ollama
```

### Problem 4: FFmpeg Bulunamadı

```bash
# FFmpeg kurulu mu kontrol et
ffmpeg -version

# Yol ekle (Linux/macOS)
export PATH=$PATH:/usr/local/bin

# Windows için sistem PATH'ine ekleyin
```

### Problem 5: Mikrofon İzin Hatası

**macOS:**
```bash
# Sistem Tercihleri > Güvenlik ve Gizlilik > Mikrofon
# Terminal/iTerm için izin verin
```

**Linux:**
```bash
# Ses sistemini kontrol et
pulseaudio --check
alsamixer

# Kullanıcıyı audio grubuna ekle
sudo usermod -a -G audio $USER
```

**Windows:**
```bash
# Ayarlar > Gizlilik > Mikrofon
# Uygulamalar için mikrofon izni verin
```

## ⚙️ Gelişmiş Yapılandırma

### Model Seçimi

```python
# config.py dosyasında
OLLAMA_MODEL = "llama3.2:latest"  # Varsayılan
# Alternatifleri:
# "llama3.2:1b"    # Hızlı, düşük RAM
# "llama3.2:3b"    # Dengeli
# "llama3.2:8b"    # Yüksek kalite
```

### Whisper Model Ayarları

```python
# Hız vs Kalite dengesi
WHISPER_MODEL = "base"    # Dengeli (önerilen)
# "tiny"                  # En hızlı
# "small"                 # Hızlı, iyi kalite
# "medium"                # Yavaş, yüksek kalite
# "large"                 # En yavaş, en iyi kalite
```

### TTS Ses Seçimi

```python
# Mevcut Türkçe sesler
TTS_VOICE = "tr-TR-EmelNeural"    # Kadın, doğal
# "tr-TR-AhmetNeural"             # Erkek, güçlü
# "tr-TR-RıfatNeural"             # Erkek, samimi
# "tr-TR-CansuNeural"             # Kadın, genç
# "tr-TR-KartalNeural"            # Erkek, olgun
```

## 🚨 Acil Durum Çözümleri

### Tamamen Sıfırlama

```bash
# Tüm dosyaları sil ve baştan kur
rm -rf venv
rm -rf __pycache__
rm conversations.db
python3 setup.py
```

### Minimum Test

```bash
# Sadece temel bileşenleri test et
python3 -c "import streamlit; print('Streamlit OK')"
python3 -c "import ollama; print('Ollama OK')"
python3 -c "import edge_tts; print('TTS OK')"
```

### Log Kontrol

```bash
# Streamlit logları
streamlit run main.py --logger.level=debug

# Ollama logları
# macOS: brew services log ollama
# Linux: journalctl -u ollama
```

## 📱 Platform Özel Notlar

### 🍎 macOS

- **Apple Silicon (M1/M2)**: Tam destek, hızlı çalışır
- **Intel**: Rosetta2 gerekebilir
- **Ses izinleri**: Güvenlik ayarlarından mikrofon izni verin
- **Homebrew**: Paket yöneticisi olarak kullanılır

### 🐧 Linux

- **Ubuntu 20.04+**: Test edildi, tam destek
- **Debian**: Çalışır, ek paketler gerekebilir
- **Arch/Fedora**: Manuel yapılandırma gerekli
- **PulseAudio**: Ses sistemi olarak önerilen

### 🪟 Windows

- **Windows 10+**: WSL2 önerilen ama native çalışır
- **PowerShell**: Admin yetkisi gerekebilir
- **Visual Studio Build Tools**: C++ bileşenler için
- **Antivirus**: Bazen engel olabilir, istisna ekleyin

## 🏆 Başarılı Kurulum Kontrol Listesi

- [ ] Python 3.11+ kurulu
- [ ] Sanal ortam oluşturuldu ve aktif
- [ ] `pip install -r requirements.txt` başarılı
- [ ] Ollama kurulu ve çalışıyor
- [ ] `ollama list` ile model görünüyor
- [ ] FFmpeg PATH'te mevcut
- [ ] Mikrofon izinleri verildi
- [ ] `python test_components.py` tüm testler geçti
- [ ] `streamlit run main.py` çalışıyor
- [ ] `http://localhost:8501` açılıyor

## 🆘 Yardım Alma

Eğer sorunlar devam ediyorsa:

1. **GitHub Issues**: Detaylı hata raporu açın
2. **Log dosyaları**: Hata mesajlarını paylaşın
3. **Sistem bilgileri**: OS, Python versiyonu, RAM vb.
4. **Test sonuçları**: `python test_components.py` çıktısı

## 📞 Teknik Destek

- 🐛 **Hata Raporu**: GitHub Issues
- 💬 **Soru-Cevap**: GitHub Discussions  
- 📧 **Direkt İletişim**: [email@example.com]

---

**🎉 Kurulum tamamlandı! ASYA'nızla sohbet etmeye başlayabilirsiniz!** 