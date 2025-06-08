#!/usr/bin/env python3
"""
Türkçe Sesli AI Asistanı - Bileşen Test Scripti
Tüm sistem bileşenlerini test eder
"""

import time
import os
import sys
from datetime import datetime

def test_python_modules():
    """Python modüllerini test et"""
    print("🔄 Python modülleri test ediliyor...")
    start_time = time.time()
    
    try:
        import streamlit
        print("✅ Streamlit - OK")
        
        try:
            import faster_whisper
            print("✅ Faster-Whisper - OK")
        except ImportError:
            print("❌ Faster-Whisper - Eksik")
            return False
        
        try:
            import sounddevice
            print("✅ SoundDevice - OK")
        except ImportError:
            print("❌ SoundDevice - Eksik")
            return False
            
        try:
            import speech_recognition
            print("✅ SpeechRecognition - OK")
        except ImportError:
            print("❌ SpeechRecognition - Eksik")
            return False
        
        import edge_tts
        print("✅ Edge-TTS - OK")
        
        import ollama
        print("✅ Ollama - OK")
        
        import pydub
        print("✅ PyDub - OK")
        
        import requests
        print("✅ Requests - OK")
        
        import sqlite3
        print("✅ SQLite3 - OK")
        
        return True
        
    except ImportError as e:
        print(f"❌ Python modül hatası: {e}")
        return False
    except Exception as e:
        print(f"❌ Beklenmeyen hata: {e}")
        return False
    finally:
        elapsed = time.time() - start_time
        result = "Başarılı" if 'return True' in str(locals()) else "Başarısız"
        print(f"{'✅' if result == 'Başarılı' else '❌'} Python Modülleri - {result} ({elapsed:.2f}s)")

def test_whisper_stt():
    """Whisper Speech-to-Text test et"""
    print("\n🔄 Faster-Whisper modeli test ediliyor...")
    start_time = time.time()
    
    try:
        from faster_whisper import WhisperModel
        
        # Model yükleme testi (küçük model)
        model = WhisperModel("tiny", device="cpu", compute_type="int8")
        print("✅ Faster-Whisper modeli başarıyla yüklendi")
        
        return True
        
    except Exception as e:
        print(f"❌ Faster-Whisper test hatası: {e}")
        return False
    finally:
        elapsed = time.time() - start_time
        result = "Başarılı" if 'return True' in str(locals()) else "Başarısız"
        print(f"{'✅' if result == 'Başarılı' else '❌'} Faster-Whisper STT - {result} ({elapsed:.2f}s)")

def test_ollama_llm():
    """Ollama LLM bağlantısını test et"""
    print("\n🔄 Ollama bağlantısı test ediliyor...")
    start_time = time.time()
    
    try:
        import ollama
        
        # Ollama servis kontrolü
        response = ollama.list()
        print("✅ Ollama servisi çalışıyor")
        
        # Mevcut modelleri listele
        models = [model['name'] for model in response['models']]
        if models:
            print(f"📋 Mevcut modeller: {', '.join(models)}")
        else:
            print("⚠️ Hiç model bulunamadı")
            
        return True
        
    except Exception as e:
        print(f"❌ Ollama test hatası: {e}")
        return False
    finally:
        elapsed = time.time() - start_time
        result = "Başarılı" if 'return True' in str(locals()) else "Başarısız"
        print(f"{'✅' if result == 'Başarılı' else '❌'} Ollama LLM - {result} ({elapsed:.2f}s)")

def test_edge_tts():
    """Edge-TTS test et"""
    print("\n🔄 TTS sistemi test ediliyor...")
    start_time = time.time()
    
    try:
        import edge_tts
        import asyncio
        import tempfile
        import os
        
        async def test_tts():
            voice = "tr-TR-EmelNeural"
            text = "Merhaba, bu bir test mesajıdır."
            
            communicate = edge_tts.Communicate(text, voice)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                tmp_path = tmp_file.name
                
            await communicate.save(tmp_path)
            
            # Dosya oluşturuldu mu kontrol et
            if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 0:
                os.unlink(tmp_path)  # Test dosyasını temizle
                return True
            return False
        
        # Async fonksiyonu çalıştır
        result = asyncio.run(test_tts())
        
        if result:
            print("✅ TTS sistemi çalışıyor")
            return True
        else:
            print("❌ TTS test başarısız")
            return False
            
    except Exception as e:
        print(f"❌ TTS test hatası: {e}")
        return False
    finally:
        elapsed = time.time() - start_time
        result = "Başarılı" if 'return True' in str(locals()) else "Başarısız"
        print(f"{'✅' if result == 'Başarılı' else '❌'} Edge-TTS - {result} ({elapsed:.2f}s)")

