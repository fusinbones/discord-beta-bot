#!/usr/bin/env python3
"""
Minimal Discord bot test for Railway deployment
"""
import discord
import os
from discord.ext import commands

# Bot setup with minimal intents
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Test bot is online! Logged in as {bot.user}')
    print(f'Connected to {len(bot.guilds)} servers')

@bot.command()
async def ping(ctx):
    """Simple ping command to test bot functionality"""
    await ctx.send('Pong! Bot is working on Railway!')

if __name__ == "__main__":
    token = os.getenv('DISCORD_BOT_TOKEN')
    if not token:
        print("ERROR: DISCORD_BOT_TOKEN not found in environment variables")
        exit(1)
    
    print("Starting minimal test bot...")
    bot.run(token)
