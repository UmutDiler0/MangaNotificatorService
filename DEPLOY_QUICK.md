# Render Deploy - Hızlı Başlangıç

## 🚀 Render'a Deploy Etme (3 Adım)

### Adım 1: GitHub'a Push
```bash
git add .
git commit -m "Ready for Render deployment"
git push origin main
```

### Adım 2: Render'da Servis Oluştur

1. [Render Dashboard](https://dashboard.render.com/) → **New +** → **Web Service**
2. GitHub repository'nizi seçin: **MangaNotificatorService**
3. Ayarları yapın:

```
Name: manga-notificator-api
Region: Frankfurt (veya size en yakın)
Branch: main
Runtime: Python 3

Build Command: pip install -r requirements.txt
Start Command: (Procfile otomatik kullanılacak)
```

### Adım 3: Environment Variables

**Environment** sekmesinden ekleyin:

#### Zorunlu:
```
RENDER=true
PRODUCTION=true
```

#### Firebase (Zorunlu):
Firebase Console'dan indirdiğiniz `firebase-service-account.json` dosyasının içeriğini kopyalayıp:

```
FIREBASE_CREDENTIALS={"type":"service_account","project_id":"YOUR_PROJECT","private_key_id":"...","private_key":"-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n","client_email":"...@....iam.gserviceaccount.com",...}
```

💡 **İpucu**: JSON'u tek satır yapın, yeni satırları `\n` ile değiştirin.

---

## ✅ Hazır Dosyalar

- ✅ `requirements.txt` - Tüm Python dependencies (gunicorn dahil)
- ✅ `Procfile` - Gunicorn başlatma komutu
- ✅ `render.yaml` - Otomatik yapılandırma
- ✅ `runtime.txt` - Python 3.11.0
- ✅ `start.sh` - Başlangıç scripti
- ✅ `.gitignore` - Credentials güvenliği

---

## 🧪 Deploy Sonrası Test

Render size bir URL verecek: `https://manga-notificator-api.onrender.com`

### Health Check:
```bash
curl https://manga-notificator-api.onrender.com/health
```

Beklenen:
```json
{
  "status": "online",
  "message": "Manga Notificator API is running"
}
```

### Scheduler Durumu:
```bash
curl https://manga-notificator-api.onrender.com/api/scheduler/status
```

### Manga Sorgulama:
```bash
curl -X POST https://manga-notificator-api.onrender.com/api/manga/latest \
  -H "Content-Type: application/json" \
  -d '{"manga_list":["One Piece","Lookism"]}'
```

---

## 🔧 Özellikler

✅ **Otomatik Deploy**: GitHub'a push → Otomatik deployment
✅ **Health Check**: `/health` endpoint ile otomatik sağlık kontrolü
✅ **Logging**: Tüm loglar Render Dashboard'da görünür
✅ **Environment Vars**: Firebase credentials güvenli şekilde saklanır
✅ **Auto-Restart**: Crash durumunda otomatik yeniden başlatma
✅ **HTTPS**: Ücretsiz SSL sertifikası

---

## 📱 Android Uygulamasını Güncelle

Retrofit base URL'i değiştir:

```kotlin
private const val BASE_URL = "https://manga-notificator-api.onrender.com/"
```

---

## ⚠️ Önemli Notlar

### Free Plan Limitler:
- **750 saat/ay** (tek service için yeterli)
- **512 MB RAM**
- **0.1 CPU**
- **15 dakika inactivity → sleep mode**
- **İlk istek 30-60 saniye sürebilir** (cold start)

### Database:
- Render Free plan'de dosya sistemi **ephemeral** (geçici)
- Her deploy'da database sıfırlanır
- Kalıcı veri için PostgreSQL kullanın (ücretsiz plan mevcut)

### Scheduler:
- Otomatik olarak her gün 18:00'de çalışır
- Sleep mode'da scheduler durur
- Manuel tetikleme için: `POST /api/scheduler/run-now`

---

## 🐛 Sorun Giderme

### "Application failed to respond"
- Render loglarını kontrol edin
- Timeout artırın: `--timeout 300`

### "Module not found"
```bash
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update requirements"
git push
```

### Firebase hatası
- Environment variable doğru mu?
- JSON formatı geçerli mi?
- Tek satır mı? (yeni satırlar `\n` olmalı)

### Database kayboluyor
- Normal! Render Free ephemeral storage kullanır
- PostgreSQL ekleyin (Render Dashboard → New + → PostgreSQL)

---

## 📊 Monitoring

Render Dashboard'da:
- **Logs**: Real-time log görüntüleme
- **Metrics**: CPU, Memory, Request count
- **Events**: Deploy history
- **Shell**: Servis içinde terminal

---

## 🎯 Production Checklist

- [ ] GitHub repository güncel
- [ ] Render servisi oluşturuldu
- [ ] Environment variables eklendi (`FIREBASE_CREDENTIALS`)
- [ ] Health check başarılı
- [ ] Scheduler çalışıyor
- [ ] Android app base URL güncellendi
- [ ] Test istekleri başarılı

---

## 💡 İleri Seviye

### PostgreSQL Ekleme:
1. Render Dashboard → New + → PostgreSQL
2. Database URL'i kopyala
3. Environment variable ekle: `DATABASE_URL`
4. `database.py` dosyasını PostgreSQL kullanacak şekilde güncelle

### Custom Domain:
1. Render Dashboard → Settings → Custom Domain
2. DNS kayıtlarını güncelle
3. SSL otomatik aktif olur

### Monitoring:
- [UptimeRobot](https://uptimerobot.com) ile 5 dakikada bir ping at (sleep mode önleme)
- Logs için [Better Stack](https://betterstack.com) kullan

---

🎉 **Deploy başarılı olursa URL'i paylaşabilirsiniz!**
