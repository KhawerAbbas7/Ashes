import discord
from discord.ext import commands
from cordia import CordiaClient
import os
class Analytics(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
    self.cordia = CordiaClient(api_key=os.getenv("CORDIA_API_KEY"),bot_id="1443165621100740668",debug=True,batch_size=50,flush_interval=60000,auto_scale=True)
  @commands.Cog.listener()
  async def on_ready(self):
    self.cordia.start(loop=self.bot.loop)
    print("📊 Cordia Analytics: Background Loops Started")
    await self.cordia.post_guild_count(len(self.bot.guilds))

  @commands.Cog.listener()
  async def on_command_completion(self, ctx):
    await self.cordia.track_command(command=ctx.command.name,user_id=str(ctx.author.id),guild_id=str(ctx.guild.id) if ctx.guild else None)
  @commands.Cog.listener()
  async def on_message(self, message):
    if message.author.bot:return
    await self.cordia.track_user(user_id=str(message.author.id),guild_id=str(message.guild.id) if message.guild else None,action="message_sent")

  async def cog_unload(self):
    await self.cordia.close()
    print("💾 Cordia Analytics: Final flush performed.")
async def setup(bot):await bot.add_cog(Analytics(bot))