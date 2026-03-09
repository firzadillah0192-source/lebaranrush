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
- **Database**: SQLite (No complex setup required)
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

## 🎮 How to Join
1. **Host**: Open `http://localhost:8000/host` on your laptop.
2. **Players**: Scan the QR code displayed on the host screen or go to the URL shown in your terminal (e.g., `http://192.168.1.15:8000`).

## 🛠️ Troubleshooting
- **Cannot connect?** Ensure your laptop and players are on the same Wi-Fi network. Check your firewall settings.
- **Windows PowerShell?** If `start.bat` doesn't run, try `./start.bat`. Do not try to run `.sh` files in PowerShell directly.
- **IP Address?** The server will print your local IP address in the terminal. Give this address to players if the QR code fails.

---
Developed for the ultimate Lebaran gathering experience! 🌙✨
