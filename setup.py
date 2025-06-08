#!/usr/bin/env python3
"""
Türkçe Sesli AI Asistanı - Kurulum Scripti
Bu script, sistem kurulumunu ve yapılandırmasını otomatik olarak yapar.
"""

import os
import sys
import subprocess
import platform
import requests
import time

def print_step(step, message):
    """Kurulum adımlarını güzel şekilde yazdır"""
    print(f"\n{'='*50}")
    print(f"ADIM {step}: {message}")
    print(f"{'='*50}")

def run_command(command, description="", check=True):
    """Komut çalıştır ve sonucu kontrol et"""
    print(f"🔄 {description}")
    print(f"   Komut: {command}")
    
    try:
        result = subprocess.run(command, shell=True, check=check, 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - Başarılı")
            return True
        else:
            print(f"❌ {description} - Hata: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {description} - Hata: {e}")
        return False

def check_python_version():
    """Python versiyonunu kontrol et"""
    print_step(1, "Python Versiyonu Kontrol Ediliyor")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 8:
        print(f"✅ Python {version.major}.{version.minor}.{version.micro} - Uygun")
        return True
    else:
        print(f"❌ Python {version.major}.{version.minor}.{version.micro} - Uygun değil")
        print("💡 Python 3.8 veya üstü gerekli!")
        return False

def install_ollama():
    """Ollama'yı kur"""
    print_step(2, "Ollama Kurulumu")
    
    system = platform.system().lower()
    
    if system == "linux" or system == "darwin":  # macOS
        if run_command("which ollama", "Ollama mevcut mu kontrol et", check=False):
            print("✅ Ollama zaten kurulu")
            return True
        
        print("📥 Ollama indiriliyor ve kuruluyor...")
        return run_command("curl https://ollama.ai/install.sh | sh", "Ollama kurulumu")
    
    elif system == "windows":
        print("💡 Windows için Ollama'yı manuel olarak indirip kurmanız gerekiyor:")
        print("   https://ollama.ai/download")
        input("Ollama'yı kurduktan sonra Enter'a basın...")
        return True
    
    else:
        print(f"❌ Desteklenmeyen işletim sistemi: {system}")
        return False

def start_ollama():
    """Ollama servisini başlat"""
    print_step(3, "Ollama Servisi Başlatılıyor")
    
    # Ollama'nın çalışıp çalışmadığını kontrol et
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama zaten çalışıyor")
            return True
    except:
        pass
    
    print("🚀 Ollama servisi başlatılıyor...")
    
    system = platform.system().lower()
    if system == "linux" or system == "darwin":
        # Background'da başlat
        subprocess.Popen(["ollama", "serve"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("💡 Windows'ta Ollama'yı manuel olarak başlatın")
    
    # Servisin başlamasını bekle
    for i in range(30):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                print("✅ Ollama servisi başarıyla başlatıldı")
                return True
        except:
            time.sleep(1)
            print(f"⏳ Ollama başlatılıyor... ({i+1}/30)")
    
    print("❌ Ollama servisi başlatılamadı")
    return False

def download_llm_model():
    """LLM modelini indir"""
    print_step(4, "LLM Modeli İndiriliyor")
    
    model = "mistral:7b"  # Türkçe'de en iyi performans
    
    print(f"📥 {model} modeli indiriliyor... (Bu işlem uzun sürebilir)")
    return run_command(f"ollama pull {model}", f"{model} model indirme")

def install_python_packages():
    """Python paketlerini kur"""
    print_step(5, "Python Paketleri Kuruluyor")
    
    packages = [
        "streamlit==1.28.1",
        "openai-whisper==20230918", 
        "pyaudio==0.2.13",
        "edge-tts==6.1.9",
        "ollama==0.1.7",
        "pydub==0.25.1",
        "requests",
    ]
    
    success = True
    for package in packages:
        if not run_command(f"pip install {package}", f"{package} kurulumu"):
            success = False
    
    return success

def install_system_dependencies():
    """Sistem bağımlılıklarını kur"""
    print_step(6, "Sistem Bağımlılıkları Kuruluyor")
    
    system = platform.system().lower()
    
    if system == "linux":
        # Ubuntu/Debian için
        commands = [
            "sudo apt update",
            "sudo apt install -y ffmpeg portaudio19-dev python3-dev",
        ]
        for cmd in commands:
            if not run_command(cmd, f"Linux bağımlılık kurulumu: {cmd}"):
                return False
        return True
    
    elif system == "darwin":  # macOS
        # Homebrew ile kur
        commands = [
            "brew install ffmpeg portaudio",
        ]
        for cmd in commands:
            if not run_command(cmd, f"macOS bağımlılık kurulumu: {cmd}"):
                print("💡 Homebrew kurulu değilse: /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
                return False
        return True
    
    elif system == "windows":
        print("💡 Windows için manuel kurulum gerekli:")
        print("   1. FFmpeg: https://ffmpeg.org/download.html")
        print("   2. Visual Studio Build Tools (C++ desteği)")
        input("Bağımlılıkları kurduktan sonra Enter'a basın...")
        return True
    
    return True

def create_startup_script():
    """Başlatma scripti oluştur"""
    print_step(7, "Başlatma Scripti Oluşturuluyor")
    
    script_content = """#!/bin/bash
# Türkçe Sesli AI Asistanı Başlatma Scripti

echo "🚀 Türkçe Sesli AI Asistanı başlatılıyor..."

# Ollama servisini kontrol et
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "📥 Ollama servisi başlatılıyor..."
    ollama serve &
    sleep 5
fi

echo "🌐 Web arayüzü başlatılıyor..."
streamlit run main.py --server.port 8501 --server.address 0.0.0.0

echo "✅ Uygulama başlatıldı: http://localhost:8501"
"""
    
    try:
        with open("start.sh", "w") as f:
            f.write(script_content)
        
        # Çalıştırılabilir yap
        os.chmod("start.sh", 0o755)
        
        print("✅ start.sh dosyası oluşturuldu")
        return True
    except Exception as e:
        print(f"❌ Başlatma scripti oluşturulamadı: {e}")
        return False

def run_tests():
    """Sistem testlerini çalıştır"""
    print_step(8, "Sistem Testleri Çalıştırılıyor")
    
    tests = [
        ("Python modülleri", "python -c 'import whisper, edge_tts, ollama, streamlit'"),
        ("Ollama bağlantısı", "curl -s http://localhost:11434/api/tags"),
        ("FFmpeg", "ffmpeg -version"),
    ]
    
    success = True
    for test_name, command in tests:
        if not run_command(command, f"{test_name} testi", check=False):
            success = False
    
    return success

def main():
    """Ana kurulum fonksiyonu"""
    print("🗣️ Türkçe Sesli AI Asistanı - Kurulum Başlatılıyor")
    print("=" * 60)
    
    # Kurulum adımları
    steps = [
        check_python_version,
        install_system_dependencies,
        install_python_packages,
        install_ollama,
        start_ollama,
        download_llm_model,
        create_startup_script,
        run_tests,
    ]
    
    # Her adımı çalıştır
    for i, step in enumerate(steps, 1):
        try:
            if not step():
                print(f"\n❌ Kurulum {i}. adımda başarısız oldu!")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n⏸️ Kurulum kullanıcı tarafından durduruldu")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Beklenmeyen hata: {e}")
            sys.exit(1)
    
    # Başarılı kurulum mesajı
    print("\n" + "="*60)
    print("🎉 KURULUM BAŞARIYLA TAMAMLANDI!")
    print("="*60)
    print()
    print("📋 Çalıştırma Talimatları:")
    print("   1. Terminal açın ve proje klasörüne gidin")
    print("   2. Aşağıdaki komutlardan birini çalıştırın:")
    print()
    print("   🔹 Linux/macOS:")
    print("      ./start.sh")
    print()
    print("   🔹 Manuel başlatma:")
    print("      streamlit run main.py")
    print()
    print("   🔹 Tarayıcıda açın:")
    print("      http://localhost:8501")
    print()
    print("✨ İyi kullanımlar!")

if __name__ == "__main__":
    main() 