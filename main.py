from typing import Tuple
from dotenv import load_dotenv
import os
import discord
from discord.ext import commands
import logging
from typing import List, Tuple, Optional
import argparse
from db import *
from datetime import datetime, timezone, timedelta


intents = discord.Intents.default()
intents.message_content=True
bot = commands.Bot(command_prefix='!', intents=intents)

offset_spain = timezone(timedelta(hours=1))
fecha_obj = datetime(2025, 12, 7, 0, 0, 0, tzinfo=offset_spain)


load_dotenv()

TOKEN=os.environ.get("DISCORD_TOKEN")
# Obtenemos el ID y lo convertimos a int. Si no existe, usamos 0.
try:
    WORDLE_BOT_ID=int(os.environ.get("WORDLE_BOT_ID", "0"))
    if WORDLE_BOT_ID == 0:
        print("ADVERTENCIA: WORDLE_BOT_ID no está configurado en .env o es 0. El bot no podrá encontrar mensajes.")
except ValueError:
    print("ERROR: WORDLE_BOT_ID en .env no es un número válido.")
    WORDLE_BOT_ID = 0


parser = argparse.ArgumentParser(description="Analyze Wordle messages")
# parser.add_argument("--debug", action="store_true", help="To log all discarded messages into discarded.log")
parser.add_argument("--overwrite", action="store_true", help="To overwrite existing log files")
args = parser.parse_args()

logger = logging.getLogger(__name__)
if args.overwrite:
    logging.basicConfig(filename="score.log", level=logging.INFO, filemode="w")
else:
    logging.basicConfig(filename="score.log", level=logging.INFO)

def process_message(msg: discord.Message, users: List[Tuple[str, int]]) -> List[int] | None:
    """
    Comprueba un mensaje de resultados.
    Devuelve el ID del usuario ganador si se encuentra, o None.
    """
    if "results" not in msg.content.lower(): # Usamos .lower() por si acaso
        return None

    lines = msg.content.split('\n')
    if len(lines) < 2:
        return None # No hay segunda línea

    ret = []
    # Comprobamos cada usuario registrado
    for username, user_id in users:
        # Comprobamos si el nombre (guardado en la DB) o el ID (como string) están en la segunda línea
        if username in lines[1] or str(user_id) in lines[1]:
            ret.append(user_id) # Devuelve el ID del ganador
            
    return ret if ret != [] else None

def process_comparison(msg: discord.Message, user_a: discord.Member, user_b: discord.Member) -> Optional[int]:
    """
    Comprueba un mensaje para un enfrentamiento H2H (Head-to-Head).
    Devuelve el ID del ganador (user_a.id o user_b.id) o None.
    """
    if "results" not in msg.content.lower():
        return None
        
    # Creamos un conjunto de todos los posibles identificadores para cada usuario
    # (nombre de usuario, apodo en el servidor, ID como string)
    a_ids = {user_a.name, user_a.display_name, str(user_a.id)}
    b_ids = {user_b.name, user_b.display_name, str(user_b.id)}

    lines = msg.content.split('\n')
    a_line_index = -1
    b_line_index = -1

    # Buscamos en qué línea aparece cada usuario
    for i, line in enumerate(lines):
        if any(identifier in line for identifier in a_ids):
            a_line_index = i
        if any(identifier in line for identifier in b_ids):
            b_line_index = i
            
    # Si uno de los dos (o ambos) no aparecen, no es un enfrentamiento H2H
    if a_line_index == -1 or b_line_index == -1:
        return None
        
    # Si A está en una línea anterior a B, A gana
    if a_line_index < b_line_index:
        return user_a.id
    # Si B está en una línea anterior a A, B gana
    elif b_line_index < a_line_index:
        return user_b.id
    # Si están en la misma línea, es un empate, no una victoria
    else:
        return -1   # -1 Indica empate


@bot.event
async def on_ready():
    init_db()
    print(f"Connected as {bot.user}")

@bot.command()
async def login(ctx):
    """Registra a un usuario en la base de datos para el seguimiento."""
    try:
        add_user(ctx.author.id, ctx.author.display_name)
        logger.info(f"New user {ctx.author.display_name} (ID: {ctx.author.id})")
        await ctx.send(f"¡Registrado! {ctx.author.display_name}, tus victorias se contarán.")
    except Exception as e:
        logger.error(f"Error al registrar a {ctx.author.id}: {e}")
        await ctx.send("Hubo un error al registrarte.")
        

