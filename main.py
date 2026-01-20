import discord, os
from discord.ext import commands
from dotenv import load_dotenv
import os, aiosqlite
from cogs.views import *
load_dotenv()
token=os.getenv("TOKEN")
os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'
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
bot = Ashes()
@bot.command()
async def help(ctx):
  v = Helpview(ctx)
  await ctx.send(view= v)
@bot.command()
@commands.has_permissions(manage_messages=True, description= "Change the way you can call bot in your guild.", extras={'usableBy': 'Anyone with manage_messages permission.'})
async def prefix(ctx, newPrefix: str):
  if len(newPrefix) > 3: return await ctx.send("The length of prefix must not exceed 3 characters.")
  await bot.settingsdb.execute("INSERT INTO settings (guildId,prefix) VALUES (?,?) ON CONFLICT(guildId) DO UPDATE SET prefix=excluded.prefix", (ctx.guild.id, newPrefix))
  await bot.settingsdb.commit()
  return await ctx.send(f"Bot's new prefix -> `{newPrefix}`")

bot.run(token)