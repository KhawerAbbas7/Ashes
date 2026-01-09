import random
from cogs.views import *
from discord import ui 
from collections import deque
import asyncio
class BattingInning():
  def __init__(self,player):
    self.player=player
    self.name = player.name
    self.runs=0
    self.balls=0
  @property
  def sr(self): return round((self.runs/self.balls)*100,2) if self.balls else 0.0
class BowlingInning():
  def __init__(self,player):
    self.player=player
    self.name=player.name
    self.runsConceded=0
    self.wickets=0
    self.balls=0
class Inning():
  def __init__(self):
    self.inningNo = None 
    self.battingTeam = None 
    self.bowlingTeam = None 
    self.batters = {}
    self.bowlers = {} 
    self.cantBat= []
    self.currentBatters = []
    self.currentBowlers = deque(maxlen=2)
    self.runs = 0
    self.wickets = 0
    self.balls = 0
class Team():
  def __init__(self, name: str = 'Team A', id: int = 1):
    self.name = name
    self.id = id
    self.captain = None 
    self.players = []
  def checkForCaptain(self):
    if self.players and (self.captain is None or self.captain not in self.players):
      self.captain = random.choice(self.players)
class Player():
  def __init__(self):
    self.user,self.name, self.id, self.mention= 0,0,0,0
  async def send(self,content=None, **kwargs):
    for _ in range(3):
      try:
        return await self.user.send(content, **kwargs)
      except (discord.HTTPException):await asyncio.sleep(1)
  def fromUser(self,user):
    self.user,self.name, self.id, self.mention =user, user.name, user.id, user.mention
    return self
