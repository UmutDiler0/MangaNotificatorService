#!/bin/bash
# Render başlangıç scripti

echo "🚀 Manga Notificator API başlatılıyor..."
echo "📦 Python versiyonu: $(python --version)"
echo "📁 Çalışma dizini: $(pwd)"

# Environment variables kontrol
if [ -z "$FIREBASE_CREDENTIALS" ]; then
    echo "⚠️  UYARI: FIREBASE_CREDENTIALS environment variable ayarlanmamış!"
    echo "   Firebase bildirimleri çalışmayacak."
fi

# Database dizini oluştur
mkdir -p /tmp
echo "✓ /tmp dizini hazır"

# Gunicorn ile başlat
echo "🌐 Gunicorn başlatılıyor..."
exec gunicorn wsgi:app \
    --bind 0.0.0.0:$PORT \
    --workers 2 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -
