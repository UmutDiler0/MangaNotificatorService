import requests
from bs4 import BeautifulSoup
import re
import time

class MangaScraper:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def _try_ravenscans(self, manga_name):
        """Raven Scans sitesinden veri çeker"""
        try:
            # Manga ismini URL formatına çevir
            manga_slug = manga_name.lower().replace(' ', '-').replace(':', '')
            url = f"https://ravenscans.org/manga/{manga_slug}/"
            
            response = requests.get(url, headers=self.headers, timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Son bölümü bul - sitede "Chapter X" formatında
                chapters = soup.find_all('a', href=re.compile(f'/{manga_slug}-chapter-'))
                
                if chapters:
                    # İlk link genellikle en son bölümdür
                    first_chapter = chapters[0]
                    chapter_text = first_chapter.get_text()
                    
                    # "Chapter 590" gibi formatlardan sayıyı çıkar
                    match = re.search(r'Chapter\s+(\d+)', chapter_text, re.IGNORECASE)
                    if match:
                        return match.group(1)
                    
                    # Sadece sayı varsa
                    match = re.search(r'(\d+)', chapter_text)
                    if match:
                        return match.group(1)
        except Exception as e:
            pass
        return None
    
    def _try_mangadex(self, manga_name):
        """MangaDex API'sini kullanır - Yedek yöntem"""
        try:
            # MangaDex API ile arama yap
            search_url = "https://api.mangadex.org/manga"
            params = {
                'title': manga_name,
                'limit': 5,
                'contentRating[]': ['safe', 'suggestive', 'erotica'],
                'order[relevance]': 'desc'
            }
            response = requests.get(search_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if data['data']:
                    # En alakalı sonucu bul
                    for manga in data['data']:
                        titles = manga['attributes']['title']
                        alt_titles = manga['attributes'].get('altTitles', [])
                        
                        # Başlık eşleşmesi kontrol et
                        all_titles = list(titles.values())
                        for alt in alt_titles:
                            all_titles.extend(alt.values())
                        
                        if any(manga_name.lower() in title.lower() for title in all_titles):
                            manga_id = manga['id']
                            
                            # Son bölümü al
                            chapters_url = f"https://api.mangadex.org/manga/{manga_id}/feed"
                            chapters_params = {
                                'limit': 1,
                                'order[chapter]': 'desc',
                                'translatedLanguage[]': ['en'],
                                'includeFutureUpdates': '0'
                            }
                            time.sleep(0.5)  # Rate limiting
                            chapters_response = requests.get(chapters_url, params=chapters_params, timeout=10)
                            
                            if chapters_response.status_code == 200:
                                chapters_data = chapters_response.json()
                                if chapters_data['data']:
                                    chapter_num = chapters_data['data'][0]['attributes'].get('chapter')
                                    if chapter_num:
                                        return chapter_num
                            break
        except Exception as e:
            pass
        return None
    
    def get_latest_chapter(self, manga_name):
        """
        Belirtilen manga/manhwa'nın son bölüm numarasını alır
        Önce Raven Scans'i dener, sonra MangaDex'i yedek olarak kullanır
        """
        # Önce Raven Scans'i dene
        chapter = self._try_ravenscans(manga_name)
        
        # Bulamazsa MangaDex'i dene
        if not chapter:
            chapter = self._try_mangadex(manga_name)
        
        if chapter:
            return f"{manga_name} {chapter}"
        else:
            return f"{manga_name}: Bulunamadı"
    
    def get_multiple_manga_chapters(self, manga_list):
        """
        Birden fazla manga için son bölümleri alır
        """
        results = []
        print(f"\n{len(manga_list)} manga için bilgi alınıyor...\n")
        
        for i, manga in enumerate(manga_list, 1):
            print(f"[{i}/{len(manga_list)}] {manga} kontrol ediliyor...")
            result = self.get_latest_chapter(manga)
            results.append(result)
            time.sleep(0.5)  # Rate limiting
        
        return results


def main():
    scraper = MangaScraper()
    
    # İstenen manga/manhwa listesi
    manga_list = [
        "One Piece",
        "Lookism",
        "Nano Machine"
    ]
    
    print("=" * 50)
    print("RAVEN SCANS - MANGA/MANHWA SON BÖLÜM BİLGİLERİ")
    print("=" * 50)
    
    results = scraper.get_multiple_manga_chapters(manga_list)
    
    print("\n" + "=" * 50)
    print("SONUÇLAR:")
    print("=" * 50)
    for result in results:
        print(f"  {result}")
    print("=" * 50)


if __name__ == "__main__":
    main()