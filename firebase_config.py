import firebase_admin
from firebase_admin import credentials, messaging
import os
import json
import base64

class FirebaseNotificationService:
    def __init__(self):
        self.initialized = False
        self._initialize_firebase()
    
    def _initialize_firebase(self):
        """Firebase Admin SDK'yı başlatır"""
        try:
            # Önce environment variable'ları kontrol et (Render, Heroku vb. için)
            if os.environ.get('FIREBASE_CREDENTIALS'):
                # JSON string olarak environment variable
                cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                print("✓ Firebase Admin SDK başlatıldı (Environment Variable)")
                return
            
            elif os.environ.get('FIREBASE_CREDENTIALS_BASE64'):
                # Base64 encoded JSON
                cred_json = base64.b64decode(os.environ.get('FIREBASE_CREDENTIALS_BASE64'))
                cred_dict = json.loads(cred_json)
                cred = credentials.Certificate(cred_dict)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                print("✓ Firebase Admin SDK başlatıldı (Base64)")
                return
            
            # Local file kontrolü (development için)
            service_account_path = os.path.join(os.path.dirname(__file__), 'firebase-service-account.json')
            
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                print("✓ Firebase Admin SDK başlatıldı (Local File)")
            else:
                print("⚠ firebase-service-account.json dosyası bulunamadı")
                print("⚠ Firebase Console'dan servis hesabı JSON dosyasını indirip proje klasörüne kaydedin")
                print("⚠ Veya FIREBASE_CREDENTIALS environment variable'ını ayarlayın")
                self.initialized = False
        except Exception as e:
            print(f"⚠ Firebase başlatma hatası: {e}")
            self.initialized = False
    
    def send_notification(self, token, title, body, data=None):
        """
        FCM üzerinden push notification gönderir
        
        Args:
            token (str): Android cihazın FCM token'ı
            title (str): Bildirim başlığı
            body (str): Bildirim içeriği
            data (dict): Ek veri (opsiyonel)
        
        Returns:
            dict: Başarı/hata bilgisi
        """
        if not self.initialized:
            return {
                'success': False,
                'error': 'Firebase Admin SDK başlatılmadı. firebase-service-account.json dosyasını ekleyin.'
            }
        
        try:
            # Bildirim mesajını oluştur
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=data if data else {},
                token=token,
                android=messaging.AndroidConfig(
                    priority='high',
                    notification=messaging.AndroidNotification(
                        sound='default',
                        channel_id='manga_updates'
                    )
                )
            )
            
            # Mesajı gönder
            response = messaging.send(message)
            
            return {
                'success': True,
                'message_id': response,
                'sent_to': token
            }
            
        except messaging.UnregisteredError:
            return {
                'success': False,
                'error': 'Token geçersiz veya uygulaması kaldırılmış'
            }
        except messaging.SenderIdMismatchError:
            return {
                'success': False,
                'error': 'Token bu Firebase projesine ait değil'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Bildirim gönderme hatası: {str(e)}'
            }
    
    def send_bulk_notification(self, tokens, title, body, data=None):
        """
        Birden fazla cihaza toplu bildirim gönderir
        
        Args:
            tokens (list): FCM token listesi
            title (str): Bildirim başlığı
            body (str): Bildirim içeriği
            data (dict): Ek veri (opsiyonel)
        
        Returns:
            dict: Başarı/hata bilgisi
        """
        if not self.initialized:
            return {
                'success': False,
                'error': 'Firebase Admin SDK başlatılmadı'
            }
        
        try:
            # Çoklu mesaj oluştur
            messages = []
            for token in tokens:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title=title,
                        body=body,
                    ),
                    data=data if data else {},
                    token=token,
                    android=messaging.AndroidConfig(
                        priority='high',
                        notification=messaging.AndroidNotification(
                            sound='default',
                            channel_id='manga_updates'
                        )
                    )
                )
                messages.append(message)
            
            # Toplu gönder
            response = messaging.send_all(messages)
            
            return {
                'success': True,
                'success_count': response.success_count,
                'failure_count': response.failure_count,
                'total': len(tokens)
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Toplu bildirim hatası: {str(e)}'
            }
