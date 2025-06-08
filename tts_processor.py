import edge_tts
import asyncio
import tempfile
import io
import wave
from typing import Optional
from config import TTS_VOICE, TTS_RATE, TTS_PITCH

class TTSProcessor:
    """Edge-TTS kullanarak metni sese çevirme sınıfı"""
    
    def __init__(self):
        self.voice = TTS_VOICE
        self.rate = TTS_RATE
        self.pitch = TTS_PITCH
        print(f"🔊 TTS sistemi başlatıldı - Ses: {self.voice}")
    
    async def _text_to_speech_async(self, text: str) -> bytes:
        """Async olarak metni sese çevir - MP3 formatında"""
        try:
            # TTS oluştur
            communicate = edge_tts.Communicate(
                text=text, 
                voice=self.voice,
                rate=self.rate,
                pitch=self.pitch
            )
            
            # Ses verilerini topla
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            
            return audio_data
            
        except Exception as e:
            print(f"❌ TTS hatası: {e}")
            return b""
    
    def text_to_speech(self, text: str) -> Optional[bytes]:
        """Metni sese çevir (sync wrapper) - MP3 formatında döndürür"""
        if not text.strip():
            return None
            
        try:
            print(f"🔊 Ses oluşturuluyor: {text[:50]}...")
            
            # Async fonksiyonu çalıştır
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            audio_data = loop.run_until_complete(self._text_to_speech_async(text))
            loop.close()
            
            if audio_data:
                print("✅ Ses başarıyla oluşturuldu")
                return audio_data
            else:
                print("⚠️ Ses oluşturulamadı")
                return None
                
        except Exception as e:
            print(f"❌ TTS işlemi hatası: {e}")
            return None
    
    def save_audio_to_file(self, audio_data: bytes, filename: str) -> bool:
        """Ses verilerini dosyaya kaydet"""
        try:
            with open(filename, 'wb') as f:
                f.write(audio_data)
            print(f"✅ Ses dosyası kaydedildi: {filename}")
            return True
        except Exception as e:
            print(f"❌ Ses kaydetme hatası: {e}")
            return False
    
    def get_audio_stream(self, text: str) -> Optional[io.BytesIO]:
        """Ses verilerini BytesIO stream olarak döndür"""
        audio_data = self.text_to_speech(text)
        if audio_data:
            return io.BytesIO(audio_data)
        return None
    
    async def get_available_voices(self) -> list:
        """Kullanılabilir Türkçe sesleri listele"""
        try:
            voices = await edge_tts.list_voices()
            turkish_voices = [
                voice for voice in voices 
                if voice['Locale'].startswith('tr-TR')
            ]
            return turkish_voices
        except Exception as e:
            print(f"❌ Ses listesi alınamadı: {e}")
            return []
    
    def change_voice(self, new_voice: str) -> bool:
        """Ses tipini değiştir"""
        try:
            self.voice = new_voice
            print(f"✅ Ses değiştirildi: {new_voice}")
            return True
        except Exception as e:
            print(f"❌ Ses değiştirme hatası: {e}")
            return False
    
    def adjust_speech_rate(self, rate: str) -> bool:
        """Konuşma hızını ayarla (örn: +20%, -10%, +0%)"""
        try:
            self.rate = rate
            print(f"✅ Konuşma hızı ayarlandı: {rate}")
            return True
        except Exception as e:
            print(f"❌ Hız ayarlama hatası: {e}")
            return False
    
    def adjust_pitch(self, pitch: str) -> bool:
        """Ses tonunu ayarla (örn: +5Hz, -10Hz, +0Hz)"""
        try:
            self.pitch = pitch
            print(f"✅ Ses tonu ayarlandı: {pitch}")
            return True
        except Exception as e:
            print(f"❌ Ton ayarlama hatası: {e}")
            return False
    
    def create_ssml_text(self, text: str, emotion: str = "neutral") -> str:
        """SSML formatında metin oluştur (duygu desteği için)"""
        ssml_text = f"""
        <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="tr-TR">
            <voice name="{self.voice}">
                <prosody rate="{self.rate}" pitch="{self.pitch}">
                    {text}
                </prosody>
            </voice>
        </speak>
        """
        return ssml_text.strip()
    
    def get_voice_info(self) -> dict:
        """Mevcut ses ayarları hakkında bilgi döndür"""
        return {
            "voice": self.voice,
            "rate": self.rate,
            "pitch": self.pitch,
            "language": "tr-TR"
        } 