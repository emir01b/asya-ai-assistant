import ollama
import requests
from typing import Optional, Dict, List
from config import OLLAMA_BASE_URL, OLLAMA_MODEL, SYSTEM_PROMPT

class LLMProcessor:
    """Ollama kullanarak yerel LLM işleme sınıfı"""
    
    def __init__(self):
        self.base_url = OLLAMA_BASE_URL
        self.model = OLLAMA_MODEL
        self.system_prompt = SYSTEM_PROMPT
        
        print(f"🤖 LLM sistemi başlatılıyor - Model: {self.model}")
        
        # Ollama bağlantısını test et
        if self.check_ollama_connection():
            print("✅ Ollama bağlantısı başarılı")
            # Modeli kontrol et ve indir
            self.ensure_model_available()
        else:
            print("❌ Ollama bağlantısı başarısız!")
    
    def check_ollama_connection(self) -> bool:
        """Ollama servisinin çalışıp çalışmadığını kontrol et"""
        try:
            response = requests.get(f"{self.base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception as e:
            print(f"❌ Ollama bağlantı hatası: {e}")
            return False
    
    def ensure_model_available(self) -> bool:
        """Modelin mevcut olduğundan emin ol, yoksa indir"""
        try:
            # Mevcut modelleri listele
            response = requests.get(f"{self.base_url}/api/tags")
            models = response.json()
            
            model_names = [model['name'] for model in models.get('models', [])]
            
            if self.model not in model_names:
                print(f"📥 Model indiriliyor: {self.model}")
                self.pull_model()
            else:
                print(f"✅ Model mevcut: {self.model}")
            
            return True
            
        except Exception as e:
            print(f"❌ Model kontrol hatası: {e}")
            return False
    
    def pull_model(self) -> bool:
        """Modeli Ollama'ya indir"""
        try:
            print(f"📥 {self.model} modeli indiriliyor... (Bu işlem zaman alabilir)")
            
            response = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": self.model},
                stream=True,
                timeout=300
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            import json
                            data = json.loads(line)
                            if 'status' in data:
                                print(f"📥 {data['status']}")
                        except:
                            pass
                
                print(f"✅ Model başarıyla indirildi: {self.model}")
                return True
            else:
                print(f"❌ Model indirilemedi: {response.status_code}")
                return False
                
        except Exception as e:
            print(f"❌ Model indirme hatası: {e}")
            return False
    
    def generate_response(self, user_message: str, conversation_context: str = "") -> Optional[str]:
        """Kullanıcı mesajına LLM yanıtı üret"""
        try:
            # Tam prompt oluştur
            full_prompt = self._create_full_prompt(user_message, conversation_context)
            
            print(f"🤖 LLM'den yanıt bekleniyor...")
            
            # Ollama API ile isteği gönder
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40,
                        "num_predict": 300
                    }
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                ai_response = result.get('response', '').strip()
                
                if ai_response:
                    print(f"✅ LLM yanıtı alındı: {ai_response[:100]}...")
                    return ai_response
                else:
                    print("⚠️ LLM boş yanıt döndü")
                    return "Üzgünüm, şu anda yanıt veremiyorum. Lütfen tekrar deneyin."
            else:
                print(f"❌ LLM API hatası: {response.status_code}")
                return "Teknik bir sorun yaşıyorum. Lütfen daha sonra tekrar deneyin."
                
        except Exception as e:
            print(f"❌ LLM işleme hatası: {e}")
            return "Bir hata oluştu. Lütfen tekrar deneyin."
    
    def _create_full_prompt(self, user_message: str, conversation_context: str = "") -> str:
        """Tam prompt oluştur"""
        prompt_parts = [self.system_prompt]
        
        if conversation_context:
            prompt_parts.append(f"\nÖnceki konuşmalar:\n{conversation_context}")
        
        prompt_parts.append(f"\nKullanıcı: {user_message}")
        prompt_parts.append("\nASYA:")
        
        return "\n".join(prompt_parts)
    
    def generate_streaming_response(self, user_message: str, conversation_context: str = ""):
        """Streaming yanıt üret (generator)"""
        try:
            full_prompt = self._create_full_prompt(user_message, conversation_context)
            
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": full_prompt,
                    "stream": True,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "top_k": 40
                    }
                },
                stream=True,
                timeout=120
            )
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        try:
                            import json
                            data = json.loads(line)
                            if 'response' in data:
                                yield data['response']
                        except json.JSONDecodeError:
                            continue
            
        except Exception as e:
            print(f"❌ Streaming yanıt hatası: {e}")
            yield "Bir hata oluştu."
    
    def get_available_models(self) -> List[str]:
        """Kullanılabilir modelleri listele"""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json()
                return [model['name'] for model in models.get('models', [])]
            return []
        except Exception as e:
            print(f"❌ Model listesi hatası: {e}")
            return []
    
    def change_model(self, new_model: str) -> bool:
        """Kullanılan modeli değiştir"""
        try:
            available_models = self.get_available_models()
            if new_model in available_models:
                self.model = new_model
                print(f"✅ Model değiştirildi: {new_model}")
                return True
            else:
                print(f"❌ Model mevcut değil: {new_model}")
                return False
        except Exception as e:
            print(f"❌ Model değiştirme hatası: {e}")
            return False
    
    def get_model_info(self) -> Dict:
        """Mevcut model hakkında bilgi al"""
        try:
            response = requests.post(
                f"{self.base_url}/api/show",
                json={"name": self.model}
            )
            
            if response.status_code == 200:
                return response.json()
            return {}
            
        except Exception as e:
            print(f"❌ Model bilgisi hatası: {e}")
            return {}
    
    def is_model_ready(self) -> bool:
        """Model kullanıma hazır mı kontrol et"""
        try:
            # Basit bir test mesajı gönder
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": "Test",
                    "stream": False,
                    "options": {"num_predict": 1}
                },
                timeout=10
            )
            return response.status_code == 200
        except:
            return False 