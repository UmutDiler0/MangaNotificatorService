import requests
import json

# API URL
BASE_URL = "http://localhost:5000"

def test_health():
    """Health check testi"""
    print("=" * 60)
    print("TEST 1: Health Check")
    print("=" * 60)
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_manga_list():
    """Manga listesi gönderme testi"""
    print("=" * 60)
    print("TEST 2: Manga Listesi")
    print("=" * 60)
    
    payload = {
        "manga_list": [
            "One Piece",
            "Lookism",
            "Nano Machine"
        ]
    }
    
    print(f"Request Body:")
    print(json.dumps(payload, indent=2))
    print()
    
    response = requests.post(
        f"{BASE_URL}/api/manga/latest",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print()


def test_empty_list():
    """Boş liste testi"""
    print("=" * 60)
    print("TEST 3: Boş Liste (Hata Testi)")
    print("=" * 60)
    
    payload = {
        "manga_list": []
    }
    
    response = requests.post(
        f"{BASE_URL}/api/manga/latest",
        json=payload,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
    print()


if __name__ == "__main__":
    try:
        print("\n" + "=" * 60)
        print("MANGA NOTIFICATOR API TEST")
        print("=" * 60)
        print()
        
        # Testleri çalıştır
        test_health()
        test_manga_list()
        test_empty_list()
        
        print("=" * 60)
        print("TÜM TESTLER TAMAMLANDI")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ HATA: API'ye bağlanılamadı!")
        print("Lütfen önce 'python api.py' komutu ile API'yi başlatın.")
    except Exception as e:
        print(f"\n❌ HATA: {str(e)}")
