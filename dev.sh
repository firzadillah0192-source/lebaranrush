#!/bin/bash

echo "🛠️ Running Dev Preparation..."

# Activate venv
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Migrations
python manage.py migrate

# Collect Static
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput

# Runserver
echo "🚀 Starting Dev Server..."
python manage.py runserver 0.0.0.0:8000
