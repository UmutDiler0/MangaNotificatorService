# Otomatik Bildirim Sistemi Kullanımı

## Nasıl Çalışır?

1. **Kullanıcı Kaydı**: Android uygulamadan kullanıcılar FCM token'larını ve takip etmek istedikleri manga listesini kaydederler
2. **Otomatik Kontrol**: Her gün saat **18:00**'de sistem otomatik olarak tüm takip edilen mangaları kontrol eder
3. **Bildirim Gönderimi**: Yeni bölüm tespit edilirse, o mangayı takip eden tüm kullanıcılara FCM ile push notification gönderilir

## Android Entegrasyonu

### 1. Kullanıcı Kaydı (İlk Açılışta)

```kotlin
// Kullanıcıyı kaydet ve FCM token'ı gönder
suspend fun registerUser(deviceId: String, fcmToken: String, mangaList: List<String>) {
    val request = RegisterRequest(
        device_id = deviceId,
        token = fcmToken,
        manga_list = mangaList
    )
    
    val response = apiService.registerUser(request)
    // Kullanıcı kaydedildi
}
```

**Endpoint:** `POST /api/user/register`

**Request:**
```json
{
  "device_id": "unique_device_id_12345",
  "token": "fcm_token_from_firebase",
  "manga_list": ["One Piece", "Lookism", "Solo Leveling"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Kullanıcı kaydedildi",
  "device_id": "unique_device_id_12345"
}
```

### 2. Manga Listesi Güncelleme

Kullanıcı takip listesine manga ekler/çıkarırsa:

```kotlin
suspend fun updateMangaList(deviceId: String, mangaList: List<String>) {
    val request = UpdateMangaListRequest(
        device_id = deviceId,
        manga_list = mangaList
    )
    
    val response = apiService.updateMangaList(request)
}
```

**Endpoint:** `POST /api/user/manga-list`

**Request:**
```json
{
  "device_id": "unique_device_id_12345",
  "manga_list": ["One Piece", "Lookism", "Solo Leveling", "Nano Machine"]
}
```

**Response:**
```json
{
  "success": true,
  "message": "Manga listesi güncellendi",
  "manga_count": 4
}
```

### 3. Kullanıcı Bilgilerini Alma

```kotlin
suspend fun getUserInfo(deviceId: String): UserInfo {
    val response = apiService.getUserInfo(deviceId)
    return response.user
}
```

**Endpoint:** `GET /api/user/{device_id}`

**Response:**
```json
{
  "success": true,
  "user": {
    "device_id": "unique_device_id_12345",
    "manga_list": ["One Piece", "Lookism"],
    "created_at": "2026-01-21T12:00:00"
  }
}
```

### 4. Bildirimleri Alma (FCM)

Bildirimleri almak için `MyFirebaseMessagingService.kt` kullanın:

```kotlin
override fun onMessageReceived(message: RemoteMessage) {
    message.notification?.let {
        val title = it.title ?: ""
        val body = it.body ?: ""
        
        // Data payload
        val mangaName = message.data["manga_name"]
        val chapter = message.data["chapter"]
        val url = message.data["url"]
        val image = message.data["image"]
        
        // Bildirimi göster
        showNotification(title, body, url, image)
    }
}
```

**Bildirim Data Formatı:**
```json
{
  "type": "chapter_update",
  "manga_name": "One Piece",
  "chapter": "1171",
  "url": "https://ravenscans.org/one-piece-chapter-1171/",
  "image": "https://ravenscans.org/wp-content/uploads/2025/09/one-piece.jpg"
}
```

## API Retrofit Interface

