import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import hashlib

class DatabaseManager:
    def __init__(self, db_path='database.json'):
        # Render için /tmp dizinini kullan (ephemeral storage)
        if os.environ.get('RENDER'):
            self.db_path = '/tmp/database.json'
        else:
            self.db_path = db_path
        self.db = self._load_database()
        print(f"📁 Database yolu: {self.db_path}")
    
    def _load_database(self):
        """Veritabanını yükler, yoksa oluşturur"""
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Veritabanı yükleme hatası: {e}")
                return self._create_empty_db()
        else:
            return self._create_empty_db()
    
    def _create_empty_db(self):
        """Boş veritabanı yapısı oluşturur"""
        return {
            'users': {},  # {username: {password_hash, fcm_token, manga_list, created_at}}
            'manga_chapters': {},  # {manga_name: {chapter, url, image, last_checked}}
            'last_check': None
        }
    
    def _save_database(self):
        """Veritabanını dosyaya kaydeder"""
        try:
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(self.db, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Veritabanı kaydetme hatası: {e}")
            return False
    
    def _hash_password(self, password: str) -> str:
        """Şifreyi hash'ler"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Şifreyi doğrular"""
        return self._hash_password(password) == password_hash
    
    # USER OPERATIONS
    
    def create_user(self, username: str, password: str, fcm_token: str = None) -> bool:
        """Yeni kullanıcı oluşturur"""
        if username in self.db['users']:
            return False  # Kullanıcı zaten var
        
        self.db['users'][username] = {
            'password_hash': self._hash_password(password),
            'fcm_token': fcm_token or '',
            'manga_list': [],
            'created_at': datetime.now().isoformat()
        }
        
        self._save_database()
        return True
    
    def authenticate_user(self, username: str, password: str) -> bool:
        """Kullanıcı girişini doğrular"""
        user = self.db['users'].get(username)
        if not user:
            return False
        
        return self._verify_password(password, user['password_hash'])
    
    def update_fcm_token(self, username: str, fcm_token: str) -> bool:
        """Kullanıcının FCM token'ını günceller"""
        if username in self.db['users']:
            self.db['users'][username]['fcm_token'] = fcm_token
            self._save_database()
            return True
        return False
    
    def add_or_update_user(self, device_id: str, token: str, manga_list: List[str] = None):
        """Eski API uyumluluğu için - DEPRECATED"""
        # Geriye dönük uyumluluk için username olarak device_id kullan
        if device_id not in self.db['users']:
            self.db['users'][device_id] = {
                'password_hash': '',  # Eski kullanıcılar için boş
                'fcm_token': token,
                'manga_list': manga_list or [],
                'created_at': datetime.now().isoformat()
            }
        else:
            self.db['users'][device_id]['fcm_token'] = token
            if manga_list is not None:
                self.db['users'][device_id]['manga_list'] = manga_list
        
        self._save_database()
        return True
    
    def get_user(self, username: str) -> Optional[Dict]:
        """Kullanıcı bilgilerini getirir (şifre hash'i hariç)"""
        user = self.db['users'].get(username)
        if user:
            # Şifre hash'ini çıkar
            return {
                'username': username,
                'fcm_token': user.get('fcm_token', ''),
                'manga_list': user.get('manga_list', []),
                'created_at': user.get('created_at')
            }
        return None
    
    def get_all_users(self) -> Dict:
        """Tüm kullanıcıları getirir"""
        return self.db['users']
    
    def update_user_manga_list(self, username: str, manga_list: List[str]) -> bool:
        """Kullanıcının manga listesini günceller"""
        if username in self.db['users']:
            self.db['users'][username]['manga_list'] = manga_list
            self._save_database()
            return True
        return False
    
    def add_manga_to_user(self, username: str, manga_name: str) -> bool:
        """Kullanıcının listesine manga ekler"""
        if username in self.db['users']:
            if manga_name not in self.db['users'][username]['manga_list']:
                self.db['users'][username]['manga_list'].append(manga_name)
                self._save_database()
            return True
        return False
    
    def remove_manga_from_user(self, username: str, manga_name: str) -> bool:
        """Kullanıcının listesinden manga çıkarır"""
        if username in self.db['users']:
            if manga_name in self.db['users'][username]['manga_list']:
                self.db['users'][username]['manga_list'].remove(manga_name)
                self._save_database()
            return True
        return False
    
    def remove_user(self, username: str) -> bool:
        """Kullanıcıyı siler"""
        if username in self.db['users']:
            del self.db['users'][username]
            self._save_database()
            return True
        return False
    
    # MANGA OPERATIONS
    
    def update_manga_chapter(self, manga_name: str, chapter: str, url: str = None, image: str = None):
        """Manga bölüm bilgisini günceller"""
        self.db['manga_chapters'][manga_name] = {
            'chapter': chapter,
            'url': url,
            'image': image,
            'last_checked': datetime.now().isoformat()
        }
        self._save_database()
    
    def get_manga_chapter(self, manga_name: str) -> Optional[Dict]:
        """Manga bölüm bilgisini getirir"""
        return self.db['manga_chapters'].get(manga_name)
    
    def get_all_manga_chapters(self) -> Dict:
        """Tüm manga bölüm bilgilerini getirir"""
        return self.db['manga_chapters']
    
    def check_chapter_changed(self, manga_name: str, new_chapter: str) -> tuple[bool, bool]:
        """
        Bölümün değişip değişmediğini kontrol eder
        Returns: (is_new, has_changed)
            - is_new: İlk kez mi kontrol ediliyor
            - has_changed: Bölüm değişmiş mi
        """
        old_data = self.get_manga_chapter(manga_name)
        if not old_data:
            return (True, False)  # İlk kez, değişiklik yok (henüz bildirim gönderme)
        
        has_changed = old_data.get('chapter') != new_chapter
        return (False, has_changed)  # İlk değil, değişiklik kontrolü
    
    def update_last_check(self):
        """Son kontrol zamanını günceller"""
        self.db['last_check'] = datetime.now().isoformat()
        self._save_database()
    
    def get_last_check(self) -> Optional[str]:
        """Son kontrol zamanını getirir"""
        return self.db['last_check']
    
    # ANALYTICS
    
    def get_stats(self) -> Dict:
        """İstatistikleri döner"""
        return {
            'total_users': len(self.db['users']),
            'total_manga': len(self.db['manga_chapters']),
            'last_check': self.db['last_check']
        }
    
    def get_all_tracked_manga(self) -> List[str]:
        """Tüm kullanıcıların takip ettiği benzersiz manga listesi"""
        all_manga = set()
        for user in self.db['users'].values():
            all_manga.update(user.get('manga_list', []))
        return list(all_manga)
