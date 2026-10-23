# Streaming konuşma ve tempo — 19 Ekim 2026

İlk ses için 45 karakteri aşan bir cümle beklemek, kısa yanıtları ve uzun
giriş cümlelerini geciktiriyordu. Streaming metin artık ilk tamamlanan kısa
cümleyi hemen, ilk virgüllü ifadeyi en az 32 karakter ve beş sözcükten sonra
ses üretimine verir. Devam eden cümleler en az 60, virgüllü ifadeler 100
karakter civarında gruplanır; noktalamasız metin 240 karakteri geçtiğinde
sözcük sınırında bölünür. Ses üretimi LLM tüketicisinden ayrı bir görevdir.
Bu, Chatterbox'ın token veya PCM seviyesinde streaming desteği olduğu
anlamına gelmez; her ses parçasının inference işlemi tamamlanmalıdır.

`SpeechChunker`, tokenlar arasında bölünmüş düşünce/kod etiketlerini takip
eder. Bu bloklar ve tamamlanmamış gizli içerik seslendirilmez. Ekrandaki
orijinal LLM metni korunur. Ondalık sayılar, yaygın kısaltmalar, tarih ve
madde numarası sonundaki noktalar ilk parçayı yanlışlıkla bölmez.

Kullanıcının mevcut Zehra karakter prompt'u değiştirilmez. Sesli isteklerin
etkin sistem prompt'una doğal cümle, anlamlı virgül/nokta ve doğrudan
seslendirilebilir çıktı kuralları eklenir. Yazılı yanıtlara bu ek uygulanmaz.
`[durakla]` veya SSML gibi yönergeler üretmesi istenmez; Chatterbox bunları
bir kontrol protokolü olarak desteklemez. Ayrıntı isteyen soruların kapsamı
gereksiz bir cümle sayısı sınırıyla daraltılmaz.

Tempo ayrıca gerçek ses üzerinde uygulanır: `chat_speech_rate` varsayılan
0,90; aralık 0,75–1,15. Ayarlar ekranından kaydedilir ve sonraki sohbet
yanıtlarında kullanılır. FFmpeg `atempo`, sample rate veya perdeyi düşürmeden
konuşmayı yavaşlatır. Son işlem GPU kuyruğunu bloke eden bir sistem çağrısı
yerine yardımcı thread üzerinde yürütülür. Üretilen her parçanın sonuna
virgül/noktalı virgül/iki nokta için 140 ms, cümle sonu için 280 ms, zorunlu
sözcük kesimi için 100 ms sessizlik eklenir. Parça içindeki noktalama yine
modelin prozodisine bağlıdır. Oynatılan ve kaydedilen WAV aynı tempoyu ve
duraklamayı içerir. Ses Stüdyosu varsayılan üretim hızı 1,00× olarak kalır.

Klon seste aynı aktif referansın conditioning işlemi parçalar arasında
yeniden yapılmaz. Referans değişince, dosya değişince veya varsayılan sese
dönülünce önbellek geçersizleşir. Model ağırlıkları değiştirilmez.

## Doğrulama

- Son kontrol: 54 backend testi, 10 frontend testi ve iki Edge tarayıcı testi
  başarılı; TypeScript kontrolü ve production build tamamlandı.
- Backend testleri: akış bitmeden ses teslimi, erken sesten sonra iptal,
  metin sırası/kaybı, farklı token boylarında gizli bloklar, tarih ve sayılar,
  referans önbelleğinin geçersizleşmesi ve eski HTTP/WebSocket regresyonları.
  Ses kuyruğu doluyken iptal edilen yanıtın kilitlenmeden sonlanması da kapsanır.
- Gerçek FFmpeg testi: 440 Hz ses 0,80× tempoda uzar; frekans korunur ve
  istenen sessizlik gerçekten dosyada bulunur.
- `scripts/verify-streaming-speech.py`: gerçek CUDA Chatterbox ve izinli
  referans ses kullanılarak erken ses teslimi ve WAV duraklamaları doğrulandı.
  Kontrollü token kaynağı ilk sesi almadan son tokenları göndermez; bu bir
  gerçek LLM gecikme benchmark'ı değildir. Sonuçlar
  `docs/streaming-speech-results.json`, dinleme örneği
  `data/verification/streaming-speech/generations/gated-preview.wav` içindedir.
- Bu çalıştırmada LM Studio API'si kapalıydı. Gerçek LLM ile önce/sonra
  gecikme karşılaştırması yapılmadı. Modelin soğuk yüklenmesi hâlâ ilk yanıta
  ek süre getirir. Doğal duyulma değerlendirmesi kullanıcı dinlemesi gerektirir.
- TypeScript tipleri OpenAPI'den yeniden üretildi; frontend testleri ve
  production build başarılı. Tarayıcı testi hız kontrolünün kaydedilip
  yenilemeden sonra korunmasını ve karakter prompt'unun değişmemesini kapsar.

Kontrol komutları:

```powershell
.\scripts\test.ps1
.\.venv\Scripts\python.exe scripts\verify-streaming-speech.py
# Uygulama açıkken:
cd apps\frontend
$env:VOICE_TEST_BASE_URL = 'http://127.0.0.1:8000'
npx.cmd playwright test e2e/speech-settings.spec.ts
```

Yeni backend kodunu kullanmak için uygulamayı yeniden başlatın, ardından
tarayıcı sayfasını yenileyin. Önceden üretilmiş sesler yeniden işlenmez.