@bot.command()
async def scoreboard(ctx):
    """Muestra la tabla de clasificación de victorias totales."""
    channel = ctx.message.channel
    users_list = get_users() # Lista de tuplas (username, id)
    
    if not users_list:
        await ctx.send("Nadie se ha registrado todavía. Usa `!login` para empezar.")
        return

    # Creamos un mapa de ID -> Nombre para la puntuación
    # y un diccionario de puntuaciones inicializado a 0
    user_map = {}
    scores = {}
    for username, user_id in users_list:
        user_map[user_id] = username
        scores[user_id] = 0

    logger.info(f"Getting scoreboard for: {user_map.values()}")
    
    processing_msg = await ctx.send(f"Analizando el historial de Wordle... 🔍 (max {2000} mensajes)")

    # Recorremos el historial
    async for msg in channel.history(limit=2000, after=fecha_obj): # Pon un límite para no sobrecargar
        if msg.author.id == WORDLE_BOT_ID:
            winner_ids = process_message(msg, users_list)
            if winner_ids == None:
                continue
            for winner_id in winner_ids:
                if winner_id in scores:
                    scores[winner_id] += 1
                
    # Ordenamos los resultados
    sorted_scores = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    
    # Creamos el embed
    embed = discord.Embed(title="🏆 Scoreboard de Victorias 🏆", color=0x6aaa64)
    description = ""
    rank = 1
    for user_id, score in sorted_scores:
        emoji = ""
        if rank == 1: emoji = "🥇 "
        elif rank == 2: emoji = "🥈 "
        elif rank == 3: emoji = "🥉 "
        
        # Obtenemos el nombre del mapa, si no, usamos el ID
        username = user_map.get(user_id, f"Usuario (ID: {user_id})")
        description += f"{emoji}**{rank}. {username}**: {score} victorias\n"
        rank += 1
        
    embed.description = description
    
    await processing_msg.delete() # Borramos el mensaje "Analizando..."
    await ctx.send(embed=embed)


@bot.command()
async def compare(ctx, user_a: discord.Member, user_b: discord.Member):
    """Compara quién ha ganado más entre dos usuarios. Uso: !compare @UsuarioA @UsuarioB"""
    channel = ctx.message.channel
    
    h2h_scores = {
        user_a.id: 0,
        user_b.id: 0,
        -1: 0,
    }
    
    logger.info(f"Iniciando comparación H2H entre {user_a.display_name} y {user_b.display_name}")
    processing_msg = await ctx.send(f"Analizando enfrentamientos entre {user_a.display_name} y {user_b.display_name}... ⚔️")

    async for msg in channel.history(limit=2000, after=fecha_obj):
        if msg.author.id == WORDLE_BOT_ID:
            winner_id = process_comparison(msg, user_a, user_b)
            if winner_id in h2h_scores:
                h2h_scores[winner_id] += 1
                
    # Preparamos el resultado
    embed = discord.Embed(
        title=f"⚔️ Enfrentamiento: {user_a.display_name} vs {user_b.display_name} ⚔️",
        color=0x4a6a9b
    )
    
    embed.add_field(
        name=user_a.display_name,
        value=f"**{h2h_scores[user_a.id]}** victorias",
        inline=True
    )
    embed.add_field(
        name=user_b.display_name,
        value=f"**{h2h_scores[user_b.id]}** victorias",
        inline=True
    )
    embed.add_field(
        name="Empates",
        value=f"**{h2h_scores[-1]}** victorias",
        inline=True
    )
    
    # Determinamos un ganador
    if h2h_scores[user_a.id] > h2h_scores[user_b.id]:
        winner_text = f"¡{user_a.display_name} va ganando!"
    elif h2h_scores[user_b.id] > h2h_scores[user_a.id]:
        winner_text = f"¡{user_b.display_name} va ganando!"
    else:
        winner_text = "¡Es un empate!"
        
    embed.set_footer(text=winner_text)
    
    await processing_msg.delete()
    await ctx.send(embed=embed)


if TOKEN is not None:
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error al iniciar el bot: {e}")
else:
    print("ERROR: DISCORD_TOKEN no encontrado en el fichero .env")
