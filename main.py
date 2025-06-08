import streamlit as st
import tempfile
import os
import time
import io
import base64
from datetime import datetime
import threading

# Yerel modüllerimizi import et
from config import APP_TITLE, APP_SUBTITLE
from memory_manager import MemoryManager
from speech_processor import SpeechProcessor
from tts_processor import TTSProcessor
from llm_processor import LLMProcessor

# Sayfa yapılandırması
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🗣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS stilleri - Modern ChatGPT benzeri tasarım
st.markdown("""
<style>
    /* Ana sayfa ayarları */
    .main > div {
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 0 !important;
        max-width: 100% !important;
    }
    
    /* Header Bölümü */
    .main-header {
        text-align: center;
        padding: 2.5rem 0;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 20px;
        margin-bottom: 2rem;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.3);
        backdrop-filter: blur(10px);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        text-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    
    .main-header p {
        font-size: 1.2rem;
        opacity: 0.9;
        font-weight: 400;
        margin: 0;
    }
    
    /* Hoşgeldin Bölümü */
    .welcome-section {
        background: rgba(255, 255, 255, 0.95);
        border-radius: 20px;
        padding: 2rem;
        margin-bottom: 2rem;
        text-align: center;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        backdrop-filter: blur(10px);
    }
    
    .welcome-section h2 {
        color: #667eea;
        font-size: 1.8rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .welcome-section p {
        color: #555;
        font-size: 1.1rem;
        line-height: 1.6;
        margin-bottom: 0.8rem;
    }
    
    .welcome-features {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
        gap: 1.5rem;
        margin-top: 2rem;
    }
    
    .feature-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 15px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.2);
        transition: transform 0.3s ease;
    }
    
    .feature-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 25px rgba(102, 126, 234, 0.3);
    }
    
    .feature-card h3 {
        font-size: 1.3rem;
        margin-bottom: 0.8rem;
        font-weight: 600;
    }
    
    .feature-card p {
        font-size: 0.95rem;
        opacity: 0.9;
        margin: 0;
    }
    
    /* Chat Container - Modern ChatGPT Tarzı */
    .chat-container {
        height: 450px;
        background: #f8fafc;
        border-radius: 20px;
        border: 1px solid rgba(102, 126, 234, 0.1);
        margin-bottom: 1.5rem;
        overflow: hidden;
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        position: relative;
    }
    
    .chat-messages {
        height: 100%;
        overflow-y: auto;
        padding: 1.5rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }
    
    .chat-messages::-webkit-scrollbar {
        width: 6px;
    }
    
    .chat-messages::-webkit-scrollbar-track {
        background: transparent;
    }
    
    .chat-messages::-webkit-scrollbar-thumb {
        background: rgba(102, 126, 234, 0.3);
        border-radius: 3px;
    }
    
    .chat-messages::-webkit-scrollbar-thumb:hover {
        background: rgba(102, 126, 234, 0.5);
    }
    
    /* Mesaj Balonları */
    .message-bubble {
        max-width: 70%;
        padding: 1rem 1.2rem;
        border-radius: 18px;
        font-size: 0.95rem;
        line-height: 1.5;
        word-wrap: break-word;
        animation: messageSlide 0.3s ease-out;
        position: relative;
    }
    
    @keyframes messageSlide {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
    
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        align-self: flex-end;
        border-bottom-right-radius: 6px;
        box-shadow: 0 2px 12px rgba(102, 126, 234, 0.3);
    }
    
    .ai-message {
        background: white;
        color: #333;
        align-self: flex-start;
        border: 1px solid rgba(102, 126, 234, 0.1);
        border-bottom-left-radius: 6px;
        box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    }
    
    .ai-message .ai-label {
        color: #667eea;
        font-weight: 600;
        font-size: 0.85rem;
        margin-bottom: 0.3rem;
        display: block;
    }
    
    .message-time {
        font-size: 0.75rem;
        opacity: 0.6;
        margin-top: 0.5rem;
        text-align: right;
    }
    
    /* Hoşgeldin Mesajı (Chat Boşken) */
    .empty-chat-welcome {
        height: 100%;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
    }
    
    .welcome-card {
        text-align: center;
        background: white;
        padding: 2.5rem;
        border-radius: 20px;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        max-width: 500px;
    }
    
    .welcome-card h3 {
        color: #667eea;
        font-size: 1.8rem;
        margin-bottom: 1rem;
        font-weight: 600;
    }
    
    .welcome-card p {
        color: #666;
        font-size: 1.1rem;
        margin-bottom: 1.5rem;
        line-height: 1.5;
    }
    
    .welcome-tips {
        display: grid;
        gap: 1rem;
        margin-top: 1.5rem;
    }
    
    .tip-item {
        background: rgba(102, 126, 234, 0.05);
        padding: 1rem;
        border-radius: 12px;
        border-left: 3px solid #667eea;
        text-align: left;
    }
    
    .tip-item strong {
        color: #667eea;
        font-weight: 600;
    }
    
    /* Input Alanı - Modern Tasarım */
    .input-section {
        background: white;
        border-radius: 20px;
        padding: 1.5rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 4px 20px rgba(0,0,0,0.05);
        margin-bottom: 1rem;
    }
    
    .status-bar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 1rem;
        padding-bottom: 0.8rem;
        border-bottom: 1px solid rgba(102, 126, 234, 0.1);
    }
    
    .status-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        font-size: 0.9rem;
        color: #666;
    }
    
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
    }
    
    .status-online { background: #4CAF50; }
    .status-recording { 
        background: #f44336; 
        animation: pulse 1s infinite;
    }
    .status-offline { background: #9E9E9E; }
    
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.3; }
    }
    
    .input-row {
        display: flex;
        gap: 0.8rem;
        align-items: flex-end;
    }
    
    .text-input-wrapper {
        flex: 1;
    }
    
    .voice-button {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        border: none;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        font-size: 1.2rem;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 2px 12px rgba(102, 126, 234, 0.3);
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .voice-button:hover {
        transform: scale(1.05);
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4);
    }
    
    .voice-button:active {
        transform: scale(0.95);
    }
    
    .voice-button.recording {
        background: linear-gradient(135deg, #f44336 0%, #e91e63 100%);
        animation: pulse 1s infinite;
    }
    
    /* Streamlit Input Öğeleri için Gelişmiş Özelleştirmeler */
    .stTextInput > div > div > input {
        border-radius: 15px !important;
        border: 2px solid rgba(102, 126, 234, 0.2) !important;
        padding: 1rem 1.2rem !important;
        font-size: 1rem !important;
        color: #333 !important;
        background: #f8fafc !important;
        transition: all 0.3s ease !important;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif !important;
        font-weight: 400 !important;
        line-height: 1.5 !important;
    }
    
    .stTextInput > div > div > input:focus {
        border-color: #667eea !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
        background: white !important;
        color: #333 !important;
        outline: none !important;
    }
    
    .stTextInput > div > div > input::placeholder {
        color: #9ca3af !important;
        font-weight: 400 !important;
    }
    
    /* Butonlar için gelişmiş stil */
    .stButton > button {
        border-radius: 15px !important;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        border: none !important;
        color: white !important;
        font-weight: 600 !important;
        padding: 0.8rem 1.5rem !important;
        transition: all 0.3s ease !important;
        box-shadow: 0 2px 12px rgba(102, 126, 234, 0.3) !important;
        font-size: 0.95rem !important;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px) !important;
        box-shadow: 0 4px 20px rgba(102, 126, 234, 0.4) !important;
        background: linear-gradient(135deg, #5a67d8 0%, #6b46c1 100%) !important;
    }
    
    .stButton > button:active {
        transform: translateY(0px) !important;
        box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3) !important;
    }
    
    .stButton > button:focus {
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.2) !important;
    }
    
    /* Özel buton stilleri */
    div[data-testid="column"]:nth-child(2) button,
    div[data-testid="column"]:nth-child(3) button {
        width: 50px !important;
        height: 50px !important;
        border-radius: 50% !important;
        padding: 0 !important;
        min-height: 50px !important;
        font-size: 1.2rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        border: none !important;
        transition: all 0.3s ease !important;
    }
    
    /* Hoparlör butonu */
    div[data-testid="column"]:nth-child(2) button {
        background: linear-gradient(135deg, #4CAF50 0%, #45a049 100%) !important;
        box-shadow: 0 3px 15px rgba(76, 175, 80, 0.3) !important;
    }
    
    div[data-testid="column"]:nth-child(2) button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 5px 20px rgba(76, 175, 80, 0.4) !important;
    }
    
    /* Mikrofon butonu */
    div[data-testid="column"]:nth-child(3) button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        box-shadow: 0 3px 15px rgba(102, 126, 234, 0.3) !important;
    }
    
    div[data-testid="column"]:nth-child(3) button:hover {
        transform: scale(1.05) !important;
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4) !important;
    }
    
    /* Kayıt durumunda mikrofon butonu */
    .recording-button {
        background: linear-gradient(135deg, #f44336 0%, #e91e63 100%) !important;
        box-shadow: 0 3px 15px rgba(244, 67, 54, 0.3) !important;
        animation: pulse 1s infinite !important;
    }
    
    /* Modern input container */
    .modern-input-container {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
        border-radius: 25px;
        padding: 1.5rem;
        margin: 1rem 0;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.1);
        backdrop-filter: blur(10px);
    }
    
    /* Typing Indicator */
    .typing-indicator {
        display: flex;
        align-items: center;
        gap: 0.5rem;
        padding: 1rem 1.2rem;
        background: white;
        border-radius: 18px;
        border-bottom-left-radius: 6px;
        border: 1px solid rgba(102, 126, 234, 0.1);
        box-shadow: 0 2px 12px rgba(0,0,0,0.1);
        margin: 1rem 0;
        max-width: 150px;
        color: #667eea;
        font-style: italic;
    }
    
    .typing-dots {
        display: flex;
        gap: 2px;
    }
    
    .typing-dot {
        width: 6px;
        height: 6px;
        background: #667eea;
        border-radius: 50%;
        animation: typingDot 1.4s infinite;
    }
    
    .typing-dot:nth-child(2) {
        animation-delay: 0.2s;
    }
    
    .typing-dot:nth-child(3) {
        animation-delay: 0.4s;
    }
    
    @keyframes typingDot {
        0%, 60%, 100% { transform: initial; }
        30% { transform: translateY(-8px); }
    }
    
    /* Responsive Tasarım */
    @media (max-width: 768px) {
        .main-header h1 {
            font-size: 2rem;
        }
        
        .main-header p {
            font-size: 1rem;
        }
        
        .welcome-features {
            grid-template-columns: 1fr;
        }
        
        .message-bubble {
            max-width: 85%;
        }
        
        .chat-container {
            height: 350px;
        }
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Session state'i başlat"""
    if 'initialized' not in st.session_state:
        st.session_state.initialized = True
        st.session_state.memory_manager = None
        st.session_state.speech_processor = None
        st.session_state.tts_processor = None
        st.session_state.llm_processor = None
        st.session_state.is_recording = False
        st.session_state.conversation_history = []
        st.session_state.system_ready = False
        st.session_state.current_messages = []  # Mevcut oturumdaki mesajlar
        st.session_state.voice_enabled = True  # Sesli yanıt açık/kapalı
        st.session_state.audio_html = None  # Ses için HTML
        st.session_state.speech_rate = 0  # Konuşma hızı ayarı

def load_components():
    """Sistem bileşenlerini yükle"""
    if not st.session_state.system_ready:
        with st.spinner("🚀 Sistem başlatılıyor..."):
            try:
                # Bileşenleri başlat
                st.session_state.memory_manager = MemoryManager()
                st.session_state.speech_processor = SpeechProcessor()
                st.session_state.tts_processor = TTSProcessor()
                st.session_state.llm_processor = LLMProcessor()
                
                # Sistem hazır
                st.session_state.system_ready = True
                st.success("✅ Sistem başarıyla başlatıldı!")
                
            except Exception as e:
                st.error(f"❌ Sistem başlatılamadı: {e}")
                return False
    
    return st.session_state.system_ready

def display_header():
    """Ana başlığı göster"""
    st.markdown(f"""
    <div class="main-header">
        <h1>{APP_TITLE}</h1>
        <p>{APP_SUBTITLE}</p>
    </div>
    """, unsafe_allow_html=True)

def display_welcome_section():
    """Hoşgeldin bölümünü göster"""
    st.markdown("""
    <div class="welcome-section">
        <h2>👋 Hoşgeldiniz!</h2>
        <p>Ben ASYA, size yardımcı olmak için buradayım. Türkçe konuşabilen yapay zeka asistanınızım.</p>
        <p>Benimle hem yazarak hem de konuşarak iletişim kurabilirsiniz.</p>
        
        <div class="welcome-features">
            <div class="feature-card">
                <h3>💬 Metin Chat</h3>
                <p>Sorularınızı yazarak sorabilir, hızlı cevaplar alabilirsiniz</p>
            </div>
            <div class="feature-card">
                <h3>🎤 Sesli Konuşma</h3>
                <p>Mikrofon butonuna basarak benimle konuşabilirsiniz</p>
            </div>
            <div class="feature-card">
                <h3>🧠 Akıllı Hafıza</h3>
                <p>Konuşmalarımızı hatırlayarak bağlamsal cevaplar veririm</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def check_system_status():
    """Sistem durumunu kontrol et ve göster"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        if st.session_state.speech_processor and st.session_state.speech_processor.is_model_loaded():
            st.markdown('<div class="status-box status-success">🎙️ Whisper Hazır</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-box status-error">❌ Whisper Hatası</div>', unsafe_allow_html=True)
    
    with col2:
        if st.session_state.llm_processor and st.session_state.llm_processor.is_model_ready():
            st.markdown('<div class="status-box status-success">🤖 LLM Hazır</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-box status-error">❌ LLM Hatası</div>', unsafe_allow_html=True)
    
    with col3:
        if st.session_state.tts_processor:
            st.markdown('<div class="status-box status-success">🔊 TTS Hazır</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-box status-error">❌ TTS Hatası</div>', unsafe_allow_html=True)
    
    with col4:
        if st.session_state.memory_manager:
            st.markdown('<div class="status-box status-success">💾 Hafıza Hazır</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="status-box status-error">❌ Hafıza Hatası</div>', unsafe_allow_html=True)

def handle_voice_interaction():
    """Sesli etkileşimi yönet"""
    st.subheader("🎙️ Sesli Konuşma")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if not st.session_state.is_recording:
            if st.button("🎤 Kayıt Başlat", key="start_record", help="Konuşmak için tıklayın"):
                if st.session_state.speech_processor.start_recording():
                    st.session_state.is_recording = True
                    st.rerun()
                else:
                    st.error("❌ Kayıt başlatılamadı!")
        else:
            if st.button("⏹️ Kayıt Durdur", key="stop_record", help="Kaydı bitirmek için tıklayın"):
                with st.spinner("🔄 Ses işleniyor..."):
                    transcribed_text = st.session_state.speech_processor.stop_recording()
                    st.session_state.is_recording = False
                    
                    if transcribed_text:
                        # Kullanıcı mesajını işle
                        process_user_message(transcribed_text)
                    else:
                        st.warning("⚠️ Ses algılanamadı, lütfen tekrar deneyin.")
                
                st.rerun()

def handle_unified_interaction():
    """Birleşik ses ve metin etkileşimi"""
    st.subheader("🗣️ Konuşma")
    
    # Kayıt durumu kontrolü
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if not st.session_state.is_recording:
            if st.button("🎤 Kayıt Başlat", key="start_record", help="Konuşmak için tıklayın"):
                if st.session_state.speech_processor.start_recording():
                    st.session_state.is_recording = True
                    st.rerun()
                else:
                    st.error("❌ Kayıt başlatılamadı!")
        else:
            if st.button("⏹️ Kayıt Durdur", key="stop_record", help="Kaydı bitirmek için tıklayın"):
                with st.spinner("🔄 Ses işleniyor..."):
                    transcribed_text = st.session_state.speech_processor.stop_recording()
                    st.session_state.is_recording = False
                    
                    if transcribed_text:
                        # Kullanıcı mesajını işle
                        process_user_message(transcribed_text)
                    else:
                        st.warning("⚠️ Ses algılanamadı, lütfen tekrar deneyin.")
    
    st.markdown("---")
    
    # Metin girişi - sadece kayıt yapılmıyorsa göster
    if not st.session_state.is_recording:
        with st.form(key="text_form", clear_on_submit=True):
            user_input = st.text_input(
                "Mesajınızı yazın:",
                placeholder="Merhaba ASYA, nasılsın? (Enter'a basarak gönderebilirsiniz)",
                key="text_input_form"
            )
            
            col1, col2 = st.columns([1, 4])
            with col1:
                submitted = st.form_submit_button("📤 Gönder")
                
            if submitted and user_input.strip():
                process_user_message(user_input.strip())
    else:
        st.info("🎤 Kayıt yapılıyor... Metin girişi devre dışı.")

def handle_text_interaction():
    """Metin tabanlı etkileşimi yönet"""
    st.subheader("⌨️ Metin ile Konuşma")
    
    # Form kullanarak text input sorununu çözelim
    with st.form(key="text_form", clear_on_submit=True):
        user_input = st.text_input(
            "Mesajınızı yazın:",
            placeholder="Merhaba ASYA, nasılsın?",
            key="text_input_form"
        )
        
        col1, col2 = st.columns([1, 4])
        with col1:
            submitted = st.form_submit_button("📤 Gönder")
            
        if submitted and user_input.strip():
            process_user_message(user_input.strip())

def handle_audio_upload():
    """Ses dosyası yükleme"""
    st.subheader("📁 Ses Dosyası Yükle")
    
    uploaded_file = st.file_uploader(
        "Ses dosyanızı seçin (WAV, MP3, M4A)",
        type=['wav', 'mp3', 'm4a'],
        help="Maksimum 60 saniye sürebilir"
    )
    
    if uploaded_file is not None:
        if st.button("🔄 Dosyayı İşle", key="process_audio"):
            with st.spinner("🔄 Ses dosyası işleniyor..."):
                transcribed_text = st.session_state.speech_processor.transcribe_audio_file(uploaded_file)
                
                if transcribed_text:
                    process_user_message(transcribed_text)
                else:
                    st.error("❌ Ses dosyası işlenemedi!")

def process_user_message(user_message: str):
    """Kullanıcı mesajını işle ve yanıt üret"""
    try:
        # Kullanıcı mesajını session state'e ekle
        st.session_state.current_messages.append({"role": "user", "content": user_message})
        
        # Konuşma bağlamını al
        context = st.session_state.memory_manager.get_conversation_context()
        
        # LLM'den yanıt al
        with st.spinner("🤖 ASYA düşünüyor..."):
            ai_response = st.session_state.llm_processor.generate_response(user_message, context)
        
        if ai_response:
            # AI yanıtını session state'e ekle
            st.session_state.current_messages.append({"role": "assistant", "content": ai_response})
            
            # Konuşmayı hafızaya kaydet
            st.session_state.memory_manager.save_conversation(user_message, ai_response)
            
            # Ses üret - Base64 HTML kullanarak
            with st.spinner("🔊 Ses oluşturuluyor..."):
                audio_data = st.session_state.tts_processor.text_to_speech(ai_response)
                
                if audio_data:
                    play_audio_base64(audio_data)
                else:
                    st.warning("⚠️ Ses oluşturulamadı")
        else:
            st.error("❌ Yanıt alınamadı!")
            
    except Exception as e:
        st.error(f"❌ İşleme hatası: {e}")

def display_message(message: str, role: str):
    """Mesajı ekranda göster"""
    if role == "user":
        st.markdown(f"""
        <div class="chat-message user-message">
            <strong>👤 Sen:</strong><br>
            {message}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-message ai-message">
            <strong>🤖 ASYA:</strong><br>
            {message}
        </div>
        """, unsafe_allow_html=True)

def show_conversation_history():
    """Konuşma geçmişini göster"""
    st.subheader("💬 Konuşma Geçmişi")
    
    if st.session_state.memory_manager:
        conversations = st.session_state.memory_manager.get_recent_conversations(limit=10)
        
        if conversations:
            for conv in conversations:
                display_message(conv['user'], "user")
                display_message(conv['assistant'], "assistant")
                st.markdown("---")
        else:
            st.info("Henüz konuşma geçmişi yok.")

def show_settings():
    """Ayarlar paneli"""
    st.subheader("⚙️ Ayarlar")
    
    # Model ayarları
    with st.expander("🤖 Model Ayarları"):
        if st.session_state.llm_processor:
            available_models = st.session_state.llm_processor.get_available_models()
            if available_models:
                selected_model = st.selectbox(
                    "LLM Modeli:",
                    available_models,
                    index=0 if st.session_state.llm_processor.model in available_models else 0
                )
                if st.button("Modeli Değiştir"):
                    st.session_state.llm_processor.change_model(selected_model)
                    st.success(f"✅ Model değiştirildi: {selected_model}")
    
    # Ayarlar
    with st.expander("⚙️ Ayarlar"):
        # Ses hızı
        speech_rate = st.slider(
            "Konuşma Hızı", 
            -50, 50, 
            st.session_state.speech_rate, 
            5,
            help="% cinsinden konuşma hızı ayarı"
        )
        
        # Hız değiştiğinde otomatik güncelle
        if speech_rate != st.session_state.speech_rate:
            st.session_state.speech_rate = speech_rate
            new_rate = f"+{speech_rate}%" if speech_rate >= 0 else f"{speech_rate}%"
            if st.session_state.tts_processor:
                st.session_state.tts_processor.adjust_speech_rate(new_rate)
                st.success(f"✅ Konuşma hızı: {new_rate}")
                st.rerun()
        
        # Hız sıfırlama butonu
        if st.button("🔄 Hızı Sıfırla"):
            st.session_state.speech_rate = 0
            if st.session_state.tts_processor:
                st.session_state.tts_processor.adjust_speech_rate("+0%")
                st.success("✅ Hız sıfırlandı")
                st.rerun()
        
        # Mevcut hız göstergesi
        current_rate = f"+{st.session_state.speech_rate}%" if st.session_state.speech_rate >= 0 else f"{st.session_state.speech_rate}%"
        st.info(f"Mevcut Hız: {current_rate}")
        
        # Ses testi
        if st.button("🔊 Ses Testi Yap"):
            test_text = "Merhaba! Ben ASYA. Beni duyabiliyor musunuz?"
            audio_data = st.session_state.tts_processor.text_to_speech(test_text)
            if audio_data:
                play_audio_base64(audio_data)
                st.success("✅ Test sesi oluşturuldu!")
            else:
                st.error("❌ Ses oluşturulamadı!")
    
    # Hafıza ayarları
    with st.expander("💾 Hafıza Ayarları"):
        if st.button("🗑️ Hafızayı Temizle", help="Tüm konuşma geçmişini sil"):
            if st.session_state.memory_manager.clear_memory():
                st.success("✅ Hafıza temizlendi!")
                st.rerun()

def display_current_conversation():
    """Mevcut konuşmayı göster"""
    for message in st.session_state.current_messages:
        if message["role"] == "user":
            display_modern_message(message["content"], "user")
        else:
            display_modern_message(message["content"], "assistant")

def display_typing_indicator():
    """Modern yazıyor göstergesi"""
    st.markdown("""
    <div class="typing-indicator">
        <span>🤖 ASYA yazıyor</span>
        <div class="typing-dots">
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
            <div class="typing-dot"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def display_chat_container():
    """Mesajları scroll yapılabilir şekilde göster"""
    if st.session_state.current_messages:
        # Scroll yapılabilir mesaj alanı
        with st.container():
            # Tüm mesajları göster
            for message in st.session_state.current_messages:
                if message["role"] == "user":
                    st.info(f"👤 **Sen:** {message['content']}")
                else:
                    st.success(f"🤖 **ASYA:** {message['content']}")
        
        st.markdown("---")

def display_modern_message(message: str, role: str, timestamp: str = ""):
    """Modern mesaj balonları"""
    if role == "user":
        st.markdown(f"""
        <div class="message-bubble user-message">
            {message}
            {f'<div class="message-time">{timestamp}</div>' if timestamp else ''}
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="message-bubble ai-message">
            <span class="ai-label">🤖 ASYA</span>
            {message}
            {f'<div class="message-time">{timestamp}</div>' if timestamp else ''}
        </div>
        """, unsafe_allow_html=True)

def display_modern_input():
    """Modern ve estetik input arayüzü"""
    
    # Modern input container
    st.markdown('<div class="modern-input-container">', unsafe_allow_html=True)
    
    # Status bar - daha şık
    col_status, col_voice_status = st.columns([3, 1])
    with col_status:
        if st.session_state.is_recording:
            st.markdown("🎤 <span style='color: #f44336; font-weight: 600;'>Kayıt yapılıyor...</span>", unsafe_allow_html=True)
        elif st.session_state.system_ready:
            st.markdown("✅ <span style='color: #4CAF50; font-weight: 600;'>ASYA hazır</span>", unsafe_allow_html=True)
        else:
            st.markdown("⏳ <span style='color: #ff9800; font-weight: 600;'>Sistem başlatılıyor...</span>", unsafe_allow_html=True)
    
    with col_voice_status:
        voice_status_text = "🔊 Açık" if st.session_state.voice_enabled else "🔇 Kapalı"
        voice_color = "#4CAF50" if st.session_state.voice_enabled else "#9E9E9E"
        st.markdown(f"<span style='color: {voice_color}; font-size: 0.9rem; font-weight: 500;'>{voice_status_text}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Input row - 3 kolonlu modern tasarım
    col_input, col_speaker, col_mic = st.columns([6, 1, 1])
    
    with col_input:
        if not st.session_state.is_recording:
            with st.form(key="modern_chat_form", clear_on_submit=True):
                user_input = st.text_input(
                    "",
                    placeholder="💬 ASYA ile konuşun... (Enter'a basın)",
                    key="modern_chat_input",
                    label_visibility="collapsed"
                )
                
                # Gizli submit button (Enter ile çalışması için)
                submitted = st.form_submit_button("📤", use_container_width=False)
                
                if submitted and user_input.strip():
                    process_chat_message(user_input.strip())
        else:
            st.text_input(
                "",
                value="🎤 Kayıt yapılıyor... Durdur butonuna basın",
                disabled=True,
                label_visibility="collapsed"
            )
    
    with col_speaker:
        # Sesli yanıt toggle butonu
        voice_icon = "🔊" if st.session_state.voice_enabled else "🔇"
        if st.button(voice_icon, key="voice_toggle_btn", help="Sesli yanıtı aç/kapat"):
            st.session_state.voice_enabled = not st.session_state.voice_enabled
            status = "açık" if st.session_state.voice_enabled else "kapalı"
            st.success(f"✅ Sesli yanıt {status}")
            st.rerun()
    
    with col_mic:
        # Mikrofon butonu
        if not st.session_state.is_recording:
            if st.button("🎤", key="modern_voice_btn", help="Ses kaydı başlat"):
                if st.session_state.speech_processor.start_recording():
                    st.session_state.is_recording = True
                    st.rerun()
                else:
                    st.error("❌ Kayıt başlatılamadı!")
        else:
            if st.button("⏹️", key="modern_stop_btn", help="Kaydı durdur"):
                with st.spinner("🔄 Ses işleniyor..."):
                    transcribed_text = st.session_state.speech_processor.stop_recording()
                    st.session_state.is_recording = False
                    
                    if transcribed_text:
                        process_chat_message(transcribed_text)
                    else:
                        st.warning("⚠️ Ses algılanamadı, lütfen tekrar deneyin.")
                        st.rerun()
    
    # Container'ı kapat
    st.markdown("</div>", unsafe_allow_html=True)

def process_chat_message(user_message: str):
    """Chat mesajını işle"""
    try:
        # Kullanıcı mesajını ekle
        st.session_state.current_messages.append({
            "role": "user", 
            "content": user_message,
            "timestamp": datetime.now().strftime("%H:%M")
        })
        
        # Sayfayı yenile (kullanıcı mesajını göster)
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Mesaj işleme hatası: {e}")

def generate_ai_response(user_message: str):
    """AI yanıtı oluştur"""
    try:
        # Konuşma bağlamını al
        context = st.session_state.memory_manager.get_conversation_context()
        
        # LLM'den yanıt al
        ai_response = st.session_state.llm_processor.generate_response(user_message, context)
        
        if ai_response:
            # AI yanıtını ekle
            st.session_state.current_messages.append({
                "role": "assistant",
                "content": ai_response,
                "timestamp": datetime.now().strftime("%H:%M")
            })
            
            # Hafızaya kaydet
            st.session_state.memory_manager.save_conversation(user_message, ai_response)
            
            # Sesli yanıt - sadece açık olduğunda
            if st.session_state.voice_enabled:
                audio_data = st.session_state.tts_processor.text_to_speech(ai_response)
                if audio_data:
                    play_audio_base64(audio_data)
            
            return True
        return False
        
    except Exception as e:
        st.error(f"❌ AI yanıt hatası: {e}")
        return False

def play_audio_base64(audio_data: bytes):
    """Base64 encode edip HTML audio tag'i ile ses oynat"""
    try:
        # Ses verilerini base64'e encode et
        audio_base64 = base64.b64encode(audio_data).decode()
        
        # HTML audio tag'i oluştur
        audio_html = f"""
        <audio controls autoplay style="width: 100%; margin: 10px 0;">
            <source src="data:audio/mp3;base64,{audio_base64}" type="audio/mp3">
            Tarayıcınız audio tag'ini desteklemiyor.
        </audio>
        """
        
        # HTML'i session state'e kaydet
        st.session_state.audio_html = audio_html
        
    except Exception as e:
        st.error(f"❌ Ses oynatma hatası: {e}")

def main():
    """Ana uygulama - Modern ChatGPT Tarzı"""
    # Session state'i başlat
    initialize_session_state()
    
    # Header section - aynı kalacak
    display_header()
    
    # Bileşenleri yükle
    if not load_components():
        st.error("❌ Sistem başlatılamadı! Lütfen tekrar deneyin.")
        return
    
    # Ana chat container - yeniden tasarlanmış
    display_chat_container()
    
    # AI yanıtı oluşturma
    if (st.session_state.current_messages and 
        st.session_state.current_messages[-1]["role"] == "user" and
        (len(st.session_state.current_messages) == 1 or 
         st.session_state.current_messages[-2]["role"] == "assistant")):
        
        # Typing indicator göster
        display_typing_indicator()
        
        with st.spinner("🤖 ASYA düşünüyor..."):
            user_msg = st.session_state.current_messages[-1]["content"]
            if generate_ai_response(user_msg):
                st.rerun()
    
    # Audio HTML'ini göster (eğer varsa)
    if st.session_state.audio_html:
        st.markdown(st.session_state.audio_html, unsafe_allow_html=True)
        # Bir kez gösterildikten sonra temizle
        st.session_state.audio_html = None
    
    # Modern input alanı
    display_modern_input()
    
    # Sidebar - aynı kalacak
    with st.sidebar:
        st.markdown("### 📊 Sistem Durumu")
        
        if st.session_state.system_ready:
            st.success("✅ Sistem Hazır")
            
            # Sistem bileşenleri durumu
            col1, col2 = st.columns(2)
            with col1:
                if st.session_state.speech_processor and st.session_state.speech_processor.is_model_loaded():
                    st.success("🎙️ Whisper")
                else:
                    st.error("❌ Whisper")
                    
                if st.session_state.tts_processor:
                    st.success("🔊 TTS")
                else:
                    st.error("❌ TTS")
            
            with col2:
                if st.session_state.llm_processor and st.session_state.llm_processor.is_model_ready():
                    st.success("🤖 LLM")
                else:
                    st.error("❌ LLM")
                    
                if st.session_state.memory_manager:
                    st.success("💾 Hafıza")
                else:
                    st.error("❌ Hafıza")
            
            # Mikrofon durumu
            if st.session_state.speech_processor.is_microphone_available():
                st.success("🎙️ Mikrofon Aktif")
            else:
                st.warning("⚠️ Mikrofon Bulunamadı")
        else:
            st.error("❌ Sistem Başlatılıyor...")
        
        st.markdown("---")
        
        # Konuşma kontrolü
        st.markdown("### 🗣️ Konuşma Kontrolü")
        
        # Sesli yanıt durumu
        voice_status = "🔊 Açık" if st.session_state.voice_enabled else "🔇 Kapalı"
        st.info(f"Sesli Yanıt: {voice_status}")
        
        if st.button("🗑️ Sohbeti Temizle", use_container_width=True):
            st.session_state.current_messages = []
            st.success("✅ Sohbet temizlendi!")
            st.rerun()
        
        # Mesaj sayısı
        msg_count = len(st.session_state.current_messages)
        st.info(f"💬 {msg_count} mesaj")
        
        st.markdown("---")
        
        # Ayarlar
        with st.expander("⚙️ Ayarlar"):
            # Ses hızı
            speech_rate = st.slider(
                "Konuşma Hızı", 
                -50, 50, 
                st.session_state.speech_rate, 
                5,
                help="% cinsinden konuşma hızı ayarı"
            )
            
            # Hız değiştiğinde otomatik güncelle
            if speech_rate != st.session_state.speech_rate:
                st.session_state.speech_rate = speech_rate
                new_rate = f"+{speech_rate}%" if speech_rate >= 0 else f"{speech_rate}%"
                if st.session_state.tts_processor:
                    st.session_state.tts_processor.adjust_speech_rate(new_rate)
                    st.success(f"✅ Konuşma hızı: {new_rate}")
                    st.rerun()
            
            # Hız sıfırlama butonu
            if st.button("🔄 Hızı Sıfırla"):
                st.session_state.speech_rate = 0
                if st.session_state.tts_processor:
                    st.session_state.tts_processor.adjust_speech_rate("+0%")
                    st.success("✅ Hız sıfırlandı")
                    st.rerun()
            
            # Mevcut hız göstergesi  
            current_rate = f"+{st.session_state.speech_rate}%" if st.session_state.speech_rate >= 0 else f"{st.session_state.speech_rate}%"
            st.info(f"Mevcut Hız: {current_rate}")
            
            # Ses testi
            if st.button("🔊 Ses Testi Yap"):
                test_text = "Merhaba! Ben ASYA. Beni duyabiliyor musunuz?"
                audio_data = st.session_state.tts_processor.text_to_speech(test_text)
                if audio_data:
                    play_audio_base64(audio_data)
                    st.success("✅ Test sesi oluşturuldu!")
                else:
                    st.error("❌ Ses oluşturulamadı!")
        
        st.markdown("---")
        st.markdown("### 💡 Kullanım İpuçları")
        st.markdown("""
        • **Metin**: Mesaj kutusuna yazıp Enter'a basın
        • **Ses**: 🎤 butonuna basıp konuşun
        • **Hızlı**: Kısa ve net sorular sorun
        • **Bağlam**: Önceki mesajlarınızı hatırlıyorum
        • **Temizlik**: Yeni konu için sohbeti temizleyin
        """)

if __name__ == "__main__":
    main() 