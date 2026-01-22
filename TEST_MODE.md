# Test Modunda Çalıştırma Rehberi

## 🧪 Test Modu Nasıl Çalışır?

Test modunda scheduler **her 2 dakikada bir** otomatik olarak:
1. Tüm kullanıcıların takip ettiği mangaları kontrol eder
2. Yeni bölüm varsa veritabanını günceller
3. İlgili kullanıcılara FCM push notification gönderir

## 🚀 Test Modunu Başlatma

### Local (Development):

```bash
# Environment variable ile test modunu aktif et
set TEST_MODE=true  # Windows
export TEST_MODE=true  # Linux/Mac

# Sunucuyu başlat
python run_server.py
```

### Render (Production Test):

1. **Render Dashboard** → Servisinizi seçin
2. **Environment** sekmesi
3. **Add Environment Variable**
   - Key: `TEST_MODE`
   - Value: `true`
4. **Save Changes**
5. Otomatik redeploy olacak

## 📝 Test Senaryosu

### 1. Kullanıcı Kaydı

Test için bir kullanıcı kaydedin:

```bash
curl -X POST http://localhost:5000/api/user/register \
  -H "Content-Type: application/json" \
  -d '{
    "device_id": "test_device_123",
    "token": "YOUR_FCM_TOKEN_HERE",
    "manga_list": ["One Piece", "Lookism"]
  }'
```

**Response:**
```json
{
  "success": true,
  "message": "Kullanıcı kaydedildi",
  "device_id": "test_device_123"
}
```

### 2. İlk Kontrol

İlk kontrolde tüm mangalar "yeni" olarak algılanacak:

```
============================================================
Manga güncellemeleri kontrol ediliyor... 2026-01-22 15:00:00
============================================================
📚 Kontrol edilen manga sayısı: 2
🔍 Kontrol ediliyor: One Piece
  ✅ YENİ BÖLÜM: One Piece - Chapter 1171
🔍 Kontrol ediliyor: Lookism
  ✅ YENİ BÖLÜM: Lookism - Chapter 590

📢 2 yeni bölüm bulundu!
  ✅ Bildirim gönderildi: One Piece -> 1/1 cihaz
  ✅ Bildirim gönderildi: Lookism -> 1/1 cihaz
============================================================
```

### 3. İkinci Kontrol (2 dakika sonra)

Bölüm değişmediği için bildirim gönderilmeyecek:

```
============================================================
Manga güncellemeleri kontrol ediliyor... 2026-01-22 15:02:00
============================================================
📚 Kontrol edilen manga sayısı: 2
🔍 Kontrol ediliyor: One Piece
  ℹ Değişiklik yok: One Piece - Chapter 1171
🔍 Kontrol ediliyor: Lookism
  ℹ Değişiklik yok: Lookism - Chapter 590

✓ Hiç güncelleme bulunamadı
============================================================
```

### 4. Manuel Güncelleme Simülasyonu

Yeni bölüm simüle etmek için database'i temizleyin:

```bash
# Database'i sıfırla (manga_chapters'ı temizle)
curl -X POST http://localhost:5000/api/scheduler/run-now
```

Veya direkt database.json dosyasını düzenleyin:

```json
{
  "manga_chapters": {
    "One Piece": {
      "chapter": "1170",  // Eski bir bölüm numarası verin
      "url": "...",
      "image": "...",
      "last_checked": "2026-01-22T14:00:00"
    }
  }
}
```

## 📱 Android App ile Test

### FCM Token Alma

Android uygulamanızda:

```kotlin
FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
    if (task.isSuccessful) {
        val token = task.result
        Log.d("FCM", "Token: $token")
        
        // Bu token'ı kullanarak kullanıcı kaydedin
        registerUser("test_device_123", token, listOf("One Piece", "Lookism"))
    }
}
```

### Bildirim Geldiğinde

