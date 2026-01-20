import os
import discord
import logging
import argparse
from discord.ext import commands, tasks
from dotenv import load_dotenv
from typing import List, Tuple, Optional
from datetime import datetime, time, timezone, timedelta
from db import *

# Args config
parser = argparse.ArgumentParser(description="Analyze Wordle messages")
parser.add_argument("--overwrite", action="store_true", help="To overwrite existing log files")
args = parser.parse_args()

# Logging config
load_dotenv()
log_mode = "w" if args.overwrite else "a"
logging.basicConfig(
    filename="score.log", 
    level=logging.INFO, 
    filemode=log_mode,
    format='%(asctime)s %(levelname)s:%(message)s'
)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("DISCORD_TOKEN")
try:
    WORDLE_BOT_ID = int(os.environ.get("WORDLE_BOT_ID", "0"))
    WORDLE_CHANNEL_ID = int(os.environ.get("WORDLE_CHANNEL_ID", "0"))
except ValueError:
    WORDLE_BOT_ID = 0
    WORDLE_CHANNEL_ID = 0
    print("ERROR: Invalid IDs in .env")

# Time config (Spain UTC+1)
SPAIN_TZ = timezone(timedelta(hours=1))
DAILY_TIME = time(0, 30, tzinfo=SPAIN_TZ)
START_DATE_FALLBACK = datetime(2025, 12, 7, 0, 0, 0, tzinfo=SPAIN_TZ)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)


def process_message(msg: discord.Message, users: List[Tuple[str, int]]) -> List[int]:
    """
    Detects absolute winners.
    """
    if "results" not in msg.content.lower():
        return []

    lines = msg.content.split('\n')
    if len(lines) < 2:
        return []

    winners = []
    # Strict check on lines[1] matches original logic
    target_line = lines[1]
    target_line_lower = target_line.lower()

    for username, user_id in users:
        # Check if username (case-insensitive) or ID is in the second line
        if username.lower() in target_line_lower or str(user_id) in target_line:
            winners.append(user_id)
            
    return winners

def process_comparison(msg: discord.Message, user_a: discord.Member, user_b: discord.Member) -> Optional[int]:
    """
    Head-to-Head logic.
    Winner ID, -1 if tie, None if not found.
    """
    if "results" not in msg.content.lower():
        return None

    a_ids = {user_a.name.lower(), user_a.display_name.lower(), str(user_a.id)}
    b_ids = {user_b.name.lower(), user_b.display_name.lower(), str(user_b.id)}

    lines = msg.content.split('\n')
    idx_a = -1
    idx_b = -1

    for i, line in enumerate(lines):
        line_lower = line.lower()
        if idx_a == -1 and any(uid in line_lower for uid in a_ids):
            idx_a = i
        if idx_b == -1 and any(uid in line_lower for uid in b_ids):
            idx_b = i
        
        if idx_a != -1 and idx_b != -1:
            break
    
    if idx_a == -1 or idx_b == -1:
        return None

    if idx_a < idx_b:
        return user_a.id
    elif idx_b < idx_a:
        return user_b.id
    else:
        return -1

async def sync_results(channel: discord.TextChannel):
    """
    Reads new messages and updates DB using efficient cursor.
    """
    last_id = get_last_processed_id()
    # If no last_id (clean DB), start from fallback date
    after_marker = discord.Object(id=last_id) if last_id else START_DATE_FALLBACK
    
    users = get_users()
    count = 0
    last_seen_id = last_id

    logger.info(f"Syncing from {last_id if last_id else f'Start ({START_DATE_FALLBACK})'}...")
    logger.info(f"Users in DB: {len(users)}")
    
    if len(users) == 0:
        logger.warning("WARNING: No users in DB. Use !login.")

    async for msg in channel.history(limit=None, after=after_marker):
        if msg.author.id == WORDLE_BOT_ID:
            winners = process_message(msg, users)
            for winner_id in winners:
                log_win(msg.id, winner_id, msg.created_at.timestamp())
                count += 1
            logger.info(f"Winners: {winners}  date {msg.created_at}")
        last_seen_id = msg.id

    if last_seen_id and last_seen_id != last_id:
        set_last_processed_id(last_seen_id)
        logger.info(f"Sync complete. {count} new wins logged. New cursor: {last_seen_id}")
    else:
        logger.info("Sync complete. No new messages.")

    return count


