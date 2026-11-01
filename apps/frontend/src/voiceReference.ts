export const MAX_REFERENCE_BYTES = 200 * 1024 * 1024;
export const MAX_REFERENCE_SECONDS = 300;

export function referenceFileError(
  size: number,
  duration?: number,
): string | null {
  if (size > MAX_REFERENCE_BYTES) return "Dosya en fazla 200 MB olabilir.";
  if (
    duration !== undefined &&
    (!Number.isFinite(duration) ||
      duration < 0.25 ||
      duration > MAX_REFERENCE_SECONDS)
  )
    return "Kayıt 0,25 saniye ile 5 dakika arasında olmalıdır.";
  return null;
}

export function referenceClipError(
  start: number,
  end: number,
  duration: number,
): string | null {
  if (
    !Number.isFinite(start) ||
    !Number.isFinite(end) ||
    start < 0 ||
    end > duration ||
    end - start < 0.25
  )
    return "Klip kayıt sınırları içinde ve en az 0,25 saniye uzunluğunda olmalıdır. 6–10 saniye önerilir.";
  return null;
}

export function readAudioDuration(file: File): Promise<number> {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const audio = new Audio();
    const cleanup = () => {
      clearTimeout(timer);
      audio.onloadedmetadata = null;
      audio.onerror = null;
      audio.removeAttribute("src");
      URL.revokeObjectURL(url);
    };
    const failed = () => {
      cleanup();
      reject(
        new Error("Dosyanın süresi okunamadı. WAV veya MP3 dosyası seçin."),
      );
    };
    const timer = window.setTimeout(failed, 15000);
    audio.preload = "metadata";
    audio.onloadedmetadata = () => {
      const duration = audio.duration;
      cleanup();
      resolve(duration);
    };
    audio.onerror = failed;
    audio.src = url;
  });
}
