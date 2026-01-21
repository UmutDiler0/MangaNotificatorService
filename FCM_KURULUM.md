# Firebase Cloud Messaging (FCM) Kurulumu

## 1. Firebase Console Adımları

### Firebase Projesi Oluşturma
1. [Firebase Console](https://console.firebase.google.com/) adresine gidin
2. "Add Project" tıklayın
3. Proje adını girin (örn: manga-notificator)
4. Google Analytics'i etkinleştirin (isteğe bağlı)
5. "Create Project" tıklayın

### Android Uygulamasını Firebase'e Ekleme
1. Firebase Console'da projenize tıklayın
2. "Add App" > Android simgesine tıklayın
3. Android paket adınızı girin (örn: com.yourcompany.manganotificator)
4. "Register app" tıklayın
5. `google-services.json` dosyasını indirin
6. Bu dosyayı Android projenizin `app/` klasörüne koyun

### Servis Hesabı JSON Dosyasını İndirme
1. Firebase Console'da projenize gidin
2. Sol üst köşedeki ⚙️ (Settings) > Project Settings
3. "Service Accounts" sekmesine tıklayın
4. "Generate new private key" butonuna tıklayın
5. İndirilen JSON dosyasını `firebase-service-account.json` olarak kaydedin
6. Bu dosyayı backend proje klasörüne (`manga_notificator/`) koyun

## 2. Backend Kurulumu

Backend zaten hazır! Sadece Firebase servis hesabı dosyasını eklemeniz yeterli:

```
manga_notificator/
├── api.py
├── firebase_config.py
├── firebase-service-account.json  ← Bu dosyayı ekleyin
└── ...
```

## 3. Android Uygulama Kurulumu

### build.gradle (Project level)
```gradle
buildscript {
    dependencies {
        classpath 'com.google.gms:google-services:4.4.0'
    }
}
```

### build.gradle (App level)
```gradle
plugins {
    id 'com.android.application'
    id 'com.google.gms.google-services'  // En alta ekleyin
}

dependencies {
    implementation platform('com.google.firebase:firebase-bom:32.7.0')
    implementation 'com.google.firebase:firebase-messaging-ktx'
}
```

### AndroidManifest.xml
```xml
<manifest>
    <uses-permission android:name="android.permission.INTERNET" />
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />

    <application>
        <!-- Firebase Messaging Service -->
        <service
            android:name=".MyFirebaseMessagingService"
            android:exported="false">
            <intent-filter>
                <action android:name="com.google.firebase.MESSAGING_EVENT" />
            </intent-filter>
        </service>

        <!-- Notification Channel -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_channel_id"
            android:value="manga_updates" />
    </application>
</manifest>
```

### MyFirebaseMessagingService.kt
```kotlin
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import android.util.Log
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

class MyFirebaseMessagingService : FirebaseMessagingService() {

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        Log.d("FCM", "New token: $token")
        
        // Token'ı backend'e kaydedin
        sendTokenToServer(token)
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        
        message.notification?.let {
            showNotification(it.title ?: "", it.body ?: "")
        }
    }

    private fun showNotification(title: String, body: String) {
        val notificationManager = getSystemService(NOTIFICATION_SERVICE) as NotificationManager
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                "manga_updates",
                "Manga Updates",
                NotificationManager.IMPORTANCE_HIGH
            )
            notificationManager.createNotificationChannel(channel)
        }
        
        val notification = NotificationCompat.Builder(this, "manga_updates")
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setAutoCancel(true)
            .build()
        
        notificationManager.notify(System.currentTimeMillis().toInt(), notification)
    }

    private fun sendTokenToServer(token: String) {
        // Backend'e token'ı gönderin
        // Retrofit veya başka HTTP client kullanabilirsiniz
    }
}
```

### MainActivity.kt - FCM Token Alma
```kotlin
import com.google.firebase.messaging.FirebaseMessaging

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // FCM Token'ı al
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (task.isSuccessful) {
                val token = task.result
                Log.d("FCM", "Token: $token")
                
                // Backend'e token'ı gönderin
                sendTokenToBackend(token)
            }
        }
    }
    
    private fun sendTokenToBackend(token: String) {
        // API'nize token'ı gönderin
    }
}
```

## 4. API Kullanımı

### Tek Cihaza Bildirim Gönderme

**Endpoint:** `POST /api/notification/send`

**Request Body:**
```json
{
  "token": "fcm_device_token_here",
  "device": "device_id_optional",
  "title": "One Piece Güncelleme",
  "body": "Bölüm 1171 yayınlandı!",
  "data": {
    "manga_name": "One Piece",
    "chapter": "1171",
    "url": "https://ravenscans.org/one-piece-chapter-1171/"
  }
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "projects/manga-notificator/messages/0:1234567890",
  "sent_to": "fcm_device_token_here"
}
```

### Toplu Bildirim Gönderme

**Endpoint:** `POST /api/notification/send-bulk`

**Request Body:**
```json
{
  "tokens": [
    "token1",
    "token2",
    "token3"
  ],
  "title": "Manga Güncellemeleri",
  "body": "Yeni bölümler yayınlandı!",
  "data": {
    "type": "bulk_update"
  }
}
```

**Response:**
```json
{
  "success": true,
  "success_count": 3,
  "failure_count": 0,
  "total": 3
}
```

## 5. Test Etme

### Postman veya cURL ile Test
```bash
curl -X POST http://localhost:5000/api/notification/send \
  -H "Content-Type: application/json" \
  -d '{
    "token": "your_fcm_token_here",
    "title": "Test Bildirimi",
    "body": "Bu bir test bildirimidir"
  }'
```

## Güvenlik Notları

⚠️ **ÖNEMLİ:**
- `firebase-service-account.json` dosyasını **asla Git'e eklemeyin**
- `.gitignore` dosyasına `firebase-service-account.json` ekleyin
- Bu dosya production sunucuda güvenli bir yerde saklanmalı
- Android uygulama için `google-services.json` gereklidir ama backend için değil

## Sorun Giderme

### "Firebase Admin SDK başlatılmadı" hatası
- `firebase-service-account.json` dosyasının doğru konumda olduğundan emin olun
- JSON dosyasının geçerli olduğunu kontrol edin

### Token geçersiz hatası
- FCM token'ın geçerli olduğundan emin olun
- Uygulama kaldırılıp yeniden yüklendiğinde token değişir
- Token süresinin dolmuş olabilir

### Bildirim gelmiyor
- Android cihazda bildirim izinlerinin verildiğinden emin olun
- Notification channel'ın oluşturulduğunu kontrol edin
- Firebase Console'da test bildirimi göndererek kontrol edin
