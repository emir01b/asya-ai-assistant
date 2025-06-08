import sqlite3
import datetime
from typing import List, Dict, Optional
from config import DATABASE_PATH, MAX_MEMORY_ENTRIES

class MemoryManager:
    """Konuşma hafızası yönetimi için SQLite veritabanı sınıfı"""
    
    def __init__(self):
        self.db_path = DATABASE_PATH
        self.init_database()
    
    def init_database(self):
        """Veritabanını başlat ve tabloları oluştur"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Konuşma geçmişi tablosu
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS conversations (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        ai_response TEXT NOT NULL,
                        session_id TEXT,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Kullanıcı tercihleri tablosu
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_preferences (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        preference_key TEXT UNIQUE NOT NULL,
                        preference_value TEXT NOT NULL,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                conn.commit()
                print("✅ Veritabanı başarıyla başlatıldı")
                
        except Exception as e:
            print(f"❌ Veritabanı hatası: {e}")
    
    def save_conversation(self, user_message: str, ai_response: str, session_id: str = "default") -> bool:
        """Konuşmayı veritabanına kaydet"""
        try:
            timestamp = datetime.datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO conversations (timestamp, user_message, ai_response, session_id)
                    VALUES (?, ?, ?, ?)
                """, (timestamp, user_message, ai_response, session_id))
                
                # Maksimum kayıt sayısını kontrol et
                cursor.execute("SELECT COUNT(*) FROM conversations")
                count = cursor.fetchone()[0]
                
                if count > MAX_MEMORY_ENTRIES:
                    # En eski kayıtları sil
                    excess = count - MAX_MEMORY_ENTRIES
                    cursor.execute("""
                        DELETE FROM conversations 
                        WHERE id IN (
                            SELECT id FROM conversations 
                            ORDER BY created_at ASC 
                            LIMIT ?
                        )
                    """, (excess,))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Konuşma kaydetme hatası: {e}")
            return False
    
    def get_recent_conversations(self, limit: int = 10, session_id: str = "default") -> List[Dict]:
        """Son konuşmaları getir"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_message, ai_response, timestamp 
                    FROM conversations 
                    WHERE session_id = ?
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (session_id, limit))
                
                results = cursor.fetchall()
                conversations = []
                
                for row in reversed(results):  # Kronolojik sıra için ters çevir
                    conversations.append({
                        'user': row[0],
                        'assistant': row[1],
                        'timestamp': row[2]
                    })
                
                return conversations
                
        except Exception as e:
            print(f"❌ Konuşma getirme hatası: {e}")
            return []
    
    def get_conversation_context(self, session_id: str = "default", max_tokens: int = 1000) -> str:
        """Konuşma bağlamını string olarak getir"""
        conversations = self.get_recent_conversations(limit=20, session_id=session_id)
        
        context = ""
        for conv in conversations:
            context += f"Kullanıcı: {conv['user']}\nASYA: {conv['assistant']}\n\n"
            
            # Token sayısını yaklaşık kontrol et (basit yöntem)
            if len(context) > max_tokens:
                break
        
        return context.strip()
    
    def search_conversations(self, query: str, session_id: str = "default", limit: int = 5) -> List[Dict]:
        """Konuşmalarda arama yap"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT user_message, ai_response, timestamp 
                    FROM conversations 
                    WHERE session_id = ? AND 
                          (user_message LIKE ? OR ai_response LIKE ?)
                    ORDER BY created_at DESC 
                    LIMIT ?
                """, (session_id, f"%{query}%", f"%{query}%", limit))
                
                results = cursor.fetchall()
                conversations = []
                
                for row in results:
                    conversations.append({
                        'user': row[0],
                        'assistant': row[1],
                        'timestamp': row[2]
                    })
                
                return conversations
                
        except Exception as e:
            print(f"❌ Arama hatası: {e}")
            return []
    
    def clear_memory(self, session_id: str = "default") -> bool:
        """Belirtilen oturum için hafızayı temizle"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
                conn.commit()
                print(f"✅ {session_id} oturumu hafızası temizlendi")
                return True
                
        except Exception as e:
            print(f"❌ Hafıza temizleme hatası: {e}")
            return False
    
    def save_preference(self, key: str, value: str) -> bool:
        """Kullanıcı tercihini kaydet"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO user_preferences (preference_key, preference_value, updated_at)
                    VALUES (?, ?, CURRENT_TIMESTAMP)
                """, (key, value))
                conn.commit()
                return True
                
        except Exception as e:
            print(f"❌ Tercih kaydetme hatası: {e}")
            return False
    
    def get_preference(self, key: str, default_value: str = None) -> Optional[str]:
        """Kullanıcı tercihini getir"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT preference_value FROM user_preferences WHERE preference_key = ?", (key,))
                result = cursor.fetchone()
                return result[0] if result else default_value
                
        except Exception as e:
            print(f"❌ Tercih getirme hatası: {e}")
            return default_value 