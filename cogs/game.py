import random, traceback,os, time,json
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
    self.dismissedBy = ""
    self.fours = 0
    self.sixes = 0
    self.timeline = deque(maxlen=13)
  @property
  def sr(self): return round((self.runs/self.balls)*100,2) if self.balls else 00.0
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
    self.maidens = 0 
    self.currentOverRuns = 0
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
    self.fallOfWickets = []
class Team():
  def __init__(self, name: str = 'Team A', id: int = 1):
    self.name = name
    self.id = id
    self.captain = None 
    self.players = []
    self.color = "#14f67c" if id == 1 else "#05a9e6"
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
    self.maxBalls = 540
    self.followOnTeam=None
    self.winner = None
    self.mvp = None
    self.DEBUG = False
  async def saveData(self):
    await self.ctx.bot.execute("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?)", (self.gameId, self.ctx.channel.id, self.ctx.guild.id, self.teama.name, self.teamb.name, self.winner, self.mvp.id,self.maxBalls))
    data = [(i.inningId, self.gameId, i.runs, i.balls, i.wickets, i.battingTeam.name, i.bowlingTeam.name, 1 if i.declared else 0, 1 if i.followOn else 0,) for i in self.innings]
    placeholders = ",".join(["?"] * len(data[0]))
    await self.ctx.bot.db.executemany(f"INSERT INTO innings VALUES ({placeholders})", data)
    placeholders = ",".join(["?"] * len(self.ballsData[0]))
    await self.ctx.bot.db.executemany(f"INSERT INTO deliveries VALUES ({placeholders})", self.ballsData)
    await self.ctx.bot.db.commit()
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @property
  def followOnLimit(self):
    if self.DEBUG: return 5
    if self.maxBalls == 540:
      return 75
    elif self.maxBalls == 360:
      return 50
    else:
      return 25
  @property
  def matchTotalBalls(self):
    return sum([i.balls for i in self.innings])
  @property 
  def currentInning(self): return self.innings[-1]
  @property 
  def players(self): return self.teama.players + self.teamb.players
  def getDaysAndSessions(self):
    ball = self.matchTotalBalls 
    if ball == 0: return 1,1
    balls_per_day = self.maxBalls/5
    balls_per_session = balls_per_day/3
    day = int((ball-1)//balls_per_day)+1
    session = int(((ball-1)%balls_per_day)//balls_per_session)+1
    return day,session
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
        container.add_item(ui.TextDisplay(f"Follow on is currently available, **{inn.bowlingTeam.name}** Lead by {lead} runs. Would you like to enforce follow-on?"))
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
    if self.matchTotalBalls >= self.maxBalls:
      self.winner = 'Drawn'
      return "Match Drawn"
    if len(self.innings)<2:return None
    last=self.currentInning
    bat=last.battingTeam
    bowl=last.bowlingTeam
    batTotal=self.teamTotal(bat)
    bowlTotal=self.teamTotal(bowl)
    if not last.currentBatters and len(last.cantBat)==len(bat.players):
      if self.followOnTeam==bat and last.inningNo == 3:
        lead=bowlTotal-batTotal
        if lead>0:
          self.winner = bowl.name
          return f"{bowl.name} have won by an innings and {lead} runs"
      elif len(self.innings)==3:
        lead=bowlTotal-batTotal
        if (batTotal- bowlTotal) < 0:
          self.winner = bowl.name
          return f"{bowl.name} have won by an innings and {lead} runs"
      elif len(self.innings)==4:
        batPrev=batTotal-last.runs
        target=(bowlTotal-batPrev)+1
        if last.runs==target-1:
          self.winner = "Tied"
          return "Match Tied"
      if len(self.innings)==4:
        self.winner = bowl.name
        return f"{bowl.name} have won by {bowlTotal-batTotal} runs"
    if len(self.innings)==4:
      batPrev=batTotal-last.runs
      target=(bowlTotal-batPrev)+1
      if last.runs>=target:
        self.winner = bat.name
        return f"{bat.name} have won by {len(bat.players)-last.wickets} wickets"
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
    img = Image.open(os.path.join(BASE_DIR, "templates", "BattingSummary.png")).convert("RGBA")
    draw = ImageDraw.Draw(img)
    S = 1.3325714286
    font = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "archivo.woff2"), int(65 * S))
    font2 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowRegular.woff2"), int(32.7 * S))
    font3 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowRegular.woff2"), int(27 * S))
    font4 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "archivo.woff2"), int(40 * S))
    vividGreen = "#14f67c"
    battingTeam = inn.battingTeam.name.upper()
    draw.text((210, 15), battingTeam, font=font, fill=inn.battingTeam.color)
    y = 210.3
    offset = 91.1
    for p, b in inn.batters.items():
      name = p.name.upper()[:15]
      runs = str(b.runs)
      balls = str(b.balls)
      is_not_out = not b.dismissed
      status_text = "NOT OUT" if is_not_out else b.dismissedBy
      r_w = font3.getlength(runs)
      b_w = font3.getlength(balls)
      if is_not_out:
        overlay = Image.open(os.path.join(BASE_DIR, "templates", "NotOutLine.png")).convert("RGBA")
        img.paste(overlay, (74, int(y - 20)), overlay)
        draw.text((121, y), name, font=font2, fill="black", stroke_width=0)
        draw.text((645, y), status_text, font=font2, fill="black")
        draw.text((975.7 + 63.1 / 2 - r_w / 2, y + 5), runs, font=font3, fill="black", stroke_width=0.5)
        draw.text((1075.9 + 69.4 / 2 - b_w / 2, y + 5), balls, font=font3, fill="black", stroke_width=0)
      else:
        draw.text((121, y), name, font=font2, fill="white", stroke_width=0)
        draw.text((645, y), status_text, font=font2, fill="white")
        draw.text((975.7 + 63.1 / 2 - r_w / 2, y + 5), runs, font=font3, fill="white", stroke_width=0.5)
        draw.text((1075.9 + 69.4 / 2 - b_w / 2, y + 5), balls, font=font3, fill="white", stroke_width=0)
      y += offset
    overs = str(self.ballsToOvers(inn.balls))
    score = f"{inn.runs}-{inn.wickets}"
    draw.text((781.5, 1177.9), overs, font=font4, fill="white")
    draw.text((1050.1, 1177.9), score, font=font4, fill=inn.battingTeam.color)
    with BytesIO() as image_binary:
      img.save(image_binary, 'PNG')
      image_binary.seek(0)
      return discord.File(fp=image_binary, filename='battingSC.png')
  def bowlingCard(self):
    inn = self.currentInning
    img = Image.open(os.path.join(BASE_DIR, "templates", "BowlingSummary.png")).convert("RGBA")
    draw = ImageDraw.Draw(img)
    S = 1.3325714286
    font = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "archivo.woff2"), int(65*S))
    font2 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowRegular.woff2"), int(32.7*S))
    font3 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowRegular.woff2"), int(27*S))
    font4 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "archivo.woff2"), int(40*S))
    font6 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "canvaSansRegular.woff2"), int(20*S))
    vividGreen = "#14f67c"
    bowlingTeam = inn.bowlingTeam.name.upper()
    draw.text((210, 15), bowlingTeam, font=font, fill=inn.bowlingTeam.color)
    y = 210.3
    offsets = [91.1, 91.1, 88, 88, 84, 84, 86, 84]
    bowlers_list = sorted(
        inn.bowlers.items(), 
        key=lambda x: (-x[1].wickets, x[1].runsConceded)
    )[:8]
    for index, (p, b) in enumerate(bowlers_list):
      name = p.name.upper()[:15]
      overs = str(self.ballsToOvers(b.balls))
      maidens = str(b.maidens)
      runs = str(b.runsConceded)
      wickets = str(b.wickets)
      economy = str(round((b.runsConceded / b.balls) * 6, 2)) if b.balls else "0.00"
      
      draw.text((121, y), name, font=font2, fill="white", stroke_width=0)
      draw.text((500.8 + 130 / 2 - font3.getlength(overs) / 2, y + 5), overs, font=font3, fill="white", stroke_width=0)
      draw.text((628.8 + 145 / 2 - font3.getlength(maidens) / 2, y + 5), maidens, font=font3, fill="white", stroke_width=0)
      draw.text((800.4 + 63.1 / 2 - font3.getlength(runs) / 2, y + 5), runs, font=font3, fill="white", stroke_width=0)
      draw.text((877 + 153 / 2 - font3.getlength(wickets) / 2, y + 5), wickets, font=font3, fill="white", stroke_width=0.5)
      draw.text((1029.4 + 163.7 / 2 - font3.getlength(economy) / 2, y + 5), economy, font=font3, fill="white", stroke_width=0)
      
      y += offsets[index]
    xs = [412.7, 480.1, 547.6, 621.9, 692.2, 760.6, 826.4, 899.7, 968, 1047.1, 1131.7]
    for i, f in enumerate(inn.fallOfWickets):
      if i >= len(xs): break
      draw.text((xs[i] + 30 / 2 - font6.getlength(str(f)) / 2, 1084), str(f), font=font6, fill="black", stroke_width=0.5)
    totalOvers = str(self.ballsToOvers(inn.balls))
    totalScore = f"{inn.runs}-{inn.wickets}"
    draw.text((781.5, 1177.9), totalOvers, font=font4, fill="white")
    draw.text((1050.1, 1177.9), totalScore, font=font4, fill=inn.bowlingTeam.color)
    with BytesIO() as image_binary:
      img.save(image_binary, 'PNG')
      image_binary.seek(0)
      return discord.File(fp=image_binary, filename='bowlingSC.png')
  def matchSummaryCard(self):
    img = Image.open(os.path.join(BASE_DIR, "templates", "matchSummary.png")).convert("RGBA")
    draw = ImageDraw.Draw(img)
    S = 1.3325714286
    font = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "archivo.woff2"), int(40*S))
    font2 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "canvaSansRegular.woff2"), int(30*S))
    font3 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "canvaSansRegular.woff2"), int(23*S))
    font4 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "canvaSansRegular.woff2"), int(28*S))
    font5 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "canvaSansBold.woff2"), int(28*S))
    font6 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "archivo.woff2"), int(24*S))
    font7 = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "archivo.woff2"), int(31*S))
    vividGreen = "#14f67c"
    vividAzure = "#05a9e6"
    draw.text((203.3, 139.4), f"{self.teama.name.upper()} VS {self.teamb.name.upper()}", font=font2, fill='White')
    y = 260
    offset = 215.7
    for i, inn in enumerate(self.innings):
      battingTeam = f"{inn.battingTeam.name.upper()} {inn.runs}/{inn.wickets}{'d' if inn.declared else ''}"
      if inn.inningNo == 3 and self.followOnTeam: battingTeam += " (f/o)"
      color = inn.battingTeam.color
      draw.text((100, y), battingTeam, font=font, fill=color)
      ord_s = "th" if 10 <= inn.inningNo % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(inn.inningNo % 10, "th")
      innLabel = f"{inn.inningNo}{ord_s} Inning".upper()
      draw.text((1200 - font3.getlength(innLabel), y + 10), innLabel, font=font3, fill='White')
      topBat = sorted(inn.batters.items(), key=lambda x: x[1].runs, reverse=True)[:2]
      topBowl = sorted(inn.bowlers.items(), key=lambda x: x[1].wickets, reverse=True)[:2]
      y2 = y
      offset2 = 50
      for k in range(2):
        if k < len(topBat):
          p, b = topBat[k]
          name = p.name.upper()[:15]
          runs = str(b.runs)
          balls = f"{b.balls}"
          draw.text((100, y2 + 60), name, font=font4, fill='White')
          draw.text((475.8, y2 + 60), runs, font=font5, fill='White')
          l = font5.getlength(runs) + 5
          draw.text(((475.8 + l), y2 + 70), balls, font=font6, fill='White')
        if k < len(topBowl):
          p, b = topBowl[k]
          name = p.name.upper()[:15]
          fig = f"{b.wickets}-{b.runsConceded}"
          draw.text((750, y2 + 60), name, font=font4, fill='White')
          draw.text((1190 - font5.getlength(fig), y2 + 60), fig, font=font5, fill='White')
        y2 += offset2
      if i > 0: offset = 230
      if i == 2: offset = 240
      y += offset
    footer = self.matchStatus().upper()
    draw.text(((1280 - font7.getlength(footer)) / 2, 1190), footer, font=font7, fill="black")
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
    container.add_item(ui.TextDisplay(f"**Toss:** {'✅' if self.batFirstTeam else '❌'}\n**Maximum Overs:**{self.ballsToOvers(self.maxBalls)}"))
    actionRow = ui.ActionRow()
    actionRow.add_item(OversSelection())
    container.add_item(actionRow)
    container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
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
      buttons = [Button('Bat',discord.ButtonStyle.green,winner.captain.id), Button('Bowl',discord.ButtonStyle.red,winner.captain.id)]
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
    Score += f"\nMatch Total Overs: ({self.ballsToOvers(self.matchTotalBalls)}/{self.ballsToOvers(self.maxBalls)})"
    showDeclareBtn = True
    if self.currentInning.inningNo >= 2:
      last=self.currentInning
      bat=last.battingTeam
      bowl=last.bowlingTeam
      batTotal=self.teamTotal(bat)
      bowlTotal=self.teamTotal(bowl)
      showDeclareBtn = batTotal > bowlTotal
    if returnContainer is False and showDeclareBtn and self.currentInning.inningNo != 4:
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
      return self.followOnTeam
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
    view.m =await self.ctx.send(view=view)
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
    if len(self.currentInning.currentBatters) == 2:
      p = striker=self.currentInning.currentBatters[1]
      await asyncio.sleep(1)
      await p.send(content, **kwargs)
  async def sendWicketGraphic(self, batterName, bowlerName, runsScored, ballsPlayed, FOW, SIXES, FOURS, STRIKERATE, text= None):
    img=Image.open(os.path.join(os.getcwd(), "templates/wicket.png")).convert("RGBA")
    draw=ImageDraw.Draw(img)
    font=ImageFont.truetype(os.path.join(os.getcwd(), "fonts/canvaSansBold.woff2"),60*1.3325714286)
    font2=ImageFont.truetype(os.path.join(os.getcwd(), "fonts/canvaSansBold.woff2"),30*1.3325714286)
    fontw=ImageFont.truetype(os.path.join(os.getcwd(), "fonts/canvaSansBold.woff2"),26*1.3325714286)
    font3=ImageFont.truetype(os.path.join(os.getcwd(), "fonts/canvaSansBold.woff2"),80*1.3325714286)
    font4=ImageFont.truetype(os.path.join(os.getcwd(), "fonts/canvaSansBold.woff2"),50*1.3325714286)
    draw.text((246.6,27.3),batterName.upper()[:12],font=font,fill="White",stroke_width=1)
    draw.text((250,115.3),bowlerName.upper(),font=fontw,fill=self.currentInning.bowlingTeam.color,stroke_width=1)
    draw.text((1095-font3.getlength(str(runsScored)),27.3),str(runsScored),font=font3,fill=self.currentInning.battingTeam.color,stroke_width=1)
    x = 1095-font3.getlength(str(runsScored))
    draw.text((x + 10+font3.getlength(str(runsScored)),65.3),str(ballsPlayed),font=font4,fill=self.currentInning.battingTeam.color,stroke_width=0)
    draw.text((111.2+90.7/2-font4.getlength(FOW)/2,295.2),FOW,font=font4,fill="White",stroke_width=1)
    draw.text((399.6+134.1/2-font4.getlength(FOURS)/2,295.2),FOURS,font=font4,fill="White",stroke_width=1)
    draw.text((698.5+110.4/2-font4.getlength(SIXES)/2,295.2),SIXES,font=font4,fill="White",stroke_width=1)
    draw.text((973.7+243.2/2-font4.getlength(STRIKERATE)/2,295.2),STRIKERATE,font=font4,fill="White",stroke_width=1)
    with BytesIO() as image_binary:
      img.save(image_binary, 'PNG')
      image_binary.seek(0)
      i = discord.File(fp=image_binary, filename='wicket.png')
      c =  ui.LayoutView(timeout= 60)
      container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.battingTeam.color))
      gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(i, spoiler = False))
      if text:container.add_item(ui.TextDisplay(text))
      container.add_item(gallery)
      c.add_item(container)
      await self.ctx.send(file= i, view= c)
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
      battxt = f"{batterExtraTXT}\nSend your shot ({','.join(sorted(allowed, key=int))}) **within 15s**"
      batview = ui.LayoutView(timeout=None)
      batview.add_item(self.score(True))
      batview.add_item(ui.TextDisplay(battxt))
      bowlview = ui.LayoutView(timeout=None)
      bowlview.add_item(self.score(True))
      bowlview.add_item(ui.TextDisplay(f"{bowlerExtraTXT}\nSend your delivery (1,2,3,4,6) **within 15s**"))
      await striker.send(view=batview)
      await bowler.send(view=bowlview)
      bat_task=asyncio.create_task(self.ctx.bot.wait_for("message",check=checkBatter))
      bowl_task=asyncio.create_task(self.ctx.bot.wait_for("message",check=checkBowler))
      done,pending=await asyncio.wait([bat_task,bowl_task],timeout=15)
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
          striker_p.dismissedBy = "AFK"
          striker_p.dismissed = True
          inn.fallOfWickets.append(str(inn.runs))
          pship= f"**P'ship: {inn.currentPartnership[0]} ({inn.currentPartnership[1]})**" if len(inn.currentBatters) == 2 else None
          await self.sendWicketGraphic(striker.name.upper()[:18], striker_p.dismissedBy, str(striker_p.runs), str(striker_p.balls), f"{inn.runs}-{inn.wickets+1}", str(striker_p.sixes), str(striker_p.fours), str(striker_p.sr), pship)
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
          inn.wickets+=1
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
          inn.wickets+=1
          striker_p.dismissedBy = "AFK"
          pship= f"**P'ship: {inn.currentPartnership[0]} ({inn.currentPartnership[1]})**" if len(inn.currentBatters) == 2 else None
          await self.sendWicketGraphic(striker.name.upper()[:18], striker_p.dismissedBy, str(striker_p.runs), str(striker_p.balls), f"{inn.runs}-{inn.wickets}", str(striker_p.sixes), str(striker_p.fours), str(striker_p.sr), pship)
          inn.fallOfWickets.append(str(inn.runs))
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
      pship= f"**P'ship: {inn.currentPartnership[0]} ({inn.currentPartnership[1]})**\n" if len(inn.currentBatters) == 2 else ""
      txt = f"{pship}**The Protagonist -> {bat}**"
      await self.sendWicketGraphic(striker.name.upper()[:18], f"b. {bowler.name.upper()}", str(striker_p.runs), str(striker_p.balls), f"{inn.runs}-{inn.wickets}", str(striker_p.sixes), str(striker_p.fours), str(striker_p.sr), txt)
      inn.currentPartnership = [0,0]
      await asyncio.sleep(0.3)
      await striker.send(f"Your score: \n{striker_p.runs} ({striker_p.balls})\n**You are out!!**\nBowler did {bowl}")
      inn.fallOfWickets.append(str(inn.runs))
      await asyncio.sleep(0.3)
      await bowler.send(f"Their score: \n{striker_p.runs} ({striker_p.balls})\nThey are out!!\nBatter did {bat}")
      striker_p.dismissedBy = f"b. {bowler.name[:14]}"
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
      bowler_p.currentOverRuns += 1
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
        if bat == 4: striker_p.fours += 1
        if bat == 6: striker_p.sixes += 1
        striker_p.BoundaryThisOver = True
      striker_p.runs+=bat
      bowler_p.runsConceded+=bat
      inn.currentPartnership[0] += bat
      overEnded = '\n**Over has now ended.**' if inn.balls%6==0 else ''
      youRemainOffStrike = ''
      await striker.send(f"Your score: \n{striker_p.runs} ({striker_p.balls})\nBowler did {bowl}{overEnded}")
      if bat%2==1 and inn.balls%6!=0:
        youRemainOffStrike = '\nYou are now on strike.'
      elif bat%2!=1 and inn.balls%6!=0:
        youRemainOffStrike = '\nYou stay on non-strike for the next ball.'
      elif bat%2!=1 and inn.balls%6==0:
        youRemainOffStrike = '\nYou are now on strike.'
      await asyncio.sleep(0.3)
      await bowler.send(f"Their score: \n{striker_p.runs} ({striker_p.balls})\nBatter did {bat}{overEnded}")
      await self.sendToNonStriker(f"{striker.name}'s score: \n{striker_p.runs} ({striker_p.balls})\n**Batter digit -> {bat}**\nBowler -> {bowl}{overEnded}{youRemainOffStrike}")
      inn.timeline.append(f"{bat}")
      if bat%2==1 and len(inn.currentBatters) > 1:
        inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
    if inn.balls%6==0:
      if bowler_p.currentOverRuns == 0:
        bowler_p.maidens += 1
      for b in inn.currentBatters:
        inn.batters[b].BoundaryThisOver = False
      if len(inn.currentBatters) > 1:
        inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
      self.v = self.score()
      await self.ctx.send(view=self.v)
      await self.selectBowler()
  def rawStats(self):
    return {
      "meta": {
        "id": self.gameId,
        "host": self.hostId,
        "startTime": self.startedAt,
        "endTime": time.time(),
        "settings": {"maxBalls": self.maxBalls},
        "guild": self.ctx.guild.id,
        "channel": self.ctx.channel.id
      },
      "result": {
        "winner": self.winner,
        "mvp": self.mvp.id if self.mvp else None,
        "status": self.matchStatus()
      },
      "teams": {
        "A": {"name": self.teama.name, "captain": self.teama.captain.id if self.teama.captain else None, "players": [{"id": p.id, "name": p.name} for p in self.teama.players]},
        "B": {"name": self.teamb.name, "captain": self.teamb.captain.id if self.teamb.captain else None, "players": [{"id": p.id, "name": p.name} for p in self.teamb.players]}
      },
      "innings": [
        {
          "id": i.inningId,
          "number": i.inningNo,
          "battingTeam": i.battingTeam.name,
          "bowlingTeam": i.bowlingTeam.name,
          "totals": {"runs": i.runs, "wickets": i.wickets, "balls": i.balls},
          "flags": {"declared": i.declared, "followOn": i.followOn},
          "batting": [
            {
              "id": p.id,
              "name": p.name,
              "runs": b.runs,
              "balls": b.balls,
              "sr": b.sr,
              "dismissed": b.dismissed,
            } for p, b in i.batters.items()
          ],
          "bowling": [
            {
              "id": p.id,
              "name": p.name,
              "runs": b.runsConceded,
              "wickets": b.wickets,
              "balls": b.balls,
              "economy": round((b.runsConceded / b.balls) * 6, 2) if b.balls else 0.0
            } for p, b in i.bowlers.items()
          ]
        } for i in self.innings
      ]
    }
  async def sendRawStats(self):
    buf=BytesIO(json.dumps(self.rawStats(),indent=2).encode())
    buf.seek(0)
    await self.ctx.send(file= discord.File(fp=buf, filename=f'{self.gameId}.json'))
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
            c =  ui.LayoutView(timeout= 60)
            container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.battingTeam.color))
            gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(bat, spoiler = False),discord.MediaGalleryItem(bowl, spoiler = False))
            container.add_item(gallery)
            container.add_item(ui.TextDisplay("-# Graphics: zuhair_asif"))
            c.add_item(container)
            await self.ctx.send(view=c, files=[bat, bowl])
            await asyncio.sleep(3)
            await self.checkFollowOn()
            break
          if self.currentInning.declared:
            await self.ctx.send("**Inning Declared**")
            await asyncio.sleep(1)
            bat,bowl=self.battingCard(), self.bowlingCard()
            c =  ui.LayoutView(timeout= 60)
            container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.battingTeam.color))
            gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(bat, spoiler = False),discord.MediaGalleryItem(bowl, spoiler = False))
            container.add_item(gallery)
            container.add_item(ui.TextDisplay("-# Graphics: zuhair_asif"))
            c.add_item(container)
            await self.ctx.send(view=c, files= [bat, bowl])
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
      if not self.DEBUG:await self.saveData()
      await self.ctx.send(f"{formatted}")
      self.ctx.bot.games.pop(self.ctx.channel.id)
      try: 
        await self.sendRawStats()
      except Exception as e: 
        traceback.print_exc()
    except Exception as e:
      traceback.print_exc()