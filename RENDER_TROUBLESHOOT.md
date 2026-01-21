# Render Deployment Sorun Giderme

## ❌ "No module named 'app'" Hatası

### Sebep:
Render Dashboard'da Start Command yanlış girilmiş olabilir.

### Çözüm:

1. **Render Dashboard'a gidin**
2. Servisinizi seçin
3. **Settings** → **Build & Deploy** bölümüne gidin
4. **Start Command** kısmını kontrol edin

**Doğru komut:**
```
gunicorn api:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 --access-logfile - --error-logfile -
```

**YANLIŞ komutlar:**
```
gunicorn app:app          ❌
python app.py             ❌
python api.py             ❌
```

5. Yanlışsa düzeltin ve **Save Changes**
6. **Manual Deploy** → **Deploy latest commit**

---

## 🔧 Alternatif Çözüm: Blueprint Kullan

Render'ın otomatik yapılandırmasını kullanın:

### 1. render.yaml dosyası zaten var
Proje root'unda `render.yaml` mevcut.

### 2. Yeni servis oluştururken:
- **Blueprint** seçeneğini kullanın
- `render.yaml` otomatik okunacak

### 3. Eğer manuel oluşturduysanız:
Settings → Build & Deploy → **Use render.yaml** seçeneğini aktif edin

---

## 📝 Kontrol Listesi

Render Dashboard'da şunları kontrol edin:

- [ ] **Start Command:** `gunicorn api:app ...` (app:app DEĞİL!)
- [ ] **Build Command:** `pip install -r requirements.txt`
- [ ] **Python Version:** 3.12.0 veya 3.11.0
- [ ] **Environment Variables:**
  - `RENDER=true`
  - `PRODUCTION=true`
  - `FIREBASE_CREDENTIALS={"type":...}`

---

## 🚀 Hızlı Çözüm

### Manuel Deploy Trigger:
1. Settings → Build & Deploy
2. Start Command'ı düzeltin
3. **Manual Deploy** tıklayın

### Veya Yeniden Oluşturun:
1. Mevcut servisi silin
2. New + → Web Service
3. **Deploy from Blueprint** seçin
4. Repository seçin
5. render.yaml otomatik okunacak

---

## 🐛 Diğer Yaygın Hatalar

### "Application failed to respond"
**Çözüm:** Timeout artırın
```
--timeout 300
```

### "Module not found: firebase_admin"
**Çözüm:** requirements.txt eksik
```bash
pip freeze > requirements.txt
git push
```

### Database kayboldu
**Çözüm:** Normal, Render Free ephemeral storage kullanır
- PostgreSQL ekleyin (kalıcı veri için)

---

## 📞 Render Support

- Logs: Dashboard → Logs sekmesi
- Shell: Dashboard → Shell (servis içinde terminal)
- Community: [community.render.com](https://community.render.com)

---

## ✅ Deploy Başarılı Olunca

Test edin:
```bash
curl https://YOUR-SERVICE.onrender.com/health
```

Beklenen:
```json
{"status": "online", "message": "Manga Notificator API is running"}
```