@tasks.loop(time=DAILY_TIME)
async def daily_scoreboard_task():
    if WORDLE_CHANNEL_ID == 0:
        logger.warning("WORDLE_CHANNEL_ID not set, skipping daily task.")
        return

    channel = bot.get_channel(WORDLE_CHANNEL_ID)
    if not channel or not isinstance(channel, discord.TextChannel):
        logger.error(f"Channel {WORDLE_CHANNEL_ID} invalid.")
        return

    await sync_results(channel)
    
    scores = get_total_scores()
    embed = create_scoreboard_embed(scores, "🏆 Daily Scoreboard 🏆")
    await channel.send(embed=embed)

def create_scoreboard_embed(scores, title):
    embed = discord.Embed(title=title, color=0x6aaa64)
    description = ""
    for i, (_, name, wins) in enumerate(scores, 1):
        emoji = "🥇 " if i == 1 else "🥈 " if i == 2 else "🥉 " if i == 3 else f"{i}. "
        description += f"{emoji}**{name}**: {wins} victorias\n"
    
    embed.description = description if description else "No data yet."
    return embed


@bot.event
async def on_ready():
    init_db()
    if not daily_scoreboard_task.is_running():
        daily_scoreboard_task.start()
    print(f"Connected as {bot.user}")

@bot.command()
async def login(ctx):
    try:
        add_user(ctx.author.id, ctx.author.display_name)
        logger.info(f"User registered: {ctx.author.display_name}")
        await ctx.send(f"✅ Registered {ctx.author.display_name}!")
    except Exception as e:
        logger.error(f"Error login {ctx.author.id}: {e}")
        await ctx.send("❌ Error registering.")

@bot.command()
async def scoreboard(ctx):
    msg = await ctx.send("🔄 Syncing results...")
    try:
        if isinstance(ctx.channel, discord.TextChannel):
            new_wins = await sync_results(ctx.channel)
        else:
            new_wins = 0
        
        scores = get_total_scores()
        embed = create_scoreboard_embed(scores, "🏆 Victorias 🏆")
        embed.set_footer(text=f"Synced {new_wins} new results.")
        await msg.edit(content=None, embed=embed)
    except Exception as e:
        logger.error(f"Error in scoreboard: {e}")
        await msg.edit(content="❌ Error processing data.")

@bot.command()
async def compare(ctx, user_a: discord.Member, user_b: discord.Member):
    if not isinstance(ctx.channel, discord.TextChannel):
        await ctx.send("Text channels only.")
        return

    status_msg = await ctx.send(f"⚔️ Analyzing H2H: {user_a.display_name} vs {user_b.display_name}...")
    h2h_stats = {user_a.id: 0, user_b.id: 0, -1: 0}

    async for msg in ctx.channel.history(limit=None, after=START_DATE_FALLBACK):
        if msg.author.id == WORDLE_BOT_ID:
            winner_id = process_comparison(msg, user_a, user_b)
            if winner_id is not None:
                h2h_stats[winner_id] += 1

    embed = discord.Embed(title=f"⚔️ {user_a.display_name} vs {user_b.display_name} ⚔️", color=0x4a6a9b)
    embed.add_field(name=user_a.display_name, value=f"**{h2h_stats[user_a.id]}** victorias", inline=True)
    embed.add_field(name=user_b.display_name, value=f"**{h2h_stats[user_b.id]}** victorias", inline=True)
    embed.add_field(name="Ties", value=f"**{h2h_stats[-1]}**", inline=True)

    if h2h_stats[user_a.id] > h2h_stats[user_b.id]: footer = f"¡{user_a.display_name} va ganando!"
    elif h2h_stats[user_b.id] > h2h_stats[user_a.id]: footer = f"¡{user_b.display_name} va ganando!"
    else: footer = "¡Empate!"
    
    embed.set_footer(text=footer)
    await status_msg.delete()
    await ctx.send(embed=embed)

if TOKEN:
    bot.run(TOKEN)
else:
    print("ERROR: DISCORD_TOKEN missing.")
