# ASYA'nın yerel ses stüdyosuna geçişi

İnceleme tarihi: 21 Ekim 2026.

ASYA'nın amacı Türkçe sesli sohbet, yerel LLM ve konuşma hafızasıdır.
`voice-lab` çalışma dizininde geliştirilen React/FastAPI uygulaması bu amacın
yeni uygulamasıdır. Aynı repository ve Git geçmişi üzerinde, mevcut sürümün
yanına test edilebilir parçalar eklenerek ilerlenir.

23 Ekim 2026 güncellemesi: React/FastAPI kaynakları, Windows başlatıcıları,
testler ve OpenAPI sözleşmesi bu repository'ye aktarıldı. Yeni giriş noktası
`scripts/start-app.ps1`; eski `streamlit run main.py` yolu korunuyor.
Çalıştırma ve yerel ortam bağlantıları [ASYA rehberinde](VOICE_STUDIO.md).
Aktarım Git geçmişini yeniden oluşturmaz; mevcut `evolution/voice-studio`
dalındaki çalışma ağacına eklenmiştir.

Aşağıdaki sıra ilk geçiş planıdır. Kaynak aktarımı, her satırdaki kabul ölçütünün
tamamlandığı anlamına gelmez: eski konuşmaları dönüştürme, eski ayarları birleştirme
ve temiz AI ortamı kurulumu hâlâ ayrı işlerdir. Tarihsel ölçüm raporları ve kişisel
veriler aktarılmadı. Mevcut yerel runtime bağlantıları Git dışında tutulur.

## İncelenen başlangıç noktası

