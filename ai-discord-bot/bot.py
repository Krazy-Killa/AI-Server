# bot.py

import asyncio
import logging
import math
import os
import re
import sys

import aiohttp
import discord
from discord import app_commands

from backend_api import (
    send_chat,
    send_bot_heartbeat,
    report_bot_event,
    get_models,
    select_model,
    get_bot_status,
    send_embed_request
)

from config import DISCORD_TOKEN

intents = discord.Intents.default()
intents.message_content = True
logger = logging.getLogger(__name__)
heartbeat_task: asyncio.Task | None = None

class AIBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)


bot = AIBot()


def get_mention_prompt(message: discord.Message) -> str | None:
    """Return the message text when the bot is directly mentioned."""
    if bot.user is None or bot.user not in message.mentions:
        return None

    prompt = re.sub(rf"<@!?{bot.user.id}>", "", message.content).strip()
    return prompt or (
        "A user mentioned you without asking a specific question. "
        "Greet them briefly and ask how you can help."
    )


async def reply_in_chunks(message: discord.Message, reply: str) -> None:
    """Send a long model response without exceeding Discord's message limit."""
    remaining = reply.strip()
    first_chunk = True
    allowed_mentions = discord.AllowedMentions.none()

    while remaining:
        if len(remaining) > 1900:
            split_at = max(
                remaining.rfind("\n", 0, 1900),
                remaining.rfind(" ", 0, 1900),
            )
            if split_at <= 0:
                split_at = 1900
            chunk, remaining = remaining[:split_at], remaining[split_at:].lstrip()
        else:
            chunk, remaining = remaining, ""

        if first_chunk:
            await message.reply(
                chunk,
                mention_author=False,
                allowed_mentions=allowed_mentions,
            )
            first_chunk = False
        else:
            await message.channel.send(chunk, allowed_mentions=allowed_mentions)


# ===============================
# Bot Ready Event
# ===============================
@bot.event
async def on_ready():
    global heartbeat_task

    print(f"Bot logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands.")
        event = f"Connected as {bot.user}; synced {len(synced)} slash commands."
    except Exception:
        logger.exception("Error syncing application commands")
        event = "Connected to Discord, but slash-command sync failed."

    try:
        await report_bot_event(event)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        logger.exception("Could not report bot startup event")

    if heartbeat_task is None or heartbeat_task.done():
        heartbeat_task = asyncio.create_task(bot_heartbeat_loop())


async def bot_heartbeat_loop():
    while not bot.is_closed():
        try:
            latency_ms = (
                round(bot.latency * 1000)
                if math.isfinite(bot.latency)
                else None
            )
            result = await send_bot_heartbeat(
                latency_ms,
                [command.name for command in bot.tree.get_commands()],
            )
            if result.get("restart_requested"):
                await report_bot_event("Restarting on dashboard request.")
                os.execv(sys.executable, [sys.executable, *sys.argv])
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
            logger.exception("Could not report Discord bot heartbeat")

        await asyncio.sleep(5)


@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    prompt = get_mention_prompt(message)
    if prompt is None:
        return

    try:
        async with message.channel.typing():
            result = await send_chat(prompt)
        reply = result.get("reply") if isinstance(result, dict) else None
        if not isinstance(reply, str) or not reply.strip():
            logger.warning("Chat backend returned no reply: %r", result)
            await message.reply(
                "I couldn't get a response from the AI backend. Please try again shortly.",
                mention_author=False,
                allowed_mentions=discord.AllowedMentions.none(),
            )
            return

        await report_bot_event("Answered a direct mention.")
        await reply_in_chunks(message, reply)
    except (aiohttp.ClientError, asyncio.TimeoutError, ValueError):
        logger.exception("Mention reply failed while contacting the AI backend")
        await message.reply(
            "I couldn't reach the AI backend just now. Please try again shortly.",
            mention_author=False,
            allowed_mentions=discord.AllowedMentions.none(),
        )

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
    models = data.get("models", [])
    active_model_id = data.get("active_model")
    active_model = next(
        (model for model in models if model.get("id") == active_model_id),
        None,
    )

    active_name = active_model["name"] if active_model else "None loaded"
    lines = [f"**Active Model:** {active_name}", "", "**Installed Models:**"]
    for model in models:
        status = "loaded" if model.get("loaded") else "installed"
        lines.append(f"- `{model['id']}` — {model['name']} ({status})")

    await interaction.followup.send("\n".join(lines))

# ===============================
# /selectmodel — Switch active model
# ===============================
@bot.tree.command(name="selectmodel", description="Switch the active AI model.")
async def selectmodel(interaction: discord.Interaction, model_id: str):
    await interaction.response.defer()

    result = await select_model(model_id)
    if result.get("success"):
        active_model = result.get("active_model", model_id)
        await interaction.followup.send(f"Model switched to `{active_model}`.")
    else:
        detail = result.get("detail", f"Model `{model_id}` could not be selected.")
        await interaction.followup.send(str(detail)[:1900])

# ===============================
# /status — Bot status from backend
# ===============================
@bot.tree.command(name="status", description="Get bot status from backend.")
async def status(interaction: discord.Interaction):
    await interaction.response.defer()

    data = await get_bot_status()
    last_restart = data.get("last_restart")
    last_restart_text = (
        f"<t:{int(last_restart)}:R>" if last_restart is not None else "Unknown"
    )
    latency = data.get("latency_ms")
    latency_text = f"{latency}ms" if latency is not None else "N/A"
    msg = (
        f"**Bot Online:** {data['online']}\n"
        f"**Latency:** {latency_text}\n"
        f"**Last Restart:** {last_restart_text}"
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
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)
