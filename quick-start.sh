#!/bin/bash

# 🚀 ASYA - Hızlı Başlatma Scripti
# Bu script ASYA'yı hızlıca çalıştırmanızı sağlar

echo "🎙️ ASYA - Akıllı Sesli Yapay Zeka Asistanı"
echo "==========================================="
echo ""

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Platform tespit et
if [[ "$OSTYPE" == "darwin"* ]]; then
    PLATFORM="macOS"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    PLATFORM="Linux"
else
    PLATFORM="Windows/Other"
fi

echo -e "${BLUE}Platform: $PLATFORM${NC}"
echo ""

# Python versiyon kontrolü
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✅ Python3 bulundu: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}❌ Python3 bulunamadı! Lütfen Python 3.11+ kurun.${NC}"
    exit 1
fi

# Sanal ortam kontrolü
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}📦 Sanal ortam oluşturuluyor...${NC}"
    python3 -m venv venv
fi

# Sanal ortamı aktif et
echo -e "${BLUE}🔄 Sanal ortam aktifleştiriliyor...${NC}"
source venv/bin/activate

# Bağımlılık kontrolü
if [ ! -f "venv/lib/python*/site-packages/streamlit" ]; then
    echo -e "${YELLOW}📋 Bağımlılıklar kuruluyor...${NC}"
    pip install -r requirements.txt
fi

# Ollama kontrolü
if command -v ollama &> /dev/null; then
    echo -e "${GREEN}✅ Ollama bulundu${NC}"
    
    # Ollama servis kontrolü
    if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Ollama servisi çalışıyor${NC}"
    else
        echo -e "${YELLOW}🔄 Ollama servisi başlatılıyor...${NC}"
        if [[ "$PLATFORM" == "macOS" ]]; then
            brew services start ollama
        else
            ollama serve &
        fi
        sleep 3
    fi
    
    # Model kontrolü
    if ollama list | grep -q "mistral:7b"; then
        echo -e "${GREEN}✅ Mistral 7B modeli mevcut${NC}"
    else
        echo -e "${YELLOW}📥 Mistral 7B modeli indiriliyor... (Bu biraz zaman alabilir)${NC}"
        ollama pull mistral:7b
    fi
else
    echo -e "${RED}❌ Ollama bulunamadı!${NC}"
    echo -e "${YELLOW}📖 Kurulum için: https://ollama.ai/download${NC}"
    
    # macOS'ta otomatik kurulum teklifi
    if [[ "$PLATFORM" == "macOS" ]] && command -v brew &> /dev/null; then
        echo -e "${BLUE}🍺 Homebrew ile kurmak ister misiniz? (y/n)${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            brew install ollama
        fi
    fi
fi

# Sistem testi
echo ""
echo -e "${BLUE}🧪 Hızlı sistem testi...${NC}"
if python test_components.py | grep -q "TÜM TESTLER BAŞARILI"; then
    echo -e "${GREEN}✅ Sistem testleri geçti!${NC}"
else
    echo -e "${YELLOW}⚠️ Bazı testler başarısız. Detay için: python test_components.py${NC}"
fi

# Streamlit başlat
echo ""
echo -e "${GREEN}🚀 ASYA başlatılıyor...${NC}"
echo -e "${BLUE}📱 Tarayıcınızda açılacak: http://localhost:8501${NC}"
echo ""
echo -e "${YELLOW}⏹️ Durdurmak için: Ctrl+C${NC}"
echo ""

streamlit run main.py 