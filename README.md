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

### ⚠️ Important: Use the same deploy branch as your running VPS
Before pulling, always verify which branch is currently deployed to avoid accidentally overriding production settings:

```bash
cd ~/lebaranrush
git branch --show-current
git remote -v
```

If production uses `main`, then always run:

```bash
git checkout main
git pull origin main
```

If production uses `development`, then always run:

```bash
git checkout development
git pull origin development
```

Do **not** mix branches on the same production folder unless you intentionally redeploy from a different branch.

### 🔁 Updating an Existing VPS Deployment (After `git pull`)
When new commits are pushed, use this quick deploy flow inside your existing server folder:

```bash
cd ~/lebaranrush
source .venv/bin/activate  # or source venv/bin/activate if your env is named venv

# pull latest code (example for production on main)
git checkout main
git pull origin main

# if your production branch is development, replace both commands with development

# install any new dependencies
pip install -r requirements.txt

# apply database changes (if any migration exists)
python manage.py migrate

# refresh static files (needed when templates/css/images/js changed)
python manage.py collectstatic --noinput

# optional sanity check
python manage.py check
```

Then restart your process manager (example):

```bash
# systemd example
sudo systemctl restart lebaranrush
sudo systemctl status lebaranrush --no-pager
```

### ✅ What to run depending on changed files
- If only Python logic changed (views/models/consumers): `git pull`, `pip install -r requirements.txt`, `python manage.py migrate`, restart service.
- If `requirements.txt` changed: run `pip install -r requirements.txt` before restart.
- If `migrations/` changed: run `python manage.py migrate`.
- If `templates/`, `static/`, or frontend assets changed: run `python manage.py collectstatic --noinput`.
- If `settings.py` / env usage changed: update VPS environment variables and restart service.

---
Developed for the ultimate Lebaran gathering experience! 🌙✨
