import discord, traceback
from discord.ext import commands
import asyncio, json, copy
import uvicorn
from fastapi import FastAPI, WebSocket
import threading
from pydantic import BaseModel
class Type:
  value= 2
async def run_in_bot_loop(coro, bot):
  fut = asyncio.run_coroutine_threadsafe(coro, bot.loop)
  return await asyncio.wrap_future(fut)
api = FastAPI()

class MyCog(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot
    api.bot = bot
    self.server = None
    self.thread = None
    self.connections= []
  def start_api(self):
    config = uvicorn.Config(api, host="0.0.0.0", port=20375, log_level="info")
    self.server = uvicorn.Server(config)
    asyncio.run(self.server.serve())

  async def cog_load(self):
    loop = asyncio.get_running_loop()
    self.thread = threading.Thread(target=self.start_api, daemon=True)
    self.thread.start()

  async def cog_unload(self):
    if self.server and self.server.started:self.server.should_exit = True
    if self.thread and self.thread.is_alive():self.thread.join(timeout=2)
class Toggleauto(BaseModel):
  Auto: bool
  AutoSelect: bool
@api.get("/guilds")
def list_guilds():
  bot = api.bot
  return {"guilds": [g.name for g in bot.guilds]}
async def setup(bot):await bot.add_cog(MyCog(bot))
