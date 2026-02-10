import discord, os
from discord.ext import commands, tasks
from dotenv import load_dotenv
import os, aiosqlite
from cogs.views import *
import psutil
from psutil import cpu_percent
load_dotenv()
token=os.getenv("TOKEN")
os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'
def human_readable_size(size_bytes):
  if size_bytes < 1024:return f"{size_bytes} bytes"
  elif size_bytes < 1024**2:return f"{size_bytes / 1024:.2f} KB"
  elif size_bytes < 1024**3:return f"{size_bytes / 1024**2:.2f} MB"
  else:return f"{size_bytes / 1024**3:.2f} GB"
async def get_pre(bot, message):
  if not message.guild:return commands.when_mentioned_or(*["", "."])(bot, message) 
  async with bot.settingsdb.execute("SELECT prefix FROM settings WHERE guildId =?", (message.guild.id,)) as cursor:
    p = await cursor.fetchone()
    prefix_return = [p[0] if p else "as!"]
    return commands.when_mentioned_or(*prefix_return)(bot, message)
class Ashes(commands.Bot):
  def __init__(self, intents= discord.Intents.all(), command_prefix= get_pre,case_insensitive=True, strip_after_prefix= True):
    super().__init__(intents=intents, command_prefix= get_pre,case_insensitive=True, strip_after_prefix= True,help_command=None)
    self.games = {}
    self.Gifs = {
      "Batting": [
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/Kusal%20Parera%20Celebrates%20against%20South%20Africa%20151.gif",
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/Younis%20Khan%20celebrates%20his%20100%20vs%20England%20at%20Lords.gif",
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/stokes%20celebrates%20vs%20england.gif"
        ],
      "Bowling": [
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/Noman%20Ali%20Celebrates%20After%20dismissing%20Mulder%202025.gif",
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/Sajid%20Khan%20Celebrates%20After%20dismissing%20Jamie%20Smith%202024.gif",
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/Travis%20Head%20wicket%20celebration%20v%20Rishab%20Pant.gif",
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/Dale%20Steyn%20Celebrates%20After%20dismissing%20Katich%20MCG%202008.gif",
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/Jasprit%20Bumrah%20Celebrates%20After%20dismissing%20Travis%20Head%202024.gif",
        "https://raw.githubusercontent.com/KhawerAbbas7/MyGifs/refs/heads/main/public/gifs/Wasim%20Akram%20Celebrates%20After%20dismissing%20Marsh%201990%20MCG.gif"
        ]
    }
  @tasks.loop(seconds= 30)
  async def gamesDeletionCheck(self):
    for g in self.games.copy().values():
      await g.checkIfDeletable()
  async def on_guild_channel_delete(self, channel):
    if channel.id in [g.ctx.channel.id for g in self.games.copy().values()]:
      await self.games[channel.id].saveData()
      self.games[channel.id].forceYeet = True
      self.games.pop(channel.id)
  async def on_guild_remove(self, guild):
    games = [g for g in self.games.copy().values() if g.ctx.guild.id == guild.id]
    if games:
      for g in games:
        await g.saveData()
        g.forceYeet = True
        self.games.pop(g.ctx.channel.id)
  async def on_member_remove(self, member):
    guild = member.guild
    for game in self.games.copy().values():
      if guild.id == game.ctx.guild.id:
        if member.id in [p.id for p in game.players]:
          await game.ctx.send(f'**{member.name}** has left the guild.')
  async def setup_hook(self):
    self.db = await aiosqlite.connect(os.path.join(os.getcwd(), 'databases', 'ashes.db'))
    self.settingsdb = await aiosqlite.connect(os.path.join(os.getcwd(), 'databases', 'settings.db'))
    await self.db.execute("PRAGMA foreign_keys = ON")
    await self.db.execute("PRAGMA journal_mode = WAL")
    await self.settingsdb.execute("PRAGMA foreign_keys = ON")
    await self.settingsdb.execute("PRAGMA journal_mode = WAL")
    script = open("schema.sql").read()
    settingsscript = open("settingsdbschema.sql").read()
    await self.db.executescript(script)
    await self.settingsdb.executescript(settingsscript)
    await self.load_extension('jishaku')
    await self.load_extension('api')
    for file in os.listdir('cogs'):
      if file.endswith('py') and file not in ['game.py', 'views.py']:await self.load_extension('cogs.' + file[:-3])
  async def fetchrow(self, query, params=()):
    async with self.db.execute(query, params) as cursor:
      return await cursor.fetchone()
  async def fetchall(self, query, params=()):
    async with self.db.execute(query, params) as cursor:
      return await cursor.fetchall()
  async def execute(self, query, params=()):
    await self.db.execute(query, params)
    await self.db.commit()
  async def on_command_error(self, ctx, error):
    if isinstance(error,commands.CommandNotFound): pass
  async def on_ready(self):
    self.gamesDeletionCheck.start()
bot = Ashes()
@bot.command()
async def ping( ctx):
  duration= bot.latency * 1000 
  duration = round(duration, 2)
  embed = discord.Embed(title= 'Pong', color= discord.Color.from_str('#42f5a1'))
  matches=await bot.fetchrow("SELECT COUNT(DISTINCT matchId) as matches  FROM deliveries", ())
  players=await bot.fetchrow("SELECT COUNT(DISTINCT playerId) FROM (SELECT batterId AS playerId FROM deliveries WHERE batterId IS NOT NULL UNION SELECT nonStrikerId FROM deliveries WHERE nonStrikerId IS NOT NULL UNION SELECT bowlerId FROM deliveries WHERE bowlerId IS NOT NULL) t", ())
  dbsize = await bot.fetchrow("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();",())
  botstats = f"Guilds: {len(ctx.bot.guilds)}\nCurrent Games: {len(ctx.bot.games)}\nMatches so far: {matches[0]}\nPlayers: {players[0]}\nCPU Usage: {cpu_percent()}%\nLatency: {duration}ms\nDatabase size: {human_readable_size(dbsize[0])}"
  embed.description = botstats
  return await ctx.send(embed=embed, content="")
@bot.command()
async def help(ctx):
  v = Helpview(ctx)
  await ctx.send(view= v)
@bot.command(description= "Change the way you can call bot in your guild.", extras={'usableBy': 'Anyone with manage_messages permission.'})
@commands.has_permissions(manage_messages=True)
async def prefix(ctx, newPrefix: str):
  if len(newPrefix) > 3: return await ctx.send("The length of prefix must not exceed 3 characters.")
  await bot.settingsdb.execute("INSERT INTO settings (guildId,prefix) VALUES (?,?) ON CONFLICT(guildId) DO UPDATE SET prefix=excluded.prefix", (ctx.guild.id, newPrefix))
  await bot.settingsdb.commit()
  return await ctx.send(f"Bot's new prefix -> `{newPrefix}`")

bot.run(token)