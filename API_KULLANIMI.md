# Manga Notificator API Kullanımı

## API'yi Başlatma

```bash
python api.py
```

API `http://localhost:5000` adresinde çalışacak.

## Endpoints

### 1. Health Check (GET)
API'nin çalışıp çalışmadığını kontrol eder.

**URL:** `GET http://localhost:5000/health`

**Response:**
```json
{
  "status": "online",
  "message": "Manga Notificator API is running"
}
```

### 2. Manga Son Bölüm Bilgileri (POST)
Manga listesi gönderir ve son bölüm bilgilerini alır.

**URL:** `POST http://localhost:5000/api/manga/latest`

**Request Body:**
```json
{
  "manga_list": [
    "One Piece",
    "Lookism",
    "Nano Machine"
  ]
}
```

**Response (Başarılı):**
```json
{
  "success": true,
  "count": 3,
  "data": [
    {
      "name": "One Piece",
      "chapter": "1171",
      "found": true
    },
    {
      "name": "Lookism",
      "chapter": "590",
      "found": true
    },
    {
      "name": "Nano Machine",
      "chapter": "295",
      "found": true
    }
  ]
}
```

**Response (Hata):**
```json
{
  "success": false,
  "error": "manga_list parametresi gerekli"
}
```

## Android'den Kullanım (Kotlin)

### Retrofit ile:

```kotlin
// API Interface
interface MangaApi {
    @POST("api/manga/latest")
    suspend fun getLatestChapters(@Body request: MangaRequest): MangaResponse
}

// Data Classes
data class MangaRequest(
    val manga_list: List<String>
)

data class MangaResponse(
    val success: Boolean,
    val count: Int,
    val data: List<MangaData>
)

data class MangaData(
    val name: String,
    val chapter: String?,
    val found: Boolean
)

// Kullanım
val api = retrofit.create(MangaApi::class.java)
val request = MangaRequest(
    manga_list = listOf("One Piece", "Lookism", "Nano Machine")
)
val response = api.getLatestChapters(request)
```

### OkHttp ile (Basit):

```kotlin
val client = OkHttpClient()
val json = """
{
  "manga_list": ["One Piece", "Lookism", "Nano Machine"]
}
""".trimIndent()

val body = json.toRequestBody("application/json".toMediaType())
val request = Request.Builder()
    .url("http://YOUR_SERVER_IP:5000/api/manga/latest")
    .post(body)
    .build()

client.newCall(request).execute().use { response ->
    val responseBody = response.body?.string()
    // JSON'ı parse et
}
```

## Curl ile Test

```bash
# Health Check
curl http://localhost:5000/health

# Manga bilgilerini al
curl -X POST http://localhost:5000/api/manga/latest \
  -H "Content-Type: application/json" \
  -d '{"manga_list": ["One Piece", "Lookism", "Nano Machine"]}'
```

## PowerShell ile Test

```powershell
# Health Check
Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get

# Manga bilgilerini al
$body = @{
    manga_list = @("One Piece", "Lookism", "Nano Machine")
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:5000/api/manga/latest" -Method Post -Body $body -ContentType "application/json"
```

## Notlar

- API varsayılan olarak tüm IP'lerden erişime açık (`0.0.0.0`)
- CORS desteği aktif (Android'den direkt istek atabilirsiniz)
- Her manga için 0.5 saniye bekleme süresi var (rate limiting)
- Önce Raven Scans, sonra MangaDex kontrol edilir
- Production'da `debug=False` yapın ve güvenlik önlemleri ekleyin
