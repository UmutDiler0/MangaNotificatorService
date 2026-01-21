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

@app.route("/")
def home():
    return "OK"

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
                    first_chapter = chapters[0]
                    chapter_text = first_chapter.get_text()
                    chapter_url = first_chapter.get('href')
                    
                    # Tam URL'i oluştur
                    if chapter_url and not chapter_url.startswith('http'):
                        chapter_url = f"https://ravenscans.org{chapter_url}"
                    
                    match = re.search(r'Chapter\s+(\d+)', chapter_text, re.IGNORECASE)
                    if match:
                        return match.group(1), chapter_url, image_url
                    
                    match = re.search(r'(\d+)', chapter_text)
                    if match:
                        return match.group(1), chapter_url, image_url
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

# Scheduler'ı başlat (production'da)
import os
if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
    manga_scheduler.start()
    print("✓ Scheduler production modunda başlatıldı")


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


@app.route('/api/manga/latest', methods=['POST'])
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


@app.route('/api/user/register', methods=['POST'])
def register_user():
    """
    Kullanıcı kaydı ve token kaydetme
    
    Request Body:
    {
        "device_id": "unique_device_id",
        "token": "fcm_token",
        "manga_list": ["One Piece", "Lookism"]
    }
    """
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


@app.route('/api/user/manga-list', methods=['POST'])
def update_manga_list():
    """
    Kullanıcının takip ettiği manga listesini günceller
    
    Request Body:
    {
        "device_id": "unique_device_id",
        "manga_list": ["One Piece", "Lookism", "Solo Leveling"]
    }
    """
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
                'next_run': next_run.isoformat() if next_run else None,
                'last_check': stats['last_check']
            },
            'stats': {
                'total_users': stats['total_users'],
                'tracked_manga': len(db_manager.get_all_tracked_manga())
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/scheduler/run-now', methods=['POST'])
def run_scheduler_now():
    """Scheduler'ı hemen çalıştırır (test için)"""
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