def test_microphone():
    """Mikrofon erişimini test et"""
    print("\n🔄 Mikrofon erişimi test ediliyor...")
    start_time = time.time()
    
    try:
        import sounddevice as sd
        
        # Mevcut ses cihazlarını listele
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        
        if input_devices:
            print(f"✅ {len(input_devices)} mikrofon cihazı bulundu")
            
            # İlk mikrofonu test et
            default_device = input_devices[0]
            print(f"📱 Test cihazı: {default_device['name']}")
            
            # Kısa ses kaydı testi
            duration = 0.1  # 100ms test
            sample_rate = 16000
            
            recording = sd.rec(
                int(duration * sample_rate), 
                samplerate=sample_rate, 
                channels=1,
                dtype='float32'
            )
            sd.wait()  # Kaydın bitmesini bekle
            
            print("✅ Mikrofon kaydı başarılı")
            return True
        else:
            print("❌ Hiç mikrofon bulunamadı")
            return False
            
    except Exception as e:
        print(f"❌ Mikrofon test hatası: {e}")
        return False
    finally:
        elapsed = time.time() - start_time
        result = "Başarılı" if 'return True' in str(locals()) else "Başarısız"
        print(f"{'✅' if result == 'Başarılı' else '❌'} Mikrofon - {result} ({elapsed:.2f}s)")

def test_database():
    """Veritabanı sistemini test et"""
    print("\n🔄 Veritabanı sistemi test ediliyor...")
    start_time = time.time()
    
    try:
        from memory_manager import MemoryManager
        
        # Memory manager oluştur
        db = MemoryManager()
        print("✅ Veritabanı başarıyla başlatıldı")
        
        # Test verisi ekle
        session_id = "test_session"
        user_msg = "Merhaba, nasılsın?"
        ai_msg = "Merhaba! Ben iyiyim, teşekkür ederim."
        
        success = db.save_conversation(user_msg, ai_msg, session_id)
        if success:
            print("✅ Konuşma kaydetme çalışıyor")
        else:
            print("❌ Konuşma kaydetme başarısız")
            return False
        
        # Konuşmaları oku
        history = db.get_recent_conversations(limit=5, session_id=session_id)
        if history and len(history) > 0:
            print("✅ Konuşma okuma çalışıyor")
        else:
            print("❌ Konuşma okuma başarısız")
            return False
        
        # Hafızayı temizle
        db.clear_memory(session_id)
        print(f"✅ {session_id} oturumu hafızası temizlendi")
        
        print("✅ Veritabanı sistemi çalışıyor")
        return True
        
    except Exception as e:
        print(f"❌ Veritabanı test hatası: {e}")
        return False
    finally:
        elapsed = time.time() - start_time
        result = "Başarılı" if 'return True' in str(locals()) else "Başarısız"
        print(f"{'✅' if result == 'Başarılı' else '❌'} Veritabanı - {result} ({elapsed:.2f}s)")

def main():
    """Ana test fonksiyonu"""
    print("🗣️ Türkçe Sesli AI Asistanı - Sistem Testi")
    print("=" * 50)
    print(f"📅 Test Zamanı: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n")
    
    # Test fonksiyonları ve sonuçları
    tests = [
        ("Python Modülleri", test_python_modules),
        ("Faster-Whisper STT", test_whisper_stt),
        ("Ollama LLM", test_ollama_llm),
        ("Edge-TTS", test_edge_tts),
        ("Mikrofon", test_microphone),
        ("Veritabanı", test_database)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print("=" * 20, test_name, "=" * 20)
        print()
        
        try:
            result = test_func()
            results.append((test_name, result, "BAŞARILI" if result else "BAŞARISIZ"))
        except Exception as e:
            print(f"❌ {test_name} - Kritik hata: {e}")
            results.append((test_name, False, "BAŞARISIZ"))
        
        print()
    
    # Sonuçları özetle
    print("=" * 50)
    print("📊 TEST SONUÇLARI")
    print("=" * 50)
    
    successful = 0
    total = len(results)
    
    for test_name, success, status in results:
        icon = "✅" if success else "❌"
        print(f"{test_name:<20} | {icon} {status:<10}")
        if success:
            successful += 1
    
    print("-" * 50)
    print(f"Toplam: {total} | Başarılı: {successful} | Başarısız: {total - successful}")
    
    if successful == total:
        print("\n🎉 TÜM TESTLER BAŞARILI!")
        print("✅ Sistem kullanıma hazır")
        return True
    else:
        failed = total - successful
        print(f"\n⚠️ {failed} TEST BAŞARISIZ")
        print("❌ Lütfen hataları giderin")
        return False

if __name__ == "__main__":
    main() 