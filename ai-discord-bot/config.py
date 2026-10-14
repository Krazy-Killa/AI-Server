# config.py

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "").strip()
if not DISCORD_TOKEN:
    raise RuntimeError("Set DISCORD_TOKEN in the project-root .env file before starting the Discord bot.")

BOT_API_TOKEN = os.getenv("AI_SERVER_BOT_API_TOKEN", "").strip()
if len(BOT_API_TOKEN) < 32:
    raise RuntimeError(
        "Set AI_SERVER_BOT_API_TOKEN to a random value of at least 32 characters "
        "in the project-root .env file before starting the Discord bot. "
        "This is separate from the Discord application DISCORD_TOKEN."
    )

# Override AI_SERVER_API_BASE when the backend is hosted on another machine.
API_BASE = os.getenv("AI_SERVER_API_BASE", "http://127.0.0.1:8000")
