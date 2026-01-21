"""
Production-ready API server using Waitress
"""
from waitress import serve
from api import app, manga_scheduler
import logging

# Logging ayarları
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    print("=" * 60)
    print("MANGA NOTIFICATOR API - PRODUCTION SERVER")
    print("=" * 60)
    print("Server başlatılıyor...")
    print("URL: http://localhost:5000")
    print("\nEndpoints:")
    print("  GET  /health                      - API durumunu kontrol et")
    print("  POST /api/manga/latest            - Manga listesi gönder")
    print("  POST /api/user/register           - Kullanıcı kaydı")
    print("  POST /api/user/manga-list         - Manga listesi güncelle")
    print("  POST /api/notification/send       - Push notification gönder")
    print("  GET  /api/scheduler/status        - Scheduler durumu")
    print("  POST /api/scheduler/run-now       - Manuel kontrol")
    print("=" * 60)
    
    # Scheduler'ı başlat
    manga_scheduler.start()
    
    print("\nSunucu çalışıyor... (Durdurmak için CTRL+C)")
    print("=" * 60)
    
    # Waitress ile production server
    serve(app, host='0.0.0.0', port=5000, threads=4)
