# 🤝 Katkıda Bulunma Kılavuzu

ASYA projesine katkıda bulunduğunuz için teşekkür ederiz! Bu kılavuz, projeye nasıl katkıda bulunabileceğinizi açıklar.

## 🌟 Katkı Türleri

### 🐛 Hata Raporları
- Yaşadığınız sorunları GitHub Issues'da bildirin
- Detaylı açıklama ve reproduksiyon adımları ekleyin
- Sistem bilgilerinizi (OS, Python versiyonu) paylaşın

### 💡 Özellik Önerileri
- Yeni özellik fikirlerinizi Issues'da önerin
- Özelliğin neden faydalı olduğunu açıklayın
- Mümkünse mockup veya örnek ekleyin

### 📝 Dokümantasyon
- README ve diğer belgeleri geliştirin
- Türkçe çeviri ve düzeltmeler yapın
- Kurulum kılavuzunu güncelleyin

### 💻 Kod Katkıları
- Bug fix'ler yapın
- Yeni özellikler ekleyin
- Performans iyileştirmeleri sağlayın

## 🚀 Başlangıç

### 1. Projeyi Fork Edin
```bash
# GitHub'da "Fork" butonuna tıklayın
# Kendi fork'unuzu klonlayın
git clone https://github.com/[kullaniciadi]/asya-ai-assistant.git
cd asya-ai-assistant
```

### 2. Geliştirme Ortamını Kurun
```bash
# Sanal ortam oluşturun
python3 -m venv venv
source venv/bin/activate

# Bağımlılıkları kurun
pip install -r requirements.txt

# Sistem testini çalıştırın
python test_components.py
```

### 3. Branch Oluşturun
```bash
# Feature branch oluşturun
git checkout -b feature/amazing-feature

# Bug fix için
git checkout -b bugfix/fix-issue-123

# Dokümantasyon için
git checkout -b docs/update-readme
```

## 📋 Kod Standartları

### Python Stil Kılavuzu

#### 🔤 İsimlendirme
- **Değişkenler**: `snake_case`
- **Fonksiyonlar**: `snake_case`
- **Sınıflar**: `PascalCase`
- **Sabitler**: `UPPER_CASE`

#### 📝 Dokümantasyon
```python
def transcribe_audio(self, audio_data=None):
    """
    Ses verisini metne dönüştürür.
    
    Args:
        audio_data (np.array): Ses verisi
        
    Returns:
        str: Transkripsyon metni
        
    Raises:
        TranscriptionError: Ses işlenemediğinde
    """
    pass
```

#### 🧪 Test Yazma
```python
def test_speech_recognition():
    """Ses tanıma fonksiyonunu test eder"""
    processor = SpeechProcessor()
    result = processor.test_microphone()
    assert "çalışıyor" in result.lower()
```

### 📁 Dosya Organizasyonu
```
├── core/              # Ana işlem modülleri
├── ui/                # Arayüz bileşenleri  
├── utils/             # Yardımcı fonksiyonlar
├── tests/             # Test dosyaları
├── docs/              # Dokümantasyon
└── examples/          # Örnek kullanımlar
```

## 🔄 Pull Request Süreci

### 1. Değişikliklerinizi Commit Edin
```bash
# Anlamlı commit mesajları yazın
git add .
git commit -m "feat: Türkçe ses tanıma hassasiyeti artırıldı"

# Commit türleri:
# feat: Yeni özellik
# fix: Hata düzeltmesi  
# docs: Dokümantasyon
# style: Kod formatı
# refactor: Kod yeniden düzenleme
# test: Test ekleme/düzeltme
# chore: Bakım işleri
```

### 2. Fork'unuza Push Edin
```bash
git push origin feature/amazing-feature
```

