# Ajan bağlantısı

Ajanlar arayüze tıklamadan HTTP API veya MCP üzerinden ASYA'nın mevcut ses kuyruğunu kullanır. Ayrı model yüklenmez. Temel seçenek HTTP endpoint'leridir; terminal, OpenAI uyumlu istemciler ve MCP aynı işlemlere erişir.

## Başlatma ve erişim

1. ASYA'yı normal şekilde başlatın. Bu değişiklikten önce çalışan backend'i uygun zamanda yeniden başlatın; yeni Ayarlar bölümü için yeni backend kodu gerekir.
2. Ayarlar > Ajan erişimi bölümündeki **Kur** butonuna basın. Hazırlık, paket kurulumu ve doğrulama aşamaları ilerleme çubuğunda gösterilir. Kuruluysa buton **Zaten kurulu** olarak pasif görünür. Ayrı `.venv-agents` kullanılır; ses motorunun ortamı değiştirilmez. Kurulum sonunda ve ASYA'nın sonraki açılışlarında kurulu ajan servisi otomatik başlatılır. Kurulum erişim iznini açmaz.
3. Ayarlar > Ajan erişimi bölümünde Ali adlı bir anahtar oluşturun. Anahtar yalnızca bir kez gösterilir.
4. “Ajan erişimine izin ver” anahtarını açın. Değişiklik hemen kaydedilir; genel ayarları kaydet düğmesine basmanız gerekmez.

Varsayılan durum kapalıdır. Kapalıyken yalnızca `GET http://127.0.0.1:8002/.well-known/asya-agent.json` bilgi verir; API ve MCP 403 döndürür. Servis süreci bilgi adresi için açık kalır. Başlamış ses işi tamamlanabilir, ancak kapalıyken ajan sonucu alamaz. Anahtarı iptal etmek de sonraki istekleri engeller. Bu anahtar ajan servisini kontrol eder; ana uygulamanın kullanıcı arayüzü çalışmaya devam eder.

Yerel uygulama yönetimi bilgisayar sahibine güvenir. Bu bir işletim sistemi sandbox'ı değildir: bilgisayarda sınırsız terminal/dosya yetkisi olan bir programın yerel kullanıcı yetkilerini kullanmasını engellemez. Güvenilmeyen ajanları ayrı kullanıcı/sandbox üzerinde veya yalnızca ajan gateway'ine erişebilecek başka bilgisayarda çalıştırın.

## Ali örneği: terminalden ses oluşturma

Anahtarı ajanınızın gizli ortam değişkeni `ASYA_AGENT_TOKEN` olarak saklayın. Aşağıdaki PowerShell örneği mevcut değişkeni kullanır; anahtarı komut geçmişine yazmayın.

```powershell
$Headers = @{ Authorization = "Bearer $env:ASYA_AGENT_TOKEN" }
Invoke-RestMethod 'http://127.0.0.1:8002/.well-known/asya-agent.json' -Headers $Headers
$Body = @{ model = 'chatterbox-multilingual-v3'; input = 'Merhaba, ben Ali. İşlemin tamamlandı.'; voice = 'asya-default'; response_format = 'wav' } | ConvertTo-Json
Invoke-WebRequest 'http://127.0.0.1:8002/v1/audio/speech' -Method Post -Headers $Headers -ContentType 'application/json; charset=utf-8' -Body ([Text.Encoding]::UTF8.GetBytes($Body)) -OutFile 'ali.wav'
```

Ali, bilgi adresinden yalnızca izinli işlemleri, parametreleri, sonuçları ve hata kodlarını öğrenir. Sesleri listeler, ses üretir, kendi işini sorgular/iptal eder ve kendi WAV/MP3 dosyasını indirir. Özel kadın/erkek/klonlanmış sesler mevcut ses profili kimliğiyle seçilir; `asya-default` uygulamanın varsayılan profilini kullanır.

