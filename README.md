# Manga Notificator API

Android uygulamalarından manga/manhwa son bölüm bilgilerini almak için REST API.

## Özellikler

✅ REST API (Flask)
✅ JSON request/response
✅ CORS desteği (Android'den direkt erişim)
✅ Raven Scans + MangaDex entegrasyonu
✅ Rate limiting
✅ Hata yönetimi

## Kurulum

### 1. Bağımlılıkları Yükle

```bash
pip install flask flask-cors requests beautifulsoup4 lxml
```

### 2. API'yi Başlat

```bash
python api.py
```

API `http://localhost:5000` adresinde çalışacak.

### 3. Test Et

```bash
python test_api.py
```

## API Endpoints

### GET /health

API'nin çalışıp çalışmadığını kontrol eder.

**Response:**
```json
{
  "status": "online",
  "message": "Manga Notificator API is running"
}
```

### POST /api/manga/latest

Manga listesi alır ve son bölüm bilgilerini döndürür.

**Request:**
```json
{
  "manga_list": [
    "One Piece",
    "Lookism",
    "Nano Machine"
  ]
}
```

**Response:**
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

## Android Entegrasyonu

### Retrofit (Önerilen)

#### 1. Gradle Dependencies

```gradle
dependencies {
    implementation 'com.squareup.retrofit2:retrofit:2.9.0'
    implementation 'com.squareup.retrofit2:converter-gson:2.9.0'
    implementation 'com.squareup.okhttp3:logging-interceptor:4.11.0'
}
```

#### 2. API Interface

```kotlin
interface MangaApi {
    @POST("api/manga/latest")
    suspend fun getLatestChapters(@Body request: MangaRequest): MangaResponse
    
    @GET("health")
    suspend fun healthCheck(): HealthResponse
}
```

#### 3. Data Classes

```kotlin
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

data class HealthResponse(
    val status: String,
    val message: String
)
```

#### 4. Retrofit Instance

```kotlin
object RetrofitClient {
    private const val BASE_URL = "http://YOUR_SERVER_IP:5000/"
    
    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = HttpLoggingInterceptor.Level.BODY
    }
    
    private val client = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .connectTimeout(30, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .build()
    
    val api: MangaApi by lazy {
        Retrofit.Builder()
            .baseUrl(BASE_URL)
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(MangaApi::class.java)
    }
}
```

#### 5. Kullanım (ViewModel)

```kotlin
class MangaViewModel : ViewModel() {
    private val _mangaList = MutableLiveData<List<MangaData>>()
    val mangaList: LiveData<List<MangaData>> = _mangaList
    
    fun fetchLatestChapters(mangaNames: List<String>) {
        viewModelScope.launch {
            try {
                val request = MangaRequest(manga_list = mangaNames)
                val response = RetrofitClient.api.getLatestChapters(request)
                
                if (response.success) {
                    _mangaList.value = response.data
                }
            } catch (e: Exception) {
                // Hata yönetimi
                Log.e("MangaViewModel", "Error: ${e.message}")
            }
        }
    }
}
```

#### 6. Activity/Fragment'te Kullanım

```kotlin
class MainActivity : AppCompatActivity() {
    private val viewModel: MangaViewModel by viewModels()
    
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        
        // Manga listesini gözlemle
        viewModel.mangaList.observe(this) { mangaList ->
            // RecyclerView'i güncelle
            mangaList.forEach { manga ->
                if (manga.found) {
                    println("${manga.name}: Chapter ${manga.chapter}")
                } else {
                    println("${manga.name}: Bulunamadı")
                }
            }
        }
        
        // API'den veri çek
        val mangaNames = listOf("One Piece", "Lookism", "Nano Machine")
        viewModel.fetchLatestChapters(mangaNames)
    }
}
```

### AndroidManifest.xml

```xml
<uses-permission android:name="android.permission.INTERNET" />

<application
    android:usesCleartextTraffic="true">
    <!-- ... -->
</application>
```

## Sunucu Dağıtımı

### Localhost (Geliştirme)
```bash
python api.py
```

### Production (Gunicorn ile)
```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 api:app
```

### Docker
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "4", "-b", "0.0.0.0:5000", "api:app"]
```

## Notlar

- **IP Adresi:** Localhost yerine sunucunuzun IP adresini kullanın
- **CORS:** API tüm origin'lere açık (production'da kısıtlayın)
- **Rate Limiting:** Her manga için 0.5 saniye bekleme var
- **Timeout:** Request'ler 10 saniye sonra timeout olur
- **Kaynak:** Önce Raven Scans, sonra MangaDex kullanılır

## Sorun Giderme

### Connection Refused
- API'nin çalıştığından emin olun: `python api.py`
- Firewall ayarlarını kontrol edin
- Doğru IP ve port kullandığınızdan emin olun

### CORS Hatası
- `flask-cors` paketinin yüklü olduğundan emin olun
- API kodunda `CORS(app)` satırının olduğunu kontrol edin

### Timeout
- İnternet bağlantınızı kontrol edin
- Manga isimlerinin doğru olduğundan emin olun

## Lisans

MIT
