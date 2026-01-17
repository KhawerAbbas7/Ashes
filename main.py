import discord, os
from discord.ext import commands
from dotenv import load_dotenv
import os, aiosqlite
load_dotenv()
token=os.getenv("TOKEN")
os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'
class Ashes(commands.Bot):
  def __init__(self, intents= discord.Intents.all(), command_prefix= '.',case_insensitive=True, strip_after_prefix= True):
    super().__init__(intents=intents, command_prefix= command_prefix)
    self.games = {}
  async def setup_hook(self):
    self.db = await aiosqlite.connect(os.path.join(os.getcwd(), 'databases', 'ashes.db'))
    await self.db.execute("PRAGMA foreign_keys = ON")
    await self.db.execute("PRAGMA journal_mode = WAL")
    async with self.db.executescript(open("schema.sql").read()) as _:
      pass
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
bot.run(token)