```kotlin
interface MangaApi {
    @POST("/api/user/register")
    suspend fun registerUser(@Body request: RegisterRequest): RegisterResponse
    
    @POST("/api/user/manga-list")
    suspend fun updateMangaList(@Body request: UpdateMangaListRequest): UpdateMangaListResponse
    
    @GET("/api/user/{device_id}")
    suspend fun getUserInfo(@PathVariable("device_id") deviceId: String): UserInfoResponse
    
    @GET("/api/scheduler/status")
    suspend fun getSchedulerStatus(): SchedulerStatusResponse
}

data class RegisterRequest(
    val device_id: String,
    val token: String,
    val manga_list: List<String>
)

data class UpdateMangaListRequest(
    val device_id: String,
    val manga_list: List<String>
)
```

## Test ve Debug

### Scheduler Durumu Kontrolü

**Endpoint:** `GET /api/scheduler/status`

**Response:**
```json
{
  "success": true,
  "scheduler": {
    "is_running": true,
    "next_run": "2026-01-21T18:00:00",
    "last_check": "2026-01-20T18:00:00"
  },
  "stats": {
    "total_users": 5,
    "tracked_manga": 12
  }
}
```

### Manuel Kontrol Tetikleme

Test amaçlı hemen bir kontrol başlatmak için:

**Endpoint:** `POST /api/scheduler/run-now`

**Response:**
```json
{
  "success": true,
  "message": "Kontrol başlatıldı"
}
```

## Sunucu Logları

Sunucu çalışırken terminalde şu logları göreceksiniz:

```
============================================================
Manga güncellemeleri kontrol ediliyor... 2026-01-21 18:00:00
============================================================
📚 Kontrol edilen manga sayısı: 3
🔍 Kontrol ediliyor: One Piece
  ✅ YENİ BÖLÜM: One Piece - Chapter 1172
🔍 Kontrol ediliyor: Lookism
  ℹ Değişiklik yok: Lookism - Chapter 590
🔍 Kontrol ediliyor: Solo Leveling
  ❌ Bulunamadı: Solo Leveling

📢 1 yeni bölüm bulundu!
  ✅ Bildirim gönderildi: One Piece -> 3/3 cihaz

✓ Hiç güncelleme bulunamadı
============================================================
```

## Önemli Notlar

1. **Device ID**: Her cihaz için benzersiz bir ID kullanın (Android ID, UUID vb.)
2. **FCM Token Yenileme**: Token her değiştiğinde `/api/user/register` endpoint'ini tekrar çağırın
3. **Manga İsimleri**: Tam eşleşme gerektirir (büyük/küçük harf duyarlı değil)
4. **Güncelleme Saati**: Varsayılan olarak her gün 18:00 (değiştirilebilir)
5. **Rate Limiting**: Web scraping sırasında her istek arasında 0.5 saniye bekleme var

## Veritabanı

Sistem `database.json` dosyasını kullanır. Bu dosya otomatik olarak oluşturulur ve şunları içerir:

```json
{
  "users": {
    "device_id_123": {
      "token": "fcm_token",
      "manga_list": ["One Piece", "Lookism"],
      "created_at": "2026-01-21T12:00:00"
    }
  },
  "manga_chapters": {
    "One Piece": {
      "chapter": "1171",
      "url": "https://...",
      "image": "https://...",
      "last_checked": "2026-01-21T18:00:00"
    }
  },
  "last_check": "2026-01-21T18:00:00"
}
```

## Troubleshooting

### Bildirim Gelmiyor
- FCM token'ın güncel olduğunu kontrol edin
- Kullanıcının kaydedildiğini doğrulayın: `GET /api/user/{device_id}`
- Manga isminin doğru yazıldığından emin olun
- Firebase service account dosyasının yüklendiğini kontrol edin

### Scheduler Çalışmıyor
- `GET /api/scheduler/status` ile durumu kontrol edin
- Sunucu loglarını inceleyin
- `POST /api/scheduler/run-now` ile manuel test yapın

### Manga Bulunamıyor
- Manga ismini tam olarak yazın (örn: "One Piece", "one piece" değil)
- Raven Scans'te manga sayfasının var olduğunu kontrol edin
- MangaDex'te alternatif ismi deneyin
