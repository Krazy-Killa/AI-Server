# bot.py

import discord
from discord import app_commands
from discord.ext import commands

import asyncio
import time

from backend_api import (
    send_chat,
    get_models,
    select_model,
    get_bot_status,
    send_embed_request
)

from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ===============================
# Bot Ready Event
# ===============================
@bot.event
async def on_ready():
    print(f"Bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
    except Exception as e:
        print("Error syncing commands:", e)

# ===============================
# /chat — Send message to AI backend
# ===============================
@bot.tree.command(name="chat", description="Send a message to the AI backend.")
async def chat(interaction: discord.Interaction, message: str):
    await interaction.response.defer()

    reply = await send_chat(message)
    await interaction.followup.send(f"**AI:** {reply['reply']}")

# ===============================
# /models — List available models
# ===============================
@bot.tree.command(name="models", description="List available AI models.")
async def models(interaction: discord.Interaction):
    await interaction.response.defer()

    data = await get_models()
    active = data["active"]["name"]
    models = data["models"]

    msg = f"**Active Model:** {active}\n\n**Available Models:**\n"
    for m in models.values():
        msg += f"- {m['name']} ({m['type']}) — VRAM: {m['vram']}GB\n"

    await interaction.followup.send(msg)

# ===============================
# /selectmodel — Switch active model
# ===============================
@bot.tree.command(name="selectmodel", description="Switch the active AI model.")
async def selectmodel(interaction: discord.Interaction, model_id: str):
    await interaction.response.defer()

    result = await select_model(model_id)
    if result["success"]:
        await interaction.followup.send(f"Model switched to `{model_id}`.")
    else:
        await interaction.followup.send(f"Model `{model_id}` not found.")

# ===============================
# /status — Bot status from backend
# ===============================
@bot.tree.command(name="status", description="Get bot status from backend.")
async def status(interaction: discord.Interaction):
    await interaction.response.defer()

    data = await get_bot_status()
    msg = (
        f"**Bot Online:** {data['online']}\n"
        f"**Latency:** {data['latency_ms']}ms\n"
        f"**Last Restart:** <t:{int(data['last_restart'])}:R>"
    )

    await interaction.followup.send(msg)

# ===============================
# /embed — Generate embeddings (stub)
# ===============================
@bot.tree.command(name="embed", description="Generate text embeddings (stub).")
async def embed(interaction: discord.Interaction, text: str):
    await interaction.response.defer()

    data = await send_embed_request(text)
    msg = (
        f"**Embedding Stub:**\n"
        f"Status: {data['status']}\n"
        f"Input Length: {data['input_length']}\n"
        f"Message: {data['message']}"
    )

    await interaction.followup.send(msg)

# ===============================
# Run the bot
# ===============================
bot.run(DISCORD_TOKEN)
