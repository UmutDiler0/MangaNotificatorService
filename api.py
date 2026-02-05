from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
from bs4 import BeautifulSoup
import re
import time
import os

app = Flask(__name__)

# CORS ayarları - tüm originlere izin ver
CORS(app, resources={r"/*": {"origins": "*"}})


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
                    # En yüksek bölüm numarasını bul
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


class AnimeScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.base_url = "https://9animetv.to"
    
    def _clean_anime_name(self, anime_name):
        """Anime adını URL format\u0131na çevirir"""
        # Küçük harfe çevir ve özel karakterleri temizle
        cleaned = anime_name.lower()
        cleaned = re.sub(r'[^a-z0-9\s-]', '', cleaned)
        cleaned = cleaned.replace(' ', '-')
        cleaned = re.sub(r'-+', '-', cleaned)  # Çoklu tire'leri tek tire yap
        return cleaned.strip('-')
    
    def _try_9animetv(self, anime_name):
        """9animetv.to sitesinden anime bilgilerini çeker"""
        try:
            # Önce arama yap
            search_url = f"{self.base_url}/filter"
            params = {
                'keyword': anime_name
            }
            
            response = requests.get(search_url, headers=self.headers, params=params, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Arama sonuçlarından ilk anime'yi bul
                anime_items = soup.find_all('div', class_='item')
                
                if not anime_items:
                    # Alternatif: Doğrudan anime sayfasına git
                    cleaned_name = self._clean_anime_name(anime_name)
                    direct_url = f"{self.base_url}/watch/{cleaned_name}"
                    response = requests.get(direct_url, headers=self.headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        return self._parse_anime_page(soup, anime_name)
                    return None, None, None
                
                # İlk sonucun linkini al
                first_item = anime_items[0]
                anime_link = first_item.find('a', class_='name')
                
                if anime_link:
                    anime_url = anime_link.get('href')
                    if not anime_url.startswith('http'):
                        anime_url = f"{self.base_url}{anime_url}"
                    
                    # Anime sayfasına git
                    time.sleep(0.5)
                    response = requests.get(anime_url, headers=self.headers, timeout=10)
                    
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.content, 'html.parser')
                        return self._parse_anime_page(soup, anime_name)
            
        except Exception as e:
            print(f"9animetv scraping hatası: {e}")
        
        return None, None, None
    
    def _parse_anime_page(self, soup, anime_name):
        """Anime sayfasını parse eder"""
        try:
            # Poster/kapak görseli bul
            image_url = None
            poster = soup.find('img', class_='film-poster-img')
            if poster:
                image_url = poster.get('src') or poster.get('data-src')
                if image_url and not image_url.startswith('http'):
                    image_url = f"{self.base_url}{image_url}"
            
            # Bölüm listesini bul
            episodes_section = soup.find('div', id='episodes-content')
            if not episodes_section:
                episodes_section = soup.find('div', class_='ss-list')
            
            if episodes_section:
                # Bölüm linklerini bul
                episode_links = episodes_section.find_all('a', class_='ep-item')
                
                if episode_links:
                    # En yüksek bölüm numarasını bul
                    latest_episode_num = None
                    latest_episode_url = None
                    
                    for ep_link in episode_links:
                        ep_data_number = ep_link.get('data-number')
                        ep_title = ep_link.get('title', '')
                        ep_url = ep_link.get('href')
                        
                        # Bölüm numarasını al
                        ep_num = None
                        if ep_data_number:
                            try:
                                ep_num = int(ep_data_number)
                            except:
                                pass
                        
                        if not ep_num:
                            # Title'dan numara çıkarmaya çalış
                            match = re.search(r'Episode\s+(\d+)', ep_title, re.IGNORECASE)
                            if match:
                                ep_num = int(match.group(1))
                        
                        if ep_num:
                            if latest_episode_num is None or ep_num > latest_episode_num:
                                latest_episode_num = ep_num
                                latest_episode_url = ep_url
                    
                    if latest_episode_num:
                        # URL'i düzelt
                        if latest_episode_url and not latest_episode_url.startswith('http'):
                            latest_episode_url = f"{self.base_url}{latest_episode_url}"
                        
                        return str(latest_episode_num), latest_episode_url, image_url
            
        except Exception as e:
            print(f"Anime page parse hatası: {e}")
        
        return None, None, None
    
    def get_latest_episode(self, anime_name):
        """
        Belirtilen anime'nin son bölüm numarasını alır
        """
        episode, url, image = self._try_9animetv(anime_name)
        
        return {
            'name': anime_name,
            'episode': episode if episode else None,
            'found': episode is not None,
            'url': url if url else None,
            'image': image if image else None
        }


anime_scraper = AnimeScraper()


@app.route('/', methods=['GET'])
def home():
    """Ana sayfa - API bilgileri"""
    return jsonify({
        'service': 'Manga & Anime Notificator API',
        'version': '3.0.0',
        'status': 'online',
        'endpoints': {
            'manga': {
                'method': 'POST',
                'url': '/api/manga/latest',
                'description': 'Manga listesi gönder ve son bölümleri al',
                'request_body': {
                    'manga_list': ['Solo Leveling', 'One Piece', 'Lookism']
                }
            },
            'anime': {
                'method': 'POST',
                'url': '/api/anime/latest',
                'description': 'Anime listesi gönder ve son bölümleri al',
                'request_body': {
                    'anime_list': ['One Piece', 'Jujutsu Kaisen', 'Demon Slayer']
                }
            }
        }
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
    Manga listesi alır ve son bölümleri döndürür
    
    Request Body:
    {
        "manga_list": ["Solo Leveling", "One Piece", "Lookism"]
    }
    
    Response:
    [
        {
            "name": "Solo Leveling",
            "chapter": "200",
            "found": true,
            "url": "https://ravenscans.org/solo-leveling-chapter-200/",
            "image": "https://i0.wp.com/ravenscans.org/wp-content/uploads/2025/05/solo-leveling.jpg"
        },
        {
            "name": "One Piece",
            "chapter": "1171",
            "found": true,
            "url": "https://ravenscans.org/one-piece-chapter-1171/",
            "image": "https://ravenscans.org/wp-content/uploads/2024/12/one-piece.jpg"
        }
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


@app.route('/api/anime/latest', methods=['POST', 'OPTIONS'])
def get_latest_episodes():
    """
    Anime listesi alır ve son bölümleri döndürür
    
    Request Body:
    {
        "anime_list": ["One Piece", "Jujutsu Kaisen", "Demon Slayer"]
    }
    
    Response:
    [
        {
            "name": "One Piece",
            "episode": "1095",
            "found": true,
            "url": "https://9animetv.to/watch/one-piece-100/ep-1095",
            "image": "https://9animetv.to/images/one-piece.jpg"
        },
        {
            "name": "Jujutsu Kaisen",
            "episode": "47",
            "found": true,
            "url": "https://9animetv.to/watch/jujutsu-kaisen/ep-47",
            "image": "https://9animetv.to/images/jujutsu-kaisen.jpg"
        }
    ]
    """
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        # JSON verisini al
        data = request.get_json()
        
        if not data or 'anime_list' not in data:
            return jsonify({
                'error': 'anime_list parametresi gerekli'
            }), 400
        
        anime_list = data['anime_list']
        
        if not isinstance(anime_list, list):
            return jsonify({
                'error': 'anime_list bir array olmalı'
            }), 400
        
        if len(anime_list) == 0:
            return jsonify({
                'error': 'anime_list boş olamaz'
            }), 400
        
        # Her anime için bilgileri al
        results = []
        for anime_name in anime_list:
            result = anime_scraper.get_latest_episode(anime_name)
            results.append(result)
            time.sleep(0.5)  # Rate limiting
        
        # Anime listesini döndür
        return jsonify(results)
    
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


if __name__ == '__main__':
    print("=" * 60)
    print("MANGA & ANIME NOTIFICATOR API")
    print("=" * 60)
    
    # Environment kontrol
    if os.environ.get('RENDER'):
        print("🌐 Mode: PRODUCTION (Render)")
        port = int(os.environ.get('PORT', 10000))
        print(f"📡 Port: {port}")
    else:
        print("💻 Mode: DEVELOPMENT")
        print("🔗 URL: http://localhost:5000")
        port = 5000
    
    print("\n✨ Endpoints:")
    print("  POST /api/manga/latest  - Manga listesi gönder, son bölümleri al")
    print("  POST /api/anime/latest  - Anime listesi gönder, son bölümleri al")
    print("\n📝 Örnek Request Body:")
    print('  Manga: {"manga_list": ["Solo Leveling", "One Piece"]}')
    print('  Anime: {"anime_list": ["One Piece", "Jujutsu Kaisen"]}')
    print("=" * 60)
    
    # Development server
    app.run(host='0.0.0.0', port=port, debug=False)

# WSGI uyumluluk için (Gunicorn, uWSGI, vb.)
application = app
