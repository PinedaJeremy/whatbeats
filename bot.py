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
MODEL = "gpt-4"  # You can use "gpt-3.5-turbo" to save credits

# === BOT SETUP ===
intents = discord.Intents.default()
intents.message_content = True  # ✅ Add this line

bot = commands.Bot(command_prefix='!', intents=intents)

# === Global game state ===
global_game = {
    "active": False,
    "game_id": None,
    "last_guess": None,
    "last_result": None
}

# === Submit guess to WhatBeatsRock API ===
def submit_guess(game_id, guess):
    url = "https://www.whatbeatsrock.com/api/vs"
    payload = {"gameId": game_id, "guess": guess}
    try:
        response = requests.post(url, json=payload)
        return response.json()
    except Exception as e:
        return {"result": f"Error: {e}"}

# === Generate next guess from OpenAI ===
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
# === Command: Play one global round ===
@bot.command()
async def ping(ctx):
    await ctx.send("pong 🏓")

# === Command: Start new global game ===
@bot.command()
async def start(ctx):
    if global_game["active"]:
        await ctx.send("🟡 A game is already in progress. Use `!round` to play the next move.")
        return

    global_game["game_id"] = str(uuid.uuid4())
    global_game["last_guess"] = "rock"
    global_game["last_result"] = None
    global_game["active"] = True

    # ✅ Fixed string formatting here
    await ctx.send("🟢 A new global game has started!\nFirst guess: **rock**\nUse `!round` to continue!")

# === Command: Play one global round ===
@bot.command()
async def round(ctx):
    if not global_game["active"]:
        await ctx.send("❌ No game is currently running. Start one with `!start`.")
        return

    guess = global_game["last_guess"]
    result = submit_guess(global_game["game_id"], guess)

    if "result" not in result:
        await ctx.send(f"⚠️ Error from game API: {result}")
        return

    result_text = result["result"]
    await ctx.send(f"🎯 Guess: **{guess}**\n📊 Result: **{result_text}**")

    if "lose" in result_text.lower():
        global_game["active"] = False
        await ctx.send("💀 The guess LOST. The game is over for everyone. Use `!start` to begin a new game.")
        return

    next_guess = get_next_guess(result_text, guess)
    global_game["last_guess"] = next_guess
    global_game["last_result"] = result_text

    await ctx.send(f"🤖 The AI suggests the next guess: **{next_guess}**\nUse `!round` to play it!")

# === Start the bot ===
bot.run(DISCORD_TOKEN)
