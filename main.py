import discord, os
from discord.ext import commands
from dotenv import load_dotenv
import os, sqlite3
load_dotenv()
token=os.getenv("TOKEN")
os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'
class Ashes(commands.Bot):
  def __init__(self, intents= discord.Intents.all(), command_prefix= '.',case_insensitive=True, strip_after_prefix= True):
    super().__init__(intents=intents, command_prefix= command_prefix)
    self.games = {}
    self.db = sqlite3.connect(os.path.join(os.getcwd(), 'databases', 'ashes.db'))
    self.crsr = self.db.cursor()
  async def setup_hook(self):
    self.crsr.execute("PRAGMA foreign_keys = ON")
    self.crsr.execute("PRAGMA journal_mode = WAL")
    with open("schema.sql") as f:
      self.crsr.executescript(f.read())
    await self.load_extension('jishaku')
    for file in os.listdir('cogs'):
      if file.endswith('py') and file not in ['game.py', 'views.py']:await self.load_extension('cogs.' + file[:-3])
bot = Ashes()
bot.run(token)