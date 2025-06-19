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

# === Global Game State ===
global_game = {
    "active": False,
    "game_id": None,
    "last_guess": None,
    "last_result": None
}

# === Submit a Guess to the Game API ===
def submit_guess(game_id, guess):
    url = "https://www.whatbeatsrock.com/api/vs"
    payload = {"gameId": game_id, "guess": guess}
    try:
        response = requests.post(url, json=payload)
        if response.status_code == 418:
            return {
                "result": "🚫 The server thinks we're guessing too aggressively (HTTP 418). Try a new word or wait a moment.",
                "details": "Rate limited or blocked guess."
            }
        if response.status_code != 200:
            return {
                "result": f"❌ API returned unexpected status {response.status_code}",
                "details": response.text or "No response text."
            }
        if not response.text.strip():
            return {
                "result": "❌ Empty response from server.",
                "details": f"Game ID: {game_id}, Guess: {guess}"
            }
        return response.json()
    except Exception as e:
        return {"result": f"Error submitting guess: {e}"}

# === Use GPT to Get a Next Guess ===
def get_next_guess(last_result, last_guess):
    prompt = f"""
We're playing a creative word game called 'What Beats Rock'.
Last guess: "{last_guess}" — Result: "{last_result}".
Suggest a clever one-word guess that might win the next round. Just return the word.
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

# === Command: Start a New Game ===
@bot.command()
async def start(ctx):
    global_game["game_id"] = str(uuid.uuid4())
    global_game["last_guess"] = "rock"
    global_game["last_result"] = None
    global_game["active"] = True

    await ctx.send("🟢 New game started!\nFirst guess: **rock**\nUse `!round` or `!round yourword` to continue.")

# === Command: Play a Round ===
@bot.command()
async def round(ctx, *, user_guess=None):
    if not global_game["active"]:
        await ctx.send("❌ No active game. Use `!start` first.")
        return

    guess = user_guess.strip().lower() if user_guess else global_game["last_guess"]

    await ctx.send("🕒 Thinking...")
    await asyncio.sleep(2)  # Anti-spam delay

    result = submit_guess(global_game["game_id"], guess)

    await ctx.send(f"🎯 Guess: **{guess}**\n📊 Result: {result.get('result')}")

    if "details" in result:
        await ctx.send(f"🔍 Debug: `{result['details']}`")

    if "lose" in result.get("result", "").lower():
        global_game["active"] = False
        await ctx.send("💀 The guess LOST. Game over. Use `!start` to begin again.")
        return

    next_guess = get_next_guess(result.get("result", ""), guess)
    global_game["last_guess"] = next_guess
    global_game["last_result"] = result.get("result", "")

    await ctx.send(f"🤖 The AI suggests: **{next_guess}**\nUse `!round` or `!round yourword` to continue!")

# === Command: Test Bot ===
@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")

# === Run Bot ===
bot.run(DISCORD_TOKEN)
