from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time
import os
from firebase_config import FirebaseNotificationService
from database import DatabaseManager
from scheduler import MangaScheduler

app = Flask(__name__)

# CORS ayarları - production için optimize edildi
if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
    # Production'da tüm originlere izin ver (Android uygulaması için)
    CORS(app, resources={r"/*": {"origins": "*"}})
else:
    # Development'ta tüm CORS açık
    CORS(app)

# Firebase bildirim servisi
notification_service = FirebaseNotificationService()

# Veritabanı yöneticisi
db_manager = DatabaseManager()

class MangaScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def _try_ravenscans(self, manga_name):
        """Raven Scans sitesinden veri çeker"""
        try:
            manga_slug = manga_name.lower().replace(' ', '-').replace(':', '')
            url = f"https://ravenscans.org/manga/{manga_slug}/"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Manga kapak görselini bul
                image_url = None
                img_tag = soup.find('img', class_=re.compile('wp-post-image|attachment'))
                if not img_tag:
                    img_tag = soup.find('img', attrs={'loading': 'lazy'})
                if img_tag:
                    image_url = img_tag.get('src') or img_tag.get('data-src')
                    if image_url and not image_url.startswith('http'):
                        image_url = f"https://ravenscans.org{image_url}"
                
                chapters = soup.find_all('a', href=re.compile(f'/{manga_slug}-chapter-'))
                
                if chapters:
                    # En yüksek bölüm numarasını bul (ters sırada olabilir)
                    latest_chapter_num = None
                    latest_chapter_url = None
                    
                    for chapter_link in chapters:
                        chapter_text = chapter_link.get_text()
                        chapter_url = chapter_link.get('href')
                        
                        # Chapter numarasını bul
                        match = re.search(r'Chapter\s+(\d+(?:\.\d+)?)', chapter_text, re.IGNORECASE)
                        if not match:
                            match = re.search(r'(\d+(?:\.\d+)?)', chapter_text)
                        
                        if match:
                            chapter_num = float(match.group(1))
                            
                            # En yüksek bölümü sakla
                            if latest_chapter_num is None or chapter_num > latest_chapter_num:
                                latest_chapter_num = chapter_num
                                latest_chapter_url = chapter_url
                    
                    if latest_chapter_num:
                        # Tam URL'i oluştur
                        if latest_chapter_url and not latest_chapter_url.startswith('http'):
                            latest_chapter_url = f"https://ravenscans.org{latest_chapter_url}"
                        
                        # Integer olarak döndür
                        return str(int(latest_chapter_num)), latest_chapter_url, image_url
        except Exception as e:
            pass
        return None, None, None
    
    def _try_mangadex(self, manga_name):
        """MangaDex API'sini kullanır - Yedek yöntem"""
        try:
            search_url = "https://api.mangadex.org/manga"
            params = {
                'title': manga_name,
                'limit': 5,
                'contentRating[]': ['safe', 'suggestive', 'erotica'],
                'order[relevance]': 'desc',
                'includes[]': ['cover_art']
            }
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['data']:
                    for manga in data['data']:
                        titles = manga['attributes']['title']
                        alt_titles = manga['attributes'].get('altTitles', [])
                        
                        all_titles = list(titles.values())
                        for alt in alt_titles:
                            all_titles.extend(alt.values())
                        
                        if any(manga_name.lower() in title.lower() for title in all_titles):
                            manga_id = manga['id']
                            
                            # Kapak görselini al
                            image_url = None
                            relationships = manga.get('relationships', [])
                            for rel in relationships:
                                if rel['type'] == 'cover_art':
                                    cover_filename = rel['attributes'].get('fileName')
                                    if cover_filename:
                                        image_url = f"https://uploads.mangadex.org/covers/{manga_id}/{cover_filename}"
                                    break
                            
                            chapters_url = f"https://api.mangadex.org/manga/{manga_id}/feed"
                            chapters_params = {
                                'limit': 1,
                                'order[chapter]': 'desc',
                                'translatedLanguage[]': ['en'],
                                'includeFutureUpdates': '0'
                            }
                            time.sleep(0.5)
                            chapters_response = requests.get(chapters_url, params=chapters_params, timeout=10)
                            
                            if chapters_response.status_code == 200:
                                chapters_data = chapters_response.json()
                                if chapters_data['data']:
                                    chapter_num = chapters_data['data'][0]['attributes'].get('chapter')
                                    chapter_id = chapters_data['data'][0]['id']
                                    if chapter_num:
                                        chapter_url = f"https://mangadex.org/chapter/{chapter_id}"
                                        return chapter_num, chapter_url, image_url
                            break
        except Exception as e:
            pass
        return None, None, None
    
    def get_latest_chapter(self, manga_name):
        """
        Belirtilen manga/manhwa'nın son bölüm numarasını alır
        """
        # Önce Raven Scans'i dene
        chapter, url, image = self._try_ravenscans(manga_name)
        
        # Bulamazsa MangaDex'i dene
        if not chapter:
            chapter, url, image = self._try_mangadex(manga_name)
        
        return {
            'name': manga_name,
            'chapter': chapter if chapter else None,
            'found': chapter is not None,
            'url': url if url else None,
            'image': image if image else None
        }