class Game():
  def __init__(self, ctx):
    self.ctx = ctx
    self.hostId = ctx.author.id
    self.teama = Team('Team A')
    self.teamb = Team('Team B', 2)
    self.started = False 
    self.batFirstTeam = None
    self.innings = []
    self.followOnTeam=None
    self.followOnLimit=100
  def teamTotal(self,team):return sum(i.runs for i in self.innings if i.battingTeam==team)
  def inningsByTeam(self,team):return [i for i in self.innings if i.battingTeam==team]
  def checkFollowOn(self):
    if len(self.innings)==2:
      first=self.innings[0].battingTeam
      second=self.innings[1].battingTeam
      lead=self.teamTotal(first)-self.teamTotal(second)
      if lead>=self.followOnLimit:self.followOnTeam=second 
  def matchStatus(self):
    inn=self.currentInning
    bat=inn.battingTeam
    bowl=inn.bowlingTeam
    batTotal=self.teamTotal(bat)
    bowlTotal=self.teamTotal(bowl)
    innsBat=len(self.inningsByTeam(bat))
    innsBowl=len(self.inningsByTeam(bowl))
    if len(self.innings)==1:return f"{bat.name} are batting"
    if len(self.innings)<4:
      diff=batTotal-bowlTotal
      if diff>0:return f"{bat.name} lead by {diff} runs"
      if diff<0:return f"{bat.name} trail by {abs(diff)} runs"+(" (follow-on)" if self.followOnTeam==bat else "")
      return "Scores are level"
    target=bowlTotal+1
    need=target-inn.runs
    if need>0:return f"{bat.name} need {need} runs to win"
    return f"{bat.name} have won by {len(bat.players)-1-inn.wickets} wickets"
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @property 
  def currentInning(self): return self.innings[-1]
  @property 
  def players(self): return self.teama.players + self.teamb.players
  def mitigatePlayers(self):
    combined= self.players
    total = len(combined)
    mid = total // 2
    extra = total % 2
    self.teama.players = combined[:mid + extra]
    self.teamb.players = combined[mid + extra:]
    self.teama.checkForCaptain();self.teamb.checkForCaptain()
  def join(self, user):
    self.teama.players.append(Player().fromUser(user))
    self.mitigatePlayers()
  def kickAPlayer(self, index):
    combined= self.players 
    del combined[index]
    self.mitigatePlayers()
  def showPlayers(self):
    teamaP = ""
    teambP = ""
    for i,p in enumerate(self.teama.players,1):teamaP += f"{i}. {p.name} {'(C)' if p.id == self.teama.captain.id else ''} {'(H)' if p.id == self.hostId else ''}\n"
    for i,p in enumerate(self.teamb.players,len(self.teama.players)+1):teambP += f"{i}. {p.name} {'(C)' if p.id == self.teamb.captain.id else ''} {'(H)' if p.id == self.hostId else ''}\n"
    view = ui.LayoutView(timeout= None)
    container = ui.Container(accent_color = discord.Colour.from_str("#0a9b65"))
    container.add_item(ui.TextDisplay(f"### {self.teama.name}\n{teamaP}"))
    container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"### {self.teamb.name}\n{teambP}"))
    view.add_item(container)
    return view
  async def toss(self):
    if not self.teamb.captain: return 
    picker = random.choice([self.teama, self.teamb])
    other = self.teama if picker == self.teamb else self.teama 
    buttons = [Button('Heads',discord.ButtonStyle.green,picker.captain.id), Button('Tails',discord.ButtonStyle.red ,picker.captain.id)]
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    view.add_item(ui.TextDisplay(f"{picker.captain.mention}"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"Make your call!!"))
    container.add_item(actionRow)
    view.add_item(container)
    await self.ctx.send(view=view)
    await view.wait()
    if view.value:
      winner = picker if view.value == random.choice(['Heads', 'Tails']) else other
      buttons = [Button('Bat',discord.ButtonStyle.green,winner.captain.id), Button('Bowl',discord.ButtonStyle.green,winner.captain.id)]
      view = ui.LayoutView(timeout= 60)
      view.value = None
      container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
      view.add_item(ui.TextDisplay(f"{winner.captain.mention}"))
      actionRow = ui.ActionRow()
      for b in buttons: actionRow.add_item(b)
      container.add_item(ui.TextDisplay(f"Make your call!!"))
      container.add_item(actionRow)
      view.add_item(container)
      await self.ctx.send(view=view)
      await view.wait()
      if view.value:
        other = self.teamb if winner.id == 1 else self.teama
        await self.ctx.send(f"**{winner.name} have won the toss and have elected to {view.value} first**")
        if view.value == 'Bat':self.batFirstTeam = winner
        else:self.batFirstTeam = other
  def score(self):
    view = ui.LayoutView(timeout=None)
    container = ui.Container(accent_color=discord.Colour.from_str("#0a9b65"))
    t = {}
    for i in self.innings:
      s = f"{i.runs}/{i.wickets}"
      if i.inningNo == self.currentInning.inningNo:
        s += f" ({self.ballsToOvers(i.balls)})"
      if i.battingTeam.name in t: t[i.battingTeam.name] += f"& {s}"
      else: t[i.battingTeam.name] = s
    Score = "\n".join(f"**`{k.ljust(18)}{v}`**" for k,v in t.items())
    container.add_item(ui.TextDisplay(Score))
    header = f"**` {'Batters'.ljust(16)}{'R'.rjust(4)}{'B'.rjust(4)}{'SR'.rjust(9)}`**"
    rows = ["```py\n"] + [f"{b.name.ljust(16)}{str(self.currentInning.batters[b].runs).rjust(4)}{str(self.currentInning.batters[b].balls).rjust(4)}{str(self.currentInning.batters[b].sr).rjust(9)}" for b in self.currentInning.currentBatters] + ["\n```"]
    BatterScore = "\n".join([header] + rows)
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(BatterScore))
    header = f"**` {'Bowlers'.ljust(16)}{'R'.rjust(4)}{'W'.rjust(4)}{'O'.rjust(9)}`**"
    rows = ["```py\n"] + [f"{b.name.ljust(16)}{str(self.currentInning.bowlers[b].runsConceded).rjust(4)}{str(self.currentInning.bowlers[b].wickets).rjust(4)}{str(self.ballsToOvers(self.currentInning.bowlers[b].balls)).rjust(9)}" for b in self.currentInning.currentBowlers] + ["\n```"]
    BowlersScore = "\n".join([header] + rows)
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(BowlersScore))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(f"-# {self.matchStatus()}"))
    view.add_item(container)
    return view
  def nextBattingTeam(self):
    if not self.innings: return self.batFirstTeam
    return self.teamb if self.innings[-1].battingTeam == self.teama else self.teama
  async def selectBowler(self):
    inn=self.currentInning
    captain=inn.bowlingTeam.captain
    options=[{'name':p.name,'id':p.id} for p in inn.bowlingTeam.players if len(inn.currentBowlers) == 0 or p.id != inn.currentBowlers[0]]
    view=ui.LayoutView(timeout=60)
    view.value=None
    actionRow = ui.ActionRow().add_item(Selection(captain.id,options,1,'Select Bowler'))
    view.add_item(ui.TextDisplay(f"{captain.mention} select bowler"))
    view.add_item(actionRow)
    await self.ctx.send(view=view)
    await view.wait()
    pid=view.value or random.choice(options)['id']
    inn.currentBowlers.insert(0,next(p for p in inn.bowlingTeam.players if p.id==pid))
  async def selectOpeners(self):
    inn=self.currentInning
    captain=inn.battingTeam.captain
    options=[{'name':p.name,'id':p.id} for p in inn.battingTeam.players]
    view=ui.LayoutView(timeout=60)
    view.value=None
    actionRow = ui.ActionRow().add_item(Selection(captain.id,options,2,'Select Openers'))
    view.add_item(ui.TextDisplay(f"{captain.mention} select openers"))
    view.add_item(actionRow)
    await self.ctx.send(view=view)
    await view.wait()
    ids=view.value or random.sample([i['id'] for i in options], k= 2)
    inn.currentBatters=[p for p in inn.battingTeam.players if p.id in ids]
    inn.cantBat.extend(ids)
  async def selectNextBatter(self):
    inn=self.currentInning
    captain=inn.battingTeam.captain
    used={p.id for p in inn.currentBatters}
    options=[{'name':p.name,'id':p.id} for p in inn.battingTeam.players if p.id not in i.cantBat]
    view=ui.LayoutView(timeout=60)
    view.value=None
    actionRow = ui.ActionRow().add_item(Selection(captain.id,options,1,'Select Next Batter'))
    view.add_item(ui.TextDisplay(f"{captain.mention} select next batter"))
    view.add_item(actionRow)
    await self.ctx.send(view=view)
    await view.wait()
    pid=view.value or random.choice(options)['id']
    inn.currentBatters.insert(0,next(p for p in inn.battingTeam.players if p.id==pid))
  async def startInning(self):
    no=len(self.innings)+1
    bat=self.nextBattingTeam()
    bowl=self.teamb if bat==self.teama else self.teama
    inn=Inning()
    inn.inningNo=no
    inn.battingTeam=bat
    inn.bowlingTeam=bowl
    for p in bat.players: inn.batters[p]=BattingInning(p)
    for p in bowl.players: inn.bowlers[p]=BowlingInning(p)
    self.innings.append(inn)
    await asyncio.gather(self.selectBowler(),self.selectOpeners())
  async def getInputs(self):
    inn=self.currentInning
    striker=inn.currentBatters[0]
    non_striker=inn.currentBatters[1]
    bowler=inn.currentBowlers[0]
    striker_p=inn.batters[striker]
    bowler_p=inn.bowlers[bowler]
    def checkBatter(m):return m.author.id==striker.id and m.guild is None and m.content in ['0','1','2','3','4','5','6']
    def checkBowler(m):return m.author.id==bowler.id and m.guild is None and m.content in ['1','2','3','4','5','6']
    await striker.send("Send your shot (0-6) within 20s")
    await bowler.send("Send your delivery (1-6) within 20s")
    try:
      bat_msg=await asyncio.wait_for(self.ctx.bot.wait_for("message",check=checkBatter),timeout=20)
      bat=int(bat_msg.content)
    except asyncio.TimeoutError:
      bat=random.choice([0,1,2,3,4,6])
    try:
      bowl_msg=await asyncio.wait_for(self.ctx.bot.wait_for("message",check=checkBowler),timeout=20)
      bowl=int(bowl_msg.content)
    except asyncio.TimeoutError:
      bowl=random.choice([1,2,3,4,5,6])
    inn.balls+=1
    striker_p.balls+=1
    bowler_p.balls+=1
    if bat==bowl:
      inn.wickets+=1
      bowler_p.wickets+=1
      inn.currentBatters.pop(0)
      if inn.wickets < len(inn.battingTeam.players) - 1:
        await self.selectNextBatter()
      else: return 'Inning Over'
    else:
      inn.runs+=bat
      striker_p.runs+=bat
      bowler_p.runsConceded+=bat
      if bat%2==1:
        inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
    if inn.balls%6==0:
      inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
      await self.selectBowler()
    
  async def start(self):
    self.started = True 
    for i in range(4):
      await self.startInning()
      while True:
        g = await self.getInputs()
        await self.ctx.send(view=self.score())
        if g != None: break