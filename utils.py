import discord 
from discord.ext import commands, tasks
class K_Converter(commands.Converter):
  async def convert(self, ctx, argument):
    argument = argument.lower()
    if argument.endswith('k'):
      argument = argument.rstrip('k')
      if argument.isdigit():
        if int(argument) < 1: 
          raise commands.BadArgument('Invalid Amount, Minimum amount should be 1')
        else: return int(argument)*1000
      else:
        raise commands.BadArgument('Invalid Amount')
    else:
      if argument.isdigit():
        if int(argument) < 1: raise commands.BadArgument('Invalid Amount, Minimum amount should be 1')
        else: return int(argument)
      else:
        raise commands.BadArgument('Invalid Amount')
class NonBotUser(commands.Converter):
  async def convert(self, ctx, argument):
    user = await commands.UserConverter().convert(ctx, argument)
    if user.bot:
      raise commands.BadArgument("Bot can't be passed as an argument.")
    return UserConverter