scraper = MangaScraper()

# Otomatik güncelleme scheduler'ı
manga_scheduler = MangaScheduler(scraper, notification_service, db_manager)

# Production'da scheduler'ı otomatik başlat
if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
    try:
        manga_scheduler.start()
        print("✓ Scheduler production modunda başlatıldı")
    except Exception as e:
        print(f"⚠ Scheduler başlatma hatası: {e}")


@app.route('/', methods=['GET'])
def home():
    """Ana sayfa - API bilgileri"""
    return jsonify({
        'service': 'Manga Notificator API',
        'version': '1.0.0',
        'status': 'online',
        'endpoints': {
            'health_check': {
                'method': 'GET',
                'url': '/health',
                'description': 'API durumunu kontrol et'
            },
            'get_manga_chapters': {
                'method': 'POST',
                'url': '/api/manga/latest',
                'description': 'Manga listesi gönder ve son bölümleri al',
                'request_body': {
                    'manga_list': ['One Piece', 'Lookism', 'Nano Machine']
                },
                'response_example': [
                    {
                        'name': 'One Piece',
                        'chapter': '1171',
                        'found': True,
                        'url': 'https://ravenscans.org/one-piece-chapter-1171/',
                        'image': 'https://ravenscans.org/wp-content/uploads/2024/12/one-piece.jpg'
                    },
                    {
                        'name': 'Lookism',
                        'chapter': '590',
                        'found': True,
                        'url': 'https://ravenscans.org/lookism-chapter-590/',
                        'image': 'https://ravenscans.org/wp-content/uploads/2024/12/lookism.jpg'
                    }
                ]
            }
        },
        'documentation': 'API_KULLANIMI.md dosyasına bakın'
    })


@app.route('/health', methods=['GET'])
def health_check():
    """API'nin çalışıp çalışmadığını kontrol et"""
    return jsonify({
        'status': 'online',
        'message': 'Manga Notificator API is running'
    })


