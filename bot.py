import discord
import uuid
import requests
import openai
import os
import asyncio
from discord.ext import commands

# === CONFIG ===
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY
MODEL = "gpt-4"

# === BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# === Game State ===
global_game = {
    "active": False,
    "game_id": None,
    "last_guess": None,
    "last_result": None,
    "failures": 0  # Track 418 errors
}

# Cooldown tracking
user_cooldowns = {}
cooldown_seconds = 5
global_last_used = 0
global_cooldown = 0.5

# === Guess Submission ===
def submit_guess(game_id, guess):
    url = "https://www.whatbeatsrock.com/api/vs"
    payload = {"gameId": game_id, "guess": guess}
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (DiscordBot) WhatBeatsRock-Bot"
    }
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 418:
            return {
                "result": "🚫 The server thinks we're guessing too aggressively (HTTP 418).",
                "code": 418
            }
        elif response.status_code != 200 or not response.text.strip():
            return {
                "result": f"❌ API error: status {response.status_code}",
                "code": response.status_code
            }
        return response.json()
    except Exception as e:
        return {"result": f"⚠️ Network error: {e}", "code": -1}

# === OpenAI Guessing ===
def get_next_guess(last_result, last_guess):
    prompt = f"""
We're playing a word game called 'What Beats Rock'.
Last guess: "{last_guess}" — Result: "{last_result}".
Suggest a new one-word guess. Just return the word.
"""
    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1
        )
        return response["choices"][0]["message"]["content"].strip()
    except:
        return "rock"

# === Command: Start New Game ===
@bot.command()
async def start(ctx):
    global_game["game_id"] = str(uuid.uuid4())
    global_game["last_guess"] = "rock"
    global_game["last_result"] = None
    global_game["failures"] = 0
    global_game["active"] = True
    await ctx.send("🟢 New game started!\nFirst guess: **rock**\nUse `!round` or `!round yourword` to play.")

# === Command: Play Round ===
@bot.command()
async def round(ctx, *, user_guess=None):
    user_id = ctx.author.id
    now = asyncio.get_event_loop().time()

    # Check if game is active
    if not global_game["active"]:
        await ctx.send("❌ No active game. Use `!start` first.")
        return

    # Per-user cooldown
    if user_id in user_cooldowns and now - user_cooldowns[user_id] < cooldown_seconds:
        remaining = round(cooldown_seconds - (now - user_cooldowns[user_id]), 1)
        await ctx.send(f"⏳ Slow down! You must wait {remaining}s before guessing again.")
        return

    # Global cooldown
    global global_last_used
    if now - global_last_used < global_cooldown:
        await asyncio.sleep(global_cooldown)

    global_last_used = now
    user_cooldowns[user_id] = now

    # Determine guess
    guess = user_guess.strip().lower() if user_guess else global_game["last_guess"]
    if not user_guess:
        guess = get_next_guess(global_game["last_result"], global_game["last_guess"])

    await ctx.send("🕐 Processing...")
    await asyncio.sleep(0.1)  # tiny pause to simulate real-time feel

    # Submit guess
    result = submit_guess(global_game["game_id"], guess)
    code = result.get("code", 0)

    await ctx.send(f"🎯 Guess: **{guess}**\n📊 Result: {result['result']}")

    # Handle block (418)
    if code == 418:
        global_game["failures"] += 1
        if global_game["failures"] >= 3:
            await ctx.send("🔄 Too many blocks. Resetting game session.")
            await start(ctx)
        else:
            await ctx.send(f"⚠️ Warning: {global_game['failures']} failure(s). Game will reset at 3.")
        return

    # Reset failure count on success
    global_game["failures"] = 0

    if "lose" in result["result"].lower():
        global_game["active"] = False
        await ctx.send("💀 The guess LOST. Game over. Use `!start` to play again.")
        return

    # Store result for next GPT prompt
    global_game["last_guess"] = guess
    global_game["last_result"] = result["result"]

    await ctx.send(f"🤖 Next? Use `!round` or `!round yourword` to continue!")

# === Command: Ping Test ===
@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")

# === Run Bot ===
bot.run(DISCORD_TOKEN)
