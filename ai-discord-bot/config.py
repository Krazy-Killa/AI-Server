# config.py

import os

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "YOUR_DISCORD_BOT_TOKEN_HERE")

# Override AI_SERVER_API_BASE when the backend is hosted on another machine.
API_BASE = os.getenv("AI_SERVER_API_BASE", "http://127.0.0.1:8000")
