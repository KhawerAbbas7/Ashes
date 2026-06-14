import discord, time,random, json
from discord import Embed, Color,ui
from discord.ext import commands, tasks
from cogs.game import Game
from cogs.views import *
from io import BytesIO
class TestCricket(commands.Cog, name= "Test Cricket"):
  def __init__(self, bot):
    self.bot = bot
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @commands.command(aliases=['export'], description='.')
  @commands.is_owner()
  async def exp(self, ctx):
    file = ctx.bot.export_live_instance(ctx.bot.games[ctx.channel.id])
    await ctx.send(content= "Here is the export file of this game which can be used for later resumption.", file = file)
  @commands.command()
  @commands.is_owner()
  async def resume(self, ctx):
    message = ctx.message
    if message.reference and (replyMsg:= message.reference.resolved):
      file_content = await replyMsg.attachments[0].read()
      data = json.loads(file_content.decode('utf-8'))
      game = Game(ctx)
      game.resumed = True
      await game.load_from_state(data) 
      ctx.bot.games[ctx.channel.id] = game
      await ctx.send("Game state loaded successfully. Resuming match...")
      await game.start()
      await game.updateMessage(True)
  @commands.command(aliases= ['c'], description= 'Create a test match instance and invite others to join the fun.')
  async def create(self, ctx):
    if ctx.bot.creationBlocked:
      return await ctx.send(embed= Embed(title='Cannot Create!', description='Creation of new games has been temporarily blocked. Join the [support server](https://discord.gg/uxchR7sKd2) to find out why.', color=Color.from_str('#b30707')))
    if ctx.channel.id in self.bot.games:
      return await ctx.send(embed= Embed(title='There is already a game in this channel', description='Looks like this channel is already hosting a game.', color=Color.from_str('#b30707')))
    elif any(ctx.author.id==p.id for g in self.bot.games.values() for p in g.players):
      return await ctx.send(embed= Embed(title='You are already in a game', description='Looks like you are already playing a game.', color=Color.from_str('#b30707')))
    e = Embed(title='Game Of Test Cricket', description='A game of Test Cricket has been initiated. Send `.j` to join.', color=Color.from_str('#0a5d9b'))
    g = Game(ctx)
    g.join(ctx.author)
    self.bot.games[ctx.channel.id] = g
    await ctx.channel.send(embed=e)
    if ctx.author.id == ctx.bot.owner_id:await ctx.bot.postKhawiData(data= {"status": "lobby","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.lobbyCreatedAt*1000)} ,"party": {'id': g.gameId, 'size': [2,18]}})
  @commands.command(aliases= ['j'], description= 'Join an existing match.')
  async def join(self, ctx, rep:str= None):
    isRep = rep in ['r', 'rep']
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    elif not rep and any(ctx.author.id==p.id for g in self.bot.games.values() for p in g.players):
      g = next((g for g in self.bot.games.copy().values() if any(ctx.author.id==p.id for p in g.players)),None)
      if g.ctx.channel.id != ctx.channel.id:return await ctx.send(embed= Embed(title='You are already in a game', description=f'You are already playing a game at <#{g.ctx.channel.id}>.', color=Color.from_str('#b30707')))
      else:return await ctx.send(embed= Embed(title='Already Joined', description=f'You have already joined.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.lobbyLocked: 
      return await ctx.send(embed= Embed(title='Lobby Locked.', description='Lobby is locked, no can join.', color=Color.from_str('#b30707')))
    elif ctx.author.id in g.bannedUsers:
      return await ctx.send(embed= Embed(title='Banned.', description='You have been banned from the lobby.', color=Color.from_str('#b30707')))
    if ctx.author.id in [p.id for p in g.players]:return await ctx.send(embed= Embed(title='You are already in a game', description='Looks like you are already playing a game.', color=Color.from_str('#b30707')))
    if g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    elif len(g.players) == 18:return await ctx.send(embed= Embed(title='18 Players.', description='18 players have joined this game, therefore you can\'t sneak in.', color=Color.from_str('#b30707')))
    if isRep:
      g.join(ctx.author)
      g.repIds.append(ctx.author.id)
      return await ctx.send(f'{ctx.author.name} has joined the game as a rep.')
    g.join(ctx.author)
    await ctx.send(f'{ctx.author.name} has joined the game')
    if ctx.author.id == ctx.bot.owner_id or ctx.bot.owner_id in [p.id for p in g.players]:await ctx.bot.postKhawiData(data= {"status": "lobby","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.lobbyCreatedAt*1000)} ,"party": {'id': g.gameId, 'size': [len(g.players),18]}})
  @commands.command(aliases= ['l'], description= 'Leave a game.')
  async def leave(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if ctx.author.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title=f'{ctx.author} not in Game.', description='You are already not playing.', color=Color.from_str('#b30707')))
    if g.hostId == ctx.author.id:return await ctx.send(embed= Embed(title='Hosts can\'t leave', description='This command is can\'t be run by host', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    p = next((p for p in g.teama.players if p.id == ctx.author.id), None)
    
    if ctx.author.id in g.repIds:g.repIds.remove(ctx.author.id)
    if p:
      g.teama.players.pop(g.teama.players.index(p))
    else:
      p = next((p for p in g.teamb.players if p.id == ctx.author.id), None) 
      if p:g.teamb.players.pop(g.teamb.players.index(p))
    g.mitigatePlayers()
    await ctx.send(f'{ctx.author} has left the game.')
    if ctx.author.id == ctx.bot.owner_id:await ctx.bot.postKhawiData(data= {"status": "exited","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.lobbyCreatedAt*1000)} ,"party": {'id': g.gameId, 'size': [2,len(g.players)]}})
  @commands.command(aliases= ['T10'], description= 'Change the format to T10.',extras={'usableBy': 'Host only.'})
  async def t10on(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    g.T10 = True if not g.T10 else False
    await ctx.send("Changed the format to T10" if not g.T10 else "Changed the format to T10")
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
    if ctx.bot.owner_id in [p.id for p in g.players]:await ctx.bot.postKhawiData(data= {"status": "exited","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.lobbyCreatedAt*1000)} ,"party": {'id': g.gameId, 'size': [2,len(g.players)]}})
    
  @commands.command(aliases= ['unlock'],extras={'usableBy': 'Host only.'}, description= 'Lock the lobby so no one can join.')
  async def lock(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    g.lobbyLocked = True if not g.lobbyLocked else False
    if g.lobbyLocked:
      return await ctx.send(embed= Embed(title='Lobby Locked.', description='Lobby has been locked, no one new can join.', color=Color.from_str('#b30707')))
    else:
      return await ctx.send(embed= Embed(title='Lobby Unlocked.', description='Lobby has been unlocked.', color=Color.from_str('#1fb307')))
  @commands.command(aliases= ['rl'],extras={'usableBy': 'Host only.'}, description= 'Set the limit of runs a rep can score.')
  async def replimit(self, ctx, limit: int):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif limit < 5:return await ctx.send(embed= Embed(title='Invalid Limit.', description='The score limit for representative player can\'t be less than 5.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    g.repLimit = limit
    await ctx.send(f'The score limit for representative player has been set to {limit}, reps will automatically be declared out upon reaching the limit.')
  @commands.command(aliases= [],extras={'usableBy': 'Host only.'}, description= 'Unban someone from the lobby.')
  async def unban(self, ctx, user: discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif user.id not in g.bannedUsers:return await ctx.send(embed= Embed(title=f'User is Unbanned.', description='User is already unbanned.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    g.bannedUsers.remove(user.id)
    return await ctx.send(embed= Embed(title=f'{user} Unbanned.', description=f'{user} has been unbanned and join this lobby.', color=Color.from_str('#07b334')))
  @commands.command(aliases= [],extras={'usableBy': 'Host only.'}, description= 'Ban someone from the lobby.')
  async def ban(self, ctx, user: discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif user.id == ctx.author.id:
      return await ctx.send(embed= Embed(title="Can't Ban", description='You cannot ban yourself.', color=Color.from_str('#b30707')))
    
    elif user.id in g.bannedUsers:return await ctx.send(embed= Embed(title=f'User is Banned.', description='User is already banned.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    if user.id not in [p.id for p in g.players]:
      g.bannedUsers.append(user.id)
      return await ctx.send(embed= Embed(title=f'{user} Banned.', description=f'{user} has been banned and cannot join this lobby.', color=Color.from_str('#b30707')))
    else:
      p = next((p for p in g.teama.players if p.id == user.id), None)
      if user.id in g.repIds:g.repIds.remove(user.id)
      if p:
        g.teama.players.pop(g.teama.players.index(p))
      else:
        p = next((p for p in g.teamb.players if p.id == user.id), None) 
        if p:g.teamb.players.pop(g.teamb.players.index(p))
      g.mitigatePlayers()
      g.bannedUsers.append(user.id)
      await ctx.send(embed= Embed(title=f'{user} Banned.', description=f'{user} has been banned and cannot join this lobby.', color=Color.from_str('#b30707')))
      if user.id == ctx.bot.owner_id:await ctx.bot.postKhawiData(data= {"status": "exited","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.lobbyCreatedAt*1000)} ,"party": {'id': g.gameId, 'size': [2,len(g.players)]}})
    
  @commands.command(aliases= ['fuck'],extras={'usableBy': 'Host only.'}, description= 'Kick a player from the lobby, only usable before start.')
  async def kick(self, ctx, user: discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id:
      return await ctx.send(embed= Embed(title='Host Only', description='This command is only intended to be run by host.', color=Color.from_str('#b30707')))
    elif user.id == ctx.author.id:
      return await ctx.send(embed= Embed(title="Can't Kick", description='You cannot Kick yourself.', color=Color.from_str('#b30707')))
    elif user.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title=f'{user} not in Game.', description='User is already not playing.', color=Color.from_str('#b30707')))
    elif g.started:return await ctx.send(embed= Embed(title='Can\'t be used after start.', description='This command can\'t be used after the commencement of the game.', color=Color.from_str('#b30707')))
    p = next((p for p in g.teama.players if p.id == user.id), None)
    if user.id in g.repIds:g.repIds.remove(user.id)
    if p:
      g.teama.players.pop(g.teama.players.index(p))
    else:
      p = next((p for p in g.teamb.players if p.id == user.id), None) 
      if p:g.teamb.players.pop(g.teamb.players.index(p))
    g.mitigatePlayers()
    await ctx.send(f'{user} has been kicked off from the game')
    if user.id == ctx.bot.owner_id :await ctx.bot.postKhawiData(data= {"status": "exited","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.lobbyCreatedAt*1000)} ,"party": {'id': g.gameId, 'size': [2,len(g.players)]}})
    
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
    text = f"### {user}'s Score\n"
    if bat:text += f"**Batting:** {bat}\n"
    if bowl:text += f"**Bowling:** {bowl}"
    container.add_item(ui.TextDisplay(text))
    if timeline:
      container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
      container.add_item(ui.TextDisplay(" • ".join([f'**{t}**' for t in timeline])))
    if tookWickets:
      container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
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
  @commands.command(aliases= ['hltma', 'tl'], description= 'Check how much time is left before bot automatically clears this lobby.')
  async def timeleft(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.started or len(g.players) >= 6:
      return await ctx.send(embed= Embed(title='Bot won\'t delete this', description='Either the games has commenced or lobby has 6 or more players, in both cases, it won\'t be deleted.', color=Color.from_str('#b30707')))
    inSeconds = int(1800 - (time.time() - g.lobbyCreatedAt))
    if inSeconds >= 60:
      humanReadable = f"in {int(inSeconds//60)} minutes & {int(inSeconds % 60)} seconds"
    else:
      humanReadable  = f"in {inSeconds} seconds"
    await ctx.send(f'This game will be deleted at <t:{int(g.lobbyCreatedAt + 1800)}:F> ({humanReadable})')
  @commands.command(aliases= [], description= 'Get the link for live score message.')
  async def live(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if not g.started or not g.updateMsg:
      return await ctx.send(embed= Embed(title='Waiting for Game to Start', description='Game is yet to begin.', color=Color.from_str('#b30707')))
    await ctx.send(f"**[Update Message]({g.updateMsg.jump_url})**")
  #@commands.command(aliases= ['fo'], description= 'Forfiet the game.', extras={'usableBy': 'Captains only.'})
  async def forfiet(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if not g.started:return await ctx.send(embed= Embed(title='Match not started', description='Bro wants to forfiet it before start.', color=Color.from_str('#b30707')))
    if ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Captain Only', description='This command is only intended to be run by captains.', color=Color.from_str('#b30707')))
    requestingTeam = g.teama if ctx.author.id == g.teama.captain.id else g.teamb
    buttons = [Button('Yes',discord.ButtonStyle.green,otherTeam.captain.id), Button('No',discord.ButtonStyle.red ,otherTeam.captain.id)]
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"<@{requestingTeam.captain.id}> **are you in your senses to forfiet the game??**\n-# Stats will be counted anyways."))
    container.add_item(actionRow)
    view.add_item(container)
    await ctx.send(view=view)
    await view.wait()
    if view.value == "Yes":
      g.forfietedById = requestingTeam.id
      await ctx.send("**Match forfieted**")
    #await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['dr'], description= 'Offer the draw to the opposing captain.', extras={'usableBy': 'Captains only.'})
  async def drawrequest(self, ctx):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if not g.started:return await ctx.send(embed= Embed(title='Match not started', description='Bro wants to draw it before start.', color=Color.from_str('#b30707')))
    if ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Captain Only', description='This command is only intended to be run by captains.', color=Color.from_str('#b30707')))
    requestingTeam = g.teama if ctx.author.id == g.teama.captain.id else g.teamb
    otherTeam = g.teamb if ctx.author.id == g.teama.captain.id else g.teama
    buttons = [Button('Yes',discord.ButtonStyle.green,otherTeam.captain.id), Button('No',discord.ButtonStyle.red ,otherTeam.captain.id)]
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"<@{otherTeam.captain.id}> **{requestingTeam.name}** is requesting for a draw, do you agree?"))
    container.add_item(actionRow)
    view.add_item(container)
    await ctx.send(view=view)
    await view.wait()
    if view.value == "Yes":
      g.drawnByAgreement = True
      await ctx.send("**Draw request accepted**")
      if ctx.author.id == ctx.bot.owner_id or ctx.bot.owner_id in [p.id for p in g.players]:await ctx.bot.postKhawiData(data= {"status": "exited","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.lobbyCreatedAt*1000)} ,"party": {'id': g.gameId, 'size': [len(g.players,18)]}})
          
    #await ctx.send(view=g.showPlayers())
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
  @commands.command(aliases= ['sub'],description= 'Substitute a player with another player.', extras={'usableBy': 'Captains only.'})
  async def impact(self, ctx, playerA:discord.User, playerB: discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if not g.started:
      return await ctx.send(embed= Embed(title='Cannot use before start', description='This command is only intended to be run after game has commenced.', color=Color.from_str('#b30707')))
    elif ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Captain Only', description='This command is only intended to be run by captains.', color=Color.from_str('#b30707')))
    elif playerA.id not in [p.id for p in g.players]:
      return await ctx.send(embed= Embed(title='Player not in Game', description=f'{playerA} is not playing in this channel.', color=Color.from_str('#b30707')))
    elif playerB.id in [p.id for p in g.players]:
      return await ctx.send(embed= Embed(title='Player in Game', description=f'{playerB} is already playing in this channel.', color=Color.from_str('#b30707')))
    elif playerA.id == ctx.author.id:
      return await ctx.send(embed= Embed(title='You can\'t be subbed off', description=f'Captains cannot sub themselves.', color=Color.from_str('#b30707')))
    team = g.teama if ctx.author.id == g.teama.captain.id else g.teamb
    inn = g.currentInning
    if (not g.resumed and len(team.subbedOffIds) >= 2) or (g.resumed and len(team.subbedOffIds) >= 4):
      return await ctx.send(embed= Embed(title='Maximum Impact Players Used', description=f'There\'s a limit of 2 (4 if resumed) subs which is reached by {team.name}.', color=Color.from_str('#b30707')))
    elif playerB.id in team.subbedOffIds:
      return await ctx.send(embed= Embed(title='Can\'t sub this player', description=f'You cannot sub a player who has already been subbed off.', color=Color.from_str('#b30707')))
    elif playerA.id in team.subbedInIds:
      return await ctx.send(embed= Embed(title='Can\'t sub this player', description=f'You cannot sub a player who has already been subbed in.', color=Color.from_str('#b30707')))
    if playerA.id in [p.id for p in inn.currentBatters]:
        return await ctx.send(embed= Embed(title='Can\'t sub this player', description=f'You cannot sub a player who is already on crease.', color=Color.from_str('#b30707')))
    if inn.currentBowlers and playerA.id == inn.currentBowlers[0].id:
        return await ctx.send(embed= Embed(title='Can\'t sub this player', description=f'You cannot sub a player who is already on crease.', color=Color.from_str('#b30707')))
    buttons = [Button('Yes',discord.ButtonStyle.green,playerB.id), Button('No',discord.ButtonStyle.red ,playerB.id)]
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    view.add_item(ui.TextDisplay(f"{playerB.mention}"))
    container.add_item(ui.TextDisplay(f"**{team.name}** is requesting you to sub {playerA}, do you agree?"))
    container.add_item(actionRow)
    view.add_item(container)
    await ctx.send(view=view)
    await view.wait()
    if view.value == "Yes":
      if playerB.id in [p.id for p in g.players]:
        return
      g.subAPlayer(playerA, playerB)
      await ctx.send(embed= Embed(title='Impact Player', description=f'**{team.name}** have decided to sub in **{playerB}** for **{playerA}**', color=Color.from_str(team.color)))
      if playerA.id == ctx.bot.owner_id:await ctx.bot.postKhawiData(data= {"status": "exited","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.lobbyCreatedAt*1000)} ,"party": {'id': g.gameId, 'size': [len(g.players), 18]}})
      if playerB.id == ctx.bot.owner_id:await ctx.bot.postKhawiData(data= {"status": "started","image": ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(g.startedAt*1000)} ,"party": {'id': g.gameId, 'size': [len(g.players), 18]}})
      
  @commands.command(aliases= ['np'],description= 'Select next bowler or batter.', extras={'usableBy': 'Captains only.'})
  async def nextplayer(self, ctx, nextP:discord.User = None):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Captain Only', description='This command is only intended to be run by captains.', color=Color.from_str('#b30707')))
    team = g.teama if ctx.author.id == g.teama.captain.id else g.teamb
    inn = g.currentInning
    if nextP is None:
      options=[{'name':p.name,'id':p.id, 'description': g.giveDescription(p.id, batting= True)} for p in inn.battingTeam.players if p.id not in inn.cantBat and p.id not in inn.battingTeam.subbedOffIds] if inn.battingTeam.id == team.id else [{'name':p.name,'id':p.id, 'description': g.giveDescription(p.id, bowling= True)} for p in inn.bowlingTeam.players if (len(inn.currentBowlers) == 0 or p.id != inn.currentBowlers[0].id) and p.id not in g.repIds and p.id not in inn.bowlingTeam.subbedOffIds]
      if len(options) <= 1:return await ctx.send("Nothing to select.")
      view=ui.LayoutView(timeout=30)
      view.value=None
      actionRow = ui.ActionRow().add_item(Selection(ctx.author.id,options,1,'Select Batter' if inn.battingTeam.id == team.id else 'Select Bowler'))
      view.add_item(ui.TextDisplay(f"{ctx.author.mention} Select Batter" if inn.battingTeam.id == team.id else f"{ctx.author.mention} Select Bowler"))
      view.add_item(actionRow)
      view.m = await ctx.send(view=view)
      await view.wait()
      if view.value:
        if inn.battingTeam.id == team.id:
          inn.nextBatterId = int(view.value)
          return
        else:
          inn.nextBowlerId = int(view.value)
          return
    elif not g.started:return await ctx.send(embed= Embed(title='Can\'t be used before start.', description='This command can\'t be used before the commencement of the game.', color=Color.from_str('#b30707')))
    if nextP.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title='Player didn\'t join.', description='They must have joined .', color=Color.from_str('#b30707')))
    if nextP.id not in [p.id for p in team.players]:
      return await ctx.send(f"Bud is so disgusted with his team that he decided to send a player from another team.")
    if inn.battingTeam.id == team.id:
      if nextP.id in inn.cantBat or nextP.id in [b.id for b in inn.currentBatters]:
        return await ctx.send(f"**{nextP}** is either currently batting or has been dismissed, in both cases you have failed ad a captain.")
      elif nextP.id in inn.battingTeam.subbedOffIds:
        return await ctx.send(f"**{nextP}** has been subbed off.")
      inn.nextBatterId = nextP.id
      await ctx.send(f"**{nextP}** will be batting next.")
    else:
      if not inn.currentBowlers:
        return await ctx.send(f"**Hold on a sec**.")
      if nextP.id == inn.currentBowlers[0].id:
        return await ctx.send(f"**{nextP}** is currently bowling bozo.")
      if nextP.id in g.repIds:
        return await ctx.send("Representative players can't bowl.")
      elif nextP.id in inn.bowlingTeam.subbedOffIds:
        return await ctx.send(f"**{nextP}** has been subbed off.")
      inn.nextBowlerId = nextP.id
      return await ctx.send(f"**{nextP}** will be bowling next over.")
  @commands.command(aliases= ['cvc', 'vc'],description= 'Change the vice captain of a team.', extras={'usableBy': 'Captains only.'})
  async def changevicecap(self, ctx, cap:discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Captain Only', description='This command is only intended to be run by host or captains.', color=Color.from_str('#b30707')))
    if cap.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title='Vice Captain not in Game.', description='Vice captain must have joined .', color=Color.from_str('#b30707')))
    team = g.teama if ctx.author.id in [p.id for p in g.teama.players] else g.teamb
    if cap.id not in [p.id for p in team.players]:
      return await ctx.send(embed= Embed(title='Vice Captain not in your team.', description='Vice captain must be in your  team.', color=Color.from_str('#b30707')))
    if cap.id == ctx.author.id:
      return await ctx.send(embed= Embed(title='Vice captain must not be captain already.', description='You can\'t vice captain your team when you are already captain bozo.', color=Color.from_str('#b30707')))
    team.viceCaptain = next(p for p in team.players if p.id == cap.id)
    await ctx.send(f"**{cap}** will be vice captaining {team.name}")
    
    #await ctx.send(view=g.showPlayers())
  @commands.command(aliases= ['cc'],description= 'Change the captain of a team.', extras={'usableBy': 'Host or Captains only.'})
  async def changecap(self, ctx, cap:discord.User):
    if ctx.channel.id not in self.bot.games:
      return await ctx.send(embed= Embed(title='No Game', description='Looks like this channel is not hosting a game at the moment, be a man and host one yourself.', color=Color.from_str('#b30707')))
    g = self.bot.games[ctx.channel.id]
    if g.hostId != ctx.author.id and ctx.author.id not in [g.teama.captain.id, g.teamb.captain.id]:
      return await ctx.send(embed= Embed(title='Host or Captain Only', description='This command is only intended to be run by host or captains.', color=Color.from_str('#b30707')))
    if cap.id not in [p.id for p in g.players]:return await ctx.send(embed= Embed(title='New Captain not in Game.', description='New captain must have joined .', color=Color.from_str('#b30707')))
    if g.hostId == ctx.author.id:
      team = g.teama if cap.id in [p.id for p in g.teama.players] else g.teamb
      team.captain = next(p for p in team.players if p.id == cap.id)
      if cap.id == team.viceCaptain.id:team.viceCaptain = random.choice([p for p in team.players if p.id != cap.id])
      await ctx.send(f"{cap} will be captaining {team.name}")
    else:
      team = g.teama if ctx.author.id in [p.id for p in g.teama.players] else g.teamb
      if cap.id not in [p.id for p in team.players]:
        return await ctx.send(embed= Embed(title='New Captain not in your team.', description='New captain must be in your  team.', color=Color.from_str('#b30707')))
      team.captain = next(p for p in team.players if p.id == cap.id)
      if cap.id == team.viceCaptain.id:team.viceCaptain = random.choice([p for p in team.players if p.id != cap.id])
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