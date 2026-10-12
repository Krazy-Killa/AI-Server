# bot_manager.py

import time

# Simulated bot status (will be replaced with real bot integration later)
BOT_STATUS = {
    "online": True,
    "latency_ms": 42,
    "last_restart": time.time()
}

# Simulated bot logs (will be replaced with real bot logging)
BOT_LOGS = [
    "[14:01:22] Connected to Discord API",
    "[14:01:23] Loaded model: Llama 3 8B",
    "[14:01:24] Registered slash commands",
    "[14:02:01] Awaiting commands…"
]

def get_bot_status():
    """Return current bot status."""
    return BOT_STATUS

def get_bot_logs():
    """Return bot logs."""
    return BOT_LOGS

def restart_bot():
    """Simulate restarting the bot."""
    BOT_STATUS["online"] = True
    BOT_STATUS["last_restart"] = time.time()
    BOT_LOGS.append("[{}] Bot restarted".format(time.strftime("%H:%M:%S")))
    return True
