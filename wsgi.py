"""
WSGI entry point for Gunicorn
"""
import sys
import os

# Proje dizinini Python path'e ekle
sys.path.insert(0, os.path.dirname(__file__))

from api import app

if __name__ == "__main__":
    app.run()
