import discord
import uuid
import requests
import openai
import os
from discord.ext import commands

# === CONFIG ===
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
openai.api_key = OPENAI_API_KEY
MODEL = "gpt-4"

# === BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True  # Required to read ! commands
bot = commands.Bot(command_prefix='!', intents=intents)

# === Global game state (shared) ===
global_game = {
    "active": False,
    "game_id": None,
    "last_guess": None,
    "last_result": None
}

# === Submit guess to WhatBeatsRock API with debug ===
def submit_guess(game_id, guess):
    url = "https://www.whatbeatsrock.com/api/vs"
    payload = {"gameId": game_id, "guess": guess}
    try:
        response = requests.post(url, json=payload)
        if response.status_code != 200:
            return {
                "result": f"❌ API returned status {response.status_code}",
                "details": response.text
            }
        if not response.text.strip():
            return {
                "result": "❌ Empty response from server. Game ID may be expired or guess was rejected.",
                "details": f"Game ID: {game_id}, Guess: {guess}"
            }
        return response.json()
    except Exception as e:
        return {"result": f"Error submitting guess: {e}"}

# === Get next guess from OpenAI ===
def get_next_guess(last_result, last_guess):
    prompt = f"""
We're playing a clever word game called 'What Beats Rock'.
Last guess: "{last_guess}" — Result: "{last_result}".
Suggest a new, clever one-word guess. Just return the word. No explanation.
"""
    try:
        response = openai.ChatCompletion.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=1.1
        )
        return response["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return "rock"

# === Command: Start a new global game ===
@bot.command()
async def start(ctx):
    global_game["game_id"] = str(uuid.uuid4())
    global_game["last_guess"] = "rock"
    global_game["last_result"] = None
    global_game["active"] = True

    await ctx.send("🟢 New game started!\nFirst guess: **rock**\nUse `!round` or `!round yourword` to play.")

# === Command: Play round with optional user guess ===
@bot.command()
async def round(ctx, *, user_guess=None):
    if not global_game["active"]:
        await ctx.send("❌ No game running. Use `!start` first.")
        return

    guess = user_guess.strip().lower() if user_guess else global_game["last_guess"]
    result = submit_guess(global_game["game_id"], guess)

    # Always show the guess and result
    await ctx.send(f"🎯 Guess: **{guess}**\n📊 Result: {result.get('result')}")

    # Show debug details if available
    if "details" in result:
        await ctx.send(f"🔍 Debug: `{result['details']}`")

    if "lose" in result.get("result", "").lower():
        global_game["active"] = False
        await ctx.send("💀 The guess LOST. Game over for everyone. Use `!start` to try again.")
        return

    next_guess = get_next_guess(result.get("result", ""), guess)
    global_game["last_guess"] = next_guess
    global_game["last_result"] = result.get("result", "")

    await ctx.send(f"🤖 The AI suggests: **{next_guess}**\nUse `!round` or `!round yourword` to continue!")

# === Ping test ===
@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")

# === Run the bot ===
bot.run(DISCORD_TOKEN)
