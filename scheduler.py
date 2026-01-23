from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime
import time
import os
from database import DatabaseManager
from firebase_config import FirebaseNotificationService

class MangaScheduler:
    def __init__(self, manga_scraper, notification_service: FirebaseNotificationService, db_manager: DatabaseManager):
        self.manga_scraper = manga_scraper
        self.notification_service = notification_service
        self.db_manager = db_manager
        self.scheduler = BackgroundScheduler()
        self.is_running = False
        self.test_mode = os.environ.get('TEST_MODE', 'false').lower() == 'true'
    
    def check_single_manga_by_position(self):
        """Her 14 dakikada bir, sıradaki pozisyondaki mangaları kontrol eder"""
        print(f"\n{'='*60}")
        print(f"⏰ Pozisyon bazlı manga kontrolü... {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")
        
        try:
            # Tüm kullanıcıları al
            all_users = self.db_manager.get_all_users()
            
            if not all_users:
                print("⚠ Kayıtlı kullanıcı yok")
                return
            
            # Kontrol edilecek pozisyonu al/başlat
            if not hasattr(self, 'current_position'):
                self.current_position = 0
            
            # Bu pozisyondaki tüm benzersiz mangaları topla
            manga_at_position = set()
            max_list_length = 0
            
            for device_id, user_data in all_users.items():
                manga_list = user_data.get('manga_list', [])
                max_list_length = max(max_list_length, len(manga_list))
                
                # Bu pozisyonda manga varsa ekle
                if self.current_position < len(manga_list):
                    manga_at_position.add(manga_list[self.current_position])
            
            # Manga yoksa başa dön
            if not manga_at_position:
                print(f"📍 Pozisyon {self.current_position + 1}: Manga yok, başa dönülüyor")
                self.current_position = 0
                return
            
            print(f"📍 Pozisyon {self.current_position + 1}: {len(manga_at_position)} manga kontrol edilecek")
            
            updates_found = []
            
            # Bu pozisyondaki her mangayı kontrol et
            for manga_name in manga_at_position:
                try:
                    print(f"🔍 Kontrol ediliyor: {manga_name}")
                    
                    # Manga bilgilerini çek
                    manga_info = self.manga_scraper.get_latest_chapter(manga_name)
                    
                    if manga_info['found']:
                        new_chapter = manga_info['chapter']
                        
                        # Önceki bölüm bilgisini al
                        old_info = self.db_manager.get_manga_chapter(manga_name)
                        
                        # Bölüm değişikliğini kontrol et
                        is_new, has_changed = self.db_manager.check_chapter_changed(manga_name, new_chapter)
                        
                        if is_new:
                            # İlk kez kontrol ediliyor - sadece kaydet
                            print(f"  📝 İlk kayıt: {manga_name} - Chapter {new_chapter}")
                            self.db_manager.update_manga_chapter(
                                manga_name=manga_name,
                                chapter=new_chapter,
                                url=manga_info['url'],
                                image=manga_info['image']
                            )
                        elif has_changed:
                            # Bölüm değişmiş - güncelle ve bildirim gönder
                            old_chapter = old_info['chapter'] if old_info else 'unknown'
                            print(f"  ✅ YENİ BÖLÜM: {manga_name} - {old_chapter} → {new_chapter}")
                            
                            # Veritabanını güncelle
                            self.db_manager.update_manga_chapter(
                                manga_name=manga_name,
                                chapter=new_chapter,
                                url=manga_info['url'],
                                image=manga_info['image']
                            )
                            
                            # Güncelleme bilgisini kaydet
                            updates_found.append({
                                'manga_name': manga_name,
                                'chapter': new_chapter,
                                'url': manga_info['url'],
                                'image': manga_info['image'],
                                'old_chapter': old_chapter
                            })
                        else:
                            print(f"  ℹ Değişiklik yok: {manga_name} - Chapter {new_chapter}")
                    else:
                        print(f"  ❌ Bulunamadı: {manga_name}")
                    
                except Exception as e:
                    print(f"  ❌ Hata ({manga_name}): {e}")
                    continue
            
            # Güncelleme varsa bildirimleri gönder
            if updates_found:
                print(f"\n📢 {len(updates_found)} yeni bölüm bulundu!")
                self._send_update_notifications(updates_found)
            
            # Sonraki pozisyona geç
            self.current_position += 1
            
            # En uzun listenin sonuna geldiysek başa dön
            if self.current_position >= max_list_length:
                print(f"\n🔄 Tüm pozisyonlar kontrol edildi, başa dönülüyor\n")
                self.current_position = 0
            else:
                print(f"\n➡️  Sonraki pozisyon: {self.current_position + 1}\n")
            
            # Son kontrol zamanını güncelle
            self.db_manager.update_last_check()
            
            print(f"{'='*60}\n")
            
        except Exception as e:
            print(f"❌ Kontrol hatası: {e}")
    
    def check_manga_updates(self):
        """Eski metod - geriye uyumluluk için"""
        self.check_single_manga_by_position()
    
    def _send_update_notifications(self, updates):
        """Güncellenen mangalar için bildirimleri gönderir"""
        try:
            # Tüm kullanıcıları al
            all_users = self.db_manager.get_all_users()
            
            if not all_users:
                print("⚠ Bildirim gönderilecek kullanıcı yok")
                return
            
            # Her güncelleme için
            for update in updates:
                manga_name = update['manga_name']
                chapter = update['chapter']
                url = update['url']
                image = update['image']
                old_chapter = update['old_chapter']
                
                # Bu mangayı takip eden kullanıcıları bul
                tokens_to_send = []
                for device_id, user_data in all_users.items():
                    if manga_name in user_data.get('manga_list', []):
                        tokens_to_send.append(user_data['token'])
                
                if tokens_to_send:
                    # Bildirim başlığı ve içeriği
                    title = f"{manga_name} - Yeni Bölüm!"
                    body = f"Chapter {chapter} yayınlandı! 📖"
                    
                    # Bildirim verisi
                    notification_data = {
                        'type': 'chapter_update',
                        'manga_name': manga_name,
                        'chapter': chapter,
                        'old_chapter': old_chapter,
                        'url': url or '',
                        'image': image or ''
                    }
                    
                    # Toplu bildirim gönder
                    result = self.notification_service.send_bulk_notification(
                        tokens=tokens_to_send,
                        title=title,
                        body=body,
                        data=notification_data
                    )
                    
                    if result['success']:
                        print(f"  ✅ Bildirim gönderildi: {manga_name} -> {result['success_count']}/{len(tokens_to_send)} cihaz")
                    else:
                        print(f"  ❌ Bildirim hatası: {result.get('error')}")
                else:
                    print(f"  ℹ {manga_name} için bildirim gönderilecek kullanıcı yok")
                    
        except Exception as e:
            print(f"❌ Bildirim gönderme hatası: {e}")
    
    def start(self):
        """Scheduler'ı başlatır - Her 3 saatte bir çalışır, mangalar arası 14 dakika"""
        if self.is_running:
            print("⚠ Scheduler zaten çalışıyor")
            return
        
        if self.test_mode:
            # TEST MODE: Her 2 dakikada bir çalışır (hızlı test için)
            self.scheduler.add_job(
                self.check_manga_updates,
                'interval',
                minutes=2,
                id='manga_update_check',
                name='Manga Güncelleme Kontrolü (TEST)',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            print("\n" + "="*60)
            print("🧪 TEST MODU AKTİF - OTOMATIK GÜNCELLEME")
            print("="*60)
            print("⏰ Kontrol Zamanı: Her 2 dakikada bir")
            print("📍 Pozisyon bazlı kontrol (1. manga → 2. manga → ...)")
            print("📊 Durum: Çalışıyor")
        else:
            # PRODUCTION MODE: Her 14 dakikada bir çalışır
            self.scheduler.add_job(
                self.check_manga_updates,
                'interval',
                minutes=14,
                id='manga_update_check',
                name='Manga Güncelleme Kontrolü (14 Dakika)',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            
            print("\n" + "="*60)
            print("🕐 OTOMATIK GÜNCELLEME SİSTEMİ AKTİF")
            print("="*60)
            print("⏰ Kontrol Zamanı: Her 14 dakikada bir")
            print("📍 Her seferinde sıradaki pozisyonun mangalarını kontrol eder")
            print("🔄 Render sürekli aktif kalır")
            print("📊 Durum: Çalışıyor")
        
        # İstatistikler
        stats = self.db_manager.get_stats()
        print(f"👥 Kayıtlı Kullanıcı: {stats['total_users']}")
        print(f"📚 Takip Edilen Manga: {len(self.db_manager.get_all_tracked_manga())}")
        if stats['last_check']:
            print(f"🕒 Son Kontrol: {stats['last_check']}")
        print("="*60 + "\n")
    
    def stop(self):
        """Scheduler'ı durdurur"""
        if not self.is_running:
            print("⚠ Scheduler zaten durmuş")
            return
        
        self.scheduler.shutdown()
        self.is_running = False
        print("✓ Scheduler durduruldu")
    
    def run_now(self):
        """Hemen bir kontrol çalıştırır (test için)"""
        print("🚀 Manuel kontrol başlatılıyor...")
        self.check_manga_updates()
    
    def get_next_run(self):
        """Bir sonraki çalışma zamanını döner"""
        if not self.is_running:
            return None
        
        job = self.scheduler.get_job('manga_update_check')
        if job:
            return job.next_run_time
        return None
