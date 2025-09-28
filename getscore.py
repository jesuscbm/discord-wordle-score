"""
Wordle Results Analyzer 

Counts wins from Discord Wordle bot messages

Author: Jesús Blázquez
"""
from dotenv import load_dotenv
import os
import discord
import logging
import argparse

intents = discord.Intents.default()
intents.message_content=True
client = discord.Client(intents=intents)
"""
For self-botting, delete the three lines above and uncomment the line below:
"""
# client = discord.Client()

load_dotenv()

TOKEN=os.environ.get("DISCORD_TOKEN")
CHANNEL_ID=os.environ.get("CHANNEL_ID", "0")
WORDLE_BOT_ID=os.environ.get("WORDLE_BOT_ID", "0")

U1_ID=os.environ.get("U1_ID", "0")
U2_ID=os.environ.get("U2_ID", "0")
U1_NAME=os.environ.get("U1_NAME", "0")
U2_NAME=os.environ.get("U2_NAME", "0")
U1_DISCORD_NAME=os.environ.get("U1_DISCORD_NAME", "0")
U2_DISCORD_NAME=os.environ.get("U2_DISCORD_NAME", "0")

parser = argparse.ArgumentParser(description="Analyze Wordle messages")
parser.add_argument("--debug", action="store_true", help="To log all discarded messages into discarded.log")
parser.add_argument("--overwrite", action="store_true", help="To overwrite existing log files")
args = parser.parse_args()

u2_score: int = 0 
u1_score: int = 0
ties: int = 0

logger = logging.getLogger(__name__)
if args.overwrite:
    logging.basicConfig(filename="score.log", level=logging.INFO, filemode="w")
else:
    logging.basicConfig(filename="score.log", level=logging.INFO)

if args.debug:
    discarded = logging.getLogger("discarded")
    discarded.addHandler(logging.FileHandler("discarded.log"))

def process_message(msg: discord.Message):
    global u2_score, u1_score, ties
    if "results" in msg.content:
        u1_position = msg.content.find(U1_ID)
        u2_position = msg.content.find(U2_ID)
        if u1_position == -1:
            u1_position = msg.content.find(U1_DISCORD_NAME)
        if u2_position == -1:
            u2_position = msg.content.find(U2_DISCORD_NAME)
        time = msg.created_at.strftime("%Y-%m-%d")
        if u1_position == -1 or u2_position == -1:
            if args.debug:
                discarded.info(f"\n{time}\n{msg.content}")
                return
        elif u2_position > u1_position:
            if msg.content.find("\n", u1_position, u2_position) != -1:
                u1_score += 1 
                logger.info(f"{time}: {U1_NAME} wins\n {msg.content}")
            else:
                ties += 1
                logger.info(f"{time}: Tie\n {msg.content}")
        elif u1_position > u2_position:
            if msg.content.find("\n", u2_position, u1_position) != -1:
                u2_score += 1
                logger.info(f"{time}: {U2_NAME} wins\n {msg.content}")
            else:
                ties += 1
                logger.info(f"{time}: Tie\n {msg.content}")


@client.event
async def on_ready():
    channel_id = int(CHANNEL_ID)
    if channel_id:
        channel = await client.fetch_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            async for msg in channel.history(limit=None, oldest_first=True):
                if msg.author.id==int(WORDLE_BOT_ID):
                    process_message(msg)

    print("\n=== RESULTS ===")
    print(f"{U1_NAME} wins: {u1_score}")
    print(f"{U2_NAME} wins: {u2_score}")
    print(f"Ties: {ties}")

    await client.close()

if TOKEN is not None:
    client.run(TOKEN)
