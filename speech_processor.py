import logging
import numpy as np
import sounddevice as sd
import speech_recognition as sr
from faster_whisper import WhisperModel
import tempfile
import wave
import threading
import time
from config import Config

class SpeechProcessor:
    def __init__(self):
        """Ses işleme bileşenini başlatır"""
        self.config = Config()
        self.is_recording = False
        self.audio_data = []
        self.sample_rate = 16000
        self.channels = 1
        
        # Faster Whisper modelini yükle
        try:
            self.whisper_model = WhisperModel(
                self.config.WHISPER_MODEL, 
                device="cpu",
                compute_type="int8"
            )
            logging.info(f"Whisper modeli yüklendi: {self.config.WHISPER_MODEL}")
        except Exception as e:
            logging.error(f"Whisper modeli yüklenemedi: {e}")
            self.whisper_model = None
        
        # SpeechRecognition alternatif olarak (PyAudio olmadan)
        self.recognizer = sr.Recognizer()
        
        # Ses cihazlarını kontrol et
        try:
            devices = sd.query_devices()
            logging.info(f"Kullanılabilir ses cihazları: {len(devices)}")
        except Exception as e:
            logging.warning(f"Ses cihazları kontrol edilemedi: {e}")

    def start_recording(self):
        """Ses kaydını başlatır"""
        if self.is_recording:
            return False
        
        self.is_recording = True
        self.audio_data = []
        
        def audio_callback(indata, frames, time, status):
            if status:
                logging.warning(f"Ses kaydı durumu: {status}")
            if self.is_recording:
                self.audio_data.extend(indata[:, 0])
        
        try:
            self.stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=audio_callback,
                dtype=np.float32
            )
            self.stream.start()
            logging.info("Ses kaydı başlatıldı")
            return True
        except Exception as e:
            logging.error(f"Ses kaydı başlatılamadı: {e}")
            self.is_recording = False
            return False

    def stop_recording(self):
        """Ses kaydını durdurur ve transkripsyon yapar"""
        if not self.is_recording:
            return None
        
        self.is_recording = False
        
        try:
            self.stream.stop()
            self.stream.close()
            
            if not self.audio_data:
                logging.warning("Kayıtlı ses verisi bulunamadı")
                return None
            
            # NumPy array'e dönüştür ve normalize et
            audio_array = np.array(self.audio_data, dtype=np.float32)
            
            logging.info(f"Ses kaydı durduruldu. Kayıt süresi: {len(audio_array)/self.sample_rate:.2f} saniye")
            
            # Direk transkripsyon yap
            transcript = self.transcribe_audio(audio_array)
            return transcript
            
        except Exception as e:
            logging.error(f"Ses kaydı durdurulamadı: {e}")
            return None

    def transcribe_audio(self, audio_data=None, audio_file=None):
        """Ses verisini metne dönüştürür"""
        try:
            if self.whisper_model and audio_data is not None:
                # Faster Whisper ile transkripsyon
                return self._transcribe_with_faster_whisper(audio_data)
            elif audio_file:
                # Dosyadan transkripsyon
                return self._transcribe_file_with_speech_recognition(audio_file)
            else:
                logging.error("Ne ses verisi ne de dosya sağlandı")
                return "Transkripsyon için gerekli veri bulunamadı."
                
        except Exception as e:
            logging.error(f"Transkripsyon hatası: {e}")
            return f"Transkripsyon hatası: {str(e)}"

    def _transcribe_with_faster_whisper(self, audio_data):
        """Faster Whisper ile transkripsyon"""
        try:
            # Geçici WAV dosyası oluştur
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                # WAV dosyası yaz
                with wave.open(tmp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(self.channels)
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(self.sample_rate)
                    
                    # Float32'den int16'ya dönüştür
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                    wav_file.writeframes(audio_int16.tobytes())
                
                # Whisper ile transkripsyon
                segments, info = self.whisper_model.transcribe(
                    tmp_file.name,
                    language="tr",
                    beam_size=5,
                    best_of=5,
                    temperature=0.0,
                    condition_on_previous_text=False
                )
                
                # Metni birleştir
                transcript = " ".join(segment.text for segment in segments)
                
                logging.info(f"Whisper transkripsyonu: {transcript}")
                return transcript.strip()
                
        except Exception as e:
            logging.error(f"Faster Whisper transkripsyon hatası: {e}")
            # Geri dönüş olarak SpeechRecognition kullan
            return self._transcribe_with_speech_recognition(audio_data)

    def _transcribe_with_speech_recognition(self, audio_data):
        """SpeechRecognition ile transkripsyon"""
        try:
            # Geçici WAV dosyası oluştur
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                with wave.open(tmp_file.name, 'wb') as wav_file:
                    wav_file.setnchannels(self.channels)
                    wav_file.setsampwidth(2)
                    wav_file.setframerate(self.sample_rate)
                    
                    audio_int16 = (audio_data * 32767).astype(np.int16)
                    wav_file.writeframes(audio_int16.tobytes())
                
                # SpeechRecognition ile dosyayı oku
                with sr.AudioFile(tmp_file.name) as source:
                    audio = self.recognizer.record(source)
                
                # Google Speech Recognition ile transkripsyon
                transcript = self.recognizer.recognize_google(audio, language='tr-TR')
                logging.info(f"Google Speech transkripsyonu: {transcript}")
                return transcript
                
        except sr.UnknownValueError:
            return "Ses anlaşılamadı. Lütfen tekrar deneyin."
        except sr.RequestError as e:
            logging.error(f"Google Speech Recognition hatası: {e}")
            return "İnternet bağlantısı sorunu. Lütfen bağlantınızı kontrol edin."
        except Exception as e:
            logging.error(f"SpeechRecognition hatası: {e}")
            return "Ses tanıma hatası oluştu."

    def _transcribe_file_with_speech_recognition(self, audio_file):
        """Dosyadan SpeechRecognition ile transkripsyon"""
        try:
            with sr.AudioFile(audio_file) as source:
                audio = self.recognizer.record(source)
            
            transcript = self.recognizer.recognize_google(audio, language='tr-TR')
            logging.info(f"Dosya transkripsyonu: {transcript}")
            return transcript
            
        except sr.UnknownValueError:
            return "Ses dosyası anlaşılamadı."
        except sr.RequestError as e:
            logging.error(f"Google Speech Recognition hatası: {e}")
            return "İnternet bağlantısı sorunu."
        except Exception as e:
            logging.error(f"Dosya transkripsyon hatası: {e}")
            return "Dosya işleme hatası."

    def get_available_microphones(self):
        """Mevcut mikrofonları listeler"""
        try:
            devices = sd.query_devices()
            microphones = []
            for i, device in enumerate(devices):
                if device['max_input_channels'] > 0:
                    microphones.append({
                        'index': i,
                        'name': device['name'],
                        'channels': device['max_input_channels']
                    })
            return microphones
        except Exception as e:
            logging.error(f"Mikrofon listeleme hatası: {e}")
            return []

    def is_model_loaded(self):
        """Whisper modelinin yüklenip yüklenmediğini kontrol eder"""
        return self.whisper_model is not None

    def test_microphone(self):
        """Mikrofon test fonksiyonu"""
        try:
            # SoundDevice ile mikrofon testi
            test_duration = 2  # 2 saniye test
            test_data = sd.rec(int(self.sample_rate * test_duration), 
                             samplerate=self.sample_rate, 
                             channels=self.channels,
                             dtype=np.float32)
            sd.wait()  # Kaydın tamamlanmasını bekle
            
            # Ses seviyesini kontrol et
            volume = np.sqrt(np.mean(test_data**2))
            
            if volume > 0.001:  # Minimum ses seviyesi
                return f"Mikrofon çalışıyor! Ses seviyesi: {volume:.4f}"
            else:
                return "Mikrofon çalışıyor ancak ses algılanamadı."
                
        except Exception as e:
            logging.error(f"Mikrofon test hatası: {e}")
            return f"Mikrofon test hatası: {e}"

    def transcribe_audio_file(self, uploaded_file):
        """Yüklenen ses dosyasını transkripsyon yapar"""
        try:
            # Geçici dosya oluştur
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(uploaded_file.read())
                tmp_file_path = tmp_file.name
            
            # Transkripsyon yap
            transcript = self._transcribe_file_with_speech_recognition(tmp_file_path)
            
            # Geçici dosyayı sil
            import os
            os.unlink(tmp_file_path)
            
            return transcript
            
        except Exception as e:
            logging.error(f"Dosya transkripsyon hatası: {e}")
            return f"Dosya işleme hatası: {str(e)}"

    def is_microphone_available(self):
        """Mikrofonun kullanılabilir olup olmadığını kontrol eder"""
        try:
            devices = sd.query_devices()
            # Giriş kanalı olan cihaz var mı kontrol et
            for device in devices:
                if device['max_input_channels'] > 0:
                    return True
            return False
        except Exception as e:
            logging.error(f"Mikrofon kontrol hatası: {e}")
            return False 