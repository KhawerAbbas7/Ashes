import discord, json
from discord import app_commands
from discord.ext import commands
from discord import ui 
from cogs.views import makeProfileView
class UserInstallable(commands.Cog):
  def __init__(self, bot: commands.Bot) -> None:
    self.bot = bot
  @app_commands.command(name="say", description="Say something;owners only")
  async def say(self, interaction, message: str, messageId: int = None):
    if interaction.user.id not in interaction.client.owner_ids:return 
    c = interaction.channel 
    await interaction.response.send_message("Done", ephemeral= True)
    if messageId and m:= c.get_partial_message(messageId):
      return m.reply(message)
    return await c.send(message)
  @app_commands.command(name="stats", description="get statistics for yourself or someone else")
  @app_commands.describe(member='the user to check, leave it if you want to check yours.', ephemeral='If u want message to be secret')
  @app_commands.allowed_installs(guilds=True, users=True)
  @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
  async def playerstats(self,interaction, member: discord.User = None, ephemeral: bool = False):
    if not member:
      member = interaction.user
    v = await makeProfileView(member,interaction)
    if v == "No Games":
      return await interaction.response.send_message(content= f"{member} is yet to relish the Ashes.", ephemeral= ephemeral)
    return await interaction.response.send_message(view = v, ephemeral=ephemeral)
async def setup(bot: commands.Bot) -> None:
  await bot.add_cog(UserInstallable(bot))
  await bot.tree.sync()