OpenAI uyumlu istemcide base URL `http://127.0.0.1:8002/v1`, API key ajan anahtarı, model `chatterbox-multilingual-v3` olur. Yalnızca ses üretme sözleşmesi desteklenir; OpenAI bulut modelleri, realtime streaming veya instructions desteklenmez. WAV/MP3 çıktı, hız 0.75–1.15, en fazla 12000 karakter. Senkron bekleme 300 saniyeyi aşarsa 504 içindeki job_id ile sorgulamaya devam edin.

Uzun işler için `POST /api/v1/agent/speech` hemen iş kimliği döndürür. `GET /api/v1/agent/jobs/{id}`, `POST /api/v1/agent/jobs/{id}/cancel`, `GET /api/v1/agent/jobs/{id}/audio?format=wav` kullanılır. Aynı talebi güvenle tekrar sorgulamak için `Idempotency-Key` başlığı gönderin. Belirsiz gönderimde 409 döner; otomatik yeni ses üretimi başlatmayın.

## MCP

Streamable HTTP: `http://127.0.0.1:8002/mcp`, başlık `Authorization: Bearer <anahtar>`.

MCP araçları `get_capabilities` ve `execute`; kaynak `asya://guide`. Önce yetenekleri okuyun, ardından örneğin `execute(operation="generate_speech", arguments={"input":"Merhaba, ben Ali."})` çağırın. `get_job` ve `get_audio` işlemlerine `job_id` verin. MCP ses sonucu MIME tipi ve base64 veridir.

Stdio kullanan istemcide proje klasörünü çalışma dizini yapın:

```json
{
  "mcpServers": {
    "asya": {
      "command": "C:/PROJE/.venv-agents/Scripts/python.exe",
      "args": ["-m", "apps.agents.stdio"],
      "cwd": "C:/PROJE",
      "env": { "ASYA_AGENT_TOKEN": "AJAN_ANAHTARI" }
    }
  }
}
```

`C:/PROJE` yerine gerçek proje yolunu yazın. İstemcinizin gizli anahtar saklama özelliğini tercih edin. Stdio köprüsü de çalışan HTTP servisine bağlanır ve aynı kapatma anahtarına tabidir. OpenClaw sürümünüzün HTTP TTS sağlayıcısı veya MCP istemcisi üzerinden bu adresleri kullanın; OpenClaw'ın kendisiyle canlı bağlantı testi yapılmadı.

## Ek yetkiler ve yerel ağ

Anahtar oluştururken isteğe bağlı izinler: ses kaydını yazıya dönüştürme, izinli örnek kayıtla profil oluşturma/düzenleme, profil silme, ses ayarlarını okuma/değiştirme, boş modelleri bellekten çıkarma ve kendi üretim geçmişini silme. Ajan anahtar oluşturamaz, izin yükseltemez, erişim anahtarını açamaz. Paylaşılan ses profili silme tüm kullanıcıları etkiler. API sohbet geçmişini veya işletim sistemi komutlarını sunmaz.

Aynı bilgisayarda varsayılan 127.0.0.1 kullanılır. Başka bilgisayar için açıkça özel LAN IP'si ve o IP'ye uygun güvenilir TLS sertifikası gerekir:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/start-agents.ps1 -LanAddress 192.168.1.20 -Certificate C:\certs\server.crt -PrivateKey C:\certs\server.key
```

Ana backend localhost modunda olmalı; eski LAN modu açıksa ağ geçidi başlamaz ve sonradan açılırsa işlemleri reddeder. Ajan servisi port 8002'yi kullanır; güvenlik duvarını otomatik değiştirmez. LAN kipinde belirtilen IP'ye bağlanır; localhost örneklerindeki adresi `https://IP:8002` olarak değiştirin. Stdio köprüsü varsayılan localhost kurulumu içindir. İnternete port yönlendirmesi yapmayın.

Ajan kayıtları, anahtar özetleri ve iş sahipliği `data/agents/gateway.sqlite3` içinde tutulur. Düz metin anahtar saklanmaz. Ajan erişimi ana uygulamanın ses veritabanından ayrı yönetilir.
