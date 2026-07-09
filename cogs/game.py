import random, traceback,os, time,json, math
from cogs.views import *
from discord import Embed, Color,ui
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
    self.BoundaryThisOver= 0
    self.AFKs = 0
    self.dismissed = False
    self.dismissedBy = "DNB"
    self.fours = 0
    self.sixes = 0
    self.timeline = deque(maxlen=13)
  @property
  def cantDoBoundaryThisOver(self):
    if self.balls >= 15:
      return self.BoundaryThisOver == 2 
    else:
      return self.BoundaryThisOver == 1  
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
    self.lastOverMaiden = False
    self.currentOverRuns = 0
  @property
  def isOnHattrick(self):
    return len(self.timeline) >= 2 and self.timeline[-1] == "W" and self.timeline[-2] == "W" and (len(self.timeline) == 2 or self.timeline[-3] != "W")
class Inning():
  def __init__(self):
    self.inningId = str(uuid7())
    self.inningNo = None 
    self.battingTeam = None 
    self.bowlingTeam = None 
    self.commentary = deque(maxlen=25)
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
    self.currentPartnership = {"runs": 0, "balls": 0, "batters": {}}
    self.currentOverRuns = 0
    self.lastOverRuns = 0
    self.zeroByBowler = 0
    self.partnerships = {}
    self.fallOfWickets = []
    self.nextBatterId = None
    self.nextBowlerId = None
  def resetPartnership(self):
    if len(self.currentPartnership["batters"]) == 2:
      key = tuple(sorted(self.currentPartnership["batters"].keys()))
      self.partnerships[key] = self.currentPartnership
    if len(self.currentBatters) == 2:
      key = tuple(sorted(b.id for b in self.currentBatters))
      if key in self.partnerships:
        self.currentPartnership = self.partnerships[key]
      else:
        self.currentPartnership = {"runs": 0, "balls": 0, "batters": {b.id: {"runs": 0, "balls": 0} for b in self.currentBatters}}
    else:
      self.currentPartnership = {"runs": 0, "balls": 0, "batters": {b.id: {"runs": 0, "balls": 0} for b in self.currentBatters}}
class Team():
  def __init__(self, name: str = 'Team A', id: int = 1):
    self.name = name
    self.id = id
    self.captain = None 
    self.viceCaptain = None 
    self.players = []
    self.subbedOffIds = []
    self.subbedInIds = []
    self.color = "#14f67c" if id == 1 else "#05a9e6"
  def checkForCaptain(self):
    if self.players and (self.captain is None or self.captain not in self.players):
      if self.viceCaptain:
        self.captain = random.choice([p for p in self.players if p.id != self.viceCaptain.id])
      else:
        self.captain = random.choice(self.players)
    if len(self.players)>= 2 and (self.viceCaptain is None or self.viceCaptain not in self.players):
      self.viceCaptain = random.choice([p for p in self.players if p.id != self.captain.id])
class Player():
  def __init__(self):
    self.user,self.name, self.id, self.mention,self.avatar= 0,0,0,0,0
  def __str__(self): return self.name
  async def send(self,content=None, **kwargs):
    for _ in range(3):
      try:
        return await self.user.send(content, **kwargs)
      except (discord.HTTPException):await asyncio.sleep(1)
  def fromUser(self,user):
    self.user,self.name, self.id, self.mention, self.avatar =user, user.name, user.id, user.mention, user.avatar
    return self
