# Lebaran Rush 🌙

Lebaran Rush is a **web-based multiplayer party game** designed to bring fun and excitement to family gatherings during Lebaran. It features real-time interactions, mystery boxes, and high-stakes games controlled by a central Host.

## ✨ Features
- **Host Dashboard**: A "Bandar" (Host) controls the game and displays animations on a TV/Laptop.
- **Mobile Controller**: Players join by scanning a QR code and play directly from their mobile browsers.
- **Real-time Gameplay**: Powered by WebSockets for instant synchronization.
- **Three Mini-Games**:
  1. **Gacha Lebaran**: Pick mystery boxes and win points or spins.
  2. **Undercover**: Find the spy among your family members!
  3. **Spin Wheel**: Use earned points to spin for prizes.
- **Leaderboard**: Automatic point tracking and a grand championship reveal.

## 🛠️ Technology Stack
- **Backend**: Python, Django, Django Channels (WebSockets)
- **Frontend**: TailwindCSS, AlpineJS, HTMX
- **Real-time**: Daphne ASGI server
- **Database**: SQLite (development) / PostgreSQL via `DATABASE_URL` (production)
- **QR Codes**: `python-qrcode`

## 📂 Project Structure
- `core/`: Base configurations and shared templates.
- `rooms/`: Room management, Host Dashboard, and player sessions.
- `players/`: Player model and point/spin tracking.
- `games/`: Mini-game logic (Gacha, Undercover, Spin Wheel).
- `engine/`: Central state manager and game transitions.
- `chat/`: Real-time chat system for specific game phases.
- `votes/`: Voting mechanics for Undercover.

## 🚀 Setup Instructions

### 1. Prerequisites
- Python 3.10+ installed.

### 2. Clone and Setup
Run the following commands in your terminal:

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Initialize Database
```bash
python manage.py migrate
```

### 4. Run the Server (Quick Start)
Depending on your operating system, run the appropriate script from the project root:

- **Windows (CMD or PowerShell)**:
  ```cmd
  start.bat
  ```
  *(Note: This script handles virtual environment creation, activation, and server startup automatically.)*

- **Linux / macOS**:
  ```bash
  ./start.sh
  ```
  *(Note: Make sure to `chmod +x start.sh` before running.)*

## 🌐 VPS Deployment
To host this on a VPS (e.g., DigitalOcean, AWS, Linode), follow these steps:

1. **Clone the Repo**:
   ```bash
   git clone https://github.com/firzadillah0192-source/lebaranrush.git
   cd lebaranrush
   ```
2. **Environment Setup**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Set production environment variables** (important):
   ```bash
   export DEBUG=False
   export SECRET_KEY="replace-with-a-strong-random-secret"
   export ALLOWED_HOSTS="your-domain.com,www.your-domain.com"
   export DATABASE_URL="postgresql://db_user:db_password@127.0.0.1:5432/lebaranrush"
   export REDIS_URL="redis://127.0.0.1:6379/1"
   ```
4. **Database & Static**:
   ```bash
   python manage.py migrate
   python manage.py collectstatic --noinput
   python seed_undercover.py  # Add initial word pairs
   ```
5. **Run with Daphne (Production)**:
   ```bash
   # Make sure you are in the virtualenv
   daphne -b 0.0.0.0 -p 8000 lebaranrush.asgi:application
   ```
   *Tip: Use `tmux` or `systemd` to keep the process running.*

---
Developed for the ultimate Lebaran gathering experience! 🌙✨
