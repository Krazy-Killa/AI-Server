# config.py

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
if not DISCORD_TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in the project-root .env file before starting the Discord bot.")

# Override AI_SERVER_API_BASE when the backend is hosted on another machine.
API_BASE = os.getenv("AI_SERVER_API_BASE", "http://127.0.0.1:8000")
