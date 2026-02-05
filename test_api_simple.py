import requests
import json

# API endpoint
url = "http://localhost:5000/api/manga/latest"

# Request body
data = {
    "manga_list": ["Solo Leveling"]
}

try:
    # POST isteği gönder
    response = requests.post(url, json=data)
    
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    
except Exception as e:
    print(f"Hata: {e}")
