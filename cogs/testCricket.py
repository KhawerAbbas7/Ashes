import discord
from discord import Embed, Color,ui
from discord.ext import commands, tasks
from cogs.game import Game
from cogs.views import *
class TestCricket(commands.Cog, name= "Test Cricket"):
  def __init__(self, bot):
    self.bot = bot
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @commands.command(aliases= ['c'], description= 'Create a test match instance and invite others to join the fun.')
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
  @commands.command(aliases= ['j'], description= 'Join an existing match.')
  async def join(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    elif any(ctx.author.id==p.id for g in self.bot.games.values() for p in g.players):
      return await ctx.send(embed= Embed(title='You are already in a game', description='Looks like you are already playing a game.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    elif len(g.players) == 18:return await ctx.send(embed= Embed(title='18 Players.', description='18 players have joined this game, therefore you can\'t sneak in.', color=Color.from_str('#b30707')))
    g.join(ctx.author)
    await ctx.send(f'{ctx.author.name} has joined the game')
  @commands.command(aliases= ['l'], description= 'Leave a game.')
  async def leave(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if ctx.author.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title=f'{ctx.author} not in Game.', description='You are already not playing.', color=Color.from_str('#b30707')))
    if g.hostId == ctx.author.id:return await ctx.send(embed= Embed(title='Hosts can\'t leave', description='This command is can\'t be run by host', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    p = next((p for p in g.teama.players if p.id == ctx.author.id), None)
    if p:
      g.teama.players.pop(g.teama.players.index(p))
    else:
      p = next((p for p in g.teamb.players if p.id == ctx.author.id), None) 
      if p:g.teamb.players.pop(g.teamb.players.index(p))
    g.mitigatePlayers()
    await ctx.send(f'{ctx.author} has decided to be a prick and left the game')
  @commands.command(aliases= ['delete'], description= 'Delete a game, cannot be used if gane has started.',extras={'usableBy': 'Host only.'})
  async def yeet(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    buttons = [Button('Yes',discord.ButtonStyle.green,ctx.author.id), Button('No',discord.ButtonStyle.red ,ctx.author.id)]
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"Are you sure to yeet this game?"))
    container.add_item(actionRow)
    view.add_item(container)
    await ctx.send(view=view)
    await view.wait()
    if view.value in [None, 'No']: return 
    ctx.bot.games.pop(ctx.channel.id)
    await ctx.send("Game yeeted!")
  @commands.command(aliases= ['fuck'],extras={'usableBy': 'Host only.'}, description= 'Kick a player from the lobby, only usable before start.')
  async def kick(self, ctx, user: discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif user.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title=f'{user} not in Game.', description='User is already not playing.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    p = next((p for p in g.teama.players if p.id == user.id), None)
    if p:
      g.teama.players.pop(g.teama.players.index(p))
    else:
      p = next((p for p in g.teamb.players if p.id == user.id), None) 
      if p:g.teamb.players.pop(g.teamb.players.index(p))
    g.mitigatePlayers()
    await ctx.send(f'{user} has been kicked off from the game')
  @commands.command(aliases= ['userscore'], description= 'View the performance of yourself or someone in the current game.')
  async def score(self, ctx, user: discord.User= None):
    if not user: user = ctx.author
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if user.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title='Not In Game.', description=f'{user} is not playing in this server.', color=Color.from_str('#b30707')))
    elif not g.started:
      return await ctx.send(embed= Embed(title='Waiting for Game to Start', description='Game is yet to begin.', color=Color.from_str('#b30707')))
    bat=[]
    bowl=[]
    timeline=[]
    tookWickets = []
    player = next(p for p in g.players if p.id == user.id)
    for inn in g.innings:
      if player in inn.batters:
        tookWickets = []
        i=inn.batters[player]
        timeline = i.timeline
        if i.balls>0: bat.append(f"{i.runs}({i.balls}){'*' if not i.dismissed else ''}")
      if player in inn.bowlers:
        i=inn.bowlers[player]
        tookWickets = i.wicketsDigits
        timeline = i.timeline
        if i.balls>0: bowl.append(f"{i.runsConceded}/{i.wickets} ({self.ballsToOvers(i.balls)})")
    bat, bowl = " & ".join(bat), " & ".join(bowl)
    view = ui.LayoutView(timeout= 60)
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b")) 
    container.add_item(ui.TextDisplay(f"**Batting:** {bat}\n**Bowling:**{bowl}"))
    if timeline:
      container.add_item(ui.TextDisplay(" • ".join([f'**{t}**' for t in timeline])))
    if tookWickets:
      w = " • ".join([f'**{t}**' for t in tookWickets])
      container.add_item(ui.TextDisplay(f"Wickets on: {w}"))
    view.add_item(container)
    await ctx.send(view=view)
  @commands.command(aliases= ['pl'], description= 'View the roster for each team.')
  async def playersList(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    await ctx.send(view=g.showPlayers())
  @commands.command(aliases= [''], description= 'Get the link for live score message.')
  async def live(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if not g.started or not g.updateMsg:
      return await ctx.send(embed= Embed(title='Waiting for Game to Start', description='Game is yet to begin.', color=Color.from_str('#b30707')))
    await ctx.send(f"**[Update Message]({g.updateMsg.jump_url})**")
  @commands.command(aliases= ['t'], description= 'Call the toss.', extras={'usableBy': 'Host or Captains only.'})
  async def toss(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.batFirstTeam is not None:return await ctx.send(embed= Embed(title='Toss Done', description='Toss had already been done', color=Color.from_str('#b30707')))
    if g.hostId != ctx.author.id and ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Host or Captain Only', description='This command is only intended to be run by host or captains.', color=Color.from_str('#b30707')))
    await g.toss()
    #await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['ctn'],description= 'Change the name of a team.', extras={'usableBy': 'Host or Captains only.'})
  async def changeteamname(self, ctx, teamIndex:int,*, teamName: str):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id and ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Host or Captain Only', description='This command is only intended to be run by host or captains.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    elif not teamName.replace(' ','').isalpha() or len(teamName) > 20 :
      return await ctx.send(embed= Embed(title='Invalid Team Name', description='Team name must only be 20 characters or less and can only consist of alphabets and whitespace.', color=Color.from_str('#b30707')))
    elif teamIndex > 2 or teamIndex <1:
      return await ctx.send(embed= Embed(title='Invalid Team Index', description='Team index must only be 1 or 2.', color=Color.from_str('#b30707')))
    team = g.teama if teamIndex == 1 else g.teamb
    if team.captain.id != ctx.author.id and g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Invalid Team', description='You can\'t change the name of other team.', color=Color.from_str('#b30707')))
    oldTeamName = team.name 
    team.name = teamName
    await ctx.send(f"{oldTeamName} will now be called as **{team.name}**")
    #await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['ch'],description= 'Change the host.', extras={'usableBy': 'Host.'})
  async def changehost(self, ctx, host:discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    if host.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title='New host not in Game.', description='New host must have joined .', color=Color.from_str('#b30707')))
    g.hostId = host.id
    await ctx.send(f"{host} is the new host.")
    #await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['np'],description= 'Select next bowler or batter.', extras={'usableBy': 'Captains only.'})
  async def nextplayer(self, ctx, nextP:discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Captain Only', description='This command is only intended to be run by captains.', color=Color.from_str('#b30707')))
    elif not g.started:return await ctx.send(embed= Embed(title='Can\'t be used before start.', description='This command can\'t be used before the commencement of the game.', color=Color.from_str('#b30707')))
    if nextP.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title='Player didn\'t join.', description='They must have joined .', color=Color.from_str('#b30707')))
    team = g.teama if ctx.author.id == g.teama.captain.id else g.teamb
    inn = g.currentInning
    if nextP.id not in [p.id for p in team.players]:
      return await ctx.send(f"Bud is so disgusted with his team that he decided to send a player from another team.")
    if inn.battingTeam.id == team.id:
      if nextP.id in inn.cantBat or nextP.id in [b.id for b in inn.currentBatters]:
        return await ctx.send(f"**{nextP}** is either currently batting or has been dismissed, in both cases you have failed ad a captain.")
      inn.nextBatterId = nextP.id
      await ctx.send(f"**{nextP}** will be batting next.")
    else:
      if not inn.currentBowlers:
        return await ctx.send(f"**Hold on a sec**.")
      if nextP.id == inn.currentBowlers[0].id:
        return await ctx.send(f"**{nextP}** is currently bowling bozo.")
      inn.nextBowlerId = nextP.id
      return await ctx.send(f"**{nextP}** will be bowling next over.")
    
  @commands.command(aliases= ['cc'],description= 'Change the captain of a team.', extras={'usableBy': 'Host or Captains only.'})
  async def changecap(self, ctx, cap:discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id and ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Host or Captain Only', description='This command is only intended to be run by host or captains.', color=Color.from_str('#b30707')))
    if cap.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title='New Captain not in Game.', description='New captain must have joined .', color=Color.from_str('#b30707')))
    team = g.teama if cap.id in [p.id for p in g.teama.players] else g.teamb
    team.captain = next(p for p in team.players if p.id == cap.id)
    await ctx.send(f"{cap} will be captaining {team.name}")
    #await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['sp'],description= 'Swap between two players.', extras={'usableBy': 'Host only.'})
  async def swap(self, ctx, idx: int, idx2: int):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    try:
      a,b = g.players[idx-1], g.players[idx2-1]
      g.swap(idx-1, idx2-1)
      await ctx.send(f"Swapped {a} with {b}")
    except:
      await ctx.send(f"Couldn't swap, perhaps wrong indexes?")
      
    #await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['s'],description= 'Start the game.', extras={'usableBy': 'Host only.'})
  async def start(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Game has already started', description='Game has already commenced, you can\'t start it twice, it is not your relationship.', color=Color.from_str('#b30707')))
    elif g.batFirstTeam is None:return await ctx.send(embed= Embed(title='Toss Not Done', description='Toss has not taken place yet', color=Color.from_str('#b30707')))
    elif len(g.players)%2 != 0 or len(g.players) < 4:return await ctx.send(embed= Embed(title='Unequal Teams', description='Teams are unequal. Just like your love for them vs their love for you.', color=Color.from_str('#b30707')))
    await g.start()
    #await ctx.send(view=g.showPlayers())
async def setup(bot):await bot.add_cog(TestCricket(bot))