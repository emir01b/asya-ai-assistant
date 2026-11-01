# Doğal ses ve referans seçimi

Ses profiline en fazla 200 MiB ve 300 saniyelik bir kayıt yüklenebilir. Yüklenen özgün dosya ve çözümlenmiş tam kayıt saklanır. ASYA yeni profilde ses düzeyi, sessizlik ve kırpılma gibi basit ölçülere göre yaklaşık 8 saniyelik bir bölüm önerir; bu yöntem konuşmayı tanımaz ve bölümün temiz olduğunu garanti etmez. başlangıç ve bitiş alanlarıyla bölüm değiştirilebilir. 6–10 saniyelik temiz konuşma önerilir. Sessizlik, düşük seviye veya olası kırpılma uyarıları kayıt üzerinde otomatik gürültü giderme ya da ses perdesi değişikliği yapmaz. Eski profiller düzenlenmedikçe önceki referanslarını kullanır.

Ayarlar bölümündeki **Hızlı**, **Dengeli** ve **Kalite** seçenekleri konuşmanın parçalara ayrılma davranışını değiştirir; varsayılan Dengeli'dir. Üretim isteği bir mod, seed ve profilin değerlerini geçersiz kılan parametreler belirtebilir. İş geçmişi kullanılan ayarları ve referansı kaydeder.

**Adayları karşılaştır** deneysel bir seçenektir. İki üretim yapılır; kullanılabilir olduğunda konuşma tanımanın metinle uyumu ve eşitlikte konuşmacı benzerliği seçime yardımcı olur. Tanıma kullanılamazsa ilk aday seçilir ve hata adayın değerlendirmesinde gösterilir. Adaylar geçmişten dinlenip elle seçilebilir. Bu ölçümler insan değerlendirmesinin yerini tutmaz; doğal ses kalitesinde iyileşme henüz gerçek kullanıcı veya donanım testleriyle kanıtlanmamıştır. Karşılaştırma daha uzun sürer ve daha fazla kaynak kullanır.

Backend testleri Windows'ta proje kökünden çalıştırılabilir:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s apps/backend/tests -v
```

Test istemcisi yerel loopback soketi kullanır; kısıtlı ortamlarda bunun için uygun çalışma izni gerekebilir. Gerçek TTS çıktılarının dinleyici değerlendirmesi ayrıca gereklidir.


## Gerçek donanım deneyi

`scripts/benchmark-natural-voice.py`, mevcut izinli profilin referans kaydını canlı SQLite veritabanından yalnızca okur ve ayrı bir test deposuna kopyalar. Çevrimdışı yerel modelle önce ısınma üretimi, ardından 12 Türkçe metnin her biri için Hızlı, Dengeli ve Kalite üretimleri yapılır. Aynı seed ile 3 × 3 ifade ve CFG kombinasyonu, ayrıca iki aday ve yerel konuşma tanıma değerlendirmesi denenir. Metin normalleştirmesi açıktır. Üretim süreleri ses analiz süresini içermez; model yüklemesi ilk çalışmada ayrıca kaydedilir.

Ham ve 0,9 tempolu sesler, sesli olduğu tahmin edilen karelerde medyan perde ve süreler ayrı kaydedilir. Perde kestirimi içeriğe ve konuşma biçimine bağlıdır; tek başına sesin inceliğini veya kalitesini kanıtlamaz. `paired-listening.html` aynı metinde Dengeli/Kalite çıktısını rastgele A/B sırasıyla dinletir. Değerlendirme bitene kadar eşleme anahtarını açmayın; notları ayrıca kaydedin. İnsan dinleme değerlendirmesi olmadan daha doğal ses iddia edilemez.

```powershell
.\.venv\Scripts\python.exe scripts/benchmark-natural-voice.py --output data/verification/natural-voice/smoke --smoke
.\.venv\Scripts\python.exe scripts/benchmark-natural-voice.py --output data/verification/natural-voice/full
```

### Tamamlanan yerel ölçüm

NVIDIA GeForce RTX 5060 Ti üzerinde çevrimdışı `full-final` çalışması tamamlandı: 12 Türkçe metin × 3 mod, aynı metin ve seed ile 9 ifade/CFG kombinasyonu ve bir iki-aday karşılaştırması olmak üzere **46 sonuç**. Isınma dahil 47 işin tamamı test deposunda `completed`; kayıtlı hata sayısı sıfır. Ölçüm dosyası, karşılaştırma adayları ve dinleme sayfalarının sesleri dahil 209 WAV dosyası sonlu, boş olmayan örnekler ve geçerli süreler açısından doğrulandı. Bu denemede mevcut eski profilin 44,203 saniyelik referansı kullanıldı; yeni 6–10 saniyelik referans seçiminin kalitesini bu çalışma doğrulamaz.

Isınma üretimi hariç, mod başına 12 metnin medyanları:

| Mod | İlk ses parçası hazır | Toplam üretim | Üretim/ses süresi oranı |
| --- | ---: | ---: | ---: |
| Hızlı | 3,523 sn | 4,406 sn | 0,902 |
| Dengeli | 3,292 sn | 3,944 sn | 0,864 |
| Kalite | 3,905 sn | 3,920 sn | 0,877 |

İlk ses ölçümü backend'de ilk parçanın hazır olma anıdır; tarayıcıda gerçekten duyulma gecikmesini ölçmez. Sonuçlar tek cihazda, tek referansla, sırayla yapılan bir çalışmadandır; mod adları hız veya kalite garantisi vermez. Model yükleme 8,480 saniye, ayrı ısınma işinin toplam süresi 19,783 saniyeydi. Analiz ve sonradan uygulanan 0,9 tempo işlemi tablodaki üretim sürelerine dahil değildir.

Seed `4202` sabitken ifade `{0,3; 0,5; 0,7}` ve CFG `{0; 0,3; 0,5}` matrisindeki dokuz ham WAV'ın SHA-256 değerleri birbirinden farklıdır. Bu, ayarların bu çalışmada çıktıyı değiştirdiğini gösterir; doğal ses veya kimlik benzerliğinin iyileştiğini göstermez. Dengeli/Kalite çiftlerinin biri aynı WAV hash'ine sahiptir; tüm çiftlerde duyulabilir fark varsayılmamalıdır.

Gerçek yerel konuşma tanıma değerlendirmesinde iki aday da metin uyumu `1,0` aldı; konuşmacı benzerliği `0,909087` ve `0,895394` olduğu için aday 0 seçildi. Bu tek karşılaştırmanın toplam süresi 19,154 saniyeydi ve değerlendirme hatası kaydedilmedi. Bunlar model skorlarıdır; insan tarafından verilmiş kalite puanları değildir.

İncelenebilir yerel çıktılar: [ölçümler](../data/verification/natural-voice/full-final/measurements.json), [doğrulama özeti ve hash'ler](../data/verification/natural-voice/full-final/summary.json), [aynı metinle kör A/B dinleme](../data/verification/natural-voice/full-final/paired-listening.html). A/B sayfası 12 Dengeli/Kalite çifti içerir. Doğallık, telaffuz, referansa benzerlik ve kopukluk için insan dinleme kabulü **bekliyor**; Kalite modu deneysel kabul edilmelidir.

Sesleri yeniden üretmeden mevcut sonuçları doğrulamak için:

```powershell
.\.venv\Scripts\python.exe scripts/summarize-natural-voice.py data/verification/natural-voice/full-final
```