```kotlin
override fun onMessageReceived(message: RemoteMessage) {
    message.notification?.let {
        Log.d("FCM", "Title: ${it.title}")  // "📖 One Piece"
        Log.d("FCM", "Body: ${it.body}")    // "Yeni bölüm yayınlandı! Chapter 1171"
    }
    
    message.data?.let {
        Log.d("FCM", "Manga: ${it["manga_name"]}")  // "One Piece"
        Log.d("FCM", "Chapter: ${it["chapter"]}")    // "1171"
        Log.d("FCM", "URL: ${it["url"]}")            // "https://..."
        Log.d("FCM", "Image: ${it["image"]}")        // "https://..."
    }
}
```

## 🔍 Monitoring

### Scheduler Durumu

```bash
curl http://localhost:5000/api/scheduler/status
```

**Response:**
```json
{
  "success": true,
  "scheduler": {
    "is_running": true,
    "next_run": "2026-01-22T15:02:00",
    "last_check": "2026-01-22T15:00:00"
  },
  "stats": {
    "total_users": 1,
    "tracked_manga": 2
  }
}
```

### Manuel Kontrol Tetikleme

2 dakika beklemeden hemen kontrol yapmak için:

```bash
curl -X POST http://localhost:5000/api/scheduler/run-now
```

## 📊 Log Takibi

### Local:
Terminal'de tüm loglar görünür.

### Render:
Dashboard → Logs sekmesinde real-time log görüntüleme.

## ⚠️ Önemli Notlar

### Test Modundan Production'a Geçiş

Test tamamlandığında:

1. **Render Dashboard** → Environment Variables
2. `TEST_MODE` değişkenini **silin** veya `false` yapın
3. Servis otomatik redeploy olacak
4. Scheduler günde 1 kez (18:00) çalışacak

### Rate Limiting

Test modunda sık sık web scraping yapıldığı için:
- Rate limit'e takılabilirsiniz
- Raven Scans/MangaDex IP'nizi geçici olarak engelleyebilir
- Üretimde günde 1 kez çalıştırın

### Database

Test modunda database sık sık güncellenir. Render Free plan'de:
- Database ephemeral (geçici)
- Her deploy'da sıfırlanır
- Kalıcı veri için PostgreSQL kullanın

## ✅ Test Checklist

- [ ] TEST_MODE=true environment variable eklendi
- [ ] Sunucu başlatıldı
- [ ] Kullanıcı kaydedildi (FCM token ile)
- [ ] İlk 2 dakika beklendi
- [ ] Bildirim geldi mi kontrol edildi
- [ ] Scheduler status kontrol edildi
- [ ] Loglar incelendi
- [ ] İkinci kontrol (2 dakika sonra) gözlemlendi
- [ ] Test bittikten sonra TEST_MODE kaldırıldı

## 🎯 Başarı Kriterleri

✅ Scheduler her 2 dakikada otomatik çalışıyor
✅ Kullanıcı database'e kaydediliyor
✅ Manga bilgileri web scraping ile alınıyor
✅ Yeni bölüm tespit ediliyor
✅ FCM bildirimi Android cihaza ulaşıyor
✅ Bildirimde manga adı, bölüm, URL ve görsel var
✅ İkinci kontrolde bildirim gönderilmiyor (değişiklik yok)

## 🐛 Sorun Giderme

### Bildirim Gelmiyor
1. FCM token doğru mu?
2. Firebase credentials environment variable'da mı?
3. Android app'te bildirim izni var mı?
4. Logları kontrol edin

### Scheduler Çalışmıyor
1. TEST_MODE=true ayarlandı mı?
2. Sunucu çalışıyor mu?
3. `/api/scheduler/status` endpoint'ini kontrol edin

### Manga Bulunamıyor
1. Manga ismi doğru yazılmış mı?
2. Raven Scans'te sayfa var mı?
3. Rate limit'e takıldınız mı?

---

🎉 **Test başarılı olunca production'a geçebilirsiniz!**
