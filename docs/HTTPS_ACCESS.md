# Yerel HTTPS ve mikrofon

Repo kökünde `scripts/start-lan.ps1 -LanAddress <yerel-IP>` komutunu çalıştırın.
PowerShell 7, HTTPS sertifika işlemleri için gereklidir. Başlatıcı gerekirse
kurulu PowerShell 7'yi bulur ve Windows güvenlik duvarı kuralı için yönetici
onayı ister. IP, bu bilgisayarın özel IPv4 adresi olmalıdır.

LAN adresi `https://<yerel-IP>:8000`, sunucu bilgisayarındaki HTTP adresi
`http://127.0.0.1:8001` olur. İki adres aynı backend ve GPU kuyruğunu kullanır.
LAN modunda aynı ağdaki cihazlar uygulamanın kayıtlarına erişebilir.

## İstemci cihazında güven

1. `https://<yerel-IP>:8000/api/v1/system/local-ca.crt` adresinden açık yerel
   CA sertifikasını indirin. İlk sertifika uyarısı sırasında bu sunucunun sizin
   bilgisayarınız olduğunu kontrol edin.
2. Mac'te sertifikayı Anahtar Zinciri Erişimi'ne ekleyin. “ASYA Local CA” (önceki kurulumlarda “Voice AI Studio Local CA”) için Güven bölümünde SSL güvenini “Her Zaman Güven” olarak ayarlayın.
3. Tarayıcıyı kapatıp açın, HTTPS uygulama adresine gidin ve mikrofon izni verin.

Sertifikalar Git dışında `data/certs` altındadır. Kök CA'nın özel anahtarı
Windows CurrentUser DPAPI ile korunur; indirme API'si yalnızca açık sertifikayı
sunar. Aynı kullanıcı ve CA korunduğu sürece IP değişince yalnızca sunucu
sertifikası yenilenir. İstemci güvenini yeniden kurmak gerekmez.

İki cihaz aynı ağda bulunmalıdır; misafir ağı veya istemci izolasyonu erişimi
engelleyebilir. `-HttpOnly` modu LAN üzerinden mikrofon kullanımı için uygun
değildir. Tekrar başlatırken mevcut sunucuyu kendi terminalinde Ctrl+C ile kapatın.
