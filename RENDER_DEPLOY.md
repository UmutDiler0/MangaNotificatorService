# Render Deployment Rehberi

## 🚀 Render'da Deploy Etme

### 1. GitHub Repository Hazırlama

Proje zaten GitHub'a yüklenmiş durumda. Eğer değilse:

```bash
git add .
git commit -m "Add Render deployment configuration"
git push origin main
```

### 2. Render Hesabı Oluşturma

1. [Render.com](https://render.com) adresine gidin
2. GitHub hesabınızla giriş yapın
3. "New +" butonuna tıklayın
4. "Web Service" seçin

### 3. Repository Bağlama

1. GitHub repository'nizi seçin: `MangaNotificatorService`
2. Aşağıdaki ayarları yapın:

**Temel Ayarlar:**
- **Name**: `manga-notificator-api`
- **Region**: Frankfurt (veya size en yakın)
- **Branch**: `main`
- **Runtime**: Python 3

**Build & Deploy:**
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn api:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120`

### 4. Environment Variables

Render Dashboard'da "Environment" sekmesinden şu değişkenleri ekleyin:

#### Zorunlu Environment Variables:

```
RENDER=true
PRODUCTION=true
PORT=10000  (Render otomatik ekler)
```

#### Firebase için (Zorunlu):

Firebase servis hesabı JSON içeriğini environment variable olarak ekleyin:

**Yöntem 1: JSON String olarak**
```
FIREBASE_CREDENTIALS={"type":"service_account","project_id":"...","private_key":"..."}
```

**Yöntem 2: Base64 encode edilmiş**
```
FIREBASE_CREDENTIALS_BASE64=eyJ0eXBlIjoic2VydmljZV9hY2NvdW50Ii...
```

### 5. Firebase Credentials Ayarlama

`firebase_config.py` dosyasını Environment Variable'dan okuyacak şekilde güncelleyin:

```python
import os
import json
import base64

def _initialize_firebase(self):
    try:
        # Render'da environment variable'dan oku
        if os.environ.get('FIREBASE_CREDENTIALS'):
            # JSON string
            cred_dict = json.loads(os.environ.get('FIREBASE_CREDENTIALS'))
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            self.initialized = True
            print("✓ Firebase (Environment Variable) başlatıldı")
        elif os.environ.get('FIREBASE_CREDENTIALS_BASE64'):
            # Base64 encoded
            cred_json = base64.b64decode(os.environ.get('FIREBASE_CREDENTIALS_BASE64'))
            cred_dict = json.loads(cred_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            self.initialized = True
            print("✓ Firebase (Base64) başlatıldı")
        else:
            # Local file
            service_account_path = 'firebase-service-account.json'
            if os.path.exists(service_account_path):
                cred = credentials.Certificate(service_account_path)
                firebase_admin.initialize_app(cred)
                self.initialized = True
                print("✓ Firebase (File) başlatıldı")
    except Exception as e:
        print(f"⚠ Firebase hatası: {e}")
        self.initialized = False
```

### 6. Deploy

1. "Create Web Service" butonuna tıklayın
2. Render otomatik olarak build ve deploy edecek
3. Deploy tamamlandığında size bir URL verilecek: `https://manga-notificator-api.onrender.com`

### 7. Health Check

Deploy tamamlandıktan sonra test edin:

```bash
curl https://manga-notificator-api.onrender.com/health
```

**Beklenen Response:**
```json
{
  "status": "online",
  "message": "Manga Notificator API is running"
}
```

## 📋 Render Dosya Yapısı

Projenizde şu dosyaların olması gerekiyor (✅ hazır):

- ✅ `requirements.txt` - Python dependencies (gunicorn eklendi)
- ✅ `Procfile` - Render start komutu
- ✅ `render.yaml` - Render yapılandırması
- ✅ `.gitignore` - Credentials'ları ignore et

## 🔧 Ayarlamalar

### Database Persistence (Ücretsiz Plan)

Render Free plan'de dosya sistemi ephemeral'dır (geçici). Database için şu seçenekler var:

**Seçenek 1: PostgreSQL (Önerilen)**
- Render'da ücretsiz PostgreSQL instance oluşturun
- `database.py` dosyasını PostgreSQL kullanacak şekilde güncelleyin

**Seçenek 2: External Storage**
- AWS S3, Google Cloud Storage vb. kullanın
- `database.json` dosyasını cloud storage'a kaydedin

**Seçenek 3: Redis**
- Upstash Redis (ücretsiz) kullanın
- In-memory cache olarak kullanın

### Scheduler için Auto-Start

Scheduler otomatik başlatma kodu zaten eklendi:

```python
import os
if os.environ.get('RENDER') or os.environ.get('PRODUCTION'):
    manga_scheduler.start()
```

## 🐛 Sorun Giderme

### "Application failed to respond" Hatası

**Sebep**: Gunicorn timeout çok kısa

**Çözüm**: `Procfile`'da timeout'u artırın:
```
web: gunicorn api:app --bind 0.0.0.0:$PORT --workers 2 --timeout 300
```

### "Module not found" Hatası

**Sebep**: `requirements.txt` eksik veya hatalı

**Çözüm**: Tüm dependencies'leri kontrol edin:
```bash
pip freeze > requirements.txt
```

### Firebase Initialization Failed

**Sebep**: Environment variable yanlış veya eksik

**Çözüm**: 
1. Render Dashboard > Environment Variables
2. `FIREBASE_CREDENTIALS` değişkenini kontrol edin
3. JSON formatının geçerli olduğundan emin olun

### Database Kayboldu (Free Plan)

**Sebep**: Render Free plan ephemeral storage kullanır

**Çözüm**: 
- PostgreSQL veya external storage kullanın
- Veya her deploy'da veritabanı sıfırdan başlar (test için uygundur)

## 📊 Monitoring

Render Dashboard'da:
- **Logs**: Real-time log görüntüleme
- **Metrics**: CPU, Memory kullanımı
- **Events**: Deploy history

## 💰 Maliyet

**Free Plan Limitleri:**
- 750 saat/ay (1 service için yeterli)
- 512 MB RAM
- 0.1 CPU
- 15 dakika inactivity sonrası sleep mode
- Aylık restart

**Dikkat**: Free plan'de servis 15 dakika kullanılmazsa uyur. İlk istek 30-60 saniye sürebilir.

## 🔗 Production URL

Deploy sonrası API'niz şu URL'de çalışacak:

```
https://manga-notificator-api.onrender.com
```

### Android Uygulamada Güncelleme

Retrofit base URL'i güncelleyin:

```kotlin
private const val BASE_URL = "https://manga-notificator-api.onrender.com/"

val retrofit = Retrofit.Builder()
    .baseUrl(BASE_URL)
    .addConverterFactory(GsonConverterFactory.create())
    .build()
```

## 📝 Deploy Checklist

- [ ] GitHub repository hazır
- [ ] `requirements.txt` güncel (gunicorn eklendi)
- [ ] `Procfile` oluşturuldu
- [ ] `render.yaml` yapılandırıldı
- [ ] Firebase credentials environment variable olarak hazır
- [ ] `.gitignore` güncellendi
- [ ] Render account oluşturuldu
- [ ] Web Service oluşturuldu
- [ ] Environment variables eklendi
- [ ] Health check başarılı
- [ ] Android app base URL güncellendi

## 🚀 Hızlı Deploy Komutu

```bash
# Son değişiklikleri commit et
git add .
git commit -m "Add Render deployment configuration"
git push origin main

# Render otomatik olarak yeni commit'i deploy edecek
```

## 📞 Destek

Render sorunları için:
- [Render Docs](https://render.com/docs)
- [Render Community](https://community.render.com)
- [Render Status](https://status.render.com)
