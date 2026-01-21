import json
import os
from datetime import datetime
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self, db_path='database.json'):
        self.db_path = db_path
        self.db = self._load_database()
    
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
            'users': {},  # {device_id: {token, manga_list, created_at}}
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
    
    # USER OPERATIONS
    
    def add_or_update_user(self, device_id: str, token: str, manga_list: List[str] = None):
        """Kullanıcı ekler veya günceller"""
        if device_id not in self.db['users']:
            self.db['users'][device_id] = {
                'token': token,
                'manga_list': manga_list or [],
                'created_at': datetime.now().isoformat()
            }
        else:
            self.db['users'][device_id]['token'] = token
            if manga_list is not None:
                self.db['users'][device_id]['manga_list'] = manga_list
        
        self._save_database()
        return True
    
    def get_user(self, device_id: str) -> Optional[Dict]:
        """Kullanıcı bilgilerini getirir"""
        return self.db['users'].get(device_id)
    
    def get_all_users(self) -> Dict:
        """Tüm kullanıcıları getirir"""
        return self.db['users']
    
    def update_user_manga_list(self, device_id: str, manga_list: List[str]):
        """Kullanıcının manga listesini günceller"""
        if device_id in self.db['users']:
            self.db['users'][device_id]['manga_list'] = manga_list
            self._save_database()
            return True
        return False
    
    def remove_user(self, device_id: str):
        """Kullanıcıyı siler"""
        if device_id in self.db['users']:
            del self.db['users'][device_id]
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
    
    def check_chapter_changed(self, manga_name: str, new_chapter: str) -> bool:
        """Bölümün değişip değişmediğini kontrol eder"""
        old_data = self.get_manga_chapter(manga_name)
        if not old_data:
            return True  # İlk kez kontrol ediliyorsa değişiklik var sayılır
        
        return old_data.get('chapter') != new_chapter
    
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
