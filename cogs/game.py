import random, traceback,os, time
from cogs.views import *
from discord import ui 
from collections import deque
import asyncio
import discord
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from uuid6 import uuid7
BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
class customCtx():
  def __init__(self,ctx):
    self.ctx = ctx
    self.guild = ctx.guild
    for key, value in vars(ctx).items ():setattr(self, key, value)
  async def send(self,content=None, **kwargs):
    for _ in range(3):
      try:
        return await self.ctx.send(content, **kwargs)
      except:await asyncio.sleep(1)
class BattingInning():
  def __init__(self,player):
    self.player=player
    self.name = player.name
    self.runs=0
    self.balls=0
    self.consecutiveDots=0
    self.BoundaryThisOver= False
    self.AFKs = 0
    self.dismissed = False
    self.timeline = deque(maxlen=13)
  @property
  def sr(self): return round((self.runs/self.balls)*100,2) if self.balls else 0.0
class BowlingInning():
  def __init__(self,player):
    self.player=player
    self.name=player.name
    self.runsConceded=0
    self.wickets=0
    self.balls=0
    self.timeline = deque(maxlen=13)
    self.wicketsDigits = []
    self.AFKs = 0
class Inning():
  def __init__(self):
    self.inningId = str(uuid7())
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
    self.followOn = False
    self.runs = 0
    self.wickets = 0
    self.balls = 0
    self.currentPartnership= [0,0]
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
  def __str__(self): return self.name
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
    self.gameId = str(uuid7())
    self.ctx = customCtx(ctx)
    self.hostId = ctx.author.id
    self.teama = Team('Team A')
    self.teamb = Team('Team B', 2)
    self.started = False 
    self.startedAt = None
    self.batFirstTeam = None
    self.innings = []
    self.ballsData = []
    self.v = None
    self.followOnTeam=None
    self.followOnLimit=75
    self.winner = None
    self.mvp = None
  async def saveData(self):
    await self.ctx.bot.execute("INSERT INTO matches VALUES (?,?,?,?,?,?,?)", (self.gameId, self.ctx.channel.id, self.ctx.guild.id, self.teama.name, self.teamb.name, self.winner, self.mvp.id,))
    data = [(i.inningId, self.gameId, i.runs, i.balls, i.wickets, i.battingTeam.name, i.bowlingTeam.name, 1 if i.declared else 0, 1 if i.followOn else 0,) for i in self.innings]
    placeholders = ",".join(["?"] * len(data[0]))
    await self.ctx.bot.db.executemany(f"INSERT INTO innings VALUES ({placeholders})", data)
    placeholders = ",".join(["?"] * len(self.ballsData[0]))
    await self.ctx.bot.db.executemany(f"INSERT INTO deliveries VALUES ({placeholders})", self.ballsData)
    await self.ctx.bot.db.commit()
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  
  @property
  def matchTotalBalls(self):
    return sum([i.balls for i in self.innings])
  @property 
  def currentInning(self): return self.innings[-1]
  @property 
  def players(self): return self.teama.players + self.teamb.players
  def getDaysAndSessions(self):
    total_overs = float(self.ballsToOvers(self.matchTotalBalls))
    if total_overs < 1: return 1, 1
    days=(total_overs+19)//20
    rem=total_overs%20
    if rem==0:
      return int(days),3
    if rem<=6:
      return int(days),1
    if rem<=12:
      return int(days),2
    return int(days),3
  def teamTotal(self,team):return sum(i.runs for i in self.innings if i.battingTeam==team)
  def inningsByTeam(self,team):return [i for i in self.innings if i.battingTeam==team]
  def swap(self,idx1,idx2):
    if self.started or idx1==idx2:return False
    combined=self.players
    if idx1<0 or idx2<0 or idx1>=len(combined) or idx2>=len(combined):return False
    combined[idx1],combined[idx2]=combined[idx2],combined[idx1]
    total=len(combined);mid=total//2;extra=total%2
    self.teama.players=combined[:mid+extra];self.teamb.players=combined[mid+extra:]
    self.teama.checkForCaptain();self.teamb.checkForCaptain()
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
    return f"{bat.name} have won by {len(bat.players)-inn.wickets} wickets"
  def checkForWinner(self):
    if self.matchTotalBalls >= 600:
      self.winner = 'Drawn'
      return "Match Drawn"
    if len(self.innings)<2:return None
    last=self.currentInning
    bat=last.battingTeam
    bowl=last.bowlingTeam
    batTotal=self.teamTotal(bat)
    bowlTotal=self.teamTotal(bowl)
    if not last.currentBatters and len(last.cantBat)==len(bat.players):
      if self.followOnTeam==bat:
        lead=bowlTotal-batTotal
        if lead>0:
          self.winner = bowl.name
          return f"{bowl.name} have won by an innings and {lead} runs"
      elif len(self.innings)==3:
        lead=bowlTotal-batTotal
        if (batTotal- bowlTotal) < 0:
          self.winner = bowl.name
          return f"{bowl.name} have won by an innings and {lead} runs"
      if len(self.innings)==4:
        self.winner = bowl.name
        return f"{bowl.name} have won by {bowlTotal-batTotal} runs"
    if len(self.innings)==4:
      batPrev=batTotal-last.runs
      target=(bowlTotal-batPrev)+1
      if last.runs>=target:
        self.winner = bat.name
        return f"{bat.name} have won by {len(bat.players)-last.wickets} wickets"
      elif last.runs==target-1:
        self.winner = "Tied"
        return "Match Tied"
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
  def battingCard(self):
    inn = self.currentInning
    img=Image.open(os.path.join(BASE_DIR,"templates","battingSummary.png")).convert("RGBA")
    draw=ImageDraw.Draw(img)
    font=ImageFont.truetype(os.path.join(BASE_DIR,"fonts","Helvetica-Bold.ttf"),120*0.256)
    darkVoilet = "#32267B"
    white= "#EAEDF2"
    inningNum = f"INNING {inn.inningNo}"
    battingTeam = inn.battingTeam.name.upper()
    bowlingTeam= inn.bowlingTeam.name.upper()
    draw.text((((5000*0.256)-font.getlength(inningNum))/2,554.5*0.256),inningNum,font=font,fill=white)
    draw.text((300*0.256,554.5*0.256),battingTeam,font=font,fill=darkVoilet)
    draw.text((3171.7*0.256,554.5*0.256),bowlingTeam,font=font,fill=darkVoilet)
    font2=ImageFont.truetype(os.path.join(BASE_DIR,"fonts","Helvetica-Bold.ttf"),110*0.256)
    font=ImageFont.truetype(os.path.join(BASE_DIR,"fonts","Helvetica-Bold.ttf"),150*0.256)
    y = 1017*0.256
    offset = 303*0.256
    for p,i in inn.batters.items():
      draw.text((300*0.256,y),p.name.upper()[:18],font=font,fill=darkVoilet)
      batterRuns = f"{i.runs}"
      batterBalls = f"{i.balls}"
      l = font.getlength(batterRuns)
      b = font2.getlength(batterBalls)+(20*0.256)
      draw.text(((4700*0.256)-(l+b),y),batterRuns,font=font,fill=darkVoilet)
      draw.text((((4700*0.256)-b),y+(30*0.256)),batterBalls,font=font2,fill=darkVoilet)
      y += offset
    font=ImageFont.truetype(os.path.join(BASE_DIR,"fonts","Helvetica-Bold.ttf"),180*0.256)
    inningScore = f"{inn.runs}/{inn.wickets} ({self.ballsToOvers(inn.balls)}) {'d' if inn.declared else ''}"
    draw.text((((5000*0.256)-font.getlength(inningScore))/2,(4582*0.256)+(54.5*0.256)),inningScore,font=font,fill=darkVoilet)
    
    with BytesIO() as image_binary:
      img.save(image_binary, 'PNG')
      image_binary.seek(0)
      return discord.File(fp=image_binary, filename='battingSC.png')
  def bowlingCard(self):
    inn = self.currentInning
    img = Image.open(os.path.join(BASE_DIR,"templates","bowlingSummary.png")).convert("RGBA")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(os.path.join(BASE_DIR,"fonts","Helvetica-Bold.ttf"),120*0.256)
    darkVoilet = "#32267B"
    white = "#EAEDF2"
    inningNum = f"INNING {inn.inningNo}"
    battingTeam = inn.battingTeam.name.upper()
    bowlingTeam = inn.bowlingTeam.name.upper()
    draw.text((((5000*0.256)-font.getlength(inningNum))/2, 554.5*0.256), inningNum, font=font, fill=white)
    draw.text((300*0.256, 554.5*0.256), battingTeam, font=font, fill=darkVoilet)
    draw.text((3171.7*0.256, 554.5*0.256), bowlingTeam, font=font, fill=darkVoilet)
    y = 1225*0.256
    offset = 303*0.256
    for p, i in inn.bowlers.items():
      bowler = p.name.upper()[:18]
      w = str(i.wickets)
      o = str(self.ballsToOvers(i.balls))
      r = str(i.runsConceded)
      eo = str(round((i.runsConceded/i.balls)*6, 2)) if i.balls else "0.0"
      draw.text((350*0.256, y), bowler, font=font, fill=darkVoilet)
      draw.text(((3023.2*0.256)+(98.4*0.256)/2-font.getlength(w)/2, y), w, font=font, fill=darkVoilet)
      draw.text(((3398.1*0.256)+(81.9*0.256)/2-font.getlength(o)/2, y), o, font=font, fill=darkVoilet)
      draw.text(((3761.9*0.256)+(70.3*0.256)/2-font.getlength(r)/2, y), r, font=font, fill=darkVoilet)
      draw.text(((4175.2*0.256)+(145.5*0.256)/2-font.getlength(eo)/2, y), eo, font=font, fill=darkVoilet)
      y += offset
    font = ImageFont.truetype(os.path.join(BASE_DIR,"fonts","Helvetica-Bold.ttf"), 180*0.256)
    inningScore = f"{inn.runs}/{inn.wickets}({self.ballsToOvers(inn.balls)}) {'d' if inn.declared else ''}"
    draw.text((((5000*0.256)-font.getlength(inningScore))/2, (4582*0.256)+(54.5*0.256)), inningScore, font=font, fill=darkVoilet)
    
    with BytesIO() as image_binary:
      img.save(image_binary, 'PNG')
      image_binary.seek(0)
      return discord.File(fp=image_binary, filename='bowlingSC.png',)
  def matchSummaryCard(self):
    img = Image.open(os.path.join(BASE_DIR, "templates","matchSummary.png")).convert("RGBA")
    draw = ImageDraw.Draw(img)
  
    font = ImageFont.truetype(os.path.join(BASE_DIR,"fonts","Helvetica-Bold.ttf"),120*0.256)
    darkVoilet = "#32267B"
    white = "#EAEDF2"
    y = 588.4*0.256
    offset = 966.2*0.256
    for inn in self.innings:
      battingTeam = inn.battingTeam.name.upper() 
      if inn.inningNo == 3 and self.followOnTeam:
        battingTeam += " (f/o)"
      score = f"{inn.runs}/{inn.wickets} ({self.ballsToOvers(inn.balls)}) {'d' if inn.declared else ''}"
      draw.text((300*0.256, y + (54.5*0.256)), battingTeam, font=font, fill=white)
      draw.text(((4700*0.256) - font.getlength(score), y + (54.5*0.256)), score, font=font, fill=white)
      topBat = sorted(inn.batters.items(), key=lambda x: x[1].runs, reverse=True)[:2]
      topBowl = sorted(inn.bowlers.items(), key=lambda x: x[1].wickets, reverse=True)[:2]
      y2 = y + (262*0.256)
      offset2 = 303*0.256
      for k in range(2):
        if k < len(topBat):
          p, i = topBat[k]
          if i.balls > 0:
            batter = p.name.upper()[:15]
            batterScore = f"{i.runs} ({i.balls})"
            draw.text((320*0.256, y2 + (70.5*0.256)), batter, font=font, fill=darkVoilet)
            draw.text(((2180*0.256) - font.getlength(batterScore), y2 + (70.5*0.256)), batterScore, font=font, fill=darkVoilet)
        if k < len(topBowl):
          p, i = topBowl[k]
          if i.balls > 0:
            bowler = p.name.upper()[:15]
            bowlerScore = f"{i.wickets}/{i.runsConceded} ({self.ballsToOvers(i.balls)})"
            draw.text((2820*0.256, y2 + (70.5*0.256)), bowler, font=font, fill=darkVoilet)
            draw.text(((4680*0.256) - font.getlength(bowlerScore), y2 + (70.5*0.256)), bowlerScore, font=font, fill=darkVoilet)
        y2 += offset2
      y += offset
    footer = self.matchStatus().upper()
    font=ImageFont.truetype(os.path.join(BASE_DIR,"fonts","Helvetica-Bold.ttf"),120*0.256)
    draw.text((((5000*0.256)-font.getlength(footer))/2,(4582*0.256)+(79.5*0.256)),footer,font=font,fill=darkVoilet)
    
    with BytesIO() as image_binary:
      img.save(image_binary, 'PNG')
      image_binary.seek(0)
      return discord.File(fp=image_binary, filename='matchSummary.png')
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
    DaysAndSessions = self.getDaysAndSessions()
    container.add_item(ui.TextDisplay(f"**Day {DaysAndSessions[0]} | Session {DaysAndSessions[1]}**"))
    t = {}
    for i in self.innings:
      s = f"{i.runs}/{i.wickets} {'(f/o) ' if i.inningNo == 3 and self.followOnTeam else ''} {'(D) ' if i.declared else ''}"
      if i.inningNo == self.currentInning.inningNo:
        s += f" ({self.ballsToOvers(i.balls)})"
      if i.battingTeam.name in t: t[i.battingTeam.name] += f"& {s}"
      else: t[i.battingTeam.name] = s
    Score = "\n".join(f"**`{k.ljust(18)}{v}`**" for k,v in t.items())
    Score += f"\nMatch Total Overs: ({self.ballsToOvers(self.matchTotalBalls)}/100)"
    if returnContainer is False:
      container.add_item(ui.Section(ui.TextDisplay(Score), accessory=DeclareBTN()))
    else: container.add_item(ui.TextDisplay(Score))
    header = f"**` {'Batters'.ljust(16)}{'R'.rjust(4)}{'B'.rjust(4)}{'SR'.rjust(9)}`**"
    rows=["```py\n"]+[f"{b.name.ljust(16)}{str(self.currentInning.batters[b].runs).rjust(4)}{str(self.currentInning.batters[b].balls).rjust(4)}{str(self.currentInning.batters[b].sr).rjust(9)}\nCan Do 0: {'✅' if self.currentInning.batters[b].consecutiveDots!=3 else '❌'}  Can Do 4,6: {'✅' if self.currentInning.batters[b].BoundaryThisOver is not True else '❌'}" for b in self.currentInning.currentBatters]
    if len(self.currentInning.currentBatters) == 2:
      rows += [f"P'ship: {self.currentInning.currentPartnership[0]} ({self.currentInning.currentPartnership[1]})\n```"]
    else: rows += ["\n```"]
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
    if len(options) == 1:
      pid = options[0]['id']
      inn.currentBowlers.appendleft(next(p for p in inn.bowlingTeam.players if p.id==pid))
      return
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
    if len(options) == 1:
      pid = options[0]['id']
      inn.currentBatters.insert(0,next(p for p in inn.battingTeam.players if p.id==pid))
      inn.cantBat.append(pid)
      return
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
  def calculateMvp(self):
    stats = {}
    for inn in self.innings:
      for p, b in inn.batters.items():
        if p.id not in stats: stats[p.id] = {'p': p, 'pts': 0}
        stats[p.id]['pts'] += b.runs
      for p, b in inn.bowlers.items():
        if p.id not in stats: stats[p.id] = {'p': p, 'pts': 0}
        stats[p.id]['pts'] += b.wickets * 12
    winner = next((t for t in [self.teama, self.teamb] if t.name == self.winner), None)
    if winner:
      for p in winner.players:
        if p.id in stats: 
          stats[p.id]['pts']*= 1.2
    best = max(stats.values(), key=lambda x: x['pts'])
    self.mvp = best['p']
    return best['p']
  async def startInning(self):
    no=len(self.innings)+1
    bat=self.nextBattingTeam()
    bowl=self.teamb if bat==self.teama else self.teama
    inn=Inning()
    inn.inningNo=no
    inn.battingTeam=bat
    inn.bowlingTeam=bowl
    if no == 3 and self.followOnTeam:
      inn.followOn = True
    for p in bat.players: inn.batters[p]=BattingInning(p)
    for p in bowl.players: inn.bowlers[p]=BowlingInning(p)
    self.innings.append(inn)
    await asyncio.gather(self.selectBowler(),self.selectOpeners())
  async def sendToNonStriker(self, content= None, **kwargs):
    if len(inn.currentBatters) == 2:
      p = striker=inn.currentBatters[1]
      await asyncio.sleep(1)
      await p.send(content, **kwargs)
  async def getInputs(self):
    bowlerExtraTXT = ""
    batterExtraTXT = ""
    while True:
      ballId = str(uuid7())
      inn=self.currentInning
      striker=inn.currentBatters[0]
      bowler=inn.currentBowlers[0]
      DaysAndSessions = self.getDaysAndSessions()
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
      battxt = f"{batterExtraTXT}\nSend your shot ({','.join(sorted(allowed, key=int))}) within 20s"
      batview = ui.LayoutView(timeout=None)
      batview.add_item(self.score(True))
      batview.add_item(ui.TextDisplay(battxt))
      bowlview = ui.LayoutView(timeout=None)
      bowlview.add_item(self.score(True))
      bowlview.add_item(ui.TextDisplay(f"{bowlerExtraTXT}\nSend your delivery (1,2,3,4,6) within 20s"))
      await striker.send(view=batview)
      await bowler.send(view=bowlview)
      bat_task=asyncio.create_task(self.ctx.bot.wait_for("message",check=checkBatter))
      bowl_task=asyncio.create_task(self.ctx.bot.wait_for("message",check=checkBowler))
      done,pending=await asyncio.wait([bat_task,bowl_task],timeout=20)
      bat_ok=bat_task in done and not bat_task.cancelled()
      bowl_ok=bowl_task in done and not bowl_task.cancelled()
      if not bat_ok and not bowl_ok:
        
        for t in pending: t.cancel()
        bowler_p.AFKs += 1; striker_p.AFKs += 1
        await self.ctx.send(f"Both the bowler and batter were afk, replaying the ball. Bowler AFKs: 3/{bowler_p.AFKs}\nBatter AFKs: 6/{striker_p.AFKs}")
        await asyncio.sleep(0.3)
        await striker.send(f"You didn't respond in time. Replaying the ball.\n{'' if striker_p.AFKs not in [3,6] else 'You are retiring out!'}")
        await asyncio.sleep(0.3)
        if bowler_p.AFKs == 3:
          await bowler.send(f"You didn't respond in time. Replaying the ball.\nYou are retiring from the crease\n-# We know your girlfriend deseres more attention than a fucking discord bot!'")
          bowler_p.AFKs = 0
          await self.selectBowler()
        else:
          bowlerExtraTXT = "You didn't respond in time. Replaying the ball."
        if striker_p.AFKs == 3:
          self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            0,
            0,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            None, None,
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
          inn.currentBatters.pop(0)
          inn.cantBat.remove(striker.id)
          await self.selectNextBatter()
          if inn.currentBatters[0].id != striker.id: inn.currentPartnership = [0,0]
        elif striker_p.AFKs == 6:
          striker_p.dismissed = True 
          self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            1,
            0,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            None, None,
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
          await striker.send(f"You didn't respond in time. Replaying the ball.\nYou AFKed for 6 balls, you are being deported to Epstein Island, happy sucking !!")
          await self.sendToNonStriker("Striker was declared out because of being AFK.")
          inn.currentBatters.pop(0)
          if len(inn.cantBat) < len(inn.battingTeam.players):await self.selectNextBatter(); inn.currentPartnership = [0,0]
          elif not inn.currentBatters:return 'Inning Over'
        else:
          batterExtraTXT = "You were AFK, try this again."
          self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            0,
            0,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            None, None,
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
        continue
      elif not bat_ok and bowl_ok:
        for t in pending: t.cancel()
        striker_p.AFKs += 1
        await self.ctx.send(f"Batter was afk, replaying the ball\nBatter AFKs: {striker_p.AFKs}/6")
        await asyncio.sleep(0.3)
        if striker_p.AFKs == 3:
          self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            0,
            0,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            None, int(bowl_task.result().content),
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
          inn.currentBatters.pop(0)
          inn.cantBat.remove(striker.id)
          await self.selectNextBatter()
          if inn.currentBatters[0].id != striker.id: inn.currentPartnership = [0,0]
        elif striker_p.AFKs == 6:
          striker_p.dismissed = True 
          self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            1,
            0,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            None, int(bowl_task.result().content),
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
          await self.sendToNonStriker("Striker was declared out because of being AFK.")
          await striker.send(f"You didn't respond in time. Replaying the ball.\nYou AFKed for 6 balls, you are being deported to Epstein Island, happy sucking !!")
          inn.currentBatters.pop(0)
          if len(inn.cantBat) < len(inn.battingTeam.players):await self.selectNextBatter();inn.currentPartnership = [0,0]
          elif not inn.currentBatters:return 'Inning Over'
        else:
          self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            0,
            0,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            None, int(bowl_task.result().content),
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
          batterExtraTXT = "You were AFK, try this again."
        bowlerExtraTXT = "Batter didn't respond in time. Replaying the ball."
        continue
      elif bat_ok and not bowl_ok:
        for t in pending: t.cancel()
        bowler_p.AFKs += 1
        await self.ctx.send(f"Bowler was afk, replaying the ball.\nBowler AFKs: {bowler_p.AFKs}/3")
        self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            0,
            0,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            int(bat_task.result().content),None, 
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
        if bowler_p.AFKs == 3:
          bowler_p.AFKs = 0
          await self.selectBowler()
        else:
          bowlerExtraTXT = "You didn't respond in time. Replaying the ball."
        await asyncio.sleep(0.3)
        batterExtraTXT = "Bowler didn't respond in time. Replaying the ball"
        continue
      bat=int(bat_task.result().content)
      bowl=int(bowl_task.result().content)
      for t in pending: t.cancel()
      break
    inn.balls+=1
    striker_p.balls+=1
    bowler_p.balls+=1
    inn.currentPartnership[1] +=1
    striker_p.timeline.append(str(bat))
    if bat!=0: striker_p.consecutiveDots=0
    else: striker_p.consecutiveDots+=1
    if bat==bowl:
      striker_p.dismissed = True 
      inn.wickets+=1
      bowler_p.timeline.append("W")
      self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            1,
            0,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            bat, bowl,
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
      v = ui.LayoutView(timeout=None)
      c = ui.Container(accent_color=discord.Colour.from_str("#9b0a0a"))
      wkttxt = f"# It's A Wicket!!\n**{striker.name}** {striker_p.runs} ({striker_p.balls})\n**{bowler.name}** {bowler_p.runsConceded}/{bowler_p.wickets+1} ({self.ballsToOvers(bowler_p.balls)})\n**Number: {bat}**"
      if len(inn.currentBatters) == 2:
        wkttxt += f"\n**Partnership: ** {inn.currentPartnership[0]} ({inn.currentPartnership[1]})"
      c.add_item(ui.TextDisplay(wkttxt))
      v.add_item(c)
      inn.currentPartnership = [0,0]
      await self.ctx.send(view=v)
      await asyncio.sleep(0.3)
      await striker.send(f"Your score: \n{striker_p.runs} ({striker_p.balls})\n**You are out!!**\nBowler did {bowl}")
      await asyncio.sleep(0.3)
      await bowler.send(f"Their score: \n{striker_p.runs} ({striker_p.balls})\nThey are out!!\nBatter did {bat}")
      await asyncio.sleep(0.3)
      await self.sendToNonStriker(f"{striker.name}'s score: \n{striker_p.runs} ({striker_p.balls})\n**They are out!!**\nBowler -> {bowl}")
      inn.timeline.append("W")
      
      bowler_p.wicketsDigits.append(f"{bowl}")
      bowler_p.wickets+=1
      inn.currentBatters.pop(0)
      if len(inn.cantBat) < len(inn.battingTeam.players):
        await self.selectNextBatter()
      elif not inn.currentBatters:
        return 'Inning Over'
    else:
      bowler_p.timeline.append(str(bowl))
      inn.runs+=bat
      self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.BoundaryThisOver else 1, 
            0,
            bat,
            inn.runs,
            inn.balls,
            float(self.ballsToOvers(inn.balls)),
            inn.wickets,
            bat, bowl,
            int(time.time()),
            DaysAndSessions[0], DaysAndSessions[1],
          ))
      if bat in [4,6]:
        striker_p.BoundaryThisOver = True
      striker_p.runs+=bat
      bowler_p.runsConceded+=bat
      inn.currentPartnership[0] += bat
      await striker.send(f"Your score: \n{striker_p.runs} ({striker_p.balls})\nBowler did {bowl}")
      
      await asyncio.sleep(0.3)
      await bowler.send(f"Their score: \n{striker_p.runs} ({striker_p.balls})\nBatter did {bat}")
      await self.sendToNonStriker(f"{striker.name}'s score: \n{striker_p.runs} ({striker_p.balls})\n**Batter digit -> {bat}**\nBowler -> {bowl}")
      inn.timeline.append(f"{bat}")
      if bat%2==1 and len(inn.currentBatters) > 1:
        inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
    if inn.balls%6==0:
      self.v = self.score()
      await self.ctx.send(view=self.v)
      for b in inn.currentBatters:
        inn.batters[b].BoundaryThisOver = False
      if len(inn.currentBatters) > 1:
        inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
      await self.selectBowler()
  
  async def start(self):
    try:
      self.started = True 
      self.startedAt = time.time()
      for i in range(4):
        w = self.checkForWinner()
        if w: break
        await self.startInning()
        while True:
          g = await self.getInputs()
          if self.v:
            self.v.stop()
          if self.currentInning.balls%6 !=0:
            self.v = self.score()
            await self.ctx.send(view=self.v)
          w = self.checkForWinner()
          if g != None or w:
            bat,bowl=self.battingCard(), self.bowlingCard()
            await self.ctx.send(files=[bat,bowl])
            await asyncio.sleep(3)
            await self.checkFollowOn()
            break
          if self.currentInning.declared:
            await self.ctx.send("**Inning Declared**")
            await asyncio.sleep(1)
            bat,bowl=self.battingCard(), self.bowlingCard()
            await self.ctx.send(files=[bat,bowl])
            await asyncio.sleep(0.3)
            await self.checkFollowOn()
            await asyncio.sleep(3)
            break
      summary=self.matchSummaryCard()
      await self.ctx.send(file=summary)
      duration= time.time() - self.startedAt
      mvp= self.calculateMvp()
      hours=int(duration//3600);minutes=int((duration%3600)//60);seconds=int(duration%60)
      formatted=f"MVP: **{mvp.name}**\nThis game took {hours} hours {minutes} minutes {seconds} seconds"
      await self.saveData()
      await self.ctx.send(f"{formatted}")
      self.ctx.bot.games.pop(self.ctx.channel.id)
    except Exception as e:
      traceback.print_exc()