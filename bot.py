import asyncio
import logging
import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from keep_alive import keep_alive

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("bot")

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True   # Message Content Intent
intents.members = True           # Server Members Intent
intents.presences = True         # Presence Intent
intents.voice_states = True      # needed for on_voice_state_update


class MyBot(commands.Bot):
    async def setup_hook(self):
        await self.load_extension("cogs.vc_announcer")
        await self.load_extension("cogs.music")
        logger.info("Cogs loaded.")


bot = MyBot(command_prefix="!", intents=intents)


@bot.event
async def on_ready():
    logger.info(f"Logged in as {bot.user} (ID: {bot.user.id})")


async def main():
    if not TOKEN:
        raise RuntimeError("DISCORD_TOKEN is not set — check your .env file.")
    
    # Start the dummy web server to keep Render happy
    keep_alive()
    
    async with bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
