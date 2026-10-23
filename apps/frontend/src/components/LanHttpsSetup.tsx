import type { SystemStatus } from "../types";

export default function LanHttpsSetup({
  network,
}: {
  network: SystemStatus["network"];
}) {
  if (!network?.https_url || window.isSecureContext) return null;
  return (
    <section className="panel padded" aria-label="Yerel HTTPS kurulumu">
      <h2>Diğer cihazda mikrofonu açın</h2>
      <p>Yerel sertifikayı bir kez yükleyin, sonra HTTPS adresini açın.</p>
      <ol>
        <li>
          <a
            href="/api/v1/system/local-ca.crt"
            download="ASYA-Local-CA.crt"
          >
            Yerel sertifikayı indir
          </a>
          .
        </li>
        <li>
          Mac: dosyayı Anahtar Zinciri Erişimi’nde açın. “ASYA Local CA” (önceki kurulumlarda “Voice AI Studio Local CA”) sertifikasına çift tıklayıp Güven → SSL için “Her Zaman Güven”
          seçin ve değişikliği kaydedin.
        </li>
        <li>
          <a href={network.https_url}>HTTPS ile aç: {network.https_url}</a>.
          Mikrofon düğmesine basıp tarayıcı iznini verin.
        </li>
      </ol>
    </section>
  );
}
