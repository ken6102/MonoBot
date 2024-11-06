#######################################################################

import discord
import os
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
from googleapiclient.discovery import build
from discord import app_commands, FFmpegPCMAudio, FFmpegOpusAudio
from discord.ext import commands, tasks
from deep_translator import GoogleTranslator
from datetime import timezone
from pydub import AudioSegment
from io import BytesIO

#######################################################################

intents = discord.Intents().all()
client = commands.Bot(command_prefix='!', intents=intents)
client.remove_command('help')

respond = ["respondpls"]

openai.api_key = 'hidden'
youtube_api_key = 'hidden'
token = 'hidden'
gpt3_model = "gpt-3.5-turbo"
gpt4_model = "gpt-4-turbo-preview"
game_sessions = {}
queue = []
looping = False
current_song = None
disconnect_timer_task = None
previously_asked = []
commandlock = False
op_ids = 'hidden'

#######################################################################

@client.event
async def on_ready():
  print('Bot logged in as {0.user}'.format(client))
  await client.change_presence(activity=discord.Activity(
    type=discord.ActivityType.playing, name="Discord Adventure 2"))
  try:
    synced = await client.tree.sync()
    print(f"Synced {len(synced)} command(s)")
  except Exception as e:
    print(e)
  client.loop.create_task(check_birthday())

#######################################################################

@client.event
async def on_command_error(ctx, error):
  if isinstance(error, discord.ext.commands.errors.CommandNotFound):
    await ctx.send("Unknown command, use !help to see available commands")
    
#######################################################################

async def commandlockcheck(ctx):
  global commandlock
  if commandlock == True and ctx.author.id not in op_ids:
    await ctx.send("Commands are currently locked.")
    return True
  return False

#######################################################################

@client.command(name='help')
async def help(ctx):
  if await commandlockcheck(ctx):
    return

  embed = discord.Embed(title='Help', description='MonoBot command list', color=discord.Color.blue())
  embed.add_field(name="!help", value="Displays this menu", inline=False)
  embed.add_field(name="!changelog", value="Posts the latest update changelog", inline=False)
  embed.add_field(name="!random (entry 1), (entry 2), ...", value="Randomly selects something from given entries", inline=False)
  embed.add_field(name="!calculate (entry 1) (+-*/) (entry 2) ...", value="Computes the result of an arithmetic problem", inline=False)
  embed.add_field(name="!youtube (query)", value="Posts a youtube video link based off the entered query", inline=False)
  embed.add_field(name="!translate (lang from) (lang to) (query)", value="Translates from one language to another", inline=False)
  embed.add_field(name="!gpt (query)", value="Gives an AI response to a prompt", inline=False)
  embed.add_field(name="!connect4 (@username/bot)", value="Lets you play connect4 with the bot or another player", inline=False)
  embed.add_field(name="!trivia", value="Lets you play trivia against the bot", inline=False)
  embed.add_field(name="!stopgame", value="Stops the current game in progress (excluding trivia)", inline=False)
  embed.add_field(name="!vc", value="Displays a list of voice call commands", inline=False)
  embed.add_field(name="/ping", value="Slash command to ping the bot", inline=False)
  await ctx.send(embed=embed)

#######################################################################

@client.command(name='changelog')
async def changelog(ctx):
    if await commandlockcheck(ctx):
        return

    changelog_path = 'changelog.txt'

    if not os.path.exists(changelog_path):
        await ctx.send("The changelog file does not exist.")
        return

    try:
        with open(changelog_path, 'r', encoding='utf-8') as file:
            content = file.read()

        MAX_MESSAGE_LENGTH = 2000

        if len(content) <= MAX_MESSAGE_LENGTH:
            await ctx.send(f"**__Changelog:__**\n\n{content}")
        else:
            await ctx.send("The changelog is too long to display in one message.")
    except Exception as e:
        await ctx.send(f"An error occurred while reading the changelog: {str(e)}")
        
#######################################################################

