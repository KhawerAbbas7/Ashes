import discord, os, json, time, sys, aiohttp, asyncio
from discord.ext import commands, tasks
from dotenv import load_dotenv
from discord import ui
import aiosqlite
from cogs.views import *
import psutil
from psutil import cpu_percent
from io import BytesIO
load_dotenv()
token=os.getenv("TOKEN")
os.environ['JISHAKU_NO_UNDERSCORE'] = 'true'
def human_readable_size(size_bytes):
  if size_bytes < 1024:return f"{size_bytes} bytes"
  elif size_bytes < 1024**2:return f"{size_bytes / 1024:.2f} KB"
  elif size_bytes < 1024**3:return f"{size_bytes / 1024**2:.2f} MB"
  else:return f"{size_bytes / 1024**3:.2f} GB"
async def get_pre(bot, message):
  if not message.guild:return commands.when_mentioned_or(*["", "."])(bot, message) 
  async with bot.settingsdb.execute("SELECT prefix FROM settings WHERE guildId =?", (message.guild.id,)) as cursor:
    p = await cursor.fetchone()
    prefix_return = [p[0] if p else "as!"]
    prefix_return.append('as!')
    return commands.when_mentioned_or(*prefix_return)(bot, message)
class Ashes(commands.Bot):
  def __init__(self, intents= discord.Intents.all(), command_prefix= get_pre,case_insensitive=True, strip_after_prefix= True):
    super().__init__(intents=intents, command_prefix= get_pre,case_insensitive=True, strip_after_prefix= True,help_command=None, owner_ids= {1127649150079606865, 759713678013890560})
    self.supportServerLink = "https://discord.gg/uxchR7sKd2"
    self.creationBlocked= False
    self.games = {}
    self.statsCache = {}
    self.AshesCoin = "<:AshesCoin:1525822431066062879>"
    self.dev_id = 759713678013890560
    self.staticData = {}
    self.bannedUsers = {}
    self.Gifs = {}
    self.messageCooldownMap = {}
    self._debounceKhawiTask = None
  @tasks.loop(seconds= 30)
  async def votesReminders(self):
    timeNow = int(time.time())
    rows = await self.cfetchall("SELECT userId FROM cooldowns WHERE reminded=? AND (? - lastClaimAt) >= 43200 AND command= ?", (0, timeNow, 'vote'))
    for r in rows:
      user = self.get_user(r[0])
      if user:
        view=ui.LayoutView(timeout=30)
        container=ui.Container(accent_color=discord.Colour.from_str("#277de4"))
        b = ui.Button(label="vote here", style=discord.ButtonStyle.link, url="https://top.gg/bot/1443165621100740668/vote")
        container.add_item(ui.Section(f"Your vote at TOPGG is now available, vote now to keep your streak active.", accessory= b))
        view.add_item(container)
        try:
          await user.send(view= view)
        except:
          pass
      await self.cexecute("UPDATE cooldowns SET reminded= ? WHERE userId = ? AND command = ?", (1, r[0], 'vote'))
      await asyncio.sleep(1)
  @tasks.loop(seconds= 30)
  async def gamesDeletionCheck(self):
    for g in self.games.copy().values():
      await g.checkIfDeletable()
  async def _sendKhawiRequest(self, data):
    timeout = aiohttp.ClientTimeout(total=10)
    async with aiohttp.ClientSession(timeout=timeout) as session:
      await session.post("http://de3.bot-hosting.net:20593/ashes",json=data )
  async def updateTOPGG(self):
    headers = {"Authorization": f"Bearer {os.getenv('TOPGGAPIToken')}","Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
      async with session.patch("https://top.gg/api/v1/projects/@me/metrics", headers= headers, json={"server_count": len(self.guilds), "shard_count": 1})
  async def postKhawiData(self, data):
    if self._debounceKhawiTask:
      self._debounceKhawiTask.cancel()
    self._debounceKhawiTask = asyncio.create_task(self._debouncedKhawi(data))
  async def _debouncedKhawi(self, data):
    try:
      await asyncio.sleep(5)
      await self._sendKhawiRequest(data)
    except Exception as e: print(e)
  async def on_guild_channel_delete(self, channel):
    if channel.id in [g.ctx.channel.id for g in self.games.copy().values()]:
      await self.games[channel.id].saveData()
      self.games[channel.id].forceYeet = True
      self.games.pop(channel.id)
  async def on_guild_remove(self, guild):
    await self.updateTOPGG()
    games = [g for g in self.games.copy().values() if g.ctx.guild.id == guild.id]
    if games:
      for g in games:
        await g.saveData()
        g.forceYeet = True
        self.games.pop(g.ctx.channel.id)
  async def on_guild_join(self, guild):
    await self.updateTOPGG()
  async def on_member_remove(self, member):
    guild = member.guild
    for game in self.games.copy().values():
      if guild.id == game.ctx.guild.id:
        if member.id in [p.id for p in game.players]:
          await game.ctx.send(f'**{member.name}** has left the guild.')
  async def checkIfAllowedCategory(self, ctx):
    if ctx.guild and ctx.guild.id == 1459434908932902914 and ctx.channel and ctx.channel.id == 1472117725135376499 and ctx.author.id != 759713678013890560: 
      await ctx.send("Commands are only usable in <#1472116180666941534>", delete_after=4)
      return False
    return True
  def loadStaticData(self):
    self.staticData = json.load(open('staticData.json', 'r'))
    self.Gifs = self.staticData['Gifs']
    self.bannedUsers = {int(k): v for k, v in self.staticData['BannedUsers'].items()}
  async def banCheck(self, ctx):
    if ctx.author and ctx.author.id in self.bannedUsers:
      reason= self.bannedUsers[ctx.author.id]
      raise commands.CheckFailure(f"You're banned from this bot. Reason: {reason}")
    else: return True
  async def setup_hook(self):
    self.loadStaticData()
    self.add_check(self.checkIfAllowedCategory)
    self.add_check(self.banCheck)
    self.db = await aiosqlite.connect(os.path.join(os.getcwd(), 'databases', 'ashes.db'))
    self.settingsdb = await aiosqlite.connect(os.path.join(os.getcwd(), 'databases', 'settings.db'))
    self.currencydb = await aiosqlite.connect(os.path.join(os.getcwd(), 'databases', 'currency.db'))
    await self.db.execute("PRAGMA foreign_keys = ON")
    await self.db.execute("PRAGMA journal_mode = WAL")
    await self.settingsdb.execute("PRAGMA foreign_keys = ON")
    await self.settingsdb.execute("PRAGMA journal_mode = WAL")
    await self.currencydb.execute("PRAGMA foreign_keys = ON")
    await self.currencydb.execute("PRAGMA journal_mode = WAL")
    script = open("schema.sql").read()
    settingsscript = open("settingsdbschema.sql").read()
    currencyscript = open("currency.sql").read()
    await self.db.executescript(script)
    await self.settingsdb.executescript(settingsscript)
    await self.currencydb.executescript(currencyscript)
    await self.load_extension('jishaku')
    await self.load_extension('api')
    for file in os.listdir('cogs'):
      if file.endswith('py') and file not in ['game.py', 'views.py']:await self.load_extension('cogs.' + file[:-3])
    #await self.tree.sync()
  async def on_message(self, message):
    if not message.author.bot and message.channel.type == discord.ChannelType.private and (message.content.startswith(".") or message.content.startswith("+")):
      if message.author.id in self.messageCooldownMap and time.time() - self.messageCooldownMap[message.author.id] < 5:
        return await self.process_commands(message)
      content = message.content[1:]
      if not content: return await self.process_commands(message)
      if len(content) >= 150: return await self.process_commands(message)
      g = next((g for g in self.games.copy().values() if any(message.author.id==p.id for p in g.players)),None)
      if g:
        if message.reference and (replyMsg:= message.reference.resolved):
          if replyMsg.author.id == 1443165621100740668 and replyMsg.content and ":" in replyMsg.content:
            m= replyMsg.content.replace("\n-# Use '+' before message to talk to captain.", "")
            lines = [l for l in m.split("\n") if l.strip()]
            collected = []
            for line in reversed(lines):
              collected.append(line)
              if line.startswith("🗣️"): break
            collected.reverse()
            replyMsg = f"> {'\n'.join(collected)}\n"
          else: replyMsg= None
        else: replyMsg = None
        if message.content.startswith(".") and len(g.currentInning.currentBatters) == 2 and message.author.id in [b.id for b in g.currentInning.currentBatters]:
          p = next(b for b in g.currentInning.currentBatters if b.id != message.author.id) 
          await p.send(f"{replyMsg if replyMsg else ''}🗣️**`{message.author}`:** {content}")
          await message.add_reaction("☑️")
          self.messageCooldownMap[message.author.id] = time.time()
        if message.content.startswith("+") and (message.author.id in [b.id for b in g.currentInning.currentBatters] or message.author.id == g.currentInning.battingTeam.captain.id):
          if message.author.id == g.currentInning.battingTeam.captain.id:
            if message.author.id in [b.id for b in g.currentInning.currentBatters]: return await self.process_commands(message)
            else: 
              for p in g.currentInning.currentBatters:
                await p.send(f"{replyMsg if replyMsg else ''}🗣️**`{message.author} (C):`** {content}\n-# Use '+' before message to talk to captain.")
              await message.add_reaction("☑️")
              self.messageCooldownMap[message.author.id] = time.time()
          else:
            p = g.currentInning.battingTeam.captain
            p2 = next((b for b in g.currentInning.currentBatters if b.id != message.author.id), None) 
            await p.send(f"{replyMsg if replyMsg else ''}🗣️**`{message.author}:`** {content}")
            if p2 and p2.id != p.id:
              await p2.send(f"{replyMsg if replyMsg else ''}🗣️**`{message.author} -> {p.name}(C):`** {content}")
            await message.add_reaction("☑️")
            self.messageCooldownMap[message.author.id] = time.time()
        if (message.author.id == g.currentInning.bowlingTeam.captain.id and g.currentInning.currentBowlers[0].id != message.author.id) or g.currentInning.currentBowlers[0].id == message.author.id:
          p = g.currentInning.bowlingTeam.captain if message.author.id != g.currentInning.bowlingTeam.captain.id else g.currentInning.currentBowlers[0]
          if p.id == message.author.id: 
            return await self.process_commands(message)
          await p.send(f"{replyMsg if replyMsg else ''}🗣️**`{message.author}:`** {content}")
          await message.add_reaction("☑️")
          self.messageCooldownMap[message.author.id] = time.time()
    return await self.process_commands(message)
  async def fetchrow(self, query, params=()):
    key = (query, tuple(params))
    if key in self.statsCache:
      return self.statsCache[key]
    async with self.db.execute(query, params) as cursor:
      r = await cursor.fetchone()
      self.statsCache[key] = r
      return r
  async def fetchall(self, query, params=()):
    key = (query, tuple(params))
    if key in self.statsCache:
      return self.statsCache[key]
    async with self.db.execute(query, params) as cursor:
      r = await cursor.fetchall()
      self.statsCache[key] = r 
      return r
  async def execute(self, query, params=()):
    statsCache = {}
    await self.db.execute(query, params)
    await self.db.commit()
  async def cfetchrow(self, query, params=()):
    async with self.currencydb.execute(query, params) as cursor:
      return await cursor.fetchone()
  async def cfetchall(self, query, params=()):
    async with self.currencydb.execute(query, params) as cursor:
      return await cursor.fetchall()
  async def cexecute(self, query, params=()):
    await self.currencydb.execute(query, params)
    await self.currencydb.commit()
  def export_live_instance(self, game):
    data = {
      "meta": {
        "id": game.gameId,
        "host": game.hostId,
        "startTime": game.startedAt,
        "endTime": time.time(),
        "settings": {"maxBalls": game.maxBalls, "T10": game.T10},
        "guild": game.ctx.guild.id,
        "channel": game.ctx.channel.id,
        "repLimit": game.repLimit,
        "repIds": game.repIds,
        "matchTotalPredictions": game.matchTotalPredictions,
        "tossStatus": game.tossStatus,
        "batFirstTeam": game.batFirstTeam.id if game.batFirstTeam else None,
        "followOnTeam": game.followOnTeam.id if game.followOnTeam else None
      },
      "result": {
        "winner": game.winner,
        "mvp": game.mvp.id if game.mvp else None,
        "status": game.matchStatus(),
        "drawnByAgreement": game.drawnByAgreement,
        "forfeitedById": game.forfeitedById
      },
      "teams": {
        "A": {"name": game.teama.name, "captain": game.teama.captain.id if game.teama.captain else None, "players": [{"id": p.id, "name": p.name, "isRep": p.id in game.repIds} for p in game.teama.players], "subbedOffIds": game.teama.subbedOffIds, "subbedInIds": game.teama.subbedInIds},
        "B": {"name": game.teamb.name, "captain": game.teamb.captain.id if game.teamb.captain else None, "players": [{"id": p.id, "name": p.name, "isRep": p.id in game.repIds} for p in game.teamb.players], "subbedOffIds": game.teamb.subbedOffIds, "subbedInIds": game.teamb.subbedInIds}
      },
      "innings": [
        {
          "id": i.inningId,
          "number": i.inningNo,
          "battingTeam": i.battingTeam.name,
          "bowlingTeam": i.bowlingTeam.name,
          "totals": {"runs": i.runs, "wickets": i.wickets, "balls": i.balls},
          "flags": {"declared": i.declared, "followOn": i.followOn},
          "crease": {
            "currentBatters": [b.id for b in i.currentBatters],
            "currentBowlers": [b.id for b in i.currentBowlers],
            "currentPartnership": {
              "runs": i.currentPartnership["runs"], 
              "balls": i.currentPartnership["balls"], 
              "batters": i.currentPartnership.get("batters", {})
            },
            "timeline": list(i.timeline),
            "currentOverRuns": i.currentOverRuns,
            "lastOverRuns": i.lastOverRuns,
            "zeroByBowler": i.zeroByBowler,
            "fallOfWickets": list(i.fallOfWickets),
            "nextBatterId": i.nextBatterId,
            "nextBowlerId": i.nextBowlerId
          },
          "batting": [
            {
              "id": p.id,
              "name": p.name,
              "runs": b.runs,
              "balls": b.balls,
              "sr": b.sr,
              "dismissed": b.dismissed,
              "dismissedBy": b.dismissedBy,
              "isRep": p.id in game.repIds,
              "consecutiveDots": b.consecutiveDots,
              "BoundaryThisOver": b.BoundaryThisOver,
              "AFKs": b.AFKs,
              "fours": b.fours,
              "sixes": b.sixes,
              "timeline": list(b.timeline)
            } for p, b in i.batters.items()
          ],
          "bowling": [
            {
              "id": p.id,
              "name": p.name,
              "runs": b.runsConceded,
              "wickets": b.wickets,
              "balls": b.balls,
              "economy": round((b.runsConceded / b.balls) * 6, 2) if b.balls else 0.0,
              "timeline": list(b.timeline),
              "AFKs": b.AFKs,
              "maidens": b.maidens,
              "wicketsDigits": list(b.wicketsDigits),
              "lastOverMaiden": b.lastOverMaiden
            } for p, b in i.bowlers.items()
          ]
        } for i in game.innings
      ],
      "ballsData": list(game.ballsData)
    }
    buf = BytesIO(json.dumps(data, indent=2).encode())
    buf.seek(0)
    return discord.File(fp=buf, filename=f"state_export_{game.gameId}.json")
  async def on_command_error(self, ctx, error):
    if isinstance(error,commands.CommandNotFound): pass
    elif isinstance(error, commands.MissingRequiredArgument):
      commandName = ctx.clean_prefix + ctx.command.qualified_name + " " + ctx.command.signature
      param = error.param.name
      startingIndex = commandName.find(param)
      endingIndex = startingIndex + len(param)
      errorMsg = f"```py\n{commandName}\n{' '* startingIndex}{'^'* len(param)}\n```\n**{param}** is the required argument that is missing."
      await ctx.reply(errorMsg)
    elif isinstance(error, commands.NotOwner):
      return await ctx.send('This command is only runnable by the owner.')
    elif isinstance(error, commands.MaxConcurrencyReached):
      return await ctx.send('Please wait for previous request to end.')
    elif isinstance(error, commands.CheckFailure):
      return await ctx.send(str(error))
  async def on_ready(self):
    self.gamesDeletionCheck.start()
    self.votesReminders.start()
  
bot = Ashes()
  
@bot.command(aliases = ['close'])
@commands.is_owner()
async def shut(ctx):
  if len(ctx.bot.games) > 0:
    for game in ctx.bot.games.copy().values():
      if game.started:
        file = ctx.bot.export_live_instance(game)
        await game.ctx.send("Bot is being forced to shut down but don't worry here is the file through which you can ask the owner to resume it.", file = file)
    await ctx.send("There were games going on. But shutting myself down.")
    await ctx.bot.settingsdb.close();await ctx.bot.db.close();await ctx.bot.currencydb.close()
    await ctx.bot.close()
    sys.exit(1)
  await ctx.send("Shutting myself down")
  await ctx.bot.settingsdb.close();await ctx.bot.db.close();await ctx.bot.currencydb.close()
  await ctx.bot.close()
  sys.exit(1)
@bot.command()
async def ping( ctx):
  duration= bot.latency * 1000 
  duration = round(duration, 2)
  embed = discord.Embed(title= 'Pong', color= discord.Color.from_str('#42f5a1'))
  matches=await bot.fetchrow("SELECT COUNT(DISTINCT matchId) as matches  FROM deliveries", ())
  players=await bot.fetchrow("SELECT COUNT(DISTINCT playerId) FROM (SELECT batterId AS playerId FROM deliveries WHERE batterId IS NOT NULL UNION SELECT nonStrikerId FROM deliveries WHERE nonStrikerId IS NOT NULL UNION SELECT bowlerId FROM deliveries WHERE bowlerId IS NOT NULL) t", ())
  dbsize = await bot.fetchrow("SELECT page_count * page_size as size FROM pragma_page_count(), pragma_page_size();",())
  botstats = f"Guilds: {len(ctx.bot.guilds)}\nCurrent Games: {len(ctx.bot.games)}\nMatches so far: {matches[0]}\nPlayers: {players[0]}\nCPU Usage: {cpu_percent()}%\nLatency: {duration}ms\nDatabase size: {human_readable_size(dbsize[0])}"
  embed.description = botstats
  return await ctx.send(embed=embed, content="")
@bot.command(aliases = ["مدد"])
async def help(ctx):
  v = Helpview(ctx)
  await ctx.send(view= v)
@bot.command(description= "Change the way you can call bot in your guild.", extras={'usableBy': 'Anyone with manage_messages permission.'})
@commands.has_permissions(manage_messages=True)
async def prefix(ctx, newPrefix: str):
  if len(newPrefix) > 3: return await ctx.send("The length of prefix must not exceed 3 characters.")
  await bot.settingsdb.execute("INSERT INTO settings (guildId,prefix) VALUES (?,?) ON CONFLICT(guildId) DO UPDATE SET prefix=excluded.prefix", (ctx.guild.id, newPrefix))
  await bot.settingsdb.commit()
  return await ctx.send(f"Bot's new prefix -> `{newPrefix}`")
bot.run(token)