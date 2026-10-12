# backend_api.py

import aiohttp
from config import API_BASE

async def send_chat(message: str):
    """Send a chat message to the FastAPI backend."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/api/chat", json={"message": message}) as resp:
            return await resp.json()

async def get_models():
    """Fetch model list from backend."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/api/models") as resp:
            return await resp.json()

async def select_model(model_id: str):
    """Switch active model."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/api/model/select", json={"model_id": model_id}) as resp:
            return await resp.json()

async def get_bot_status():
    """Fetch bot status from backend."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_BASE}/api/bot/status") as resp:
            return await resp.json()

async def send_embed_request(text: str):
    """Send text to embedding stub."""
    async with aiohttp.ClientSession() as session:
        async with session.post(f"{API_BASE}/api/embed", json={"text": text}) as resp:
            return await resp.json()