class Game():
  def __init__(self, ctx):
    self.T10 = False
    self.resumed = False
    self.lobbyCreatedAt = time.time()
    self.lobbyLocked = False
    self.bannedUsers = []
    self.gameId = str(uuid7())
    self.drawnByAgreement = False
    self.forfeitedById = None
    self.ctx = customCtx(ctx)
    self.hostId = ctx.author.id
    self.teama = Team('Team A')
    self.teamb = Team('Team B', 2)
    self.started = False 
    self.startedAt = None
    self.batFirstTeam = None
    self.tossStatus = None
    self.innings = []
    self.ballsData = []
    self.repIds: list[int] = []
    self.repLimit: int = 20
    self.v = None
    self.maxBalls = 180
    self.followOnTeam=None
    self.winner = None
    self.mvp = None
    self.DEBUG = False
    self.updateMsg = None
    self.forceYeet = False
  async def checkIfDeletable(self):
    if self.started or len(self.players) >= 6: return 
    if (time.time() - self.lobbyCreatedAt) >= 1800:
      self.ctx.bot.games.pop(self.ctx.channel.id)
      return await self.ctx.send("30 Minutes, Less than 6 players, ig it's time yeet this.")
  async def editGracefully(self, m, content= None, **kwargs):
    for _ in range(3):
      try:
        return await m.edit(content=content, **kwargs)
      except Exception as e:
        print(e)
        await asyncio.sleep(1)
  async def updateMessage(self, newMsg= False):
    if not self.updateMsg or (self.updateMsg.created_at.timestamp()+60) < time.time() or newMsg:
      if self.updateMsg:
        s = self.score(True)
        m = await self.ctx.send(view= self.score())
        s.add_item(ui.TextDisplay(f"-# Update Moved To [New Message]({m.jump_url})"))
        view = ui.LayoutView(timeout=30)
        view.add_item(s)
        await self.editGracefully(self.updateMsg, view = view)
        self.updateMsg = m
      else:
        self.updateMsg = await self.ctx.send(view= self.score())
    else:
      await self.editGracefully(self.updateMsg, view = self.score())
  async def saveData(self):
    if self.matchTotalBalls == 0: return
    await self.ctx.bot.execute("INSERT INTO matches VALUES (?,?,?,?,?,?,?,?, ?)", (self.gameId, self.ctx.channel.id, self.ctx.guild.id, self.teama.name, self.teamb.name, self.winner, self.mvp.id if self.mvp else None,self.maxBalls, 1 if self.drawnByAgreement else 0,))
    data = [(i.inningId, self.gameId, i.runs, i.balls, i.wickets, i.battingTeam.name, i.bowlingTeam.name, 1 if i.declared else 0, 1 if i.followOn else 0,i.inningNo,) for i in self.innings]
    placeholders = ",".join(["?"] * len(data[0]))
    await self.ctx.bot.db.executemany(f"INSERT INTO innings VALUES ({placeholders})", data)
    placeholders = ",".join(["?"] * len(self.ballsData[0]))
    await self.ctx.bot.db.executemany(f"INSERT INTO deliveries VALUES ({placeholders})", self.ballsData)
    await self.ctx.bot.db.commit()
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @property
  def followOnLimit(self):
    if self.DEBUG: return 5
    return max(10, math.ceil(self.maxBalls * 5 / 36))
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
    if self.T10: return
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
    if not self.T10:
      inn=self.currentInning
      bat=inn.battingTeam
      bowl=inn.bowlingTeam
      batTotal=self.teamTotal(bat)
      bowlTotal=self.teamTotal(bowl)
      innsBat=len(self.inningsByTeam(bat))
      innsBowl=len(self.inningsByTeam(bowl))
      if len(self.innings)==1:return f"{bat.name} are batting"
      if inn.inningNo == 2:
        lead=bowlTotal-batTotal
        if lead>=self.followOnLimit:
          avoidFO = (lead - self.followOnLimit)+1 
          return f"{bat.name} need {avoidFO} runs to avoid follow-on."
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
    else:
      inn=self.currentInning
      bat=inn.battingTeam
      bowl=inn.bowlingTeam
      batTotal=self.teamTotal(bat)
      bowlTotal=self.teamTotal(bowl)
      innsBat=len(self.inningsByTeam(bat))
      innsBowl=len(self.inningsByTeam(bowl))
      if len(self.innings)==1:return f"{bat.name} are batting"
      batPrev=batTotal-inn.runs
      target=(bowlTotal-batPrev)+1
      need=target-inn.runs
      if need>0:return f"{bat.name} need {need} runs to win"
      return f"{bat.name} have won by {len(bat.players)-inn.wickets} wickets"
  def checkForWinner(self):
    if not self.T10:
      if self.forfeitedById:
        self.winner = self.teama.name if self.forfeitedById == 2 else self.teamb.name 
        return f"{self.winner} won by forfiet"
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
      if self.matchTotalBalls >= self.maxBalls or self.drawnByAgreement:
        self.winner = 'Drawn'
        return "Match Drawn" if not self.drawnByAgreement else  "Match Drawn By Agreement"
      return None
    else:
      if len(self.innings)<2: return 
      else:
        last=self.currentInning
        bat=last.battingTeam
        bowl=last.bowlingTeam
        batTotal=self.teamTotal(bat)
        bowlTotal=self.teamTotal(bowl)
        if bowlTotal > batTotal and not last.currentBatters and len(last.cantBat)==len(bat.players):
          self.winner = bowl.name
          return f"{bowl.name} have won by {bowlTotal-batTotal} runs"
        elif bowlTotal == batTotal and not last.currentBatters and len(last.cantBat)==len(bat.players):
          self.winner = 'Tied'
          return f"Match Tied"
        elif batTotal > bowlTotal:
          self.winner = bat.name
          return f"{bat.name} have won by {len(bat.players)-last.wickets} wickets"
  def mitigatePlayers(self):
    combined= self.players
    total = len(combined)
    mid = total // 2
    extra = total % 2
    self.teama.players = combined[:mid + extra]
    self.teamb.players = combined[mid + extra:]
    self.teama.checkForCaptain();self.teamb.checkForCaptain()
  def subAPlayer(self, userPlaying, userImpact):
    if userPlaying.id not in [p.id for p in self.players]: return 
    if userImpact.id in [p.id for p in self.players]: return
    inn = self.currentInning
    team = self.teama if userPlaying.id in [p.id for p in self.teama.players] else self.teamb 
    player = next(p for p in team.players if p.id == userPlaying.id)
    team.players.remove(player)
    playerObject = Player().fromUser(userImpact)
    team.players.append(playerObject)
    if team.id == inn.battingTeam.id:
      inn.batters[playerObject] = BattingInning(playerObject)
    else:
      inn.bowlers[playerObject] = BowlingInning(playerObject)
    team.subbedOffIds.append(userPlaying.id)
    if userPlaying.id == self.hostId:
      self.hostId = team.captain.id
    team.subbedInIds.append(userImpact.id)
    self.teama.checkForCaptain();self.teamb.checkForCaptain()
    return True
  def join(self, user):
    self.teama.players.append(Player().fromUser(user))
    self.mitigatePlayers()
  async def sendPartnershipGraphic(self, p1, p2, pScore, p1Stats, p2Stats, p1r, p2r):
    img = Image.open(os.path.join(BASE_DIR, "templates", "Pship.png")).convert("RGBA")
    draw = ImageDraw.Draw(img)
    nameFont = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowBold.woff2"), 60)
    PScoreFont = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowBold.woff2"), 200)
    ContributionFont = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowBold.woff2"), 45)
    w1 = nameFont.getlength(p1.name[:8].upper())
    x1 = 90.4 + (320 - w1)/2
    draw.text((x1, 835), p1.name[:8].upper(), font=nameFont, fill=self.currentInning.battingTeam.color, stroke_width= 1)
    w2 = nameFont.getlength(p2.name[:8].upper())
    x2 = 869.6 + (320 - w2)/2
    draw.text((x2, 835), p2.name[:8].upper(), font=nameFont, fill=self.currentInning.battingTeam.color, stroke_width= 1)
    pScore = f"{pScore}*"
    wP = PScoreFont.getlength(str(pScore))
    xP = (1280 - wP) / 2
    draw.text((xP, 384.7), str(pScore).upper(), font=PScoreFont, fill=self.currentInning.battingTeam.color)
    lineFullW = 400
    lineX = 430
    lineY = 750
    total = p1r + p2r 
    if total > 0:
      p1W = lineFullW * (p1r / total)
      p2W = lineFullW * (p2r / total)
    else:
      p1W = p2W = lineFullW /2
    draw.line((lineX, lineY, lineX + p1W, lineY), fill="#E1E5EE", width=50)
    draw.line((lineX + p1W, lineY, lineX + p1W + p2W, lineY), fill=self.currentInning.battingTeam.color, width=50)
    draw.text((408.1, 661.5), p1Stats, font=ContributionFont, fill="white")
    wC = ContributionFont.getlength(p2Stats)
    draw.text((886 - wC, 661.5), p2Stats, font=ContributionFont, fill="white")
    def returnRounded(img):
      mask = Image.new("L", img.size, 0)
      draw = ImageDraw.Draw(mask)
      draw.rounded_rectangle((0, 0, img.width, img.height), radius=18, fill=255)
      img.putalpha(mask)
      return img
    if p1.user.avatar:
      p1Data = await p1.user.avatar.read()
      partner1Pfp = Image.open(BytesIO(p1Data)).convert("RGBA").resize((285, 418), Image.Resampling.LANCZOS)
      partner1Pfp = returnRounded(partner1Pfp)
      img.paste(partner1Pfp, (108, 410), partner1Pfp)
    if p2.user.avatar:
      p2Data = await p2.user.avatar.read()
      partner2Pfp = Image.open(BytesIO(p2Data)).convert("RGBA").resize((285, 418), Image.Resampling.LANCZOS)
      partner2Pfp = returnRounded(partner2Pfp)
      img.paste(partner2Pfp, (887, 410), partner2Pfp)
    with BytesIO() as image_binary:
      img.save(image_binary, 'PNG')
      image_binary.seek(0)
      file= discord.File(fp=image_binary, filename='pship.png')
      c =  ui.LayoutView(timeout= 60)
      container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.battingTeam.color))
      gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(file, spoiler = False))
      container.add_item(gallery)
      c.add_item(container)
      await self.ctx.send(view=c, file=file)
  async def sendNewBatterGraphic(self, *batterPlayers, returnFiles = False):
    files = []
    for batterPlayer in batterPlayers:
      uid = batterPlayer.id
      bot = self.ctx.bot
      q1 = "SELECT (SELECT COUNT(DISTINCT matchId) FROM deliveries WHERE batterId=? OR bowlerId=?),COUNT(DISTINCT inningId),COALESCE(SUM(runs),0),COALESCE(SUM(isWicket),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END) FROM deliveries WHERE batterId=?"
      res1 = await bot.fetchrow(q1, (uid, uid, uid))
      matches = str(res1[0] or 0)
      inns = str(res1[1] or 0)
      runs_val = res1[2] or 0
      wickets = res1[3] or 0
      balls = res1[4] or 0
      avg = str(round((runs_val/wickets), 2)) if wickets else str(runs_val)
      sr = str(round((runs_val*100/balls), 2)) if balls else "0.00"
      runs = str(runs_val)
      q2 = "SELECT SUM(CASE WHEN r>=50 AND r<100 THEN 1 ELSE 0 END),SUM(CASE WHEN r>=100 THEN 1 ELSE 0 END) FROM (SELECT SUM(runs) r FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId)"
      res2 = await bot.fetchrow(q2, (uid,))
      fifties = str(res2[0] or 0)
      hundreds = str(res2[1] or 0)
      q3 = "SELECT r,b,notout FROM (SELECT SUM(runs) r,COUNT(*) b,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END notout FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId ORDER BY r DESC,b ASC LIMIT 1)"
      bb = await bot.fetchrow(q3, (uid,))
      best = f"{bb[0]}*" if bb and bb[2]==1 else str(bb[0]) if bb else "0"
      img = Image.open(os.path.join(BASE_DIR, "templates", "New batter.png")).convert("RGBA")
      draw = ImageDraw.Draw(img)
      nameFont = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowBold.woff2"), 90)
      statsFont = ImageFont.truetype(os.path.join(BASE_DIR, "fonts", "ArchivoNarrowBold.woff2"), 70)
      draw.text((246.6,42.5), batterPlayer.name[:16].upper(), font=nameFont, fill=self.currentInning.battingTeam.color)
      def draw_centered(text, start_x, width, y):
        w = statsFont.getlength(text)
        x = start_x + (width - w)/2
        draw.text((x, y), text, font=statsFont, fill="white")
      draw_centered(matches, 42.5, 126, 295)
      draw_centered(inns, 213.6, 113, 295)
      draw_centered(runs, 358.5, 131.4, 295)
      draw_centered(avg, 521.8, 128.1, 295)
      draw_centered(sr, 687.3, 162.2, 295)
      draw_centered(fifties, 893.6, 47.8, 295)
      draw_centered(hundreds, 1018.9, 64.4, 295)
      draw_centered(best, 1140.2, 66, 295)
      image_binary = BytesIO()
      img.save(image_binary, 'PNG')
      image_binary.seek(0)
      file = discord.File(fp=image_binary, filename=f'{batterPlayer.name}.png')
      files.append(file)
    if returnFiles: 
      return files
    c =  ui.LayoutView(timeout= 60)
    container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.battingTeam.color))
    for bat in files:
      gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(bat, spoiler = False))
      container.add_item(gallery)
      if len(files) == 2:
        container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
    c.add_item(container)
    await self.ctx.send(view=c, files=files)
  async def sendNewBowlerGraphic(self, bowlerPlayer, returnFile = False):
    uid=bowlerPlayer.id
    bot=self.ctx.bot
    q1="SELECT (SELECT COUNT(DISTINCT matchId) FROM deliveries WHERE batterId=? OR bowlerId=?),COUNT(DISTINCT inningId),COALESCE(SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN isWicket ELSE 0 END),0),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END) FROM deliveries WHERE bowlerId=?"
    res1=await bot.fetchrow(q1,(uid,uid,uid))
    matches=str(res1[0] or 0)
    inns=str(res1[1] or 0)
    wkts_val=res1[2] or 0
    runs_val=res1[3] or 0
    balls_val=res1[4] or 0
    wkts=str(wkts_val)
    avg=str(round((runs_val/wkts_val),2)) if wkts_val else "0.00"
    SR=str(round((balls_val/wkts_val),2)) if wkts_val else "0.00"
    q2="SELECT SUM(CASE WHEN w>=5 THEN 1 ELSE 0 END) FROM (SELECT SUM(isWicket) w FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId)"
    res2=await bot.fetchrow(q2,(uid,))
    fifer=str(res2[0] or 0)
    q3="SELECT SUM(CASE WHEN w>=10 THEN 1 ELSE 0 END) FROM (SELECT SUM(isWicket) w FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY matchId)"
    res3=await bot.fetchrow(q3,(uid,))
    teninamatch=str(res3[0] or 0)
    q4="SELECT w,r FROM (SELECT SUM(isWicket) w,SUM(runs) r FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId ORDER BY w DESC,r ASC LIMIT 1)"
    bb=await bot.fetchrow(q4,(uid,))
    best=f"{bb[0]}/{bb[1]}" if bb else "0/0"
    img=Image.open(os.path.join(BASE_DIR,"templates","New bowler.png")).convert("RGBA")
    draw=ImageDraw.Draw(img)
    nameFont=ImageFont.truetype(os.path.join(BASE_DIR,"fonts","ArchivoNarrowBold.woff2"),90)
    statsFont=ImageFont.truetype(os.path.join(BASE_DIR,"fonts","ArchivoNarrowBold.woff2"),70)
    draw.text((246.6,42.5),bowlerPlayer.name[:16].upper(),font=nameFont,fill=self.currentInning.bowlingTeam.color)
    def draw_centered(text,start_x,width,y):
      w=statsFont.getlength(text)
      x=start_x+(width-w)/2
      draw.text((x,y),text,font=statsFont,fill="white")
    draw_centered(matches,42.5,126.5,295)
    draw_centered(inns,213.6,113,295)
    draw_centered(wkts,351.3,123,295)
    draw_centered(avg,521.8,128.1,295)
    draw_centered(fifer,701.9,43.8,295)
    draw_centered(teninamatch,808,77.8,295)
    draw_centered(best,958.9,66,295)
    draw_centered(SR,1090,162.2,295)
    with BytesIO() as image_binary:
      img.save(image_binary,'PNG')
      image_binary.seek(0)
      file=discord.File(fp=image_binary,filename='new_bowler.png')
      if returnFile: return file
      c =  ui.LayoutView(timeout= 60)
      container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.bowlingTeam.color))
      gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(file, spoiler = False))
      container.add_item(ui.TextDisplay("**New Bowler**"))
      container.add_item(gallery)
      c.add_item(container)
      await self.ctx.send(view=c, file=file)
      
  def battingCard(self):
    inn = self.currentInning
    img = Image.open(os.path.join(BASE_DIR, "templates", "battingSummary.png")).convert("RGBA")
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
    overlay = Image.open(os.path.join(BASE_DIR, "templates", "NotOutLine.png")).convert("RGBA")
    def get_order(player):
      try:
        return inn.cantBat.index(player.id)
      except ValueError:
        try:
          return len(inn.cantBat) + inn.battingTeam.players.index(player)
        except:
          return len(inn.cantBat) + len(inn.battingTeam.players)
    ordered_batters = sorted(inn.batters.items(), key=lambda x: get_order(x[0]))
    for p, b in ordered_batters:
      name = p.name.upper()[:15]
      runs = str(b.runs)
      balls = str(b.balls)
      is_not_out = not b.dismissed and b.balls > 0
      status_text = "NOT OUT" if is_not_out else b.dismissedBy
      r_w = font3.getlength(runs)
      b_w = font3.getlength(balls)
      if is_not_out:
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
    img = Image.open(os.path.join(BASE_DIR, "templates", "bowlingSummary.png")).convert("RGBA")
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
    fonts=ImageFont.truetype(os.path.join(os.getcwd(), "fonts/archivo.woff2"),28*1.3325714286)
    fontb=ImageFont.truetype(os.path.join(os.getcwd(), "fonts/canvaSansBold.woff2"),24*1.3325714286)
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
          draw.text((475.8, y2 + 60), runs, font=fonts, fill='White')
          l = fonts.getlength(runs) + 5
          draw.text(((475.8 + l), y2 + 60), balls, font=fontb, fill='White')
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
    if not self.started:
      teamaP = ""
      teambP = ""
      playersData = {}
      for i,p in enumerate(self.teama.players,1):
        playersData[i-1] = {
          "teamName": self.teama.name,
          "playerName": p.name
        }
        teamaP += f"{i}. {p.name} {'(C)' if self.teama.captain and p.id == self.teama.captain.id else ''} {'(VC)' if self.teama.viceCaptain and p.id == self.teama.viceCaptain.id else ''} {'(H)' if p.id == self.hostId else ''} {'(R)' if p.id in self.repIds else ''}\n"
      for i,p in enumerate(self.teamb.players,len(self.teama.players)+1):
        teambP += f"{i}. {p.name} {'(C)' if self.teamb.captain and p.id == self.teamb.captain.id else ''} {'(VC)' if self.teamb.viceCaptain and p.id == self.teamb.viceCaptain.id else ''} {'(H)' if p.id == self.hostId else ''} {'(R)' if p.id in self.repIds else ''}\n"
        playersData[i-1] = {
          "teamName": self.teamb.name,
          "playerName": p.name
        }
      view = ui.LayoutView(timeout= None)
      container = ui.Container(accent_color = discord.Colour.from_str("#0a9b65"))
      tossStatus = f"**Toss:** ❌" if not self.tossStatus else f"-# {self.tossStatus}"
      if not self.T10:
        container.add_item(ui.TextDisplay(f"{tossStatus}\n**Maximum Overs:**{self.ballsToOvers(self.maxBalls)}\n**Rep Limit:** {self.repLimit}"))
        actionRow = ui.ActionRow()
        actionRow.add_item(OversSelection())
        container.add_item(actionRow)
        container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      else:
        container.add_item(ui.TextDisplay(f"**Toss:** {'✅' if self.batFirstTeam else '❌'}\n**T10:** ✅\n**Rep Limit:** {self.repLimit}"))
        
      container.add_item(ui.TextDisplay(f"### {self.teama.name}\n{teamaP}"))
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      container.add_item(ui.TextDisplay(f"### {self.teamb.name}\n{teambP}"))
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      actionRow = ui.ActionRow()
      if len(self.players) >= 2:
        actionRow.add_item(PlayersSwapSelection(playersData))
        container.add_item(actionRow)
      view.add_item(container)
    else:
      teamaP = ""
      teambP = ""
      for i,p in enumerate(self.teama.players,1):
        s =self.giveDescription(p.id, True, True)
        if s != "":sc = f"\n`{s}`\n"
        else: sc = "\n"
        teamaP += f"**`{i}. {p.name} {'(C)' if p.id == self.teama.captain.id else ''} {'(VC)' if self.teama.viceCaptain and p.id == self.teama.viceCaptain.id else ''} {'(H)' if p.id == self.hostId else ''} {'(R)' if p.id in self.repIds else ''}`**{sc}"
      for i,p in enumerate(self.teamb.players,len(self.teama.players)+1):
        s =self.giveDescription(p.id, True, True)
        if s != "":sc = f"\n`{s}`\n"
        else: sc = "\n"
        teambP += f"**`{i}. {p.name} {'(C)' if p.id == self.teamb.captain.id else ''} {'(VC)' if self.teamb.viceCaptain and p.id == self.teamb.viceCaptain.id else ''} {'(H)' if p.id == self.hostId else ''} {'(R)' if p.id in self.repIds else ''}`**{sc}"
      t = {}
      for i in self.innings:
        s = f"{i.runs}/{i.wickets} {'(f/o) ' if i.inningNo == 3 and self.followOnTeam else ''} {'(D) ' if i.declared else ''}"
        if i.inningNo == self.currentInning.inningNo:
          if not self.T10:
            s += f" ({self.ballsToOvers(i.balls)})"
          else:
            s += f" ({self.ballsToOvers(i.balls)}/10)"
        if i.battingTeam.name in t: t[i.battingTeam.name] += f"& {s}"
        else: t[i.battingTeam.name] = s
      view = ui.LayoutView(timeout= None)
      container = ui.Container(accent_color = discord.Colour.from_str("#0a9b65"))
      container.add_item(ui.TextDisplay(f"**follow-on Limit:** {self.followOnLimit}\n**Maximum Overs:**{self.ballsToOvers(self.maxBalls)}\n**Rep Limit:** {self.repLimit}\n-# **Toss:** {self.tossStatus}"))
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      container.add_item(ui.TextDisplay(f"### {self.teama.name} {t.get(self.teama.name, 'YTB')}\n{teamaP}"))
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      container.add_item(ui.TextDisplay(f"### {self.teamb.name} {t.get(self.teamb.name, 'YTB')}\n{teambP}"))
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      container.add_item(ui.TextDisplay(f"-# [{self.matchStatus()}]({self.updateMsg.jump_url})"))
      view.add_item(container)
    return view
  async def toss(self):
    if not self.teamb.captain: return 
    self.tossStatus = 'Underway'
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
    coinResult = random.choice(['Heads', 'Tails'])
    if view.value:
      winner = picker if view.value == coinResult else other
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
        self.tossStatus = f"**{winner.name}** have won the toss and have elected to {view.value} first"
        await self.ctx.send(f"**{winner.name} have won the toss and have elected to {view.value} first**")
        if view.value == 'Bat':self.batFirstTeam = winner
        else:self.batFirstTeam = other
      else:
        self.tossStatus= None
    else:
      self.tossStatus = None
  def textScore(self):
    t = {}
    for i in self.innings:
      s = f"{i.runs}/{i.wickets}{'(f/o)' if i.inningNo == 3 and self.followOnTeam else ''}{'(D)' if i.declared else ''}"
      if i.inningNo == self.currentInning.inningNo:
        s += f" ({self.ballsToOvers(i.balls)}{'/10' if self.T10 else ''})"
      if i.battingTeam.name in t:
        t[i.battingTeam.name] += f" & {s}"
      else:
        t[i.battingTeam.name] = s
    scoreLine = " | ".join(f"{k} {v}" for k, v in t.items())
    inn = self.currentInning
    batters = " ".join(f"{b.name} {inn.batters[b].runs}({inn.batters[b].balls})" for b in inn.currentBatters)
    bowlers = " ".join(f"{b.name} {inn.bowlers[b].wickets}/{inn.bowlers[b].runsConceded}({self.ballsToOvers(inn.bowlers[b].balls)})" for b in inn.currentBowlers)
    if len(self.currentInning.currentBatters) == 2:
      p = self.currentInning.currentPartnership
      pship= f"\n-# P'ship: {p['runs']} ({p['balls']})"
    else: 
      pship = ""
    return f"**{scoreLine}**\n-# Batters: {batters}{pship}\n-# Bowlers: {bowlers}\n-# {self.matchStatus()}"
    
  def score(self, returnContainer=False):
    view = ui.LayoutView(timeout=30)
    container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.battingTeam.color))
    DaysAndSessions = self.getDaysAndSessions()
    if not self.T10:
      container.add_item(ui.TextDisplay(f"**Day {DaysAndSessions[0]} | Session {DaysAndSessions[1]}**"))
    else: 
      container.add_item(ui.TextDisplay(f"**T10**"))
    t = {}
    for i in self.innings:
      s = f"{i.runs}/{i.wickets} {'(f/o) ' if i.inningNo == 3 and self.followOnTeam else ''} {'(D) ' if i.declared else ''}"
      if i.inningNo == self.currentInning.inningNo:
        if not self.T10:
          s += f" ({self.ballsToOvers(i.balls)})"
        else:
          s += f" ({self.ballsToOvers(i.balls)}/10)"
      if i.battingTeam.name in t: t[i.battingTeam.name] += f"& {s}"
      else: t[i.battingTeam.name] = s
    Score = "\n".join(f"**`{k.ljust(18)}{v}`**" for k,v in t.items())
    if not self.T10:
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
    rows=["```py\n"]+[f"{b.name.ljust(16)}{str(self.currentInning.batters[b].runs).rjust(4)}{str(self.currentInning.batters[b].balls).rjust(4)}{str(self.currentInning.batters[b].sr).rjust(9)}\nCan Do 0: {'✅' if self.currentInning.batters[b].consecutiveDots!=3 else '❌'}  Can Do 4,6: {'✅' if self.currentInning.batters[b].cantDoBoundaryThisOver is not True else '❌'}" for b in self.currentInning.currentBatters]
    runRate = round((self.currentInning.runs/self.currentInning.balls)*6,2) if self.currentInning.balls else 0.00 
    extraInfo = f"RR: {runRate}"
    actionRow = ui.ActionRow()
    if not self.T10:
      if self.currentInning.inningNo == 4:
        runsReq = self.teamTotal(self.currentInning.bowlingTeam) - self.teamTotal(self.currentInning.battingTeam) 
        ballsRem = self.maxBalls - self.matchTotalBalls
        reqRunRate = round((runsReq/ballsRem)*6,2) if ballsRem else runsReq
        extraInfo = f"RR: {runRate} RRR: {reqRunRate}"
    else:
      if self.currentInning.inningNo == 2:
        runsReq = self.teamTotal(self.currentInning.bowlingTeam) - self.teamTotal(self.currentInning.battingTeam) 
        ballsRem = 60 - self.currentInning.balls
        reqRunRate = round((runsReq/ballsRem)*6,2) if ballsRem else runsReq
        extraInfo = f"RR: {runRate} RRR: {reqRunRate}"
    for i, b in enumerate(self.currentInning.currentBatters):actionRow.add_item(ShowScoreButton(Game=self,BatterIndex=i))
    if len(self.currentInning.currentBatters) == 2:
      p = self.currentInning.currentPartnership
      pship= f"P'ship: {p['runs']} ({p['balls']})"
      rows += [f"{pship} {extraInfo}\n```"]
    else: rows += [f"{extraInfo}\n```"]
    BatterScore = "\n".join([header] + rows)
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(BatterScore))
    if self.currentInning.currentBatters:
      container.add_item(actionRow)
    header = f"**` {'Bowlers'.ljust(16)}{'R'.rjust(4)}{'W'.rjust(4)}{'O'.rjust(9)}`**"
    rows = ["```py\n"] + [f"{b.name.ljust(16)}{str(self.currentInning.bowlers[b].runsConceded).rjust(4)}{str(self.currentInning.bowlers[b].wickets).rjust(4)}{str(self.ballsToOvers(self.currentInning.bowlers[b].balls)).rjust(9)}" for b in self.currentInning.currentBowlers] + ["\n```"]
    BowlersScore = "\n".join([header] + rows)
    actionRow = ui.ActionRow()
    for i,b in enumerate(self.currentInning.currentBowlers):
      actionRow.add_item(ShowScoreButton(Game=self,BowlerIndex=i))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add_item(ui.TextDisplay(BowlersScore))
    if self.currentInning.currentBowlers:
      container.add_item(actionRow)
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    if len(self.currentInning.timeline) > 0:
      container.add_item(ui.TextDisplay(" • ".join([f'**{t}**' for t in self.currentInning.timeline])))
    container.add_item(ui.TextDisplay(f"-# {self.matchStatus()}"))
    if self.currentInning.currentBowlers:
      bowler_p=self.currentInning.bowlers[self.currentInning.currentBowlers[0]]
      if bowler_p.isOnHattrick or (self.currentInning.balls >=6 and bowler_p.lastOverMaiden and not self.currentInning.zeroByBowler):
        container.add_item(ui.TextDisplay(f"-# ⚠️Bowler can do 0"))
    view.add_item(container)
    return view if returnContainer is False else container
  def nextBattingTeam(self):
    if not self.innings: return self.batFirstTeam
    if self.followOnTeam is not None and self.innings[-1].inningNo == 2:
      return self.followOnTeam
    return self.teamb if self.innings[-1].battingTeam == self.teama else self.teama
  def giveDescription(self, playerId, batting= False, bowling= False):
    bati=[]
    bowli=[]
    player = next(p for p in self.players if p.id == playerId)
    for inn in self.innings:
      if player in inn.batters:
        i=inn.batters[player]
        bati.append(f"{i.runs}({i.balls}){'*' if not i.dismissed else ''}")
      if player in inn.bowlers:
        i=inn.bowlers[player]
        bowli.append(f"{i.runsConceded}/{i.wickets} ({self.ballsToOvers(i.balls)})")
    bat, bowl = " & ".join(bati), " & ".join(bowli)
    if batting and bowling:
      if bat and bowl: return " | ".join([bat,bowl])
      if bat: return bat
      if bowl: return bowl
    elif batting:return bat if bati else ""
    elif bowling: return bowl if bowli else ""
    return ""
  async def selectBowler(self,isStart= False):
    for i in range(2):
      try:
        inn=self.currentInning
        captain=inn.bowlingTeam.captain
        options=[{'name':p.name,'id':p.id, 'description': self.giveDescription(p.id, bowling= True)} for p in inn.bowlingTeam.players if (len(inn.currentBowlers) == 0 or p.id != inn.currentBowlers[0].id) and p.id not in self.repIds and p.id not in inn.bowlingTeam.subbedOffIds]
        if len(options) == 1:
          pid = options[0]['id']
          inn.currentBowlers.appendleft(next(p for p in inn.bowlingTeam.players if p.id==pid))
          if inn.bowlers[inn.currentBowlers[0]].balls == 0:await self.sendNewBowlerGraphic(inn.currentBowlers[0])
          await self.updateMessage()
          return
        if inn.nextBowlerId and inn.nextBowlerId in [b['id'] for b in options]:
          pid = inn.nextBowlerId 
          inn.currentBowlers.appendleft(next(p for p in inn.bowlingTeam.players if p.id==pid))
          if inn.bowlers[inn.currentBowlers[0]].balls == 0:await self.sendNewBowlerGraphic(inn.currentBowlers[0])
          inn.nextBowlerId = None 
          await self.updateMessage()
          return 
        view=ui.LayoutView(timeout=30)
        view.value=None
        actionRow = ui.ActionRow().add_item(Selection(captain.id,options,1,'Select Bowler'))
        view.add_item(ui.TextDisplay(f"{captain.mention} select bowler"))
        view.add_item(actionRow)
        m = await self.ctx.send(view=view)
        view.m= m
        await view.wait()
        pid=view.value or random.choice(options)['id']
        inn.currentBowlers.appendleft(next(p for p in inn.bowlingTeam.players if p.id==pid))
        if inn.bowlers[inn.currentBowlers[0]].balls == 0 and not isStart:await self.sendNewBowlerGraphic(inn.currentBowlers[0])
        if inn.balls != 0:
          await self.updateMessage()
        if not view.value: 
          await self.ctx.send(f"{inn.bowlingTeam.captain.mention} Failed to respond in time, therefore {inn.bowlingTeam.viceCaptain.mention} (VC) is being appointed as Captain")
          inn.bowlingTeam.captain = inn.bowlingTeam.viceCaptain
          inn.bowlingTeam.viceCaptain = None 
          inn.bowlingTeam.checkForCaptain()
        break
      except:
        pass
  async def selectOpeners(self):
    for i in range(2):
      try:
        inn=self.currentInning
        captain=inn.battingTeam.captain
        options=[{'name':p.name,'id':p.id, 'description': self.giveDescription(p.id, batting= True)} for p in inn.battingTeam.players if p.id not in inn.battingTeam.subbedOffIds]
        view=ui.LayoutView(timeout=30)
        view.value=None
        actionRow = ui.ActionRow().add_item(Selection(captain.id,options,2,'Select Openers'))
        view.add_item(ui.TextDisplay(f"{captain.mention} select openers"))
        view.add_item(actionRow)
        view.m = await self.ctx.send(view=view)
        await view.wait()
        ids=view.value or random.sample([i['id'] for i in options], k= 2)
        inn.currentBatters=[next(p for p in inn.battingTeam.players if p.id == ids[k]) for k in range(2)]
        inn.cantBat.extend(ids)
        inn.resetPartnership()
        if not view.value: 
          await self.ctx.send(f"{inn.battingTeam.captain.mention} Failed to respond in time, therefore {inn.battingTeam.viceCaptain.mention} (VC) is being appointed as Captain")
          inn.battingTeam.captain = inn.battingTeam.viceCaptain
          inn.battingTeam.viceCaptain = None 
          inn.battingTeam.checkForCaptain()
        break
      except: pass   
  async def selectNextBatter(self):
    for i in range(2):
      try:
        inn=self.currentInning
        captain=inn.battingTeam.captain
        used={p.id for p in inn.currentBatters}
        options=[{'name':p.name,'id':p.id, 'description': self.giveDescription(p.id, batting= True)} for p in inn.battingTeam.players if p.id not in inn.cantBat and p.id not in inn.battingTeam.subbedOffIds]
        if len(options) == 1:
          pid = options[0]['id']
          inn.currentBatters.insert(0,next(p for p in inn.battingTeam.players if p.id==pid))
          inn.cantBat.append(pid)
          if not int(pid) in inn.currentPartnership['batters']:inn.resetPartnership()
          await self.updateMessage()
          await self.sendNewBatterGraphic(inn.currentBatters[0])
          return
        if inn.nextBatterId and inn.nextBatterId in [b['id'] for b in options]:
          pid=inn.nextBatterId
          inn.currentBatters.insert(0,next(p for p in inn.battingTeam.players if p.id==pid))
          inn.cantBat.append(pid)
          inn.nextBatterId = None
          await self.sendNewBatterGraphic(inn.currentBatters[0])
          if not int(pid) in inn.currentPartnership['batters']:inn.resetPartnership()
          await self.updateMessage()
          return
        view=ui.LayoutView(timeout=30)
        view.value=None
        actionRow = ui.ActionRow().add_item(Selection(captain.id,options,1,'Select Next Batter'))
        view.add_item(ui.TextDisplay(f"{captain.mention} select next batter"))
        view.add_item(actionRow)
        view.m =await self.ctx.send(view=view)
        await view.wait()
        pid=view.value or random.choice(options)['id']
        inn.currentBatters.insert(0,next(p for p in inn.battingTeam.players if p.id==pid))
        inn.cantBat.append(pid)
        if not int(pid) in inn.currentPartnership['batters']:inn.resetPartnership()
        await self.updateMessage()
        await self.sendNewBatterGraphic(inn.currentBatters[0])
        if not view.value: 
          await self.ctx.send(f"{inn.battingTeam.captain.mention} Failed to respond in time, therefore {inn.battingTeam.viceCaptain.mention} (VC) is being appointed as Captain")
          inn.battingTeam.captain = inn.battingTeam.viceCaptain
          inn.battingTeam.viceCaptain = None 
          inn.battingTeam.checkForCaptain()
        break
      except: pass
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
    if self.checkForWinner() or self.forceYeet: return
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
    await asyncio.gather(self.selectBowler(isStart= True),self.selectOpeners())
    await self.updateMessage(True)
    openersStatsFiles = await self.sendNewBatterGraphic(*inn.currentBatters, returnFiles= True)
    bowlerStatsFile = await self.sendNewBowlerGraphic(inn.currentBowlers[0], returnFile= True)
    c =  ui.LayoutView(timeout= 60)
    container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.battingTeam.color))
    for bat in openersStatsFiles:
      container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(bat, spoiler = False)))
    container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
    container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(bowlerStatsFile, spoiler = False)))
    c.add_item(container)
    await self.ctx.send(view=c, files = openersStatsFiles+ [bowlerStatsFile])
  async def sendToNonStriker(self, content= None, **kwargs):
    if len(self.currentInning.currentBatters) == 2:
      p =self.currentInning.currentBatters[1]
      await asyncio.sleep(0.3)
      await p.send(content, **kwargs)
  def getGif(self,userId,achievement):return self.ctx.bot.staticData['customGIFs'].get(str(userId),{}).get(achievement)
  async def sendWicketGraphic(self, batterName, bowlerName, runsScored, ballsPlayed, FOW, SIXES, FOURS, STRIKERATE, text= None, achievement= None):
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
      if achievement:
        container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"**Also {achievement} for {self.currentInning.currentBowlers[0].name}**"))
        if achievement != "hattrick":
          container.add_item(discord.ui.MediaGallery(discord.MediaGalleryItem(random.choice(self.ctx.bot.Gifs['Bowling']) if self.getGif(self.currentInning.currentBowlers[0].id, achievement) is None else self.getGif(self.currentInning.currentBowlers[0].id, achievement), spoiler = False)))
      c.add_item(container)
      await self.ctx.send(file= i, view= c)
  async def getInputs(self):
    bowlerExtraTXT = ""
    batterExtraTXT = ""
    while True:
      if self.checkForWinner() or self.currentInning.declared or self.forceYeet: return
      ballId = str(uuid7())
      inn=self.currentInning
      striker=inn.currentBatters[0]
      isRep = striker.id in self.repIds
      bowler=inn.currentBowlers[0]
      DaysAndSessions = self.getDaysAndSessions()
      striker_p=inn.batters[striker]
      bowler_p=inn.bowlers[bowler]
      cando0=striker_p.consecutiveDots!=3
      bowlerAllowed = ['1','2','3','4','6']
      if bowler_p.isOnHattrick or (inn.balls >= 6 and bowler_p.lastOverMaiden and not inn.zeroByBowler):
        bowlerAllowed.append('0')
      if cando0 and not striker_p.cantDoBoundaryThisOver:
        allowed={'0','1','2','3','4','6'}
      elif cando0 and striker_p.cantDoBoundaryThisOver:
        allowed={'0','1','2','3'}
      elif not cando0 and striker_p.cantDoBoundaryThisOver:
        allowed={'1','2','3'}
      else:
        allowed={'1','2','3','4','6'}
      def checkBatter(m): return m.author.id==striker.id and m.guild is None and m.content in allowed
      def checkBowler(m): return m.author.id==bowler.id and m.guild is None and m.content in bowlerAllowed
      battxt = f"{batterExtraTXT}\nSend your shot ({','.join(sorted(allowed, key=int))})"
      batview = ui.LayoutView(timeout=None)
      batview.add_item(self.score(True))
      batview.add_item(ui.TextDisplay(battxt))
      batview.add_item(ui.TextDisplay(f"Respond within: 20 second(s)", id = 37))
      bowlview = ui.LayoutView(timeout=None)
      bowlview.add_item(self.score(True))
      bowlview.add_item(ui.TextDisplay(f"{bowlerExtraTXT}\nSend your delivery ({','.join(bowlerAllowed)})"))
      bowlview.add_item(ui.TextDisplay(f"Respond within: 20 second(s)", id = 37))
      msg1= await striker.send(view=batview)
      msg2 = await bowler.send(view=bowlview)
      bat_task=asyncio.create_task(self.ctx.bot.wait_for("message",check=checkBatter))
      bowl_task=asyncio.create_task(self.ctx.bot.wait_for("message",check=checkBowler))
      async def runCountdown():
        start_time = time.time()
        rangesToEdit = [17, 13, 10, 7, 5, 3, 2, 1]
        edited = set()
        while True:
          if bat_task.done() and bowl_task.done(): break
          elapsed = time.time() - start_time
          remaining = 20 - int(elapsed)
          if remaining <= 0: break
          if remaining in rangesToEdit and remaining not in edited:
            edited.add(remaining)
            if not bat_task.done():
              batview.find_item(37).content = f"Respond within: {remaining} second(s)"
              await self.editGracefully(msg1, view=batview)
            if not bowl_task.done():
              bowlview.find_item(37).content = f"Respond within: {remaining} second(s)"
              await self.editGracefully(msg2, view=bowlview)
          await asyncio.sleep(0.5)
      countdown_task= asyncio.create_task(runCountdown())
      done,pending=await asyncio.wait([bat_task,bowl_task, countdown_task],timeout=20)
      bat_ok=bat_task in done and not bat_task.cancelled()
      bowl_ok=bowl_task in done and not bowl_task.cancelled()
      if not bat_ok and not bowl_ok:
        for t in pending: t.cancel()
        bowler_p.AFKs += 1; striker_p.AFKs += 1
        await self.ctx.send(embed= Embed(title="**AFK**", description=f"Both the bowler and batter were afk, replaying the ball. Bowler AFKs: {bowler_p.AFKs}/3\nBatter AFKs: {striker_p.AFKs}/6", color=Color.from_str('#b30707')))
        await asyncio.sleep(0.3)
        await striker.send(f"You didn't respond in time. Replaying the ball.\n{'' if striker_p.AFKs not in [3,6] else 'You are retiring out!'}")
        await asyncio.sleep(0.3)
        if bowler_p.AFKs == 3:
          await bowler.send(f"You didn't respond in time. Replaying the ball.\nYou are retiring from the crease\n-# We know your girlfriend deserves more attention than a fucking discord bot!'")
          bowler_p.AFKs = 0
          inn.nextBowlerId = None
          await self.selectBowler()
          bowlerExtraTXT = ""
        else:
          bowlerExtraTXT = "You didn't respond in time. Replaying the ball."
        if striker_p.AFKs == 3:
          if not(isRep):
            self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.cantDoBoundaryThisOver else 1, 
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
          inn.nextBatterId = None
          await self.selectNextBatter()
          if inn.currentBatters[0].id != striker.id:
            batterExtraTXT = ""
        elif striker_p.AFKs == 6:
          batterExtraTXT = ""
          striker_p.dismissedBy = "AFK"
          striker_p.dismissed = True
          inn.fallOfWickets.append(str(inn.runs))
          p = inn.currentPartnership
          pship= f"**P'ship: {p['runs']} ({p['balls']})**" if len(inn.currentBatters) == 2 else ""
          await self.sendWicketGraphic(striker.name.upper()[:18], striker_p.dismissedBy, str(striker_p.runs), str(striker_p.balls), f"{inn.runs}-{inn.wickets+1}", str(striker_p.sixes), str(striker_p.fours), str(striker_p.sr), pship)
          if not(isRep):
            self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.cantDoBoundaryThisOver else 1, 
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
          if len(inn.cantBat) < len(inn.battingTeam.players):
            inn.nextBatterId = None
            await self.selectNextBatter()
          elif not inn.currentBatters:return 'Inning Over'
        else:
          batterExtraTXT = "You were AFK, try this again."
          if not(isRep):
            self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.cantDoBoundaryThisOver else 1, 
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
        await self.ctx.send(embed= Embed(title="**AFK**", description=f"Batter was afk, replaying the ball\nBatter AFKs: {striker_p.AFKs}/6", color=Color.from_str('#b30707')))
        await asyncio.sleep(0.3)
        if striker_p.AFKs == 3:
          if not(isRep):
            self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.cantDoBoundaryThisOver else 1, 
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
          inn.nextBatterId = None
          await self.selectNextBatter()
          if inn.currentBatters[0].id != striker.id:
            batterExtraTXT = ""
        elif striker_p.AFKs == 6:
          batterExtraTXT = ""
          inn.wickets+=1
          striker_p.dismissedBy = "AFK"
          p = inn.currentPartnership
          pship= f"P'ship: {p['runs']} ({p['balls']})" if len(inn.currentBatters) == 2 else ""
          await self.sendWicketGraphic(striker.name.upper()[:18], striker_p.dismissedBy, str(striker_p.runs), str(striker_p.balls), f"{inn.runs}-{inn.wickets}", str(striker_p.sixes), str(striker_p.fours), str(striker_p.sr), pship)
          inn.fallOfWickets.append(str(inn.runs))
          striker_p.dismissed = True
          if not(isRep):
            self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.cantDoBoundaryThisOver else 1, 
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
          if len(inn.cantBat) < len(inn.battingTeam.players):
            inn.nextBatterId = None
            await self.selectNextBatter()
          elif not inn.currentBatters:return 'Inning Over'
        else:
          if not(isRep):
            self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.cantDoBoundaryThisOver else 1, 
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
        await self.ctx.send(embed= Embed(title="**AFK**", description=f"Bowler was afk, replaying the ball.\nBowler AFKs: {bowler_p.AFKs}/3", color=Color.from_str('#b30707')))
        if not(isRep):
          self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.cantDoBoundaryThisOver else 1, 
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
          inn.nextBowlerId = None
          await self.selectBowler()
          bowlerExtraTXT = ""
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
    inn.currentPartnership["balls"] += 1
    if striker.id not in inn.currentPartnership["batters"]: inn.currentPartnership["batters"][striker.id] = {"runs": 0, "balls": 0}
    inn.currentPartnership["batters"][striker.id]["balls"] += 1
    striker_p.timeline.append(str(bat))
    if bowl == 0:
      inn.zeroByBowler = 1
    if bat!=0: striker_p.consecutiveDots=0
    else: striker_p.consecutiveDots+=1
    if bat==bowl:
      inn.commentary.appendleft({"ball": self.ballsToOvers(inn.balls), "text": f"{bowler.name} ({bat}) to {striker.name} ({bat}), Bowled Em!!"})
      striker_p.dismissed = True 
      inn.wickets+=1
      isHattrick = bowler_p.isOnHattrick
      bowler_p.timeline.append("W")
      if not(isRep):
        self.ballsData.append((
            ballId,
            self.gameId,
            inn.inningId,
            inn.inningNo,
            striker.id,
            None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
            bowler.id,
            1 if cando0 else 0,
            0 if striker_p.cantDoBoundaryThisOver else 1, 
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
      p = inn.currentPartnership
      pship= f"**P'ship: {p['runs']} ({p['balls']})**\n" if len(inn.currentBatters) == 2 else ""
      txt = f"{pship}**The Protagonist -> {bat}**"
      achievement= None
      if bowler_p.wickets < 3 and bowler_p.wickets+1 == 3:achievement = "3fer"
      elif bowler_p.wickets < 5 and bowler_p.wickets+1 == 5:achievement = "5fer"
      elif bowler_p.wickets < 7 and bowler_p.wickets+1 == 7:achievement = "7fer"
      if isHattrick:
        achievement = "hattrick "
      await self.sendWicketGraphic(striker.name.upper()[:18], f"b. {bowler.name.upper()}", str(striker_p.runs), str(striker_p.balls), f"{inn.runs}-{inn.wickets}", str(striker_p.sixes), str(striker_p.fours), str(striker_p.sr), txt, achievement)
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
      if self.T10 and self.currentInning.balls == 60: return 'Inning Over'
    else:
      inn.commentary.appendleft({"ball": self.ballsToOvers(inn.balls), "text": f"{bowler.name} ({bowl}) to {striker.name} ({bat}), and it's {bat} runs"})
      if isRep and (striker_p.runs + bat) >= self.repLimit:
        striker_p.dismissed = True 
        inn.wickets+=1
        excess = striker_p.runs + bat - self.repLimit
        realNumber = bat - excess
        prev_pship= inn.currentPartnership["runs"]
        inn.currentPartnership["runs"] += realNumber
        inn.currentPartnership["batters"][striker.id]["runs"] += realNumber
        curr_pship = inn.currentPartnership["runs"]
        if prev_pship // 50 < curr_pship // 50 and len(inn.currentBatters) > 1:
          p1 = inn.currentBatters[0]
          p2 = inn.currentBatters[1]
          p1s = f"{inn.currentPartnership['batters'][p1.id]['runs']} ({inn.currentPartnership['batters'][p1.id]['balls']})"
          p1r = inn.currentPartnership['batters'][p1.id]['runs']
          p2r = inn.currentPartnership['batters'][p2.id]['runs']
          p2s = f"{inn.currentPartnership['batters'][p2.id]['runs']} ({inn.currentPartnership['batters'][p2.id]['balls']})"
          await self.sendPartnershipGraphic(p1, p2, curr_pship, p1s, p2s, p1r, p2r)
        bowler_p.runsConceded+=realNumber
        bowler_p.currentOverRuns += realNumber
        inn.currentOverRuns += realNumber
        inn.runs+=realNumber
        inn.fallOfWickets.append(str(inn.runs))
        if realNumber in [4,6]:
          if realNumber == 4: striker_p.fours += 1
          if realNumber == 6: striker_p.sixes += 1
        striker_p.runs+=realNumber
        bowler_p.timeline.append(str(bowl))
        inn.timeline.append(f"W{realNumber}")
        p = inn.currentPartnership
        pship= f"**P'ship: {p['runs']} ({p['balls']})**" if len(inn.currentBatters) == 2 else None
        txt = f"{pship}**{striker.name} has reached the rep limit ({self.repLimit}) and therefore he is going off.**"
        if excess:
          txt += f"The batter scored {bat} on the previous delivery, but it has been revised to {realNumber} due to the rep limit."
        await self.sendWicketGraphic(striker.name.upper()[:18], f"REP LIMT REACHED", str(striker_p.runs), str(striker_p.balls), f"{inn.runs}-{inn.wickets}", str(striker_p.sixes), str(striker_p.fours), str(striker_p.sr), txt, None)
        await bowler.send(f"Their score: \n{striker_p.runs} ({striker_p.balls})\nBatter did {bat} (revised to {realNumber} due to rep limit)\nAnd he is out!!")
        await asyncio.sleep(0.3)
        await striker.send(f"Your score: \n{striker_p.runs} ({striker_p.balls})\nBowler did {bowl}. **Your number was reassessed to {realNumber}**\nYou have reached the rep limit with this shot, therefore you are being **declared out**.")
        await asyncio.sleep(0.3)
        await self.sendToNonStriker(f"{striker.name}'s score: \n{striker_p.runs} ({striker_p.balls})\n**Batter digit -> {bat} (reassessed to {realNumber}**\nBowler -> {bowl}")
        await asyncio.sleep(0.3)
        inn.currentBatters.pop(0)
        if len(inn.cantBat) < len(inn.battingTeam.players):
          await self.selectNextBatter()
        elif not inn.currentBatters:
          return 'Inning Over'
        if self.T10 and self.currentInning.balls == 60: return 'Inning Over'
      else:
        bowler_p.currentOverRuns += bat
        inn.currentOverRuns += bat
        bowler_p.timeline.append(str(bowl))
        inn.runs+=bat
        if not(isRep):
          self.ballsData.append((
              ballId,
              self.gameId,
              inn.inningId,
              inn.inningNo,
              striker.id,
              None if len(inn.currentBatters) == 1 else inn.currentBatters[1].id,
              bowler.id,
              1 if cando0 else 0,
              0 if striker_p.cantDoBoundaryThisOver else 1, 
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
          striker_p.BoundaryThisOver += 1
        if striker_p.runs < 30 and striker_p.runs + bat >= 30:
          await self.ctx.send(f"**It is a 30** for [{striker.name}]({random.choice(self.ctx.bot.Gifs['Batting']) if self.getGif(striker.id, '30') is None else self.getGif(striker.id, '30')})")
        elif striker_p.runs < 50 and striker_p.runs + bat >= 50:
          await self.ctx.send(f"**It is a 50** for [{striker.name}]({random.choice(self.ctx.bot.Gifs['Batting']) if self.getGif(striker.id, '50') is None else self.getGif(striker.id, '50')})")
        elif striker_p.runs < 100 and striker_p.runs + bat >= 100:
          await self.ctx.send(f"**It is a HUNDRED** for [{striker.name}]({random.choice(self.ctx.bot.Gifs['Batting']) if self.getGif(striker.id, '100') is None else self.getGif(striker.id, '100')})")
        striker_p.runs+=bat
        bowler_p.runsConceded+=bat
        prev_pship= inn.currentPartnership["runs"]
        inn.currentPartnership["runs"] += bat
        inn.currentPartnership["batters"][striker.id]["runs"] += bat
        curr_pship = inn.currentPartnership["runs"]
        if prev_pship // 50 < curr_pship // 50 and len(inn.currentBatters) > 1:
          p1 = inn.currentBatters[0]
          p2 = inn.currentBatters[1]
          p1s = f"{inn.currentPartnership['batters'][p1.id]['runs']} ({inn.currentPartnership['batters'][p1.id]['balls']})"
          p1r = inn.currentPartnership['batters'][p1.id]['runs']
          p2r = inn.currentPartnership['batters'][p2.id]['runs']
          p2s = f"{inn.currentPartnership['batters'][p2.id]['runs']} ({inn.currentPartnership['batters'][p2.id]['balls']})"
          await self.sendPartnershipGraphic(p1, p2, curr_pship, p1s, p2s,p1r, p2r)
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
        await self.sendToNonStriker(f"{self.textScore()}\n\n**Batter digit -> {bat}**\nBowler -> {bowl}{overEnded}{youRemainOffStrike}")
        inn.timeline.append(f"{bat}")
        if bat%2==1 and len(inn.currentBatters) > 1:
          inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
    if self.T10 and self.currentInning.balls == 60: return 'Inning Over'
    if inn.balls%6==0:
      inn.timeline.append("|")
      inn.lastOverRuns = inn.currentOverRuns
      if inn.currentOverRuns == 0:
        bowler_p.maidens += 1
        bowler_p.lastOverMaiden = True
      else:
        bowler_p.lastOverMaiden = False
      inn.currentOverRuns = 0
      inn.zeroByBowler = 0
      for b in inn.currentBatters:
        inn.batters[b].BoundaryThisOver = 0
      if len(inn.currentBatters) > 1:
        inn.currentBatters[0],inn.currentBatters[1]=inn.currentBatters[1],inn.currentBatters[0]
      await self.updateMessage(True)
      if self.checkForWinner() or self.currentInning.declared or self.forceYeet: return
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
        "channel": self.ctx.channel.id,
        "repLimit": self.repLimit,
        "repIds": self.repIds
      },
      "result": {
        "winner": self.winner,
        "mvp": self.mvp.id if self.mvp else None,
        "status": self.matchStatus()
      },
      "teams": {
        "A": {"name": self.teama.name, "captain": self.teama.captain.id if self.teama.captain else None, "players": [{"id": p.id, "name": p.name, "isRep": p.id in self.repIds} for p in self.teama.players]},
        "B": {"name": self.teamb.name, "captain": self.teamb.captain.id if self.teamb.captain else None, "players": [{"id": p.id, "name": p.name, "isRep": p.id in self.repIds} for p in self.teamb.players]}
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
              "isRep": p.id in self.repIds
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
  async def load_from_state(self,data):
    self.gameId=data["meta"]["id"]
    self.hostId=data["meta"]["host"]
    self.startedAt=data["meta"]["startTime"]
    self.maxBalls=data["meta"]["settings"]["maxBalls"]
    self.T10=data["meta"]["settings"].get("T10",False)
    self.repLimit=data["meta"]["repLimit"]
    self.repIds=data["meta"]["repIds"]
    self.tossStatus=data["meta"].get("tossStatus")
    self.winner=data["result"]["winner"]
    self.drawnByAgreement=data["result"].get("drawnByAgreement",False)
    self.forfeitedById=data["result"].get("forfeitedById")
    self.started=True
    self.ballsData=[tuple(b) for b in data.get("ballsData",[])]
    async def get_player(p_data):
      u = self.ctx.bot.get_user(p_data["id"])
      if not u:
        u=await self.ctx.bot.fetch_user(p_data["id"])
      return Player().fromUser(u)
    self.teama.name=data["teams"]["A"]["name"]
    self.teama.players=[await get_player(p) for p in data["teams"]["A"]["players"]]
    self.teama.subbedOffIds=data["teams"]["A"].get("subbedOffIds",[])
    self.teama.subbedInIds=data["teams"]["A"].get("subbedInIds",[])
    if data["teams"]["A"]["captain"]:
      self.teama.captain=next(p for p in self.teama.players if p.id==data["teams"]["A"]["captain"])
    self.teamb.name=data["teams"]["B"]["name"]
    self.teamb.players=[await get_player(p) for p in data["teams"]["B"]["players"]]
    self.teamb.subbedOffIds=data["teams"]["B"].get("subbedOffIds",[])
    self.teamb.subbedInIds=data["teams"]["B"].get("subbedInIds",[])
    if data["teams"]["B"]["captain"]:
      self.teamb.captain=next(p for p in self.teamb.players if p.id==data["teams"]["B"]["captain"])
    if data["meta"].get("batFirstTeam"):
      self.batFirstTeam=self.teama if data["meta"]["batFirstTeam"]==self.teama.id else self.teamb
    if data["meta"].get("followOnTeam"):
      self.followOnTeam=self.teama if data["meta"]["followOnTeam"]==self.teama.id else self.teamb
    for i_data in data["innings"]:
      inn=Inning()
      inn.inningId=i_data["id"]
      inn.inningNo=i_data["number"]
      inn.battingTeam=self.teama if i_data["battingTeam"]==self.teama.name else self.teamb
      inn.bowlingTeam=self.teamb if i_data["bowlingTeam"]==self.teamb.name else self.teama
      inn.runs=i_data["totals"]["runs"]
      inn.wickets=i_data["totals"]["wickets"]
      inn.balls=i_data["totals"]["balls"]
      inn.declared=i_data["flags"]["declared"]
      inn.followOn=i_data["flags"]["followOn"]
      inn.currentOverRuns=i_data["crease"]["currentOverRuns"]
      inn.lastOverRuns=i_data["crease"]["lastOverRuns"]
      inn.zeroByBowler=i_data["crease"]["zeroByBowler"]
      inn.timeline.extend(i_data["crease"]["timeline"])
      pship=i_data["crease"]["currentPartnership"]
      if "batters" in pship:
        pship["batters"]={int(k):v for k,v in pship["batters"].items()}
      else:
        pship["batters"]={pid:{"runs":0,"balls":0} for pid in i_data["crease"]["currentBatters"]}
        # b[2] = inningId, b[9] = isWicket, b[4] = batterId, b[10] = runs, b[15] = batterNum, b[16] = bowlerNum
        for b in reversed([b for b in data.get("ballsData",[]) if b[2]==i_data["id"]]):
          if b[9]==1: break
          if b[4] in pship["batters"]:
            if b[15] is not None and b[16] is not None:
              pship["batters"][b[4]]["runs"]+=b[10]
              pship["batters"][b[4]]["balls"]+=1
      inn.currentPartnership=pship
      inn.fallOfWickets=i_data["crease"].get("fallOfWickets",[])
      inn.nextBatterId=i_data["crease"].get("nextBatterId")
      inn.nextBowlerId=i_data["crease"].get("nextBowlerId")
      for b_data in i_data["batting"]:
        p=next(x for x in inn.battingTeam.players if x.id==b_data["id"])
        bi=BattingInning(p)
        bi.runs=b_data["runs"]
        bi.balls=b_data["balls"]
        bi.dismissed=b_data["dismissed"]
        bi.dismissedBy=b_data.get("dismissedBy","DNB")
        bi.consecutiveDots=b_data["consecutiveDots"]
        bi.BoundaryThisOver=b_data["BoundaryThisOver"]
        bi.AFKs=b_data["AFKs"]
        bi.fours=b_data.get("fours",0)
        bi.sixes=b_data.get("sixes",0)
        bi.timeline.extend(b_data.get("timeline",[]))
        inn.batters[p]=bi
      for b_data in i_data["bowling"]:
        p=next((x for x in inn.bowlingTeam.players if x.id==b_data["id"]), None)
        if not p: continue
        bi=BowlingInning(p)
        bi.runsConceded=b_data["runs"]
        bi.wickets=b_data["wickets"]
        bi.balls=b_data["balls"]
        bi.AFKs=b_data["AFKs"]
        bi.maidens=b_data["maidens"]
        bi.timeline.extend(b_data["timeline"])
        bi.wicketsDigits=b_data.get("wicketsDigits",[])
        bi.lastOverMaiden = b_data.get('lastOverMaiden')
        inn.bowlers[p]=bi
      inn.currentBatters=[next(p for p in inn.battingTeam.players if p.id==pid) for pid in i_data["crease"]["currentBatters"]]
      inn.currentBowlers=deque([next(p for p in inn.bowlingTeam.players if p.id==pid) for pid in i_data["crease"]["currentBowlers"]],maxlen=2)
      inn.cantBat=[p.id for p,b in inn.batters.items() if b.dismissed or p.id in [x.id for x in inn.currentBatters]]
      self.innings.append(inn)
    self.teama.checkForCaptain();self.teamb.checkForCaptain()
  async def start(self):
    try:
      self.started=True 
      if self.resumed: await self.updateMessage(True)
      if not self.startedAt:self.startedAt=time.time()
      try:
        if self.ctx.bot.dev_id in [p.id for p in self.players]: asyncio.create_task(self.ctx.bot.postKhawiData(data= {"status": "started","image": self.ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "started","timestamps": {"start": int(self.startedAt*1000)} ,"party": {'id': self.gameId, 'size': [len(self.players),18]}}))
      except: 
        pass
      for i in range(4 if not self.T10 else 2):
        if self.forceYeet:return
        w=self.checkForWinner()
        if w:break
        if len(self.innings)<=i:
          await self.startInning()
        elif self.innings[i].declared or not self.innings[i].currentBatters:
          continue
        while True:
          if self.forceYeet: return
          g = await self.getInputs()
          
          if self.forceYeet: return
          if self.v:
            self.v.stop()
          if self.currentInning.balls%6 !=0:
            await self.updateMessage()
          w = self.checkForWinner()
          if g != None or w:
            if self.drawnByAgreement or self.forfeitedById: break
            bat,bowl=self.battingCard(), self.bowlingCard()
            c =  ui.LayoutView(timeout= 60)
            container = ui.Container(accent_color=discord.Colour.from_str(self.currentInning.battingTeam.color))
            gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(bat, spoiler = False),discord.MediaGalleryItem(bowl, spoiler = False))
            container.add_item(gallery)
            container.add_item(ui.TextDisplay("-# Graphics: zuhair_asif"))
            c.add_item(container)
            await self.ctx.send(view=c, files=[bat, bowl])
            await asyncio.sleep(3)
            if not self.drawnByAgreement:await self.checkFollowOn()
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
      if not self.drawnByAgreement and not self.forfeitedById:
        mvp= self.calculateMvp()
        hours=int(duration//3600);minutes=int((duration%3600)//60);seconds=int(duration%60)
        formatted=f"MVP: **{mvp.name}**\nThis game took {hours} hours {minutes} minutes {seconds} seconds\n[Full Scorecard](https://ashesdb.vercel.app/match/{self.gameId})"
        if not self.DEBUG and not self.T10:await self.saveData()
        await self.ctx.send(f"{formatted}")
      else:
        hours=int(duration//3600);minutes=int((duration%3600)//60);seconds=int(duration%60)
        formatted=f"**Match Drawn By Agreement**\nThis game took {hours} hours {minutes} minutes {seconds} seconds\n[Full Scorecard](https://ashesdb.vercel.app/match/{self.gameId})"
        if not self.DEBUG and not self.T10:await self.saveData()
        await self.ctx.send(f"{formatted}")
      for p in self.players:
        if p.id in self.ctx.bot.messageCooldownMap:
          self.ctx.bot.messageCooldownMap.pop(p.id)
      self.ctx.bot.games.pop(self.ctx.channel.id)
      try:
        if self.ctx.bot.dev_id in [p.id for p in self.players]: asyncio.create_task(self.ctx.bot.postKhawiData(data= {"status": "ended","image": self.ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(self.startedAt*1000)} ,"party": {'id': self.gameId, 'size': [len(self.players),18]}}))
      except: 
        pass
      try: 
        await self.sendRawStats()
      except Exception as e: 
        traceback.print_exc()
    except Exception as e:
      file = self.ctx.bot.export_live_instance(self)
      await self.ctx.send(content= f"Unfortunately game is bugged due to this error: {e}\nBut don't worry you can ask the owner to fix the issue and resume it from the file.", file= file)
      try:
        if self.ctx.bot.dev_id in [p.id for p in self.players]: asyncio.create_task(self.ctx.bot.postKhawiData(data= {"status": "ended","image": self.ctx.bot.user.avatar.url,"details": "Playing Ashes","state": "lobby","timestamps": {"start": int(self.startedAt*1000)} ,"party": {'id': self.gameId, 'size': [len(self.players),18]}}))
      except: 
        pass
      traceback.print_exc()