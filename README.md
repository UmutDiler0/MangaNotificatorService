# Manga Notificator API - Simplified Version

Manga ve manhwa'ların en son bölüm bilgilerini almak için basit bir API.

## 🚀 Özellikler

- ✅ Giriş yapmadan kullanım
- ✅ Manga ismine göre arama
- ✅ En son bölüm bilgisi
- ✅ Manga kapak görseli
- ✅ Bölüm URL'i
- ✅ Multiple manga sorgulama

## 📡 API Endpoint

### POST /api/manga/latest

Manga listesi gönderir ve son bölüm bilgilerini alır.

**URL:** `https://manganotificatorservice-ur6m.onrender.com/api/manga/latest`

**Method:** POST

**Content-Type:** application/json

### Request Body

```json
{
  "manga_list": ["Solo Leveling", "One Piece", "Lookism"]
}
```

### Response

```json
[
  {
    "name": "Solo Leveling",
    "chapter": "200",
    "found": true,
    "url": "https://ravenscans.org/solo-leveling-chapter-200/",
    "image": "https://i0.wp.com/ravenscans.org/wp-content/uploads/2025/05/solo-leveling.jpg"
  },
  {
    "name": "One Piece",
    "chapter": "1171",
    "found": true,
    "url": "https://ravenscans.org/one-piece-chapter-1171/",
    "image": "https://ravenscans.org/wp-content/uploads/2024/12/one-piece.jpg"
  },
  {
    "name": "Lookism",
    "chapter": "590",
    "found": true,
    "url": "https://ravenscans.org/lookism-chapter-590/",
    "image": "https://ravenscans.org/wp-content/uploads/2024/12/lookism.jpg"
  }
]
```

### Response Alanları

| Alan | Tip | Açıklama |
|------|-----|----------|
| `name` | string | Manga adı |
| `chapter` | string | En son bölüm numarası |
| `found` | boolean | Manga bulundu mu? |
| `url` | string | Bölümün URL'i (null olabilir) |
| `image` | string | Manga kapak görseli (null olabilir) |

## 🧪 Test

### Python ile Test

```python
import requests

url = "http://localhost:5000/api/manga/latest"
data = {
    "manga_list": ["Solo Leveling"]
}

response = requests.post(url, json=data)
print(response.json())
```

### curl ile Test

```bash
curl -X POST http://localhost:5000/api/manga/latest \
  -H "Content-Type: application/json" \
  -d '{"manga_list": ["Solo Leveling"]}'
```

### PowerShell ile Test

```powershell
$body = @{manga_list = @("Solo Leveling")} | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:5000/api/manga/latest" `
  -Method POST `
  -Body $body `
  -ContentType "application/json"
```

## 🛠️ Kurulum

### Gereksinimler

- Python 3.8+
- pip

### Kurulum Adımları

1. Repository'yi klonlayın:
```bash
git clone <repo-url>
cd manga_notificator
```

2. Sanal ortam oluşturun:
```bash
python -m venv venv
```

3. Sanal ortamı aktifleştirin:

**Windows:**
```bash
venv\Scripts\activate
```

**Linux/Mac:**
```bash
source venv/bin/activate
```

4. Gereksinimleri yükleyin:
```bash
pip install -r requirements.txt
```

5. API'yi başlatın:
```bash
python api.py
```

API `http://localhost:5000` adresinde çalışmaya başlar.

## 📦 Deployment (Render)

1. Render.com'da yeni bir Web Service oluşturun
2. GitHub repository'nizi bağlayın
3. Build Command: `pip install -r requirements.txt`
4. Start Command: `gunicorn wsgi:application`
5. Deploy edin

## 🌐 Veri Kaynakları

API aşağıdaki kaynaklardan veri çeker:

1. **Raven Scans** (Birincil)
   - URL: https://ravenscans.org
   - Desteklenen seriler: Solo Leveling, Lookism, One Piece, vb.

2. **MangaDex** (Yedek)
   - URL: https://mangadex.org
   - API: https://api.mangadex.org

## ⚠️ Notlar

- Rate limiting: Her manga için 0.5 saniye bekleme süresi
- Timeout: 10 saniye
- Manga bulunamazsa `found: false` döner
- Manga isimleri büyük/küçük harf duyarlı değildir
- Manga isimleri normalize edilir (boşluklar çizgiye dönüştürülür)

## 📝 Değişiklik Listesi (v2.0.0)

- ✅ Giriş yapma sistemi kaldırıldı
- ✅ Bildirim sistemi kaldırıldı
- ✅ Veritabanı sistemi kaldırıldı
- ✅ Scheduler kaldırıldı
- ✅ Sadece manga arama özelliği bırakıldı
- ✅ API basitleştirildi
- ✅ Gereksiz bağımlılıklar kaldırıldı

## 📄 Lisans

MIT License