- Repository: [emir01b/asya-ai-assistant](https://github.com/emir01b/asya-ai-assistant).
- Başlangıç commit'i: `9205f79c5a61d2745814dd105e0933270e73d2a2`.
- Mevcut geçmiş: 8 Haziran 2025 tarihli iki commit, 9 Haziran 2025 tarihli
  README/görsel commit'i. Yeni çalışmalar bu geçmişin devamına eklenir.
- Çalışma dalı: `evolution/voice-studio`.
- `voice-lab` kökü Git repository'si değildir. İçindeki `chatterbox/` dizini
  ise Resemble AI'ın ayrı upstream repository'sidir.

## Kod düzeyinde devamlılık

| Mevcut ASYA | Geliştirilmiş sürümdeki karşılığı | Geçişte dikkat edilecek nokta |
| --- | --- | --- |
| `main.py`: Streamlit ekranı ve senkron sohbet | `apps/frontend` React; `apps/backend/app/main.py` FastAPI | Eski uygulama yeni arayüz kabul edilene kadar çalıştırılabilir kalır. |
| `llm_processor.py`: Ollama `/api/generate` | `apps/backend/app/llm.py`: LM Studio SSE | Eski Ollama yolu geçiş sırasında korunur; yeni model seçimi ayarlardan yapılır. |
| `speech_processor.py`: sounddevice, CPU Whisper | Tarayıcı AudioWorklet/VAD, izole `stt_worker.py` | Mikrofon tarayıcının bulunduğu cihazdan alınır. CUDA ve CPU fallback ayrı doğrulanır. |
| `tts_processor.py`: Edge-TTS | `engines.py` ve provider kaydı: yerel Chatterbox | Model yükleme, ses profilleri ve tek GPU kuyruğu ayrı sorumluluklardır. |
| `memory_manager.py`: `conversations` ve `user_preferences` | `core.py`: JSON kayıtları tutan `records` tablosu | SQLite dosyaları doğrudan birbirinin yerine konamaz; dönüştürücü gerekir. |
| `config.py`: sınıf ve modül düzeyinde ayarlar | Pydantic ayarları ve kalıcı Store | Çakışan varsayılanlar açıkça eşlenir; eski kullanıcı tercihleri korunur. |
| Tam LLM yanıtından sonra TTS çağrısı | `chat.py` tüketici kuyruğu, `SpeechChunker` | İlk anlamlı ifade hazırken üretim başlar; iptal ve ses sırası test edilir. |
| Tek bilgisayarda başlatma | HTTPS/LAN ve tekrar başlatma kontrolleri | Sertifikalar, özel anahtarlar ve cihaz adresleri yerel kalır. |

Eski `LLMProcessor` içinde streaming metodu bulunsa da `main.py` içindeki
sohbet yolları `generate_response()` çağırıyor ve TTS'yi tam yanıt sonrasında
başlatıyor. Dolayısıyla yeni metin/ses akışı somut bir davranış geliştirmesidir.

README'nin tamamen çevrimdışı çalışma iddiası mevcut kodun tamamı için doğru
değildir: Edge-TTS kullanılıyor ve STT fallback/dosya yolu
`recognize_google()` çağırıyor. Yeni yerel ses hattının kapsamı belgelenirken
ilk model indirmesi ile sonraki offline inference birbirinden ayrılmalıdır.

`Config.WHISPER_MODEL` değeri `base`, dosyanın sonundaki modül sabiti ise
`turbo`; sınıf ve modül düzeyindeki veritabanı adları da farklıdır. Bunlar
ayar geçişinde testlerle açıklığa kavuşturulmalıdır.

## Küçük commitlerle aktarım sırası

Her satır bir veya birkaç küçük commit olabilir. Bir commit tek davranışı
değiştirir; ilgili test ve kısa belge değişikliği aynı commit'e girer.

| Sıra | Kapsam / örnek commit mesajı | Tamamlanma ölçütü |
| --- | --- | --- |
| 1 | `chore: exclude local runtime data and remove Finder metadata` | Ortamlar, kişisel kayıtlar, modeller ve anahtarlar Git dışında. Hazır. |
| 2 | `docs: map ASYA architecture and plan the voice studio transition` | Mevcut kod ile yeni mimari eşleştirilmiş, aktarım sırası belirlenmiş. Bu belge. |
| 3 | `refactor: centralize assistant configuration defaults` | Eski çalışan akışın kullandığı değerler testlerle korunur; çift tanımlar giderilir. |
| 4 | `feat: introduce validated settings and persistent backend storage` | Yeni paketin bütün importları çalışır; Store/şema testleri geçer. |
| 5 | `feat: import legacy ASYA conversations into the new store` | Eski DB salt okunur açılır; oturumlar ve tarihler korunur; tekrar import kopya üretmez. |
| 6 | `feat: add LM Studio streaming transport` | Model keşfi, SSE, boş yanıt ve bağlantı hatası testleri geçer. |
| 7 | `build: provision the pinned local speech runtime` | Chatterbox sürümü ve Windows değişiklikleri tekrarlanabilir; temiz kurulum yolu belgelenir. |
| 8 | `feat: add queued local speech generation` | Tek GPU işçisi, referans ses, iptal ve dosya çıktısı çalışır. |
| 9 | `feat: isolate Whisper transcription in a reusable worker` | STT ortamı ayrı; worker yeniden kullanım ve iptal testleri geçer. |
| 10 | `feat: expose voice jobs and conversation APIs` | FastAPI yaşam döngüsü, HTTP sözleşmesi ve kalıcılık testleri geçer. |
| 11 | `feat: add the React application shell` | Sayfa iskeleti ve API istemcisi derlenir; mevcut Streamlit yolu çalıştırılabilir kalır. |
| 12 | `feat: add voice library and generation studio` | Profil oluşturma, üretim ve geçmiş ekranları gerçek API ile çalışır. |
| 13 | `feat: add continuous browser voice conversations` | Mikrofon, VAD, WebSocket, eski isteklerin elenmesi ve sıralı oynatma test edilir. |
| 14 | `perf: start speech from the first complete phrase` | LLM akışı bitmeden üretim başlar; gizli bloklar sese sızmaz. |
| 15 | `feat: add conversational speech pacing` | Hız kontrolü, anlamlı noktalama ve dosyaya uygulanan duraklamalar doğrulanır. |
| 16 | `feat: enable trusted HTTPS access on the local network` | TLS, WebSocket ve LAN erişimi doğrulanır; sırlar repository'ye girmez. |
| 17 | `fix: make Windows launchers version-aware and repeatable` | PowerShell 5.1 yönlendirmesi ve çalışan sunucuyu tekrar başlatmama testi geçer. |
| 18 | `docs: publish the ASYA voice studio setup and migration guide` | Yeni kurulum, özellik kapsamı ve eski sürümden geçiş kullanıcıya açıkça anlatılır. |

Bu sıra, mevcut dosyaları körlemesine dizinlere bölüp commit etmek anlamına
gelmez. Örneğin `core.py` bir prompt sabitini import ediyorsa o bağımlılık
aynı commit'te bulunmalıdır. Yeni frontend'in API sözleşmesi, package lock'u
ve gerekli tipleri de derlenebilen bir bütün olarak taşınır. Gerekirse
birbirinden ayrılamayan satırlar tek commit'te birleştirilir.

## Uygulama ve yayın akışı

1. Bir sonraki küçük davranış değişikliğini seç.
2. İlgili kodu ASYA dalına taşı/uyarla ve hedefli testini çalıştır.
3. Diff'i incele; model dosyası, ses kaydı, veritabanı, anahtar veya yerel
   ölçüm raporu bulunmadığını doğrula.
4. Tek amaçlı mesajla, işlemin yapıldığı tarihte commit et.
5. Tamamlanan aşamaları GitHub'a normal push ile gönder; inceleme için PR aç.
   Küçük commitlerin ana dalda da görünmesi isteniyorsa birleştirmede onları
   koruyan yöntem kullan.

Yeni kodun kaynağı olan `voice-lab` içindeki `.venv`, `.venv-stt`, `data`,
`node_modules`, derlenmiş çıktı ve kişisel test raporları taşınmaz. Kaynak
dosyalar açık bir dosya listesiyle aktarılır. Chatterbox, upstream commit'i
sabitlenen üçüncü taraf bağımlılık olarak kurulur; gerekli yerel yamalar ve
lisans bildirimleri ayrıca kaydedilir.

Mevcut backend requirements dosyası çalışan bir makinenin ek paketlerini
listeliyor; tek başına yeni bir AI ortamı kurma reçetesi değildir. Yayın öncesi
temiz ortam kurulumu ayrıca doğrulanmalıdır. Yeni sürümün Windows/CUDA üzerinde
denenmiş olması, macOS/Linux desteğinin de doğrulandığı anlamına gelmez.

Ürün adı ASYA olarak devam edebilir. Zehra gibi konuşma kişilikleri ve seçilen
ses profilleri ürün adından ayrı kullanıcı ayarları olarak ele alınır.
