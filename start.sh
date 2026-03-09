#!/bin/bash

echo "🌙 Starting Lebaran Rush..."

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Run migrations
echo "⚙️ Running database migrations..."
python manage.py migrate

# Start server
echo "🚀 Starting server at http://0.0.0.0:8000"
echo "Host Dashboard: http://localhost:8000/host"
python manage.py runserver 0.0.0.0:8000
