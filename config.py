# Yapılandırma Dosyası - Türkçe Sesli AI Asistanı

import os

class Config:
    """Uygulama ayarları sınıfı"""
    
    def __init__(self):
        # Ses işleme ayarları
        self.WHISPER_MODEL = "base"  # faster-whisper için
        self.WHISPER_LANGUAGE = "tr"
        self.SAMPLE_RATE = 16000
        self.CHUNK_SIZE = 1024
        self.MAX_AUDIO_DURATION = 30  # saniye
        
        # LLM ayarları
        self.OLLAMA_MODEL = "mistral:7b"
        self.OLLAMA_HOST = "http://localhost:11434"
        self.OLLAMA_BASE_URL = "http://localhost:11434"  # LLM processor için
        self.MAX_TOKENS = 2000
        self.TEMPERATURE = 0.7
        
        # TTS ayarları
        self.TTS_VOICE = "tr-TR-EmelNeural"
        self.TTS_RATE = "+0%"
        self.TTS_VOLUME = "+0%"
        
        # Veritabanı ayarları
        self.DATABASE_PATH = "conversations.db"
        self.MAX_HISTORY_LENGTH = 10
        
        # UI ayarları
        self.APP_TITLE = "ASYA - Akıllı Sesli Yapay Zeka Asistanı"
        self.PAGE_ICON = "🤖"
        self.LAYOUT = "wide"
        
        # Sistem ayarları
        self.DEBUG = False
        self.LOG_LEVEL = "INFO"
        
        # Mevcut sesler listesi
        self.AVAILABLE_VOICES = [
            "tr-TR-EmelNeural",
            "tr-TR-AhmetNeural", 
            "tr-TR-RıfatNeural",
            "tr-TR-CansuNeural",
            "tr-TR-KartalNeural"
        ]
        
        # Whisper modelleri
        self.AVAILABLE_WHISPER_MODELS = [
            "tiny",
            "base", 
            "small",
            "medium",
            "large",
            "turbo"
        ]

# Eski format uyumluluğu için (mevcut dosyalar için)
WHISPER_MODEL = "base"
WHISPER_LANGUAGE = "tr"
SAMPLE_RATE = 16000
CHUNK_SIZE = 1024
MAX_AUDIO_DURATION = 30

OLLAMA_MODEL = "mistral:7b" 
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_BASE_URL = "http://localhost:11434"  # LLM processor için
MAX_TOKENS = 2000
TEMPERATURE = 0.7

TTS_VOICE = "tr-TR-EmelNeural"
TTS_RATE = "+0%"
TTS_VOLUME = "+0%"

DATABASE_PATH = "conversations.db"
MAX_HISTORY_LENGTH = 10

APP_TITLE = "ASYA - Akıllı Sesli Yapay Zeka Asistanı"
PAGE_ICON = "🤖"
LAYOUT = "wide"

DEBUG = False
LOG_LEVEL = "INFO"

# Whisper Yapılandırması  
WHISPER_MODEL = "turbo"  # En hızlı ve Türkçe destekli model

# TTS Yapılandırması
TTS_RATE = "+0%"  # Konuşma hızı
TTS_PITCH = "+0Hz"  # Ses tonu

# Veritabanı Yapılandırması
DATABASE_PATH = "ai_assistant_memory.db"

# UI Yapılandırması
APP_TITLE = "🗣️ Türkçe AI Asistanı"
APP_SUBTITLE = "Sesli Konuşabilen Akıllı Asistan"

# Sistem Mesajı
SYSTEM_PROMPT = """Sen Türkçe konuşan yardımcı bir yapay zeka asistanısın. 
Adın ASYA (Akıllı Sesli Yapay zeka Asistanı). 
Kullanıcıyla dostane ve samimi bir şekilde konuş. 
Türkçe dilbilgisi kurallarına uy ve açık, anlaşılır cevaplar ver.
Konuşmaları hatırla ve bağlamsal cevaplar ver.
Kısa ve öz cevaplar vermeye çalış."""

# Maksimum dosya boyutları
MAX_MEMORY_ENTRIES = 100  # veritabanında tutulacak maksimum konuşma 