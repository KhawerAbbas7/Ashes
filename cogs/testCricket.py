import discord
from discord import Embed, Color
from discord.ext import commands, tasks
from cogs.game import Game
class TestCricket(commands.Cog, name= "Test Cricket"):
  def __init__(self, bot):
    self.bot = bot
  @commands.command(aliases= ['c'])
  async def create(self, ctx):
    if ctx.channel.id in self.bot.games:
      return await ctx.send(embed= Embed(title='There is already a game in this channel', description='Looks like this channel is already hosting a game.', color=Color.from_str('#b30707')))
    elif any(ctx.author.id==p.id for g in self.bot.games.values() for p in g.players):
      return await ctx.send(embed= Embed(title='You are already in a game', description='Looks like you are already playing a game.', color=Color.from_str('#b30707')))
    e = Embed(title='Game Of Test Cricket', description='A game of Test Cricket has been initiated. Send `.j` to join.', color=Color.from_str('#0a5d9b'))
    g = Game(ctx)
    g.join(ctx.author)
    self.bot.games[ctx.channel.id] = g
    return await ctx.channel.send(embed=e)
  @commands.command(aliases= ['j'])
  async def join(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    elif any(ctx.author.id==p.id for g in self.bot.games.values() for p in g.players):
      return await ctx.send(embed= Embed(title='You are already in a game', description='Looks like you are already playing a game.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    g.join(ctx.author)
    await ctx.send(f'{ctx.author.name} has joined the game')
  @commands.command(aliases= ['pl'])
  async def playersList(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['t'])
  async def toss(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    await g.toss()
    #await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['s'])
  async def start(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    await g.start()
    #await ctx.send(view=g.showPlayers())
async def setup(bot):await bot.add_cog(TestCricket(bot))