### 3. Pull Request Oluşturun
- GitHub'da "Pull Request" butonuna tıklayın
- Değişikliklerinizi detaylı olarak açıklayın
- Issue referansları ekleyin (#123)
- Screenshots/GIF'ler ekleyin (UI değişiklikleri için)

### 4. Review Bekleyin
- Maintainer'lar kodunuzu inceleyecek
- Gerekli değişiklikleri yapın
- CI/CD testlerinin geçtiğinden emin olun

## 🧪 Test Yazma

### Unit Test Örneği
```python
import pytest
from speech_processor import SpeechProcessor

class TestSpeechProcessor:
    def setup_method(self):
        self.processor = SpeechProcessor()
    
    def test_microphone_initialization(self):
        """Mikrofon başlatma testi"""
        assert self.processor.microphone is not None
        
    def test_audio_transcription(self):
        """Ses transkripsiyonu testi"""
        # Mock audio data
        audio_data = np.random.rand(16000)
        result = self.processor.transcribe_audio(audio_data)
        assert isinstance(result, str)
```

### Integration Test
```python
def test_full_pipeline():
    """Tüm pipeline testi"""
    # STT -> LLM -> TTS zinciri
    speech = SpeechProcessor()
    llm = LLMProcessor()
    tts = TTSProcessor()
    
    # Ses dosyası yükle
    audio = load_test_audio("test_hello.wav")
    
    # Pipeline çalıştır
    text = speech.transcribe_audio(audio)
    response = llm.generate_response(text)
    audio_out = tts.synthesize(response)
    
    assert len(text) > 0
    assert len(response) > 0
    assert len(audio_out) > 0
```

## 📚 Dokümantasyon

### README Güncellemeleri
- Yeni özellikler için dokümantasyon ekleyin
- Kurulum adımlarını güncel tutun
- Örnek kullanımları gösterin

### Code Comments
```python
# Türkçe açıklamalar tercih edilir
def ses_isle(self, audio_data):
    # Ses verisini normalize et
    normalized_audio = audio_data / np.max(np.abs(audio_data))
    
    # Whisper modeline gönder
    result = self.whisper_model.transcribe(normalized_audio)
    
    return result
```

## 🐛 Issue Raporu Template

```markdown
**🐛 Hata Açıklaması**
Kısa ve net hata açıklaması

**🔄 Reproduksiyon Adımları**
1. Şunu yap
2. Şuna tıkla  
3. Hatayı gör

**🎯 Beklenen Davranış**
Ne olması gerektiği

**📱 Sistem Bilgileri**
- OS: macOS 14.0
- Python: 3.13.0
- ASYA: v1.0.0

**📋 Ek Bağlam**
Screenshots, log dosyaları vb.
```

## 💡 Özellik Önerisi Template

```markdown
**🌟 Özellik Önerisi**
Özelliğin kısa açıklaması

**❓ Problem/İhtiyaç**
Bu özellik hangi problemi çözüyor?

**💭 Çözüm Önerisi**
Nasıl çalışmasını öneriyorsunuz?

**🔄 Alternatifler**
Başka hangi çözümler düşündünüz?

**📎 Ek Bağlam**
Mockup, referans linkler vb.
```

## 🏆 Katkıda Bulunanlar

Tüm katkıda bulunanlar [CONTRIBUTORS.md](CONTRIBUTORS.md) dosyasında listelenir.

### Hall of Fame 🌟
- **Ana Geliştiriciler**: Projeyi başlatanlar
- **Core Contributors**: Düzenli katkıda bulunanlar  
- **Community Heroes**: Dokümantasyon ve destek sağlayanlar

## 📞 İletişim

- 🐛 **Bug Reports**: GitHub Issues
- 💬 **Genel Sorular**: GitHub Discussions
- 📧 **Özel Konular**: [email@example.com]
- 💭 **Fikirler**: GitHub Discussions Ideas

## 📄 Lisans

Katkıda bulunarak, kodunuzun [MIT Lisansı](LICENSE) altında dağıtılmasını kabul etmiş olursunuz.

---

**🙏 Teşekkürler!** 

Her türlü katkınız ASYA'yı daha iyi hale getiriyor! 🚀 