@app.route('/api/manga/latest', methods=['POST', 'OPTIONS'])
def get_latest_chapters():
    """
    Android uygulamasından manga listesi alır ve son bölümleri döndürür
    
    Request Body:
    {
        "manga_list": ["One Piece", "Lookism", "Nano Machine"]
    }
    
    Response:
    [
        {"name": "One Piece", "chapter": "1171", "found": true, "url": "https://ravenscans.org/one-piece-chapter-1171/", "image": "https://ravenscans.org/wp-content/uploads/2024/12/one-piece.jpg"},
        {"name": "Lookism", "chapter": "590", "found": true, "url": "https://ravenscans.org/lookism-chapter-590/", "image": "https://ravenscans.org/wp-content/uploads/2024/12/lookism.jpg"},
        {"name": "Nano Machine", "chapter": "295", "found": true, "url": "https://ravenscans.org/nano-machine-chapter-295/", "image": "https://ravenscans.org/wp-content/uploads/2024/12/nano-machine.jpg"}
    ]
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # JSON verisini al
        data = request.get_json()
        
        if not data or 'manga_list' not in data:
            return jsonify({
                'error': 'manga_list parametresi gerekli'
            }), 400
        
        manga_list = data['manga_list']
        
        if not isinstance(manga_list, list):
            return jsonify({
                'error': 'manga_list bir array olmalı'
            }), 400
        
        if len(manga_list) == 0:
            return jsonify({
                'error': 'manga_list boş olamaz'
            }), 400
        
        # Her manga için bilgileri al
        results = []
        for manga_name in manga_list:
            result = scraper.get_latest_chapter(manga_name)
            results.append(result)
            time.sleep(0.5)  # Rate limiting
        
        # Sadece manga listesini döndür
        return jsonify(results)
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/notification/send', methods=['POST'])
def send_notification():
    """
    FCM ile push notification gönderir
    
    Request Body:
    {
        "token": "device_fcm_token",
        "device": "optional_device_id",
        "title": "Bildirim Başlığı",
        "body": "Bildirim İçeriği",
        "data": {
            "manga_name": "One Piece",
            "chapter": "1171"
        }
    }
    
    Response:
    {
        "success": true,
        "message_id": "projects/...",
        "sent_to": "device_fcm_token"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        # Gerekli parametreleri kontrol et
        token = data.get('token')
        if not token:
            return jsonify({
                'success': False,
                'error': 'token parametresi gerekli'
            }), 400
        
        title = data.get('title', 'Manga Güncelleme')
        body = data.get('body', 'Yeni bölüm yayınlandı')
        notification_data = data.get('data', {})
        
        # Device ID varsa data'ya ekle
        if 'device' in data:
            notification_data['device_id'] = data['device']
        
        # Bildirimi gönder
        result = notification_service.send_notification(
            token=token,
            title=title,
            body=body,
            data=notification_data
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/notification/send-bulk', methods=['POST'])
def send_bulk_notification():
    """
    Birden fazla cihaza toplu bildirim gönderir
    
    Request Body:
    {
        "tokens": ["token1", "token2", "token3"],
        "title": "Bildirim Başlığı",
        "body": "Bildirim İçeriği",
        "data": {
            "manga_name": "One Piece",
            "chapter": "1171"
        }
    }
    
    Response:
    {
        "success": true,
        "success_count": 3,
        "failure_count": 0,
        "total": 3
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        # Gerekli parametreleri kontrol et
        tokens = data.get('tokens')
        if not tokens or not isinstance(tokens, list):
            return jsonify({
                'success': False,
                'error': 'tokens parametresi gerekli ve liste olmalı'
            }), 400
        
        if len(tokens) == 0:
            return jsonify({
                'success': False,
                'error': 'tokens listesi boş olamaz'
            }), 400
        
        title = data.get('title', 'Manga Güncelleme')
        body = data.get('body', 'Yeni bölüm yayınlandı')
        notification_data = data.get('data', {})
        
        # Toplu bildirimi gönder
        result = notification_service.send_bulk_notification(
            tokens=tokens,
            title=title,
            body=body,
            data=notification_data
        )
        
        if result['success']:
            return jsonify(result), 200
        else:
            return jsonify(result), 400
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/auth/register', methods=['POST', 'OPTIONS'])
def auth_register():
    """
    Yeni kullanıcı kaydı (Username/Password)
    
    Request Body:
    {
        "username": "johndoe",
        "password": "securepassword123",
        "fcm_token": "optional_fcm_token"
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        print(f"\n{'='*60}")
        print("📝 REGISTER ENDPOINT ÇAĞRILDI")
        print(f"Request data: {data}")
        print(f"{'='*60}")
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        fcm_token = data.get('fcm_token', '')
        
        print(f"👤 Username: {username}")
        print(f"🔒 Password uzunluğu: {len(password) if password else 0}")
        print(f"📱 FCM Token: {fcm_token[:20]}..." if fcm_token else "Yok")
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'username ve password gerekli'
            }), 400
        
        # Kullanıcı adı kontrolü (alfanumerik ve en az 3 karakter)
        if len(username) < 3 or not username.replace('_', '').replace('-', '').isalnum():
            return jsonify({
                'success': False,
                'error': 'Kullanıcı adı en az 3 karakter olmalı ve sadece harf, rakam, - ve _ içerebilir'
            }), 400
        
        # Şifre uzunluk kontrolü
        if len(password) < 6:
            return jsonify({
                'success': False,
                'error': 'Şifre en az 6 karakter olmalı'
            }), 400
        
        # Kullanıcı oluştur
        print(f"🔨 create_user() çağrılıyor...")
        success = db_manager.create_user(username, password, fcm_token)
        
        print(f"✅ Kayıt sonucu: {success}")
        
        if success:
            # Hemen kontrol et
            all_users = db_manager.get_all_users()
            print(f"📊 Kayıttan sonra toplam kullanıcı: {len(all_users)}")
            print(f"🔑 Kullanıcılar: {list(all_users.keys())}")
            print(f"{'='*60}\n")
            
            return jsonify({
                'success': True,
                'message': 'Kullanıcı başarıyla oluşturuldu',
                'username': username
            }), 201
        else:
            print(f"{'='*60}\n")
            return jsonify({
                'success': False,
                'error': 'Bu kullanıcı adı zaten kullanılıyor'
            }), 409
        
    except Exception as e:
        print(f"❌ REGISTER HATA: {e}")
        print(f"{'='*60}\n")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/auth/login', methods=['POST', 'OPTIONS'])
def auth_login():
    """
    Kullanıcı girişi
    
    Request Body:
    {
        "username": "johndoe",
        "password": "securepassword123"
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        print(f"\n{'='*60}")
        print("🔐 LOGIN ENDPOINT ÇAĞRILDI")
        print(f"Request data: {data}")
        print(f"{'='*60}")
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        print(f"👤 Username: {username}")
        print(f"🔒 Password uzunluğu: {len(password) if password else 0}")
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'username ve password gerekli'
            }), 400
        
        # Önce mevcut kullanıcıları kontrol et
        all_users = db_manager.get_all_users()
        print(f"📊 Database'deki toplam kullanıcı: {len(all_users)}")
        print(f"🔑 Kullanıcılar: {list(all_users.keys())}")
        
        # Kullanıcıyı doğrula
        print(f"🔨 authenticate_user() çağrılıyor...")
        if db_manager.authenticate_user(username, password):
            user_data = db_manager.get_user(username)
            print(f"✅ Doğrulama başarılı, kullanıcı bilgisi alındı")
            print(f"{'='*60}\n")
            return jsonify({
                'success': True,
                'message': 'Giriş başarılı',
                'user': user_data
            }), 200
        else:
            print(f"❌ Doğrulama başarısız")
            print(f"{'='*60}\n")
            return jsonify({
                'success': False,
                'error': 'Kullanıcı adı veya şifre hatalı'
            }), 401
        
    except Exception as e:
        print(f"❌ LOGIN HATA: {e}")
        print(f"{'='*60}\n")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/profile', methods=['POST', 'OPTIONS'])
def get_user_profile():
    """
    Kullanıcı profilini getirir (manga listesi dahil)
    
    Request Body:
    {
        "username": "johndoe",
        "password": "securepassword123"
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({
                'success': False,
                'error': 'username ve password gerekli'
            }), 400
        
        # Kullanıcıyı doğrula
        if not db_manager.authenticate_user(username, password):
            return jsonify({
                'success': False,
                'error': 'Kullanıcı adı veya şifre hatalı'
            }), 401
        
        # Kullanıcı bilgilerini getir
        user_data = db_manager.get_user(username)
        
        if user_data:
            return jsonify({
                'success': True,
                'user': user_data
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Kullanıcı bulunamadı'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/update-token', methods=['POST', 'OPTIONS'])
def update_fcm_token():
    """
    Kullanıcının FCM token'ını günceller
    
    Request Body:
    {
        "username": "johndoe",
        "password": "securepassword123",
        "fcm_token": "new_fcm_token"
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        username = data.get('username')
        password = data.get('password')
        fcm_token = data.get('fcm_token')
        
        if not username or not password or not fcm_token:
            return jsonify({
                'success': False,
                'error': 'username, password ve fcm_token gerekli'
            }), 400
        
        # Kullanıcıyı doğrula
        if not db_manager.authenticate_user(username, password):
            return jsonify({
                'success': False,
                'error': 'Kullanıcı adı veya şifre hatalı'
            }), 401
        
        # Token'ı güncelle
        success = db_manager.update_fcm_token(username, fcm_token)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'FCM token güncellendi'
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Token güncellenirken hata oluştu'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/manga/add', methods=['POST', 'OPTIONS'])
def add_manga():
    """
    Kullanıcının listesine manga ekler
    
    Request Body:
    {
        "username": "johndoe",
        "manga_name": "One Piece"
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        print(f"\n{'='*60}")
        print("➕ ADD MANGA ENDPOINT ÇAĞRILDI")
        print(f"Request data: {data}")
        print(f"{'='*60}")
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        username = data.get('username')
        manga_name = data.get('manga_name')
        
        print(f"👤 Username: {username}")
        print(f"📚 Manga: {manga_name}")
        
        if not username or not manga_name:
            return jsonify({
                'success': False,
                'error': 'username ve manga_name gerekli'
            }), 400
        
        # Önce mevcut tüm kullanıcıları kontrol et
        all_users = db_manager.get_all_users()
        print(f"📊 Database'deki toplam kullanıcı: {len(all_users)}")
        print(f"🔑 Kullanıcılar: {list(all_users.keys())}")
        
        # Kullanıcının var olup olmadığını kontrol et
        user = db_manager.get_user(username)
        if not user:
            print(f"❌ Kullanıcı bulunamadı: {username}")
            print(f"{'='*60}\n")
            return jsonify({
                'success': False,
                'error': 'Kullanıcı bulunamadı'
            }), 404
        
        print(f"✅ Kullanıcı bulundu, manga ekleniyor...")
        print(f"📋 Mevcut manga listesi: {user.get('manga_list', [])}")
        
        # Manga ekle
        success = db_manager.add_manga_to_user(username, manga_name)
        
        if success:
            user_data = db_manager.get_user(username)
            print(f"✅ Manga başarıyla eklendi")
            print(f"📋 Yeni manga listesi: {user_data['manga_list']}")
            print(f"{'='*60}\n")
            return jsonify({
                'success': True,
                'message': 'Manga eklendi',
                'manga_list': user_data['manga_list']
            }), 200
        else:
            print(f"❌ Manga eklenirken hata oluştu")
            print(f"{'='*60}\n")
            return jsonify({
                'success': False,
                'error': 'Manga eklenirken hata oluştu'
            }), 500
        
    except Exception as e:
        print(f"❌ ADD MANGA HATA: {e}")
        print(f"{'='*60}\n")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/manga/remove', methods=['POST', 'OPTIONS'])
def remove_manga():
    """
    Kullanıcının listesinden manga çıkarır
    
    Request Body:
    {
        "username": "johndoe",
        "manga_name": "One Piece"
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        username = data.get('username')
        manga_name = data.get('manga_name')
        
        if not username or not manga_name:
            return jsonify({
                'success': False,
                'error': 'username ve manga_name gerekli'
            }), 400
        
        # Kullanıcının var olup olmadığını kontrol et
        user = db_manager.get_user(username)
        if not user:
            return jsonify({
                'success': False,
                'error': 'Kullanıcı bulunamadı'
            }), 404
        
        # Manga çıkar
        success = db_manager.remove_manga_from_user(username, manga_name)
        
        if success:
            user_data = db_manager.get_user(username)
            return jsonify({
                'success': True,
                'message': 'Manga çıkarıldı',
                'manga_list': user_data['manga_list']
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Manga çıkarılırken hata oluştu'
            }), 500
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/register', methods=['POST', 'OPTIONS'])
def register_user():
    """
    DEPRECATED - Geriye dönük uyumluluk için
    Kullanıcı kaydı ve token kaydetme
    
    Request Body:
    {
        "device_id": "unique_device_id",
        "token": "fcm_token",
        "manga_list": ["One Piece", "Lookism"]
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        device_id = data.get('device_id')
        token = data.get('token')
        manga_list = data.get('manga_list', [])
        
        if not device_id or not token:
            return jsonify({
                'success': False,
                'error': 'device_id ve token gerekli'
            }), 400
        
        # Kullanıcıyı kaydet
        db_manager.add_or_update_user(device_id, token, manga_list)
        
        return jsonify({
            'success': True,
            'message': 'Kullanıcı kaydedildi',
            'device_id': device_id
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/manga-list', methods=['POST', 'OPTIONS'])
def update_manga_list():
    """
    Kullanıcının takip ettiği manga listesini günceller
    
    Request Body:
    {
        "device_id": "unique_device_id",
        "manga_list": ["One Piece", "Lookism", "Solo Leveling"]
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request body gerekli'
            }), 400
        
        device_id = data.get('device_id')
        manga_list = data.get('manga_list')
        
        if not device_id or manga_list is None:
            return jsonify({
                'success': False,
                'error': 'device_id ve manga_list gerekli'
            }), 400
        
        if not isinstance(manga_list, list):
            return jsonify({
                'success': False,
                'error': 'manga_list bir array olmalı'
            }), 400
        
        # Kullanıcının manga listesini güncelle
        success = db_manager.update_user_manga_list(device_id, manga_list)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Manga listesi güncellendi',
                'manga_count': len(manga_list)
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Kullanıcı bulunamadı'
            }), 404
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/user/<device_id>', methods=['GET'])
def get_user(device_id):
    """Kullanıcı bilgilerini getirir"""
    try:
        user = db_manager.get_user(device_id)
        
        if user:
            return jsonify({
                'success': True,
                'user': {
                    'device_id': device_id,
                    'manga_list': user.get('manga_list', []),
                    'created_at': user.get('created_at')
                }
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Kullanıcı bulunamadı'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/list-users', methods=['GET'])
def list_all_users():
    """
    SADECE TEST İÇİN - Tüm kullanıcıları listeler (şifre hariç)
    """
    try:
        print(f"\n{'='*60}")
        print("📋 LIST-USERS ENDPOINT ÇAĞRILDI")
        print(f"{'='*60}")
        
        all_users = db_manager.get_all_users()
        
        print(f"📊 DB'den dönen kullanıcı sayısı: {len(all_users)}")
        print(f"🔑 Kullanıcı adları: {list(all_users.keys())}")
        
        # Şifre hash'lerini çıkar
        users_safe = {}
        for username, user_data in all_users.items():
            print(f"  → {username}: {user_data.get('manga_list', [])} manga")
            users_safe[username] = {
                'username': username,
                'fcm_token': user_data.get('fcm_token', ''),
                'manga_list': user_data.get('manga_list', []),
                'created_at': user_data.get('created_at', ''),
                'has_password': bool(user_data.get('password_hash', ''))
            }
        
        print(f"{'='*60}\n")
        
        return jsonify({
            'success': True,
            'total_users': len(users_safe),
            'users': users_safe,
            'db_path': db_manager.db_path
        }), 200
        
    except Exception as e:
        print(f"❌ LIST-USERS HATA: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/admin/reset-database', methods=['POST', 'OPTIONS'])
def reset_database():
    """
    SADECE TEST İÇİN - Database'i temizler
    
    Request Body:
    {
        "confirm": "RESET_ALL_DATA"
    }
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.get_json()
        
        if not data or data.get('confirm') != 'RESET_ALL_DATA':
            return jsonify({
                'success': False,
                'error': 'Onay gerekli: {"confirm": "RESET_ALL_DATA"}'
            }), 400
        
        # Database'i sıfırla
        db_manager.db = db_manager._create_empty_db()
        db_manager._save_database()
        
        return jsonify({
            'success': True,
            'message': 'Database temizlendi. Yeni kullanıcı kaydedebilirsiniz.'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scheduler/status', methods=['GET'])
def scheduler_status():
    """Scheduler durumunu döner"""
    try:
        stats = db_manager.get_stats()
        next_run = manga_scheduler.get_next_run()
        
        return jsonify({
            'success': True,
            'scheduler': {
                'is_running': manga_scheduler.is_running,
                'test_mode': manga_scheduler.test_mode,
                'next_run': next_run.isoformat() if next_run else None,
                'last_check': stats['last_check']
            },
            'stats': {
                'total_users': stats['total_users'],
                'tracked_manga': len(db_manager.get_all_tracked_manga()),
                'tracked_manga_list': db_manager.get_all_tracked_manga()
            },
            'database': {
                'manga_chapters': db_manager.get_all_manga_chapters()
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scheduler/run-now', methods=['POST', 'OPTIONS'])
def run_scheduler_now():
    """Scheduler'ı hemen çalıştırır (test için)"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        manga_scheduler.run_now()
        return jsonify({
            'success': True,
            'message': 'Kontrol başlatıldı'
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("MANGA NOTIFICATOR API")
    print("=" * 60)
    
    # Environment kontrol
    if os.environ.get('RENDER'):
        print("🌐 Mode: PRODUCTION (Render)")
        port = int(os.environ.get('PORT', 10000))
        print(f"📡 Port: {port}")
    else:
        print("💻 Mode: DEVELOPMENT")
        print("URL: http://localhost:5000")
        port = 5000
    
    print("\nEndpoints:")
    print("  GET  /health                      - API durumunu kontrol et")
    print("  POST /api/manga/latest            - Manga listesi gönder")
    print("  POST /api/notification/send       - Push notification gönder")
    print("  POST /api/notification/send-bulk  - Toplu push notification")
    print("  POST /api/user/register           - Kullanıcı kaydı")
    print("  POST /api/user/manga-list         - Manga listesi güncelle")
    print("  GET  /api/scheduler/status        - Scheduler durumu")
    print("  POST /api/scheduler/run-now       - Manuel kontrol")
    print("=" * 60)
    
    # Scheduler'ı başlat
    if not os.environ.get('RENDER'):
        # Development'ta manuel başlat
        manga_scheduler.start()
    
    # Development server
    app.run(host='0.0.0.0', port=port, debug=not os.environ.get('RENDER'))
