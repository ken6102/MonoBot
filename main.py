#######################################################################

import discord
import os
import sys
import requests
import re
import random
import datetime
import asyncio
import time
import pytz
import openai
import math
import sympy
import yt_dlp
import youtube_dl
import json
import asyncpraw
import qrcode
from openai import AsyncOpenAI
from googleapiclient.discovery import build
from discord import app_commands, FFmpegPCMAudio, FFmpegOpusAudio, PCMVolumeTransformer
from discord.ext import commands, tasks
from deep_translator import GoogleTranslator
from datetime import timezone
from pydub import AudioSegment
from io import BytesIO
from bs4 import BeautifulSoup
from googlesearch import search
from PIL import Image
from dotenv import load_dotenv

#######################################################################

intents = discord.Intents().all()
client = commands.Bot(command_prefix='!', intents=intents)
client.remove_command('help')

monobot = ["MonoBot"]

load_dotenv()

admin_ids = [int(uid) for uid in os.getenv('ADMIN_IDS', '').split(',') if uid.strip()]
owner_id = [int(uid) for uid in os.getenv('OWNER_ID', '').split(',') if uid.strip()]

chat_id = int(os.getenv('TTT_CHAT_ID'))
embed_img = os.getenv('EMBED_IMG')

reddit_id = os.getenv('REDDIT_ID')
reddit_secret = os.getenv('REDDIT_SECRET')
reddit_user_agent = os.getenv('REDDIT_USER_AGENT')

youtube_api_key = os.getenv('YOUTUBE_API_KEY')
openai_client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
xai_client = AsyncOpenAI(api_key=os.getenv('XAI_API_KEY'), base_url="https://api.x.ai/v1")
token = os.getenv('DISCORD_TOKEN')
restart_confirmation_pending = set()

gpt_model = "gpt-4o-mini-2024-07-18"
gpt_plus_model = "gpt-4.1-2025-04-14"
gpt_img_model = "dall-e-3"
grok_model = "grok-3-beta"
grok_img_model = "grok-2-image-1212"

game_sessions = {}

queue = []
looping = False
current_song = None
current_audio_source = None
default_volume = 0.1
suppress_auto_next = False
disconnect_timer_task = None
backup_queue = []
backup_looping = False

previously_asked = []
used_words = []

commandlock = False

#######################################################################

@client.event
async def on_ready():
    print('Bot logged in as {0.user}'.format(client))
    
    await client.change_presence(activity=discord.Activity(
        type=discord.ActivityType.playing, name="Grand Theft Auto VI"))

    client.loop.create_task(check_birthday())

    global reddit
    reddit = asyncpraw.Reddit(
        client_id=reddit_id,
        client_secret=reddit_secret,
        user_agent=reddit_user_agent)

    try:
        with open("commandlogs.txt", "r") as f:
            logs = f.readlines()

        if logs:
            last_log = logs[-1].strip()
            parts = last_log.split(";")
            if len(parts) >= 6:
                user_id, command_name, command_text, timestamp, channel_id, server_id = parts
                command_name = command_name.strip()

                if command_name == "restart":
                    channel = client.get_channel(int(channel_id.strip()))
                    if channel:
                        await channel.send("Successfully restarted the bot.")
    except FileNotFoundError:
        print("Command logs file not found.")
    except Exception as e:
        print(f"Error processing command logs: {e}")

#######################################################################

@client.event
async def on_command_error(ctx, error):
  if isinstance(error, discord.ext.commands.errors.CommandNotFound):
    await ctx.send("Unknown command, use !help to see available commands.")
    
#######################################################################

async def commandlockcheck(ctx):
  global commandlock
  if commandlock == True and ctx.author.id not in owner_id:
    await ctx.send("Commands are currently locked.")
    return True
  return False

#######################################################################

async def log_command_usage(ctx):
    try:
        user_id = ctx.author.id
        command = ctx.command.name if ctx.command else "Unknown"        
        message = ctx.message.content if ctx.message else "N/A"
        time_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        channel_id = ctx.channel.id if ctx.channel else "DM"
        server_id = ctx.guild.id if ctx.guild else "DM"
        log_entry = f"{user_id}; {command}; '{message}'; {time_str}; {channel_id}; {server_id}\n"

        with open("commandlogs.txt", "a") as f:
            f.write(log_entry)
    except Exception as e:
        print(f"Failed to log output: {e}")
    
#######################################################################

IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp")
def extract_image_attachments(msg):
    return [
        att for att in msg.attachments
        if (att.content_type and att.content_type.startswith("image"))
        or att.filename.lower().endswith(IMAGE_EXTS)
    ]

#######################################################################

async def check_birthday():
    await client.wait_until_ready()
    channel = client.get_channel(chat_id)
    
    while True:
        now = datetime.datetime.now(datetime.timezone.utc)
        if now.hour == 0 and now.minute == 0:
            try:
                with open("birthdays.txt", "r") as f:
                    birthdays = f.readlines()
                
                for entry in birthdays:
                    try:
                        user_id, birthday_str = entry.strip().split(":")
                        birthday = datetime.datetime.strptime(birthday_str, "%d/%m/%Y").date()

                        if birthday.day == now.day and birthday.month == now.month:
                            user = await client.fetch_user(int(user_id))
                            await channel.send(f"Happy birthday {user.mention}! 🎉")
                            await asyncio.sleep(1)

                    except (ValueError, IndexError) as e:
                        print(f"Error processing birthday entry: {entry}. Error: {e}")
                        
            except FileNotFoundError:
                print("birthdays.txt not found.")

            await asyncio.sleep(60) 

        await asyncio.sleep(30)

#######################################################################

@client.command(name='help', aliases=['h'])
async def help(ctx):  
  if await commandlockcheck(ctx):
    return
  await log_command_usage(ctx)

  embed = discord.Embed(title='Help', description='Help command list', color=discord.Color.blue())
  embed.set_thumbnail(url=embed_img)
  embed.add_field(name="!help", value="Displays this menu", inline=False)
  embed.add_field(name="!userinfo", value="Displays user information", inline=False)
  embed.add_field(name="!random", value="Randomly selects something from given entries", inline=False)
  embed.add_field(name="!calc", value="Computes the result of an arithmetic problem", inline=False)
  embed.add_field(name="!setbirthday", value="Lets you set your birthday", inline=False)
  embed.add_field(name="!greentext", value="Posts a random greentext", inline=False)
  embed.add_field(name="!ascii", value="Generates ASCII art from an image upload/url", inline=False)
  embed.add_field(name="!youtube", value="Posts a youtube video link based off the entered query", inline=False)
  embed.add_field(name="!translate", value="Translates between languages", inline=False)
  embed.add_field(name="!gpt", value="Uses GPT for responses, accurate up to October 2023", inline=False)
  embed.add_field(name='!games', value='Displays game commands', inline=False)
  embed.add_field(name="!vc", value="Displays voice call commands", inline=False)
  await ctx.send(embed=embed)

#######################################################################