@client.command(name='random')
async def choice(ctx, *, arg=None):
  if await commandlockcheck(ctx):
    return

  if not arg:
    await ctx.send("Please provide one or more entries separated by commas.")
    return

  try:
    entries = [entry.strip() for entry in arg.split(',') if entry.strip()]

    if not entries:
      await ctx.send("Please provide one or more entries separated by commas.")
    else:
      chosen_entry = random.choice(entries)
      await ctx.send(f"{chosen_entry}")
  except Exception as e:
    await ctx.send(f"An error occurred: {e}")

#######################################################################

@client.command(name='calculate')
async def calculate(ctx, *, expression=None):
  if await commandlockcheck(ctx):
    return

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
    await ctx.send(f'Error: {str(e)}')
    
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
    return f'An error occurred while searching: {e}'


@client.command(name='youtube')
async def youtube(ctx, *, query=None):
  if await commandlockcheck(ctx):
    return

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

    if not source_lang or not target_lang or not text:
        await ctx.send("Usage: '!translate <source_lang> <target_lang> <text>'")
        return

    try:
        translation = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        await ctx.send(f'{translation}')
    except Exception as e:
        await ctx.send(f'An error occurred while translating: {e}')

#######################################################################

@client.command(name='gpt')
async def gpt(ctx, *, prompt=None):
    if await commandlockcheck(ctx):
        return

    if not prompt:
        await ctx.send("Please enter a prompt.")
        return

    try:
        response = openai.ChatCompletion.create(
            model=gpt3_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        reply = response.choices[0].message['content'].strip()
        if len(reply) > 2000:
            reply = reply[:1900]
            reply += "...\n\n*Note: Reply was cut off due to exceeding the Discord character limit of 2000.*"

        await ctx.send(reply)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        
#######################################################################

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
    self.timeout_task = None
    self.ctx = None

  def end_game(self):
    self.game_over = True
    del game_sessions[self.player1]
    if self.player2 in game_sessions:
      del game_sessions[self.player2]

  def print_board(self):
    board_str = ''
    for row in self.board:
      board_str += ''.join(row) + '\n'
    return board_str

  def make_move(self, column, player):
    row = self.get_next_available_row(column)
    if row is None:
      return False
    self.board[row][
      column] = ':red_circle:' if player == self.player1 else ':yellow_circle:'
    return True

  def get_next_available_row(self, column):
    for row in range(5, -1, -1):
      if self.board[row][column] == ':white_large_square:':
        return row
    return None

  def check_winner(self):
    for row in range(self.rows):
      for col in range(self.cols - 3):
        if (self.board[row][col] != ':white_large_square:'
            and self.board[row][col] == self.board[row][col + 1] ==
            self.board[row][col + 2] == self.board[row][col + 3]):
          return self.board[row][col]

    for col in range(self.cols):
      for row in range(self.rows - 3):
        if (self.board[row][col] != ':white_large_square:'
            and self.board[row][col] == self.board[row + 1][col] ==
            self.board[row + 2][col] == self.board[row + 3][col]):
          return self.board[row][col]

    for row in range(self.rows - 3):
      for col in range(self.cols - 3):
        if (self.board[row][col] != ':white_large_square:'
            and self.board[row][col] == self.board[row + 1][col + 1] ==
            self.board[row + 2][col + 2] == self.board[row + 3][col + 3]):
          return self.board[row][col]

    for row in range(3, self.rows):
      for col in range(self.cols - 3):
        if (self.board[row][col] != ':white_large_square:'
            and self.board[row][col] == self.board[row - 1][col + 1] ==
            self.board[row - 2][col + 2] == self.board[row - 3][col + 3]):
          return self.board[row][col]

    return None

  def is_board_full(self):
    return all(self.board[row][col] != ':white_large_square:'
               for row in range(self.rows) for col in range(self.cols))

  def bot_make_move(self):
    for col in range(self.cols):
      if self.can_win_next_move(col, ':yellow_circle:'):
        self.make_move(col, self.player2)
        return

    for col in range(self.cols):
      if self.can_win_next_move(col, ':red_circle:'):
        self.make_move(col, self.player2)
        return

    available_columns = [
      c for c in range(self.cols) if self.get_next_available_row(c) is not None
    ]
    chosen_column = random.choice(
      available_columns) if available_columns else None
    if chosen_column is not None:
      self.make_move(chosen_column, self.player2)
      self.current_player = self.player1

  def can_win_next_move(self, column, symbol):
    row = self.get_next_available_row(column)
    if row is None:
      return False
    self.board[row][column] = symbol
    win = self.check_winner() == symbol
    self.board[row][column] = ':white_large_square:'
    return win

@client.command(name='connect4')
async def connect4(ctx, opponent: str = None):
  if await commandlockcheck(ctx):
    return

  playing_against_bot = False

  if opponent is None or opponent.lower() == 'bot':
    playing_against_bot = True
    opponent_id = -1
    opponent_mention = "CPU"
  else:
    try:
      opponent_member = await commands.MemberConverter().convert(ctx, opponent)
      if opponent_member == ctx.author or opponent_member.bot:
        await ctx.send("Invalid opponent.")
        return
      opponent_id = opponent_member.id
      opponent_mention = opponent_member.mention
    except commands.MemberNotFound:
      await ctx.send(
        "Member not found. Please mention a valid opponent or specify 'bot'.")
      return

  if ctx.author.id in game_sessions or (opponent_id in game_sessions
                                        and not playing_against_bot):
    await ctx.send("There is already a game in progress.")
    return

  session = Connect4Session(ctx.author.id, opponent_id, playing_against_bot)
  game_sessions[ctx.author.id] = session
  if not playing_against_bot:
    game_sessions[opponent_id] = session

  message_content = f"{ctx.author.mention} vs {opponent_mention}\nType `!drop (column number)` to make a move.\n" + session.print_board(
  ) + f"It's {ctx.author.name}'s turn."
  session.board_message = await ctx.send(message_content)

@client.command(name='drop')
async def drop(ctx, column: int = None):
  if await commandlockcheck(ctx):
    return

  if column is None or column < 1 or column > 7:
    await ctx.send("Please enter a column number (1-7) to make a move.")
    return

  if ctx.author.id not in game_sessions:
    await ctx.send("You are not currently in a game session.")
    return

  session = game_sessions[ctx.author.id]

  if session.game_over:
    await ctx.send("This game is already over.")
    return

  if ctx.author.id != session.current_player:
    await ctx.send("It's not your turn.")
    return

  column -= 1

  if session.make_move(column, ctx.author.id):
    winner = session.check_winner()
    if winner:
      session.game_over = True
      winning_message = ""
      if winner == ':red_circle:':
        winning_message = f"{ctx.author.mention} wins!" if ctx.author.id == session.player1 else f"{ctx.guild.get_member(session.player2).mention} wins!"
      elif winner == ':yellow_circle:':
        winning_message = "CPU wins!" if session.playing_against_bot else f"{ctx.guild.get_member(session.player2).mention} wins!"

      await session.board_message.edit(content=winning_message + "\n\n" +
                                       session.print_board())
      del game_sessions[session.player1]
      if session.player2 != -1:
        del game_sessions[session.player2]
      return
    elif session.is_board_full():
      session.game_over = True
      await session.board_message.edit(content="It's a draw!\n\n" +
                                       session.print_board())
      del game_sessions[session.player1]
      if session.player2 != -1:
        del game_sessions[session.player2]
      return

    if session.playing_against_bot:
      session.current_player = session.player2
      session.bot_make_move()
      winner = session.check_winner()
      if winner or session.is_board_full():
        session.game_over = True
        message = "CPU wins!" if winner == ':yellow_circle:' else "It's a draw!"
        await session.board_message.edit(content=message + "\n\n" +
                                         session.print_board())
        del game_sessions[session.player1]
        return
      else:
        session.current_player = session.player1
        await session.board_message.edit(
          content=f"{ctx.author.mention}'s turn.\n\n" + session.print_board())
    else:
      session.current_player = session.player2 if ctx.author.id == session.player1 else session.player1
      next_player_mention = ctx.guild.get_member(
        session.current_player).mention
      await session.board_message.edit(
        content=f"It's {next_player_mention}'s turn.\n\n" +
        session.print_board())

  else:
    await ctx.send("Invalid move. That column is full. Please choose another.")

####################################################################### 

def read_trivia_questions(file_path):
  with open(file_path, 'r') as file:
    lines = file.readlines()
  questions = {}
  for line in lines:
    question, *answers = line.strip().split(';')
    questions[question] = [answer.strip().lower() for answer in answers]
  return questions

trivia_questions_file = "questions.txt"
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

@client.command(name='trivia')
async def trivia(ctx):
  if await commandlockcheck(ctx):
    return

  question, answers = get_random_question()
  await ctx.send(f"{question}")

  def check(msg):
    return msg.author == ctx.author and msg.channel == ctx.channel

  for i in range(3):
    await ctx.send(
      f"You have {3-i} attempts left. Enter your answer within 10 seconds.")
    try:
      user_answer = await asyncio.wait_for(client.wait_for('message',
                                                           check=check),
                                           timeout=10.0)
      user_answer = user_answer.content.strip().lower()
    except asyncio.TimeoutError:
      await ctx.send("Time's up! The correct answer(s) is: " +
                     ", ".join(answers))
      return

    if user_answer in answers:
      await ctx.send("Correct answer!")
      return
    else:
      await ctx.send("That's incorrect. Try again.")

  correct_answers = ", ".join(answers)
  await ctx.send(
    f"Sorry, you've run out of attempts. The correct answer(s) is: {correct_answers}"
  )

#######################################################################

@client.command(name='stopgame')
async def stopgame(ctx):
  if await commandlockcheck(ctx):
    return

  if ctx.author.id not in op_ids:
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

    await ctx.send("Game session has been cancelled.")
    del game_sessions[session.player1]
    del game_sessions[session.player2]

####################################################################### 

async def check_birthday():
  await client.wait_until_ready(
  )
  channel = client.get_channel(
    696738982763167746
  )
  while True:
    with open("birthdays.txt", "r") as f:
      birthdays = f.readlines()
      for entry in birthdays:
        user_id, birthday = entry.strip().split(":")
        now = datetime.datetime.now(datetime.timezone.utc)
        current_time = now.strftime("%H:%M")
        if current_time == "00:00":
          birthday = datetime.datetime.strptime(birthday, "%d/%m/%Y")
          if birthday.day == now.day and birthday.month == now.month:
            user = await client.fetch_user(user_id)
            await channel.send(f"Happy birthday {user.mention}! 🎉")
            await asyncio.sleep(1)

    await asyncio.sleep(60)
    
#######################################################################

@client.command(name='vc')
async def voice(ctx):
    if await commandlockcheck(ctx):
        return

    embed = discord.Embed(title='Voice Call Commands', description='MonoBot voice call command list', color=discord.Color.blue())
    embed.add_field(name="!vc", value="Displays this menu", inline=False)
    embed.add_field(name="!joinvc", value="Makes the bot join your vc", inline=False)
    embed.add_field(name="!leavevc", value="Makes the bot leave your vc", inline=False)
    embed.add_field(name="!playsong (query)", value="Plays a song", inline=False)
    embed.add_field(name="!currentsong", value="Displays details about the currently playing song", inline=False)
    embed.add_field(name="!queue", value="Displays the queue", inline=False)
    embed.add_field(name="!addtoqueue (query) (optional - ; number)", value="Adds a song to the queue (or a position in the queue if specified)", inline=False)
    embed.add_field(name="!delfromqueue (query)", value="Deletes a song from the queue.", inline=False)
    embed.add_field(name="!loopqueue", value="Loops the queue", inline=False)
    embed.add_field(name="!shufflequeue", value="Shuffles the queue", inline=False)
    embed.add_field(name="!clearqueue", value="Clears the queue", inline=False)
    embed.add_field(name="!skipsong", value="Skips to the next song in queue", inline=False)
    embed.add_field(name="!resumesong", value="Resumes any paused song", inline=False)
    embed.add_field(name="!pausesong", value="Pauses the currently playing song", inline=False)
    embed.add_field(name="!stopsong", value="Completely stops the currently playing song", inline=False)
    await ctx.send(embed=embed)

#######################################################################

@client.command(name='joinvc', pass_context=True)
async def joinvc(ctx):
    if await commandlockcheck(ctx):
        return

    if ctx.author.voice:
        if ctx.voice_client:
            await ctx.voice_client.move_to(ctx.author.voice.channel)
        else:
            channel = ctx.author.voice.channel
            await channel.connect()
        await ctx.send("Joined the voice channel")
    else:
        await ctx.send("Error: You are not in a voice channel.")

@client.command(name='leavevc', pass_context=True)
async def leavevc(ctx):
    if await commandlockcheck(ctx):
        return

    global looping
    global queue
    global current_song
    global disconnect_timer_task

    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("Left the voice channel")
        looping = False
        queue = []
        current_song = None
        if disconnect_timer_task is not None and not disconnect_timer_task.done():
            disconnect_timer_task.cancel()
            disconnect_timer_task = None
    else:
        await ctx.send("Error: I am not currently in a voice channel.")

#######################################################################    
    
@client.command(name='playsong')    
async def playsong(ctx, *, query=None, from_play_next=False):
    if not from_play_next:
        if await commandlockcheck(ctx):
            return

    global queue
    global current_song
    global disconnect_timer_task

    if not query:
        if len(queue) == 0:
            await ctx.send("The queue is empty.")
            return
        else:
            query = queue.pop(0)
    else:
        pass

    if ctx.voice_client is None:
        if ctx.author.voice is None:
            await ctx.send("You are not connected to a voice channel.")
            return
        else:
            voice_client = await ctx.author.voice.channel.connect()
    else:
        voice_client = ctx.voice_client

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

        if not from_play_next and voice_client.is_playing():
            voice_client.stop()

        def after_play(error):
            asyncio.run_coroutine_threadsafe(handle_after_play(ctx, error), client.loop)

        source = FFmpegPCMAudio(url, **ffmpeg_options)
        voice_client.play(
            source,
            after=after_play
        )
        
        current_song = {
            'info': info,
            'start_time': time.time(),
        }
        
        if disconnect_timer_task is not None and not disconnect_timer_task.done():
            disconnect_timer_task.cancel()
            disconnect_timer_task = None

        await ctx.send(f"Now playing: {title}")
        return True

    except Exception as e:
        return False

async def handle_after_play(ctx, error):
    global current_song
    global disconnect_timer_task
    
    if not ctx.voice_client or not ctx.voice_client.is_playing():
        current_song = None
        if disconnect_timer_task is None or disconnect_timer_task.done():
            disconnect_timer_task = asyncio.create_task(disconnect_after_timeout(ctx))
        
    if error:
        await ctx.send(f"An error occurred during playback: {str(error)}.")
    else:
        await play_next(ctx)
        
async def disconnect_after_timeout(ctx):
    await asyncio.sleep(900)
    voice_client = ctx.voice_client
    if voice_client and not voice_client.is_playing():
        await voice_client.disconnect()
        await ctx.send("No audio has been played for 15 minutes. Disconnecting from the voice channel.")        

async def play_next(ctx):
    global queue
    global looping
    
    song = queue[0]
    success = await playsong(ctx, query=song, from_play_next=True)
    if success:
        if looping:
            queue.append(queue.pop(0))
        else:
            queue.pop(0)
    else:
        queue.pop(0)
        await play_next(ctx)
        
#######################################################################        
        
@client.command(name='currentsong')
async def currentsong(ctx):
    if await commandlockcheck(ctx):
        return

    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        await ctx.send("There is no song currently playing.")
        return

    global current_song

    if current_song is None:
        await ctx.send("No song information is available.")
        return

    info = current_song['info']
    start_time = current_song['start_time']
    elapsed_time = time.time() - start_time

    duration = info.get('duration')
    if duration is not None:
        duration_str = str(datetime.timedelta(seconds=int(duration)))
    else:
        duration_str = 'Unknown'

    elapsed_time_str = str(datetime.timedelta(seconds=int(elapsed_time)))

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
    embed.add_field(name="Elapsed Time", value=elapsed_time_str, inline=True)
    
    if thumbnail:
        embed.set_thumbnail(url=thumbnail)
        
    await ctx.send(embed=embed) 

#######################################################################    
    
@client.command(name='addtoqueue')
async def addtoqueue(ctx, *, arg_str: str = None):
    if await commandlockcheck(ctx):
        return

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

@client.command(name='delfromqueue')
async def deletefromqueue(ctx, *, song_name: str = None):
    if await commandlockcheck(ctx):
        return

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

@client.command(name='queue')
async def show_queue(ctx):
    if await commandlockcheck(ctx):
        return

    if len(queue) > 0:
        queue_list = '\n'.join([f'{index + 1}. {song}' for index, song in enumerate(queue)])
        await ctx.send(f"Song Queue:\n{queue_list}\nQueue loop: {'Enabled' if looping else 'Disabled'}")
    else:
        await ctx.send("The song queue is empty.")

@client.command(name='shufflequeue')
async def shuffle_queue(ctx):
    if await commandlockcheck(ctx):
        return

    global queue

    if len(queue) > 0:
        random.shuffle(queue)
        await ctx.send("Queue shuffled.")
    else:
        await ctx.send("The song queue is empty.")

@client.command(name='loopqueue')
async def toggle_queue_looping(ctx):
    if await commandlockcheck(ctx):
        return

    global looping

    looping = not looping

    await ctx.send(f"Looping the queue is {'enabled' if looping else 'disabled'}.")

@client.command(name='clearqueue')
async def clear_queue(ctx):
    if await commandlockcheck(ctx):
        return

    global queue

    if len(queue) > 0:
        queue = []
        await ctx.send("Queue cleared.")
    else:
        await ctx.send("The song queue is already empty.")

@client.command(name='skipsong')
async def skip(ctx):
    if await commandlockcheck(ctx):
        return

    if ctx.voice_client is None or not ctx.voice_client.is_playing():
        await ctx.send("There is no song currently playing.")
        return

    ctx.voice_client.stop()
    await ctx.send("Skipped to the next song.")

@client.command(name='pausesong')
async def pausesong(ctx):
    if await commandlockcheck(ctx):
        return

    if ctx.voice_client is None:
        await ctx.send("I am not connected to a voice channel.")
        return

    if ctx.voice_client.is_paused():
        await ctx.send("The audio is already paused.")
        return

    ctx.voice_client.pause()
    await ctx.send("Audio paused.")

@client.command(name='resumesong')
async def resumesong(ctx):
    if await commandlockcheck(ctx):
        return

    if ctx.voice_client is None:
        await ctx.send("I am not connected to a voice channel.")
        return

    if not ctx.voice_client.is_paused():
        await ctx.send("The audio is not paused.")
        return

    ctx.voice_client.resume()
    await ctx.send("Audio resumed.")

@client.command(name='stopsong')
async def stopsong(ctx):
    if await commandlockcheck(ctx):
        return

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

  if ctx.author.id not in op_ids:
    await ctx.send("You don't have permission to use this command.")
    return

  embed = discord.Embed(title='Admin', description='MonoBot admin command list', color=discord.Color.blue())
  embed.add_field(name="!admin", value="Displays this menu", inline=False)
  embed.add_field(name="!commandlock", value="Locks/unlocks all commands (can be toggled)", inline=False)
  embed.add_field(name="!repeat (text)", value="Makes the bot repeat anything you say", inline=False)
  embed.add_field(name='!testembed (entry1); (entry2); ...', value="Tests potential embed formats", inline=False)
  embed.add_field(name="!addquestion", value="Allows you to add a question to trivia", inline=False)
  embed.add_field(name="!resettrivia", value="Refreshes trivia (lets previously asked questions be asked again)", inline=False)
  embed.add_field(name="!stopgame", value="More powerful version that stops games (excluding trivia) even when you're not a participant", inline=False)
  embed.add_field(name="!gpt4 (query)", value="Uses GPT4 instead of regular GPT3 for better responses", inline=False)
  await ctx.send(embed=embed)
    
#######################################################################

@client.command(name='commandlock')
async def lock_commands(ctx):
  global commandlock
  if ctx.author.id in op_ids:
    commandlock = not commandlock
    if commandlock == True:
      await ctx.send("All commands locked.")
    else:
      await ctx.send("All commands unlocked.")

  else:
    await ctx.send("You don't have permission to use this command.")
    return

#######################################################################

@client.command(name='repeat')
async def repeat_message(ctx, *, message=None):
  if await commandlockcheck(ctx):
    return

  if ctx.author.id not in op_ids:
    await ctx.send("You don't have permission to use this command.")
    return

  if message is None:
    await ctx.send("Please enter a message after the command.")

  else:
    await ctx.send(message)

#######################################################################

@client.command(name='testembed')
async def testembed(ctx, *, arg=None):
    if await commandlockcheck(ctx):
        return
    
    if ctx.author.id not in op_ids:
        await ctx.send("You don't have permission to use this command.")
        return

    if not arg:
        await ctx.send("Please provide field names and values separated by semicolons.")
        return

    try:
        args = [entry.strip() for entry in arg.split(';') if entry.strip()]

        if len(args) % 2 != 0:
            await ctx.send("Please provide pairs of field names and field values separated by semicolons.")
            return

        embed = discord.Embed(
            title='Test',
            description='Embed test',
            color=discord.Color.blue()
        )

        for i in range(0, len(args), 2):
            field_name = args[i]
            field_value = args[i + 1]
            embed.add_field(name=field_name, value=field_value, inline=False)

        await ctx.send(embed=embed)

    except Exception as e:
        await ctx.send(f"An error occurred: {e}")
        
#######################################################################

@client.command(name='addquestion')
async def add_question(ctx):
    if await commandlockcheck(ctx):
        return

    if ctx.author.id not in op_ids:
        await ctx.send("You don't have permission to use this command.")
        return

    def check(msg):
        return msg.author == ctx.author and msg.channel == ctx.channel

    await ctx.send("Please enter the question you want to add:")
    try:
        user_question_msg = await client.wait_for('message', check=check, timeout=30.0)
        user_question = user_question_msg.content.strip()
    except asyncio.TimeoutError:
        await ctx.send("Question addition timed out. Please try again.")
        return

    await ctx.send(f"Question received: '{user_question}'")

    answers_list = []
    await ctx.send("Please enter the answers one by one. Type 'stop' when you're done.")
    
    while True:
        try:
            user_answer_msg = await client.wait_for('message', check=check, timeout=30.0)
            user_answer = user_answer_msg.content.strip()

            if user_answer.lower() == 'stop':
                break

            answers_list.append(user_answer)
            await ctx.send(f"Answer '{user_answer}' added. Type 'stop' if you're done, or add another answer.")
        except asyncio.TimeoutError:
            await ctx.send("Answer addition timed out. Please try again.")
            return

    if not answers_list:
        await ctx.send("No answers were provided. Question was not added.")
        return

    try:
        with open('questions.txt', 'a') as file:
            file.write(f"\n{user_question}; {'; '.join(answers_list)}")
        await ctx.send("Question and answers added successfully!")
    except Exception as e:
        await ctx.send(f"An error occurred while saving the question: {str(e)}")

#######################################################################

@client.command(name='resettrivia')
async def resettrivia(ctx):
    if await commandlockcheck(ctx):
        return
    
    if ctx.author.id not in op_ids:
        await ctx.send("You don't have permission to use this command.")
        return
    
    global previously_asked
    previously_asked = []
    await ctx.send("All trivia questions are now available again.")

#######################################################################

@client.command(name='gpt4')
async def gpt4(ctx, *, prompt=None):
    if await commandlockcheck(ctx):
        return

    if ctx.author.id not in op_ids:
        await ctx.send("You don't have permission to use this command.")
        return

    if not prompt:
        await ctx.send("Please enter a prompt.")
        return

    try:
        response = openai.ChatCompletion.create(
            model=gpt4_model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )

        reply = response.choices[0].message['content'].strip()
        if len(reply) > 2000:
            reply = reply[:1900]
            reply += "...\n\n*Note: Reply was cut off due to exceeding the Discord character limit of 2000.*"

        await ctx.send(reply)
    except Exception as e:
        await ctx.send(f"An error occurred: {e}")

#######################################################################

@client.tree.command(name='ping', description='pings the bot')
async def repeat(interaction: discord.Interaction):
  await interaction.response.send_message('pong')

######################################################################

@client.event
async def on_message(message):
  if message.author == client.user:
    return

  msg = message.content

  if any(word in msg for word in respondpls):
    await message.channel.send('okay')
    return

  await client.process_commands(message)
    
client.run(token)

#######################################################################