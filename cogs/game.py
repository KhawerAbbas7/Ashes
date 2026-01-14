import random, traceback
from cogs.views import *
from discord import ui 
from collections import deque
import asyncio
import discord
class BattingInning():
  def __init__(self,player):
    self.player=player
    self.name = player.name
    self.runs=0
    self.balls=0
    self.consecutiveDots=0
    self.BoundaryThisOver= False
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
    self.timeline = deque(maxlen=13)
    self.declared = False
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
    self.v = None
    self.followOnTeam=None
    self.followOnLimit=75
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @property 
  def currentInning(self): return self.innings[-1]
  @property 
  def players(self): return self.teama.players + self.teamb.players
  def teamTotal(self,team):return sum(i.runs for i in self.innings if i.battingTeam==team)
  def inningsByTeam(self,team):return [i for i in self.innings if i.battingTeam==team]
  def swap(self,idx1,idx2):
    if self.started or idx1==idx2:return False
    combined=self.players
    if idx1<0 or idx2<0 or idx1>=len(combined) or idx2>=len(combined):return False
    combined[idx1],combined[idx2]=combined[idx2],combined[idx1]
    self.mitigatePlayers()
    return True
  async def checkFollowOn(self):
    if len(self.innings)==2:
      first=self.innings[0].battingTeam
      second=self.innings[1].battingTeam
      lead=self.teamTotal(first)-self.teamTotal(second)
      if lead>=self.followOnLimit:
        view=ui.LayoutView(timeout=60)
        view.value=None
        inn=self.currentInning
        captain=inn.bowlingTeam.captain
        buttons = [Button('Yes',discord.ButtonStyle.green,captain.id), Button('No',discord.ButtonStyle.red ,captain.id)]
        container = ui.Container(accent_color = discord.Colour.from_str("#9b0a82"))
        view.add_item(ui.TextDisplay(f"{captain.mention}"))
        actionRow = ui.ActionRow()
        for b in buttons: actionRow.add_item(b)
        container.add_item(ui.TextDisplay(f"Follow on is currently available, **{inn.bowlingTeam.name}** Lead by {Lead} runs. Would you like to enforce follow-on?"))
        container.add_item(actionRow)
        view.add_item(container)
        await self.ctx.send(view=view)
        await view.wait()
        if view.value in [None, 'No']:
          await self.ctx.send("**Follow-on not enforced**")
        else:
          await self.ctx.send("**Follow-on enforced**")
          self.followOnTeam=second 
  def matchStatus(self):
    w = self.checkForWinner()
    if w: return w
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
    batPrev=batTotal-inn.runs
    target=(bowlTotal-batPrev)+1
    need=target-inn.runs
    if need>0:return f"{bat.name} need {need} runs to win"
    return f"{bat.name} have won by {len(bat.players)-1-inn.wickets} wickets"
  def checkForWinner(self):
    if len(self.innings)<2:return None
    last=self.currentInning
    bat=last.battingTeam
    bowl=last.bowlingTeam
    batTotal=self.teamTotal(bat)
    bowlTotal=self.teamTotal(bowl)
    if not last.currentBatters and len(last.cantBat)==len(bat.players):
      if self.followOnTeam==bat:
        lead=bowlTotal-batTotal
        if lead>0:return f"{bowl.name} have won by an innings and {lead} runs"
      if len(self.innings)==4:
        return f"{bowl.name} have won by {batTotal-bowlTotal} runs"
    if len(self.innings)==4:
      batPrev=batTotal-last.runs
      target=(bowlTotal-batPrev)+1
      if last.runs>=target:
        return f"{bat.name} have won by {len(bat.players)-1-last.wickets} wickets"
    return None
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
  def buildFullInningCard(self,container,inn):
    container.add_item(ui.TextDisplay(f"### {inn.battingTeam.name} {inn.runs}/{inn.wickets}"))
    btxt="**Batting**\n```py\n"
    for p,i in inn.batters.items():
      out="" if p in inn.currentBatters or i.balls==0 else ""
      btxt+=f"{p.name.ljust(16)}{str(i.runs).rjust(3)}({i.balls})\n"
    btxt+="```"
    container.add_item(ui.TextDisplay(btxt))
    bowl="**Bowling**\n```py\n"
    for p,i in inn.bowlers.items():
      bowl+=f"{p.name.ljust(16)}{i.runsConceded}/{i.wickets} {str(self.ballsToOvers(i.balls)).rjust(5)}\n"
    bowl+="```"
    container.add_item(ui.TextDisplay(bowl))
    container.add_item(ui.TextDisplay(self.matchStatus()))
  def buildSummaryCard(self,container):
    container.add_item(ui.TextDisplay("### Match Summary"))
    for inn in self.innings:
      container.add_item(ui.TextDisplay(f"**{inn.battingTeam.name} {inn.runs}/{inn.wickets}**"))
      topBat=sorted(inn.batters.items(),key=lambda x:x[1].runs,reverse=True)[:2]
      topBowl=sorted(inn.bowlers.items(),key=lambda x:x[1].wickets,reverse=True)[:2]
      b="Batting: "+" , ".join(f"{p.name} {i.runs}({i.balls})" for p,i in topBat if i.balls>0)
      bw="Bowling: "+" , ".join(f"{p.name} {i.wickets}/{i.runsConceded}" for p,i in topBowl if i.balls>0)
      container.add_item(ui.TextDisplay(b))
      container.add_item(ui.TextDisplay(bw))
    w = self.checkForWinner()
    if w: 
      container.add_item(ui.TextDisplay(w))
  async def sendScores(self,mode="full"):
    inn=self.currentInning
    view=ui.LayoutView(timeout=None)
    container=ui.Container(accent_color=discord.Colour.from_str("#0a769b"))
    container.add_item(ui.TextDisplay(f"### Inning {inn.inningNo}"))
    if mode=="full":self.buildFullInningCard(container,inn)
    else:self.buildSummaryCard(container)
    view.add_item(container)
    await self.ctx.send(view=view)
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
    other = self.teama if picker == self.teama else self.teamb
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
  def score(self, returnContainer=False):
    view = ui.LayoutView(timeout=30)
    container = ui.Container(accent_color=discord.Colour.from_str("#0a9b65"))
    t = {}
    for i in self.innings:
      s = f"{i.runs}/{i.wickets}"
      if i.inningNo == self.currentInning.inningNo:
        s += f" ({self.ballsToOvers(i.balls)})"
      if i.battingTeam.name in t: t[i.battingTeam.name] += f"& {s}"
      else: t[i.battingTeam.name] = s
    Score = "\n".join(f"**`{k.ljust(18)}{v}`**" for k,v in t.items())
    if returnContainer is False:
      container.add_item(ui.Section(ui.TextDisplay(Score), accessory=DeclareBTN()))
    else: container.add_item(ui.TextDisplay(Score))
    header = f"**` {'Batters'.ljust(16)}{'R'.rjust(4)}{'B'.rjust(4)}{'SR'.rjust(9)}`**"
    rows=["```py\n"]+[f"{b.name.ljust(16)}{str(self.currentInning.batters[b].runs).rjust(4)}{str(self.currentInning.batters[b].balls).rjust(4)}{str(self.currentInning.batters[b].sr).rjust(9)}\nCan Do 0: {'✅' if self.currentInning.batters[b].consecutiveDots!=3 else '❌'}  Can Do 4,6: {'✅' if self.currentInning.batters[b].BoundaryThisOver is not True else '❌'}" for b in self.currentInning.currentBatters]+["\n```"]
    BatterScore = "\n".join([header] + rows)
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(BatterScore))
    header = f"**` {'Bowlers'.ljust(16)}{'R'.rjust(4)}{'W'.rjust(4)}{'O'.rjust(9)}`**"
    rows = ["```py\n"] + [f"{b.name.ljust(16)}{str(self.currentInning.bowlers[b].runsConceded).rjust(4)}{str(self.currentInning.bowlers[b].wickets).rjust(4)}{str(self.ballsToOvers(self.currentInning.bowlers[b].balls)).rjust(9)}" for b in self.currentInning.currentBowlers] + ["\n```"]
    BowlersScore = "\n".join([header] + rows)
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(BowlersScore))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    if len(self.currentInning.timeline) > 0:
      container.add_item(ui.TextDisplay(" • ".join([f'**{t}**' for t in self.currentInning.timeline])))
    container.add_item(ui.TextDisplay(f"-# {self.matchStatus()}"))
    view.add_item(container)
    return view if returnContainer is False else container
  def nextBattingTeam(self):
    if not self.innings: return self.batFirstTeam
    if self.followOnTeam is not None and self.innings[-1].inningNo == 2:
      return 
    return self.teamb if self.innings[-1].battingTeam == self.teama else self.teama
  async def selectBowler(self):
    inn=self.currentInning
    captain=inn.bowlingTeam.captain
    options=[{'name':p.name,'id':p.id} for p in inn.bowlingTeam.players if len(inn.currentBowlers) == 0 or p.id != inn.currentBowlers[0].id]
    view=ui.LayoutView(timeout=60)
    view.value=None
    actionRow = ui.ActionRow().add_item(Selection(captain.id,options,1,'Select Bowler'))
    view.add_item(ui.TextDisplay(f"{captain.mention} select bowler"))
    view.add_item(actionRow)
    m = await self.ctx.send(view=view)
    view.m= m
    await view.wait()
    pid=view.value or random.choice(options)['id']
    inn.currentBowlers.appendleft(next(p for p in inn.bowlingTeam.players if p.id==pid))
  async def selectOpeners(self):
    inn=self.currentInning
    captain=inn.battingTeam.captain
    options=[{'name':p.name,'id':p.id} for p in inn.battingTeam.players]
    view=ui.LayoutView(timeout=60)
    view.value=None
    actionRow = ui.ActionRow().add_item(Selection(captain.id,options,2,'Select Openers'))
    view.add_item(ui.TextDisplay(f"{captain.mention} select openers"))
    view.add_item(actionRow)
    view.m = await self.ctx.send(view=view)
    await view.wait()
    ids=view.value or random.sample([i['id'] for i in options], k= 2)
    inn.currentBatters=[next(p for p in inn.battingTeam.players if p.id == ids[k]) for k in range(2)]
    inn.cantBat.extend(ids)
  async def selectNextBatter(self):
    inn=self.currentInning
    captain=inn.battingTeam.captain
    used={p.id for p in inn.currentBatters}
    options=[{'name':p.name,'id':p.id} for p in inn.battingTeam.players if p.id not in inn.cantBat]
    view=ui.LayoutView(timeout=60)
    view.value=None
    actionRow = ui.ActionRow().add_item(Selection(captain.id,options,1,'Select Next Batter'))
    view.add_item(ui.TextDisplay(f"{captain.mention} select next batter"))
    view.add_item(actionRow)
    await self.ctx.send(view=view)
    await view.wait()
    pid=view.value or random.choice(options)['id']
    inn.currentBatters.insert(0,next(p for p in inn.battingTeam.players if p.id==pid))
    inn.cantBat.append(pid)
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
    bowler=inn.currentBowlers[0]
    striker_p=inn.batters[striker]
    bowler_p=inn.bowlers[bowler]
    cando0=striker_p.consecutiveDots!=3
    if cando0 and not striker_p.BoundaryThisOver:
      allowed={'0','1','2','3','4','6'}
    elif cando0 and striker_p.BoundaryThisOver:
      allowed={'0','1','2','3'}
    elif not cando0 and striker_p.BoundaryThisOver:
      allowed={'1','2','3'}
    else:
      allowed={'1','2','3','4','6'}
    def checkBatter(m): return m.author.id==striker.id and m.guild is None and m.content in allowed
    def checkBowler(m): return m.author.id==bowler.id and m.guild is None and m.content in ['1','2','3','4','6']
    battxt = f"Send your shot ({','.join(allowed)}) within 20s"
    batview = ui.LayoutView(timeout=None)
    batview.add_item(ui.TextDisplay(battxt))
    batview.add_item(self.score(True))
    bowlview = ui.LayoutView(timeout=None)
    bowlview.add_item(ui.TextDisplay("Send your delivery (1,2,3,4,6) within 20s"))
    bowlview.add_item(self.score(True))
    await striker.send(view=batview)
    await bowler.send(view=bowlview)
    while True:
      bat_task=asyncio.create_task(self.ctx.bot.wait_for("message",check=checkBatter))
      bowl_task=asyncio.create_task(self.ctx.bot.wait_for("message",check=checkBowler))
      done,pending=await asyncio.wait([bat_task,bowl_task],timeout=20)
      bat_ok=bat_task in done and not bat_task.cancelled()
      bowl_ok=bowl_task in done and not bowl_task.cancelled()
      if not bat_ok and not bowl_ok:
        for t in pending: t.cancel()
        await self.ctx.send("Both the bowler and batter were afk, replaying the ball")
        await asyncio.sleep(0.3)
        await striker.send(f"You didn't respond in time. Replaying the ball.\n{battxt}")
        await asyncio.sleep(0.3)
        await bowler.send("You didn't respond in time. Replaying the ball.\nSend your delivery (1,2,3,4,6) within 20s")
        continue
      elif not bat_ok and bowl_ok:
        for t in pending: t.cancel()
        await self.ctx.send("Batter was afk, replaying the ball")
        await asyncio.sleep(0.3)
        await striker.send(f"You didn't respond in time. Replaying the ball.\n{battxt}")
        await asyncio.sleep(0.3)
        await bowler.send("Batter didn't respond in time. Replaying the ball.\nSend your delivery (1,2,3,4,6) within 20s")
        continue
      elif bat_ok and not bowl_ok:
        for t in pending: t.cancel()
        await self.ctx.send("Bowler was afk, replaying the ball")
        await asyncio.sleep(0.3)
        await striker.send(f"Bowler didn't respond in time. Replaying the ball.\n{battxt}")
        await asyncio.sleep(0.3)
        await bowler.send("You didn't respond in time. Replaying the ball.\nSend your delivery (1,2,3,4,6) within 20s")
        continue
      bat=int(bat_task.result().content)
      bowl=int(bowl_task.result().content)
      for t in pending: t.cancel()
      break
    inn.balls+=1
    striker_p.balls+=1
    bowler_p.balls+=1
    if bat!=0: striker_p.consecutiveDots=0
    else: striker_p.consecutiveDots+=1
    if bat==bowl:
      v = ui.LayoutView(timeout=None)
      c = ui.Container(accent_color=discord.Colour.from_str("#9b0a0a"))
      c.add_item(ui.TextDisplay(f"# It's A Wicket!!\n**{striker.name}** {striker_p.runs} ({striker_p.balls})\n**{bowler.name}** {bowler_p.runsConceded}/{bowler_p.wickets+1} ({self.ballsToOvers(bowler_p.balls)})\n**Number: {bat}**"))
      v.add_item(c)
      await self.ctx.send(view=v)
      await asyncio.sleep(0.3)
      await striker.send(f"Your score: \n{striker_p.runs} ({striker_p.balls})You are out!!\nBowler did {bowl}")
      await asyncio.sleep(0.3)
      await bowler.send(f"Their score: \n{striker_p.runs} ({striker_p.balls})\nThey are out!!\nBatter did {bat}")
      await asyncio.sleep(0.3)
      inn.timeline.append("W")
      inn.wickets+=1
      bowler_p.wickets+=1
      inn.currentBatters.pop(0)
      if len(inn.cantBat) < len(inn.battingTeam.players):
        await self.selectNextBatter()
      elif not inn.currentBatters:
        return 'Inning Over'
    else:
      if bat in [4,6]:
        striker_p.BoundaryThisOver = True
      inn.runs+=bat
      striker_p.runs+=bat
      bowler_p.runsConceded+=bat
      await striker.send(f"Your score: \n{striker_p.runs} ({striker_p.balls})\nBowler did {bowl}")
      await asyncio.sleep(0.3)
      await bowler.send(f"Their score: \n{striker_p.runs} ({striker_p.balls})\nBatter did {bat}")
      inn.timeline.append(f"{bat}")
      if bat%2==1 and len(inn.currentBatters) > 1:
        inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
    if inn.balls%6==0:
      for b in inn.currentBatters:
        inn.batters[b].BoundaryThisOver = False
      if len(inn.currentBatters) > 1:
        inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
      await self.selectBowler()

  async def start(self):
    try:
      self.started = True 
      for i in range(4):
        w = self.checkForWinner()
        if w: break
        await self.startInning()
        print('Started')
        while True:
          g = await self.getInputs()
          if self.v:
            self.v.stop()
          self.v = self.score()
          
          await self.ctx.send(view=self.v)
          w = self.checkForWinner()
          if g != None or w:
            await self.sendScores("full")
            await asyncio.sleep(3)
            await self.checkFollowOn()
            break
          if self.currentInning.declared:
            await self.ctx.send("**Inning Declared**")
            await asyncio.sleep(1)
            await self.sendScores("full")
            await asyncio.sleep(0.3)
            await self.checkFollowOn()
            await asyncio.sleep(3)
            break
      await self.sendScores("summary")
    except Exception as e:
      traceback.print_exc()