@echo off
setlocal
title Lebaran Rush - Server

echo 🌙 Starting Lebaran Rush...

:: Check if virtual environment exists, if not create it
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo ❌ Failed to create virtual environment. Please ensure Python is installed.
        pause
        exit /b 1
    )
)

:: Activate virtual environment
echo 🔌 Activating virtual environment...
call venv\Scripts\activate
if errorlevel 1 (
    echo ❌ Failed to activate virtual environment.
    pause
    exit /b 1
)

:: Install dependencies
echo 📥 Checking dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo ⚠️ Failed to install dependencies. Proceeding anyway...
)

:: Run migrations
echo ⚙️ Running database migrations...
python manage.py migrate
if errorlevel 1 (
    echo ❌ Database migration failed.
    pause
    exit /b 1
)

:: Start server bounded to 0.0.0.0
echo 🚀 Launching server...
echo.
python manage.py runserver 0.0.0.0:8000

pause