@client.command(name='userinfo', aliases=['ui'])
async def userinfo(ctx, member: discord.Member = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if member is None:
        args = ctx.message.content.split()
        if len(args) > 1:
            raw = args[1].strip()
            raw = ''.join(ch for ch in raw if ch.isdigit())
            try:
                member = await ctx.guild.fetch_member(int(raw))
            except ValueError:
                return await ctx.send("Please provide a valid user ID.")
            except discord.NotFound:
                return await ctx.send(f"User ID `{raw}` is not in this server.")
        else:
            member = ctx.author

    if not member:
        member = ctx.author

    roles = [r.mention for r in member.roles if r != ctx.guild.default_role]
    embed = discord.Embed(
        title=f"User Info • {member.display_name}",
        color=discord.Color.blue()
    )
    embed.set_thumbnail(url=member.display_avatar.url)
    embed.add_field(name="Username", value=str(member), inline=True)
    embed.add_field(name="User ID", value=member.id, inline=True)
    embed.add_field(name="Account Created", value=member.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)
    embed.add_field(name=f"Roles [{len(roles)}]", value=" ".join(roles) or "None", inline=False)
    embed.add_field(name="Top Role", value=member.top_role.mention, inline=True)
    await ctx.send(embed=embed)

#######################################################################
    
@client.command(name='random')
async def choice(ctx, *, arg=None):
  if await commandlockcheck(ctx):
    return
  await log_command_usage(ctx)

  if not arg:
    await ctx.send("Please provide one or more entries separated by semi-colons.")
    return

  try:
    entries = [entry.strip() for entry in arg.split(';') if entry.strip()]

    if not entries:
      await ctx.send("Please provide one or more entries separated by semi-colons.")
    else:
      chosen_entry = random.choice(entries)
      await ctx.send(f"{chosen_entry}")
  except Exception as e:
    await ctx.send(f"An error occurred: {e}.")

#######################################################################

@client.command(name='calculate', aliases=['calc'])
async def calculate(ctx, *, expression=None):
  if await commandlockcheck(ctx):
    return
  await log_command_usage(ctx)

  if not expression:
    await ctx.send("Please enter a mathematical expression to calculate.")
    return

  try:
    def add_parenthesis(match):
      return f"math.{match.group(1)}(math.radians({match.group(2)}))"

    expression = re.sub(r'(sin|cos|tan)\((\d+)\)', add_parenthesis, expression)

    result = eval(expression)
    await ctx.send(f'{result}')
  except Exception as e:
    await ctx.send(f'Error: {str(e)}.')
    
#######################################################################
    
@client.command(name='setbirthday', aliases=["birthday", "bday", "setbday"])
async def setbirthday(ctx, *, birthday=None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if not birthday:
        await ctx.send("Invalid date format. Please use DD/MM/YYYY.")
        return

    try:
        datetime.datetime.strptime(birthday, "%d/%m/%Y")
    except ValueError:
        await ctx.send("Invalid date format. Please use DD/MM/YYYY.")
        return

    with open("birthdays.txt", "r") as f:
        birthdays = f.readlines()

    found = False
    updated_lines = []

    for entry in birthdays:
        user_id, _ = entry.strip().split(":")
        if int(user_id) == ctx.author.id:
            updated_lines.append(f"{ctx.author.id}:{birthday}\n")
            found = True
        else:
            updated_lines.append(entry)

    if not found:
        updated_lines.append(f"{ctx.author.id}:{birthday}\n")

    with open("birthdays.txt", "w") as f:
        f.writelines(updated_lines)

    await ctx.send(f"Your birthday has been set to {birthday}.")

#######################################################################

@client.command(name='greentext')
async def greentext(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)
    try:
        subreddit = await reddit.subreddit('greentext')
        hot_posts = []

        async for post in subreddit.hot(limit=100):
            hot_posts.append(post)

        image_posts = [post for post in hot_posts if post.url.endswith(('.jpg', '.png', '.gif'))]

        if not image_posts:
            await ctx.send("No image posts found in the top 100 hot posts of r/greentext.")
        else:
            random_post = random.choice(image_posts)
            
            await ctx.send(random_post.url)
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")

#######################################################################
        
def image_to_ascii(image, width=100):
    ascii_chars = '@%#*+=-:. '
    ascii_length = len(ascii_chars) - 1

    aspect_ratio = image.height / image.width
    new_height = int(aspect_ratio * width * 0.55)
    im = image.resize((width, new_height))

    im = im.convert('L')
    pixels = im.getdata()
    ascii_str = ''

    for pixel in pixels:
        index = (pixel // 25) % (ascii_length + 1)
        ascii_str += ascii_chars[index]

    ascii_str_len = len(ascii_str)
    ascii_img = []
    for i in range(0, ascii_str_len, width):
        ascii_img.append(ascii_str[i:i+width])

    return "\n".join(ascii_img)

@client.command(name='ascii')
async def ascii(ctx, url: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    image = None
    if ctx.message.attachments:
        try:
            data = await ctx.message.attachments[0].read()
            image = Image.open(BytesIO(data))
        except Exception:
            return await ctx.send("Failed to read your uploaded image.")
    elif url:
        try:
            resp = requests.get(url, timeout=10)
            resp.raise_for_status()
            image = Image.open(BytesIO(resp.content))
        except Exception:
            return await ctx.send("Failed to download image/invalid URL.")
    else:
        return await ctx.send("Please either upload an image or provide a valid image URL.")

    try:
        ascii_art = image_to_ascii(image)
        ascii_bytes = BytesIO(ascii_art.encode('utf-8'))
        ascii_file = discord.File(ascii_bytes, filename="ascii_art.txt")
        await ctx.send(file=ascii_file)
    except Exception as e:
        await ctx.send(f"An error occurred while converting to ASCII:\n```{e}```")

#######################################################################        
        
def youtube_search(query):
  try:
    youtube = build('youtube', 'v3', developerKey=youtube_api_key)
    request = youtube.search().list(q=query,
                                    part='snippet',
                                    maxResults=1,
                                    type='video')
    response = request.execute()

    if response['items']:
      video_id = response['items'][0]['id']['videoId']
      return f'https://www.youtube.com/watch?v={video_id}'
    else:
      return 'No video found.'
  except Exception as e:
    return f'An error occurred while searching: {e}.'

@client.command(name='youtube', aliases=['yt'])
async def youtube(ctx, *, query=None):
  if await commandlockcheck(ctx):
    return
  await log_command_usage(ctx)

  if not query:
    await ctx.send("Please enter a search query.")
    return

  link = youtube_search(query)
  await ctx.send(link)
    
#######################################################################

@client.command(name='translate')
async def translate(ctx, source_lang=None, target_lang=None, *, text=None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if not source_lang or not target_lang or not text:
        await ctx.send("Usage: '!translate <source_lang> <target_lang> <text>'.")
        return

    try:
        source_lang=source_lang.lower()
        target_lang=target_lang.lower()
        translation = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        await ctx.send(f'Translation: {translation}')
    except Exception as e:
        await ctx.send(f'An error occurred while translating: {e}.')

#######################################################################

@client.command(name='gpt', aliases=['chatgpt'])
async def gpt(ctx, *, prompt: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    images = extract_image_attachments(ctx.message)
    if not prompt and not images:
        return await ctx.send("Please provide a prompt or attach an image.")

    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    if images:
        content_items = []
        if prompt:
            content_items.append({"type": "text",      "text": prompt})
        for att in images:
            content_items.append({
                "type":      "image_url",
                "image_url": {"url": att.url}
            })
        messages.append({"role": "user", "content": content_items})
    else:
        messages.append({"role": "user", "content": prompt})

    try:
        resp = await openai_client.chat.completions.create(
            model=gpt_model,
            messages=messages
        )
        reply = resp.choices[0].message.content.strip()
        for i in range(0, len(reply), 2000):
            await ctx.send(reply[i:i+2000])

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        
#######################################################################

@client.command(name='games', aliases=['g'])
async def games(ctx):  
  if await commandlockcheck(ctx):
    return
  await log_command_usage(ctx)

  embed = discord.Embed(title='Games', description='Game command list', color=discord.Color.blue())
  embed.set_thumbnail(url=embed_img)
  embed.add_field(name='!games', value='Displays this menu', inline=False)
  embed.add_field(name="!connect4", value="Lets you play connect4 with the bot/another player", inline=False)
  embed.add_field(name='!hangman', value='Lets you play hangman with the bot/another player', inline=False)
  embed.add_field(name="!trivia", value="Lets you play trivia", inline=False)
  embed.add_field(name="!stopgame", value="Stops the current game", inline=False)
  await ctx.send(embed=embed)

#######################################################################

NUMBER_EMOJIS = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣"]

class Connect4Session:
    def __init__(self, player1, player2, playing_against_bot=False):
        self.player1 = player1
        self.player2 = player2
        self.current_player = player1
        self.board = [[':white_large_square:'] * 7 for _ in range(6)]
        self.cols = 7
        self.rows = 6
        self.game_over = False
        self.playing_against_bot = playing_against_bot
        self.ctx = None
        self.board_message = None
        self.loop_task: asyncio.Task = None

    def end_game(self):
        self.game_over = True
        if self.player1 in game_sessions:
            del game_sessions[self.player1]
        if self.player2 in game_sessions:
            del game_sessions[self.player2]

    def print_board(self):
        return '\n'.join(''.join(row) for row in self.board)

    def get_next_available_row(self, column):
        for r in range(self.rows - 1, -1, -1):
            if self.board[r][column] == ':white_large_square:':
                return r
        return None

    def make_move(self, column, player):
        row = self.get_next_available_row(column)
        if row is None:
            return False
        self.board[row][column] = (
            ':red_circle:' if player == self.player1 else ':yellow_circle:'
        )
        return True

    def check_winner(self):
        b = self.board
        for r in range(self.rows):
            for c in range(self.cols - 3):
                if b[r][c] != ':white_large_square:' and \
                   b[r][c] == b[r][c+1] == b[r][c+2] == b[r][c+3]:
                    return b[r][c]
        for c in range(self.cols):
            for r in range(self.rows - 3):
                if b[r][c] != ':white_large_square:' and \
                   b[r][c] == b[r+1][c] == b[r+2][c] == b[r+3][c]:
                    return b[r][c]
        for r in range(self.rows - 3):
            for c in range(self.cols - 3):
                if b[r][c] != ':white_large_square:' and \
                   b[r][c] == b[r+1][c+1] == b[r+2][c+2] == b[r+3][c+3]:
                    return b[r][c]
        for r in range(3, self.rows):
            for c in range(self.cols - 3):
                if b[r][c] != ':white_large_square:' and \
                   b[r][c] == b[r-1][c+1] == b[r-2][c+2] == b[r-3][c+3]:
                    return b[r][c]
        return None

    def is_board_full(self):
        return all(cell != ':white_large_square:' for row in self.board for cell in row)

    def can_win_next_move(self, column, symbol):
        row = self.get_next_available_row(column)
        if row is None:
            return False
        self.board[row][column] = symbol
        win = (self.check_winner() == symbol)
        self.board[row][column] = ':white_large_square:'
        return win

    def bot_make_move(self):
        for col in range(self.cols):
            if self.can_win_next_move(col, ':yellow_circle:'):
                self.make_move(col, self.player2)
                self.current_player = self.player1
                return
        for col in range(self.cols):
            if self.can_win_next_move(col, ':red_circle:'):
                self.make_move(col, self.player2)
                self.current_player = self.player1
                return
        choices = [c for c in range(self.cols) if self.get_next_available_row(c) is not None]
        if choices:
            self.make_move(random.choice(choices), self.player2)
        self.current_player = self.player1

@client.command(name='connect4', aliases=['c4'])
async def connect4(ctx, opponent: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    playing_against_bot = False
    if opponent is None or opponent.lower() == 'bot':
        playing_against_bot = True
        opponent_id = -1
        opponent_mention = "CPU"
    else:
        try:
            member = await commands.MemberConverter().convert(ctx, opponent)
            if member == ctx.author or member.bot:
                return await ctx.send("Invalid opponent.")
            opponent_id = member.id
            opponent_mention = member.mention
        except commands.MemberNotFound:
            return await ctx.send("Member not found. Mention someone or use 'bot'.")

    if ctx.author.id in game_sessions or (opponent_id in game_sessions and not playing_against_bot):
        return await ctx.send("A game is already in progress.")

    session = Connect4Session(ctx.author.id, opponent_id, playing_against_bot)
    session.ctx = ctx
    game_sessions[ctx.author.id] = session
    if not playing_against_bot:
        game_sessions[opponent_id] = session

    session.board_message = await ctx.send(
        f"{ctx.author.mention} vs {opponent_mention}\n"
        + session.print_board()
        + f"\nIt's {ctx.author.mention}'s turn."
    )
    for emoji in NUMBER_EMOJIS:
        await session.board_message.add_reaction(emoji)

    session.loop_task = client.loop.create_task(_connect4_reaction_loop(session))


async def _connect4_reaction_loop(session: Connect4Session):
    msg = session.board_message
    ctx = session.ctx

    def check(reaction, user):
        return (
            reaction.message.id == msg.id
            and str(reaction.emoji) in NUMBER_EMOJIS
            and user.id == session.current_player
        )

    while not session.game_over:
        try:
            reaction, user = await ctx.bot.wait_for(
                'reaction_add', check=check, timeout=150.0
            )
        except asyncio.CancelledError:
            return
        except asyncio.TimeoutError:
            await ctx.send("Game timed out due to inactivity.")
            session.end_game()
            return

        col = NUMBER_EMOJIS.index(str(reaction.emoji))
        await msg.remove_reaction(reaction.emoji, user)

        if not session.make_move(col, user.id):
            await ctx.send("That column is full—pick another.")
            continue

        winner = session.check_winner()
        if winner or session.is_board_full():
            session.game_over = True
            if winner:
                if winner == ':red_circle:':
                    victor = ctx.guild.get_member(session.player1).mention
                else:
                    victor = ("CPU" if session.playing_against_bot
                              else ctx.guild.get_member(session.player2).mention)
                ending = f"{victor} wins!"
            else:
                ending = "It's a draw!"
            await msg.edit(content=ending + "\n\n" + session.print_board())
            session.end_game()
            return

        if session.playing_against_bot:
            session.current_player = session.player2
            session.bot_make_move()

            bot_win = session.check_winner()
            if bot_win or session.is_board_full():
                session.game_over = True
                if bot_win == ':yellow_circle:':
                    ending = "CPU wins!"
                else:
                    ending = "It's a draw!"
                await msg.edit(content=ending + "\n\n" + session.print_board())
                session.end_game()
                return

            session.current_player = session.player1
        else:
            session.current_player = (
                session.player2 if user.id == session.player1 else session.player1
            )

        next_player = (
            "CPU" if session.playing_against_bot and session.current_player == session.player2
            else ctx.guild.get_member(session.current_player).mention
        )
        await msg.edit(
            content=f"It's {next_player}'s turn.\n\n" + session.print_board()
        )
                
#######################################################################            

try:
    with open('hangman_words.txt', 'r', encoding='utf-8') as f:
        wordbank = [line.strip() for line in f if line.strip()]
except FileNotFoundError:
    print("Error: 'hangman_words.txt' file not found.")
    wordbank = []

def get_unique_word():
    global used_words
    available_words = [w for w in wordbank if w not in used_words]
    if not available_words:
        used_words.clear()
        available_words = wordbank.copy()
    word = random.choice(available_words)
    used_words.append(word)
    return word    
    
class HangmanSession:

    def __init__(self, player1, player2, word):
        self.player1 = player1
        self.player2 = player2
        self.word = word
        self.guessed_letters = set()
        self.remaining_attempts = 7
        self.game_over = False
        self.game_message = None

    def masked_word(self):
        return ''.join([
            letter if letter in self.guessed_letters or letter == ' ' else '-'
            for letter in self.word
        ])

    def is_word_guessed(self):
        return all(letter in self.guessed_letters or letter == ' ' for letter in self.word)

@client.command(name='hangman')
async def hangman(ctx, opponent: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    playing_against_bot = opponent is None or opponent.lower() == 'bot'
    word = ""
    if playing_against_bot:
        word = get_unique_word()
        opponent_id = -1
    else:
        if not opponent:
            await ctx.send(
                "Please mention an opponent to play against or type 'bot' to play against the CPU."
            )
            return
        try:
            opponent_member = await commands.MemberConverter().convert(ctx, opponent)
            if opponent_member.bot or opponent_member == ctx.author:
                await ctx.send("Invalid opponent.")
                return
            opponent_id = opponent_member.id
        except commands.MemberNotFound:
            await ctx.send("Member not found. Please mention a valid opponent.")
            return

        await ctx.author.send("Please DM me the word you want to use for Hangman.")

        def check_dm(message):
            return message.author == ctx.author and isinstance(
                message.channel, discord.DMChannel)

        try:
            dm_message = await client.wait_for('message', timeout=60.0, check=check_dm)
            word = dm_message.content.strip().lower()
            if not all(char.isalpha() or char == ' ' for char in word) or not 3 <= len(word.replace(' ', '')) <= 15:
                await ctx.author.send(
                    "Invalid word. The word must only contain letters, and be 3-15 characters long. Please choose another word."
                )
                return await hangman(ctx, opponent)
        except asyncio.TimeoutError:
            await ctx.author.send(
                "You took too long to provide the word. The game has been cancelled.")
            return

    if ctx.author.id in game_sessions or (opponent_id in game_sessions and not playing_against_bot):
        await ctx.send("There is already a game in progress.")
        return

    session = HangmanSession(ctx.author.id, opponent_id, word)
    game_sessions[ctx.author.id] = session
    if not playing_against_bot:
        game_sessions[opponent_id] = session

    message_content = f"{ctx.author.mention} vs {'CPU' if playing_against_bot else opponent_member.mention}\n" \
                      "Guess the word by using '!guess (letter)' or '!guess (l, e, t, t, e, r, s)'.\n" \
                      f"Word: {session.masked_word()}\nAttempts remaining: {session.remaining_attempts}"
    session.game_message = await ctx.send(message_content)
    
@client.command(name='guess')
async def guess(ctx, *, letters=None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if not letters:
        await ctx.send("Please enter one or more single letters (separated by commas) to make a guess.")
        return

    if ctx.author.id not in game_sessions:
        await ctx.send("You are not currently in a game session.")
        return

    session = game_sessions[ctx.author.id]

    if session.game_over:
        await ctx.send("The game is already over.")
        return

    if ctx.author.id == session.player1 and session.player2 != -1:
        await ctx.send("You cannot guess since you chose the word.")
        return

    letters = [letter.strip().lower() for letter in letters.split(',') if letter.strip()]
    
    invalid_letters = [letter for letter in letters if len(letter) != 1 or not letter.isalpha()]
    if invalid_letters:
        await ctx.send(f"Invalid input: {', '.join(invalid_letters)}. Please enter only single letters.")
        return

    letters = list(dict.fromkeys(letters))

    incorrect_guesses = 0
    for letter in letters:
        if letter in session.guessed_letters:
            continue

        session.guessed_letters.add(letter)
        if letter not in session.word:
            incorrect_guesses += 1

    session.remaining_attempts -= incorrect_guesses

    if session.is_word_guessed() or session.remaining_attempts <= 0:
        session.game_over = True
        result_message = "\nThe game is over. "
        if session.is_word_guessed():
            result_message += f"The word was: {session.word}. {ctx.author.mention} wins!"
        else:
            result_message += f"No more attempts left. The word was: {session.word}. "
            result_message += "CPU wins!" if session.player2 == -1 else f"{ctx.guild.get_member(session.player1).mention} wins!"
        await session.game_message.edit(content=result_message)
        del game_sessions[session.player1]
        if session.player2 in game_sessions and session.player2 != -1:
            del game_sessions[session.player2]
    else:
        message = f"Word: {session.masked_word()}\nAttempts remaining: {session.remaining_attempts}\nGuessed letters: {', '.join(sorted(session.guessed_letters))}"
        await session.game_message.edit(content=message)
            
#######################################################################
  
def read_trivia_questions(file_path):
  with open(file_path, 'r') as file:
    lines = file.readlines()
  questions = {}
  for line in lines:
    question, *answers = line.strip().split(';')
    questions[question] = [answer.strip().lower() for answer in answers]
  return questions

trivia_questions_file = "trivia_questions.txt"
trivia_questions = read_trivia_questions(trivia_questions_file)

def get_random_question():
  global previously_asked
  available_questions = [
    q for q in trivia_questions.items() if q not in previously_asked
  ]
  if not available_questions:
    previously_asked = []
    available_questions = list(trivia_questions.items())
  question, answers = random.choice(available_questions)
  previously_asked.append((question, answers))
  return question, answers

class TriviaSession:
    def __init__(self, player):
        self.player = player
        self.game_over = False

@client.command(name='trivia')
async def trivia(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id in game_sessions:
        await ctx.send("You are already in a game session.")
        return

    question, answers = get_random_question()
    session = TriviaSession(ctx.author.id)
    game_sessions[ctx.author.id] = session

    await ctx.send(f"{question}")

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel and not msg.content.startswith('!')

    for i in range(3):
        if session.game_over:
            del game_sessions[ctx.author.id]
            return

        await ctx.send(
            f"You have {3-i} attempts left. Enter your answer within 15 seconds."
        )
        try:
            user_answer = await asyncio.wait_for(client.wait_for('message',
                                                                 check=check),
                                                 timeout=15.0)
            if session.game_over:
                del game_sessions[ctx.author.id]
                return

            user_answer = user_answer.content.strip().lower()

            if user_answer in answers:
                await ctx.send("Correct answer!")
                del game_sessions[ctx.author.id]
                return
            else:
                await ctx.send("That's incorrect. Try again.")

        except asyncio.TimeoutError:
            if session.game_over:
                del game_sessions[ctx.author.id]
                return

            await ctx.send("Time's up! The correct answer(s) is: " +
                           ", ".join(answers))
            del game_sessions[ctx.author.id]
            return

    if not session.game_over:
        correct_answers = ", ".join(answers)
        await ctx.send(
            f"Sorry, you've run out of attempts. The correct answer(s) is: {correct_answers}."
        )
    del game_sessions[ctx.author.id]

#######################################################################

@client.command(name='stopgame')
async def stopgame(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id not in admin_ids:
        if ctx.author.id not in game_sessions:
            await ctx.send("You are not currently in a game session.")
            return
        session = game_sessions[ctx.author.id]
    else:
        if not game_sessions:
            await ctx.send("There are no active game sessions to stop.")
            return
        session_key = next(iter(game_sessions))
        session = game_sessions[session_key]
    if isinstance(session, Connect4Session):
        await ctx.send("Connect4 game session has been cancelled.")
        del game_sessions[session.player1]
        if session.player2 in game_sessions:
            del game_sessions[session.player2]
    elif isinstance(session, HangmanSession):
        await ctx.send("Hangman game session has been cancelled.")
        del game_sessions[session.player1]
        if session.player2 in game_sessions:
            del game_sessions[session.player2]
    elif isinstance(session, TriviaSession):
        await ctx.send("Trivia game session has been cancelled.")
        session.game_over = True
        del game_sessions[session.player]
    
####################################################################### 

@client.command(name='voice', aliases=['v', 'vc'])
async def voice(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    embed = discord.Embed(title='Voice Call', description='Voice call command list', color=discord.Color.blue())
    embed.set_thumbnail(url=embed_img)
    embed.add_field(name="!vc", value="Displays this menu", inline=False)
    embed.add_field(name="!join", value="Makes the bot join your vc", inline=False)
    embed.add_field(name="!leave", value="Makes the bot leave your vc", inline=False)
    embed.add_field(name="!p", value="Plays a song", inline=False)
    embed.add_field(name="!np", value="Displays details about the currently playing song", inline=False)
    embed.add_field(name='!vol', value='Adjusts volume from 0-100', inline=False)
    embed.add_field(name="!lyrics", value="Shows lyrics of current song", inline=False)
    embed.add_field(name="!pause", value="Pauses the current song", inline=False)
    embed.add_field(name="!resume", value="Resumes any paused song", inline=False)
    embed.add_field(name="!replay", value="Replays the current song", inline=False)
    embed.add_field(name="!jump", value="Jumps to any audio timestamp", inline=False)
    embed.add_field(name="!queue", value="Displays the queue", inline=False)
    embed.add_field(name="!atq", value="Adds a song to the queue", inline=False)
    embed.add_field(name="!dfq", value="Deletes a song from the queue", inline=False)
    embed.add_field(name="!loop", value="Loops the queue", inline=False)
    embed.add_field(name="!shuffle", value="Shuffles the queue", inline=False)
    embed.add_field(name="!clear", value="Clears the queue", inline=False)
    embed.add_field(name="!skip", value="Skips to the next song in queue", inline=False)
    embed.add_field(name="!stopsong", value="Stops the current song", inline=False)
    await ctx.send(embed=embed)

#######################################################################

@client.command(name='joinvc', aliases=['join', 'jvc'], pass_context=True)
async def joinvc(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.voice:
        if ctx.voice_client:
            await ctx.voice_client.move_to(ctx.author.voice.channel)
        else:
            channel = ctx.author.voice.channel
            await channel.connect()
        await ctx.send("Joined the voice channel.")
    else:
        await ctx.send("Error: You are not in a voice channel.")

#######################################################################        
        
@client.command(name='leavevc', aliases=['leave', 'lvc'], pass_context=True)
async def leavevc(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    global looping, queue, current_song, disconnect_timer_task

    if ctx.voice_client:
        vc = ctx.voice_client
        if vc.is_playing():
            vc.stop()
        await vc.disconnect()
        await ctx.send("Left the voice channel.")
        looping = False
        queue = []
        current_song = None
        if disconnect_timer_task is not None and not disconnect_timer_task.done():
            disconnect_timer_task.cancel()
            disconnect_timer_task = None
        await asyncio.sleep(1)
    else:
        await ctx.send("Error: I am not currently in a voice channel.")
    
#######################################################################    
    
@client.command(name='playsong', aliases=['p', 'play'])
async def playsong(ctx, *, query=None, from_play_next=False, send_embed=True):
    global current_audio_source
    global default_volume
    global current_song
    global disconnect_timer_task
    global queue
    global looping
    global backup_queue
    global backup_looping

    if not from_play_next:
        if await commandlockcheck(ctx):
            return
        await log_command_usage(ctx)

        if len(queue) > 0:
            backup_queue = queue.copy()
            backup_looping = looping
            queue.clear()
        else:
            backup_queue = []
            backup_looping = False

    if not query:
        await ctx.send("Please provide a song name or query.")
        return

    if ctx.voice_client is None:
        if ctx.author.voice is None:
            await ctx.send("You are not connected to a voice channel.")
            return
        else:
            voice_client = await ctx.author.voice.channel.connect()
    else:
        voice_client = ctx.voice_client

    if voice_client.is_playing() and not from_play_next:
        voice_client.stop()

    ydl_opts = {
        'format': 'bestaudio/best',
        'default_search': 'scsearch',
        'noplaylist': 'True',
        'quiet': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_results = ydl.extract_info(f"scsearch1:{query}", download=False)
            if 'entries' in search_results:
                info = search_results['entries'][0]
            else:
                info = search_results

            title = info['title']
            url = info['url']

        ffmpeg_options = {
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
            'options': '-vn'
        }

        def after_play(error):
            asyncio.run_coroutine_threadsafe(handle_after_play(ctx, error), client.loop)

        raw_audio_source = FFmpegPCMAudio(url, **ffmpeg_options)
        current_audio_source = PCMVolumeTransformer(raw_audio_source)
        current_audio_source.volume = default_volume

        voice_client.play(
            current_audio_source,
            after=after_play
        )

        current_song = {
            'info': info,
            'query': query,
            'stream_url': url,
            'start_time': time.time(),
            'pause_start': None,
            'accumulated_paused': 0.0,
        }

        if disconnect_timer_task is not None and not disconnect_timer_task.done():
            disconnect_timer_task.cancel()
            disconnect_timer_task = None

        duration = info.get('duration')
        duration_str = str(datetime.timedelta(seconds=int(duration))) if duration else 'Unknown'
        uploader = info.get('uploader', 'Unknown')
        webpage_url = info.get('webpage_url')
        thumbnail = info.get('thumbnail')

        if send_embed:
            embed = discord.Embed(
                title="Now Playing",
                description=f"[{title}]({webpage_url})",
                color=discord.Color.blue()
            )
            embed.add_field(name="Author", value=uploader, inline=True)
            embed.add_field(name="Duration", value=duration_str, inline=True)
            if thumbnail:
                embed.set_thumbnail(url=thumbnail)
            await ctx.send(embed=embed)

        if duration and int(duration) == 30 and send_embed:
            await ctx.send("This audio is capped at 30 seconds, the full version is only available for SoundCloud premium users.")

        if not from_play_next and backup_queue:
            queue = backup_queue.copy()
            looping = backup_looping

        return True

    except Exception as e:
        if ctx.voice_client and ctx.voice_client.is_connected():
            await ctx.send(f"Could not find the audio for '{query}'.")
            if from_play_next and len(queue) > 0:
                await ctx.send(f"Could not find the audio for '{query}'. Skipping to next song in the queue..")
                await play_next(ctx)
        return False

async def handle_after_play(ctx, error):
    global current_song, disconnect_timer_task, suppress_auto_next

    if suppress_auto_next:
        suppress_auto_next = False
        return

    if not ctx.voice_client or not ctx.voice_client.is_playing():
        current_song = None
        if disconnect_timer_task is None or disconnect_timer_task.done():
            disconnect_timer_task = asyncio.create_task(disconnect_after_timeout(ctx))

    if error:
        await ctx.send(f"An error occurred during playback: {str(error)}.")
    else:
        await play_next(ctx)

async def disconnect_after_timeout(ctx):
    await asyncio.sleep(1200)
    voice_client = ctx.voice_client
    if voice_client and not voice_client.is_playing():
        await voice_client.disconnect()
        await ctx.send("No audio has been played for 20 minutes. Disconnecting from the voice channel.")

async def play_next(ctx):
    global queue
    global looping

    if len(queue) == 0:
        return

    song = queue.pop(0)
    try:
        success = await playsong(ctx, query=song, from_play_next=True)
        if success and looping:
            queue.append(song)
    except Exception as e:
        await ctx.send(f"An error occurred while playing the next song: {e}")
        
#######################################################################        
               
@client.command(name='currentsong', aliases=['np', 'nowplaying'])
async def currentsong(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        return await ctx.send("There is no song currently playing.")

    global current_song
    if current_song is None:
        return await ctx.send("No song information is available.")

    info = current_song['info']
    start_time = current_song['start_time']
    acc = current_song.get('accumulated_paused', 0.0)
    ps = current_song.get('pause_start')
    now = time.time()

    if ps:
        elapsed = ps - start_time - acc
    else:
        elapsed = now - start_time - acc

    elapsed_str = str(datetime.timedelta(seconds=int(elapsed)))
    duration = info.get('duration')
    duration_str = str(datetime.timedelta(seconds=int(duration))) if duration else 'Unknown'
    uploader = info.get('uploader', 'Unknown')
    title = info.get('title', 'Unknown')
    thumbnail = info.get('thumbnail')
    webpage_url = info.get('webpage_url')

    embed = discord.Embed(
        title="Now Playing",
        description=f"[{title}]({webpage_url})",
        color=discord.Color.blue()
    )
    embed.add_field(name="Author", value=uploader, inline=True)
    embed.add_field(name="Duration", value=duration_str, inline=True)
    embed.add_field(name="Elapsed Time", value=elapsed_str, inline=True)
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)

    await ctx.send(embed=embed)

#######################################################################

@client.command(name='volume', aliases=['vol'])
async def set_volume(ctx, volume: int = None):
    global current_audio_source
    global default_volume

    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        await ctx.send("I am not currently playing any audio in a voice channel.")
        return

    if volume is None:
        await ctx.send("Please specify a volume between 0 and 100%.")
        return

    if volume < 0 or volume > 100:
        await ctx.send("Volume level must be between 0 and 100%.")
        return

    try:
        default_volume = volume / 100
        if current_audio_source:
            current_audio_source.volume = default_volume
            await ctx.send(f"Volume set to {volume}%.")
        else:
            await ctx.send(f"Volume set to {volume}%.")
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

#######################################################################        
        
@client.command(name='lyrics')
async def lyrics(ctx, *, query: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if query:
        if ';' not in query:
            await ctx.send("Please provide both song name and artist, separated by a semicolon. e.g. `!lyrics Nokia; Drake`")
            return

        title_part, artist_part = map(str.strip, query.split(';', 1))
        if not title_part or not artist_part:
            await ctx.send("Both song name **and** artist must be provided. e.g. `!lyrics Nokia; Drake`")
            return

        title = title_part
        artist = artist_part

    else:
        if ctx.voice_client is None or not ctx.voice_client.is_playing():
            await ctx.send("There is no song currently playing.")
            return

        global current_song
        if current_song is None:
            await ctx.send("No song information is available.")
            return

        title = current_song['info'].get('title', 'Unknown')
        artist = current_song['info'].get('uploader', 'Unknown')

    artist_formatted = artist.replace(' ', '%20')
    title_formatted = title.replace(' ', '%20')
    lyrics_api_url = f"https://api.lyrics.ovh/v1/{artist_formatted}/{title_formatted}"

    try:
        response = requests.get(lyrics_api_url)

        if response.status_code == 200:
            data = response.json()
            lyrics = data.get('lyrics', 'Lyrics not found.')

            lyrics_chunks = [lyrics[i:i + 4096] for i in range(0, len(lyrics), 4096)]

            for index, chunk in enumerate(lyrics_chunks):
                embed = discord.Embed(
                    title=f"Lyrics for {title}",
                    description=chunk,
                    color=discord.Color.blue()
                )
                if index == 0:
                    embed.set_footer(text=f"Artist: {artist}")
                await ctx.send(embed=embed)
        else:
            await ctx.send(f"Could not fetch lyrics for **{title}** by **{artist}**.")
    except Exception as e:
        await ctx.send(f"An error occurred while fetching lyrics: {e}")

#######################################################################

@client.command(name='pausesong', aliases=['ps', 'pause'])
async def pausesong(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    vc = ctx.voice_client
    if vc is None or not vc.is_playing():
        return await ctx.send("I am not currently playing audio.")

    vc.pause()

    global current_song
    if current_song and current_song.get('pause_start') is None:
        current_song['pause_start'] = time.time()

    await ctx.send("Audio paused.")

#######################################################################

@client.command(name='resumesong', aliases=['rs', 'resume'])
async def resumesong(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    vc = ctx.voice_client
    if vc is None:
        return await ctx.send("I am not connected to a voice channel.")
    if not vc.is_paused():
        return await ctx.send("The audio is not paused.")

    vc.resume()

    global current_song
    ps = current_song.get('pause_start') if current_song else None
    if current_song and ps is not None:
        current_song['accumulated_paused'] += time.time() - ps
        current_song['pause_start'] = None

    await ctx.send("Audio resumed.")   

#######################################################################

@client.command(name="replaysong", aliases=["replay"])
async def replaysong(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    vc = ctx.voice_client
    if vc is None or not vc.is_playing():
        return await ctx.send("Nothing is playing.")

    global current_song, suppress_auto_next
    song = current_song
    if song is None:
        return await ctx.send("Song data unavailable.")

    suppress_auto_next = True
    vc.stop()
    await asyncio.sleep(0)

    success = await playsong(ctx, query=song["query"], from_play_next=False, send_embed=False)
    if success:
        await ctx.send("Restarted the track from the beginning.")

#######################################################################

@client.command(name="jumpsong", aliases=["jump", "ff", "forward", "seek"])
async def seek(ctx, position: str = None):
    """
    Jump forward / back or to an absolute time-mark in the current track.

    Examples
    --------
    !jump +30   → ahead   30 s  (relative)
    !jump -10   → back    10 s  (relative)
    !jump 0     → restart        (absolute)
    !jump 125   → 2 min 5 s mark (absolute)
    """

    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    vc = ctx.voice_client
    if vc is None or not vc.is_playing():
        return await ctx.send("Nothing is playing to seek within.")

    if position is None:
        return await ctx.send(
            "Usage: !jump <±seconds> for relative jumps or !jump <second-mark> for absolute."
        )

    is_relative = position.startswith(("+", "-"))
    try:
        offset = int(position)
    except ValueError:
        return await ctx.send(
            "Time must be an integer — examples: !jump +30, !jump -10, !jump 90, !jump 0"
        )

    global current_song, default_volume, suppress_auto_next
    song = current_song
    if song is None:
        return await ctx.send("Song data unavailable.")

    duration = song["info"].get("duration")
    if duration is None:
        return await ctx.send("Cannot seek this stream (unknown duration).")

    now          = time.time()
    start        = song["start_time"]
    paused_total = song.get("accumulated_paused", 0.0)
    pause_start  = song.get("pause_start")

    elapsed = (
        pause_start - start - paused_total
        if pause_start is not None
        else now - start - paused_total
    )

    if is_relative:
        new_pos = max(0, min(elapsed + offset, duration))
    else:
        new_pos = max(0, min(offset, duration))

    if not is_relative and offset == 0:
        pass
    elif int(new_pos) == int(elapsed):
        return await ctx.send("Already at the requested position.")

    suppress_auto_next = True
    vc.stop()
    await asyncio.sleep(0)

    ffmpeg_opts = {
        "before_options": f"-ss {int(new_pos)} -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn"
    }
    src = PCMVolumeTransformer(
        FFmpegPCMAudio(song["stream_url"], **ffmpeg_opts)
    )
    src.volume = default_volume
    vc.play(
        src,
        after=lambda e: asyncio.run_coroutine_threadsafe(
            handle_after_play(ctx, e), client.loop
        )
    )

    song["start_time"]        = time.time() - new_pos
    song["pause_start"]       = None
    song["accumulated_paused"] = 0.0

    timestamp = str(datetime.timedelta(seconds=int(new_pos)))
    await ctx.send(f"Jumped to **{timestamp}**.")

#######################################################################

@client.command(name='queue', aliases=['q'])
async def show_queue(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if len(queue) > 0:
        queue_list = '\n'.join([f'{index + 1}. {song}' for index, song in enumerate(queue)])
        await ctx.send(f"Song Queue:\n{queue_list}\nQueue loop: {'Enabled' if looping else 'Disabled'}")
    else:
        await ctx.send("The song queue is empty.")

#######################################################################        
        
@client.command(name='addtoqueue', aliases=['atq'])
async def addtoqueue(ctx, *, arg_str: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    global queue

    if not arg_str:
        await ctx.send("Please enter the name of a song to add to the queue.")
        return

    parts = arg_str.rsplit(';', 1)
    song_name = parts[0].strip()
    position = None

    if len(parts) > 1 and parts[1].strip().isdigit():
        position = int(parts[1].strip()) - 1

    if not song_name:
        await ctx.send("Please enter the name of a song to add to the queue.")
        return

    if position is not None and 0 <= position < len(queue):
        queue.insert(position, song_name)
        await ctx.send(f"Added '{song_name}' to position {position + 1} in the song queue.")
    else:
        queue.append(song_name)
        await ctx.send(f"Added '{song_name}' to the song queue.")

#######################################################################        
        
@client.command(name='delfromqueue', aliases=['dfq'])
async def deletefromqueue(ctx, *, song_name: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    global queue

    if not song_name:
        await ctx.send("Please enter the name of the song you want to remove from the queue.")
        return

    song_to_remove = None
    for song in queue:
        if song_name.lower() in song.lower():
            song_to_remove = song
            break

    if song_to_remove:
        queue.remove(song_to_remove)
        await ctx.send(f"Removed '{song_to_remove}' from the song queue.")
    else:
        if len(queue) > 0:
            queue_list = '\n'.join([f'{index + 1}. {song}' for index, song in enumerate(queue)])
            await ctx.send(f"Error: '{song_name}' not found in the queue.\n\nCurrent Queue:\n{queue_list}\nQueue loop: {'Enabled' if looping else 'Disabled'}")
        else:
            await ctx.send("The song queue is empty.")

#######################################################################            
            
@client.command(name='loopqueue', aliases=['lq', 'loop'])
async def toggle_queue_looping(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    global looping

    looping = not looping

    await ctx.send(f"Looping the queue is {'enabled' if looping else 'disabled'}.")

#######################################################################    
    
@client.command(name='shufflequeue', aliases=['sq', 'shuffle'])
async def shuffle_queue(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    global queue

    if len(queue) > 0:
        random.shuffle(queue)
        await ctx.send("Queue shuffled.")
    else:
        await ctx.send("The song queue is empty.")    

#######################################################################        
        
@client.command(name='clearqueue', aliases=['cq', 'clear'])
async def clear_queue(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    global queue

    if len(queue) > 0:
        queue = []
        await ctx.send("Queue cleared.")
    else:
        await ctx.send("The song queue is already empty.")

#######################################################################        
        
@client.command(name='skipsong', aliases=['ss', 'skip'])
async def skip(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        await ctx.send("There is no song currently playing.")
        return

    ctx.voice_client.stop()
    await ctx.send("Skipped to the next song.")

#######################################################################           
        
@client.command(name='stopsong', aliases=["sts"])
async def stopsong(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.voice_client is None:
        await ctx.send("I am not connected to a voice channel.")
        return
    
    global queue
    global looping
    global current_song
    
    queue = []
    looping = False
    current_song = None

    ctx.voice_client.stop()
    await ctx.send("Audio stopped.")
                    
#######################################################################

@client.command(name='admin')
async def admin_commands(ctx):
  if await commandlockcheck(ctx):
    return
  await log_command_usage(ctx)

  if ctx.author.id not in admin_ids:
    await ctx.send("You don't have permission to use this command.")
    return

  embed = discord.Embed(title='Admin', description='Admin command list', color=discord.Color.blue())
  embed.set_thumbnail(url=embed_img)
  embed.add_field(name="!admin", value="Displays this menu", inline=False)
  embed.add_field(name="!serverinfo", value="Displays server information", inline=False)
  embed.add_field(name="!say", value="Makes the bot repeat text", inline=False)
  embed.add_field(name="!embed", value="Creates a custom embed", inline=False)
  embed.add_field(name="!addquestion", value="Lets you add a question to trivia", inline=False)
  embed.add_field(name="!admingpt", value="Uses GPT for responses, accurate up to June 2024", inline=False)
  embed.add_field(name="!grok", value="Uses Grok for responses, accurate up to December 2024", inline=False)
  embed.add_field(name="!grokimg", value="Uses Grok to generate images", inline=False)
  await ctx.send(embed=embed)
    
#######################################################################

@client.command(name='serverinfo', aliases=['si'])
async def serverinfo(ctx):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    guild = ctx.guild
    roles = guild.roles[1:]
    text_channels = len(guild.text_channels)
    voice_channels = len(guild.voice_channels)
    emojis = len(guild.emojis)

    embed = discord.Embed(
        title=f"Server Info • {guild.name}",
        color=discord.Color.blue()
    )
    if guild.icon:
        embed.set_thumbnail(url=guild.icon.url)
    embed.add_field(name="Server Name", value=guild.name, inline=True)
    embed.add_field(name="Server ID", value=guild.id, inline=True)
    embed.add_field(name="Owner", value=guild.owner.mention, inline=True)
    embed.add_field(name="Members", value=guild.member_count, inline=True)
    embed.add_field(name=f"Roles [{len(roles)}]", value=len(roles), inline=True)
    embed.add_field(name=f"Text Channels", value=text_channels, inline=True)
    embed.add_field(name=f"Voice Channels", value=voice_channels, inline=True)
    embed.add_field(name=f"Emojis", value=emojis, inline=True)
    embed.add_field(name="Created On", value=guild.created_at.strftime("%Y-%m-%d %H:%M:%S"), inline=False)

    await ctx.send(embed=embed)

#######################################################################

@client.command(name='say', aliases=['repeat'])
async def say_message(ctx, *, message: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id not in admin_ids:
        return await ctx.send("You don't have permission to use this command.")

    image_attachments = [
        att for att in ctx.message.attachments
        if att.content_type and att.content_type.startswith("image")
    ]

    if not message and not image_attachments:
        return await ctx.send("Please enter a message or attach an image.")

    files = [await att.to_file() for att in image_attachments]

    target_channel = ctx.channel
    content = message.strip() if message else None

    if message and ";" in message:
        try:
            msg_text, channel_id_str = message.rsplit(";", 1)
            channel_id = int(channel_id_str.strip())
            chan = client.get_channel(channel_id)
            if chan is None:
                return await ctx.send("Invalid channel ID provided.")
            target_channel = chan
            content = msg_text.strip() or None
        except ValueError:
            return await ctx.send("Invalid channel ID provided.")

    await target_channel.send(content=content, files=files)

    if target_channel != ctx.channel:
        await ctx.send(f"Message sent to {target_channel.mention}.")
        
######################################################################

@client.command(name='embed')
async def embed(ctx, *, args):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id not in admin_ids:
        await ctx.send("You don't have permission to use this command.")
        return
    
    fields = [field.strip() for field in args.split(';') if field.strip()]
    
    if not fields or len(fields) % 2 != 0:
        await ctx.send("Please provide field names and values in pairs, e.g., !testembed name1; value1; name2; value2")
        return
    
    if len(fields) // 2 > 25:
        await ctx.send("Cannot create embed: Too many fields (max 25).")
        return

    embed = discord.Embed(title='Embed', description='Custom embed', color=discord.Color.blue())
    embed.set_thumbnail(url=embed_img)

    for i in range(0, len(fields), 2):
        embed.add_field(name=fields[i], value=fields[i + 1], inline=False)

    await ctx.send(embed=embed)

#######################################################################
    
@client.command(name='addquestion')
async def add_question(ctx, *, input_data=None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id not in admin_ids:
        await ctx.send("You don't have permission to use this command.")
        return

    if not input_data:
        await ctx.send("Please provide the question and at least one answer.\nUsage: `!addquestion <question>; <answer1>; <answer2>...`")
        return

    parts = [part.strip() for part in input_data.split(";")]
    
    if len(parts) < 2:
        await ctx.send("You must provide at least one question and one answer.")
        return

    user_question = parts[0]
    answers_list = [answer for answer in parts[1:] if answer]

    if not answers_list:
        await ctx.send("You must provide at least one answer for the question.")
        return

    try:
        with open('trivia_questions.txt', 'a') as file:
            file.write(f"\n{user_question}; {'; '.join(answers_list)}")
        await ctx.send(f"Question and answers successfully added to trivia! Question: '{user_question}' | Answers: {', '.join(answers_list)}")
    except Exception as e:
        await ctx.send(f"An error occurred while saving the question: {str(e)}.")

#######################################################################

@client.command(name='admingpt', aliases=['gpt+', 'gptplus'])
async def admingpt(ctx, *, prompt: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id not in admin_ids:
        return await ctx.send("You don't have permission to use this command.")

    images = extract_image_attachments(ctx.message)
    if not prompt and not images:
        return await ctx.send("Please provide a prompt or attach an image.")

    messages = [{"role": "system", "content": "You are a helpful assistant."}]
    if images:
        content_items = []
        if prompt:
            content_items.append({"type": "text",      "text": prompt})
        for att in images:
            content_items.append({
                "type":      "image_url",
                "image_url": {"url": att.url}
            })
        messages.append({"role": "user", "content": content_items})
    else:
        messages.append({"role": "user", "content": prompt})

    try:
        resp = await openai_client.chat.completions.create(
            model=gpt_plus_model,
            messages=messages
        )
        reply = resp.choices[0].message.content.strip()
        for i in range(0, len(reply), 2000):
            await ctx.send(reply[i:i+2000])

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
                                
#######################################################################

@client.command(name='grok')
async def grok(ctx, *, prompt: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id not in admin_ids:
        await ctx.send("You don't have permission to use this command.")
        return
    
    if not prompt:
        await ctx.send("Please provide a prompt for Grok.")
        return

    try:
        resp = await xai_client.chat.completions.create(
            model=grok_model,
            messages=[
                {"role": "system", "content": "You are Grok, an xAI assistant."},
                {"role": "user",   "content": prompt}
            ]
        )
        reply = resp.choices[0].message.content.strip()
        for i in range(0, len(reply), 2000):
            await ctx.send(reply[i:i+2000])

    except Exception as e:
        await ctx.send(f"An error occurred generating the Grok response:\n```py\n{e}```")

#######################################################################

@client.command(name='grokimg', aliases=['grokimage'])
async def grokimg(ctx, *, prompt: str = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id not in admin_ids:
        await ctx.send("You don't have permission to use this command.")
        return

    if not prompt:
        await ctx.send("Please provide a prompt for the image generation.")
        return

    try:
        resp = await xai_client.images.generate(
            model=grok_img_model,
            prompt=prompt,
            n=1,
            user=str(ctx.author.id)
        )
        url = resp.data[0].url

        embed = discord.Embed(
            title="Your Grok AI Image",
            description=f"Prompt: *{prompt}*",
            color=discord.Color.blue()
        )
        embed.set_image(url=url)
        embed.set_footer(text=f"Requested by {ctx.author.display_name}")

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"Sorry, something went wrong generating the Grok image:\n```py\n{e}```")
        
#######################################################################
 
@client.command(name='owner')
async def owner_commands(ctx):
  if await commandlockcheck(ctx):
    return
  await log_command_usage(ctx)

  if ctx.author.id not in owner_id:
    await ctx.send("You don't have permission to use this command.")
    return

  embed = discord.Embed(title='Owner', description='Owner command list', color=discord.Color.blue())
  embed.set_thumbnail(url=embed_img)
  embed.add_field(name="!owner", value="Displays this menu", inline=False)
  embed.add_field(name="!commandlock", value="Locks/unlocks all commands", inline=False)
  embed.add_field(name="!purge", value="Purges chat messages", inline=False)
  embed.add_field(name="!restart", value="Forces the bot to restart", inline=False)
  embed.add_field(name="/ping", value="Checks bot latency", inline=False)
  await ctx.send(embed=embed)

#######################################################################

@client.command(name='commandlock')
async def lock_commands(ctx):
  await log_command_usage(ctx)
  global commandlock
  if ctx.author.id in owner_id:
    commandlock = not commandlock
    if commandlock == True:
      await ctx.send("All commands locked.")
    else:
      await ctx.send("All commands unlocked.")

  else:
    await ctx.send("You don't have permission to use this command.")
    return

#######################################################################

@client.command(name='purge')
async def purge(ctx, number: int = None):
    if await commandlockcheck(ctx):
        return
    await log_command_usage(ctx)

    if ctx.author.id not in owner_id:
        await ctx.send("You don't have permission to use this command.")
        return

    if number is None:
        await ctx.send("Please specify the number of messages to delete. Usage: `!purge <number>`")
        return
    if not (1 <= number <= 100):
        await ctx.send("Please enter a number between 1 and 100.")
        return

    try:
        deleted = await ctx.channel.purge(limit=number, before=ctx.message)
        await ctx.send(f"Purged {len(deleted)} message{'s' if len(deleted) != 1 else ''}.")
    except discord.Forbidden:
        await ctx.send("I don't have permission to delete messages.")
    except discord.HTTPException as e:
        await ctx.send(f"Failed to delete messages: {e}")
    
#######################################################################

@client.command(name='restart')
async def restart(ctx):
    if await commandlockcheck(ctx):
        return
    
    if ctx.author.id not in owner_id:
        await ctx.send("You don't have permission to use this command.")
        return

    if ctx.author.id in restart_confirmation_pending:
        restart_confirmation_pending.remove(ctx.author.id)
        
        await log_command_usage(ctx)

        try:
            await ctx.send("Restarting the bot...")

            if ctx.voice_client:
                if ctx.voice_client.is_playing():
                    ctx.voice_client.stop()
                await ctx.voice_client.disconnect()

            await asyncio.sleep(3)
            
            os.execv(sys.executable, ['python'] + sys.argv)

        except Exception as e:
            await ctx.send(f"An error occurred during restart: {e}")
        
        return

    else:
        restart_confirmation_pending.add(ctx.author.id)
        await ctx.send("Are you sure you want to restart the bot? To confirm, please run the command again within 15 seconds.")

        await asyncio.sleep(15)

        if ctx.author.id in restart_confirmation_pending:
            restart_confirmation_pending.discard(ctx.author.id)
            await ctx.send("Restart confirmation timed out.")
        
#######################################################################

@client.tree.command(name='ping', description='pings the bot')
async def ping(interaction: discord.Interaction):
  latency = round(client.latency * 1000)
  if interaction.user.id in owner_id:
        await interaction.response.send_message(f'Latency: {latency}ms.')
  else:
        await interaction.response.send_message('Pong!')
          
#######################################################################

@client.event
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    msg = message.content.lower()
    responded = False

    if any(word in msg for word in monobot) and not msg.startswith("!"):
        await message.channel.send('Hey')
        responded = True

    if not responded:
        await client.process_commands(message)
             
client.run(token)
    
# Additional python packages: discord requests pytz openai sympy yt_dlp deep_translator pydub pynacl youtube_dl bs4 googlesearch-python asyncpraw pillow selenium webdriver_manager qrcode numpy python-dotenv

#######################################################################
