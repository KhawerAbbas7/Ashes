import discord, io
from discord import Embed, Color
from discord import ui 
from prettytable import PrettyTable
from discord.ext import commands, tasks
from cogs.views import *
import matplotlib.pyplot as plt
import numpy as np
from utils import *
from discord.ext.commands.cooldowns import BucketType
def ballsToOvers(balls: int) -> float: return float(f"{balls//6}.{balls % 6}")

class Statistics(commands.Cog, name= "Statistics"):
  def __init__(self, bot):
    self.bot = bot
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @commands.command(aliases= ['me'], description= 'View statistics for yourself or others.')
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def profile(self, ctx, target: NonBotUser = None):
    if not target: target=ctx.author
    v = await makeProfileView(target,ctx)
    if v == "No Games":
      return await ctx.send(f"{target} is yet to play any Ashes game.")
    await ctx.send(view= v)
  @commands.command(aliases= ['vs'], description= 'View statistics for any individual versus another.')
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def matchup(self, ctx, player1: NonBotUser, player2: NonBotUser = None):
    if not player1:
      return await ctx.send("You have provide at least one player to have VS statistics.")
    elif not player2:
      player2 = ctx.author
    if player2.id == player1.id:
      return await ctx.send("You have provide two distinct players to have VS statistics.")
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=discord.Colour.from_str("#0a939b"))
    row=await ctx.bot.fetchrow("SELECT EXISTS(SELECT 1 FROM deliveries WHERE (batterId=? AND bowlerId=?) OR (batterId=? AND bowlerId=?))", (player1.id,player2.id,player2.id,player1.id))
    if not row or row[0] != 1:
      container.add_item(ui.TextDisplay(f"They both are yet to face delivery from each other."))
      container.accent_color = discord.Colour.from_str("#e70e0e")
    else:
      innings,total_runs,balls_faced,wickets= await ctx.bot.fetchrow("SELECT COUNT(DISTINCT inningId),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END),COALESCE(SUM(isWicket),0) FROM deliveries WHERE batterId=? AND bowlerId=?", (player1.id, player2.id))
      bat_avg = round(total_runs/wickets,2) if wickets else total_runs
      bat_sr = round((total_runs*100/balls_faced),2) if balls_faced else 0.00
      d = {
        "Innings": innings,
        "Runs": total_runs,
        "Balls": balls_faced,
        "Outs": wickets,
        "AVG": bat_avg,
        "SR": bat_sr
      }
      txt = "\n".join(f"{k.ljust(12)}{v}" for k,v in d.items())
      container.add_item(ui.TextDisplay(f"**{player1} VS {player2}**\n```py\n{txt}\n```"))
      container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
      innings,total_runs,balls_faced,wickets= await ctx.bot.fetchrow("SELECT COUNT(DISTINCT inningId),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END),COALESCE(SUM(isWicket),0) FROM deliveries WHERE batterId=? AND bowlerId=?", (player2.id, player1.id))
      bat_avg = round(total_runs/wickets,2) if wickets else total_runs
      bat_sr = round((total_runs*100/balls_faced),2) if balls_faced else 0.00
      d = {
        "Innings": innings,
        "Runs": total_runs,
        "Balls": balls_faced,
        "Outs": wickets,
        "AVG": bat_avg,
        "SR": bat_sr
      }
      txt = "\n".join(f"{k.ljust(12)}{v}" for k,v in d.items())
      container.add_item(ui.TextDisplay(f"**{player2} VS {player1}**\n```py\n{txt}\n```"))
    view.add_item(container)
    await ctx.send(view=view)
  @commands.command(aliases= ['lb'], description= 'View the leading performer across different categories.')
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def leaderboard(self, ctx):
    table = PrettyTable(padding_width=5)
    table.field_names = ["Player", "Runs", "Balls"]
    table.align = "l"
    table.border=False
    table.header=True
    table.hrules=0
    table.vrules=0
    table.left_padding_width=0
    rows=await ctx.bot.fetchall("SELECT batterId,SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) FROM deliveries GROUP BY batterId ORDER BY runs DESC LIMIT 10", ())
    for i,r in enumerate(rows,1):
      batterId, runs, balls = r
      batter = ctx.bot.get_user(batterId ) or batterId 
      table.add_row([f"{i}. {batter}", runs,balls])
    v = LBview(ctx, table)
    v.m =await ctx.send(view=v)
  @commands.command(aliases= ['clb'], description= 'View the leading performer across different categories.')
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def currencyleaderboard(self, ctx):
    table = PrettyTable(padding_width=5)
    table.field_names = ["Player", "Coins"]
    table.align = "l"
    table.border=False
    table.header=True
    table.hrules=0
    table.vrules=0
    table.left_padding_width=0
    rows=await ctx.bot.cfetchall("SELECT userId, coins FROM users ORDER BY coins DESC LIMIT 10", ())
    for i,r in enumerate(rows,1):
      userId, coins = r
      user = ctx.bot.get_user(userId ) or userId 
      table.add_row([f"{i}. {user}",coins])
    v = CurrencyLBview(ctx, table)
    v.m =await ctx.send(view=v)
  @commands.command(aliases= ['shamelb'], description= 'View the leading performer across shameful categories.')
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def hallofshame(self, ctx):
    table = PrettyTable(padding_width=5)
    table.field_names = ["Player", "AFKs"]
    table.align = "l"
    table.border=False
    table.header=True
    table.hrules=0
    table.vrules=0
    table.left_padding_width=0
    rows=await self.bot.fetchall("SELECT playerId, SUM(batter_afk+bowler_afk) AS total_afks FROM (SELECT batterId AS playerId, CASE WHEN batterNum IS NULL THEN 1 ELSE 0 END AS batter_afk, 0 AS bowler_afk FROM deliveries WHERE batterId IS NOT NULL UNION ALL SELECT bowlerId AS playerId, 0 AS batter_afk, CASE WHEN bowlerNum IS NULL THEN 1 ELSE 0 END AS bowler_afk FROM deliveries WHERE bowlerId IS NOT NULL) t GROUP BY playerId ORDER BY total_afks DESC LIMIT 10;", ())
    for i,r in enumerate(rows,1):
      batterId, afks = r
      batter = ctx.bot.get_user(batterId ) or batterId 
      table.add_row([f"{i}. {batter}", afks])
    v = ShamefulLBview(ctx, table, "Most AFKs")
    v.m =await ctx.send(view=v)
  @commands.command(aliases= ['Badges'], description= 'View the achievements/Badges.')
  async def achievements(self, ctx, target: NonBotUser = None):
    if not target: target = ctx.author
    Badges = []
    row=await ctx.bot.fetchrow("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId) FROM deliveries WHERE (batterId=? OR bowlerId=?) AND timestamp<=?",(target.id,target.id,1768935600))
    if row[0]!=0:
      Badges.append("early_supporter")
    officialGuild = ctx.bot.get_guild(1459434908932902914) 
    moderatorRole= officialGuild.get_role(1462101976983535721) 
    moderatorIds = [m.id for m in moderatorRole.members]
    if target.id in moderatorIds:
      Badges.append("official_moderator")
    if target.id in ctx.bot.staticData['Tournaments']['1459434908932902914']['WTC SEASON 1']['Winning Players']:
      if target.id == ctx.bot.staticData['Tournaments']['1459434908932902914']['WTC SEASON 1']['Winning Captain']:
        Badges.append("WTCS1winningCap")
      else:
        Badges.append("WTCS1winner")
    if target.id in ctx.bot.staticData['Tournaments']['1459434908932902914']['WTC SEASON 1']['CaptainsIds']:
      Badges.append("WTCS1CAP")
    if target.id in ctx.bot.staticData['Tournaments']['1366370821190451272']['RTC SEASON 1']['CaptainsIds']:
      Badges.append("RTCS1CAP")
    if target.id in ctx.bot.staticData['Tournaments']['1366370821190451272']['RTC SEASON 1']['Winning Players']:
      if target.id == ctx.bot.staticData['Tournaments']['1366370821190451272']['RTC SEASON 1']['Winning Captain']:
        Badges.append("RTCS1winningCap")
      else:
        Badges.append("RTCS1winner")
    firstEverGame = [759713678013890560, 882228764237508628, 998615189651980400, 1038042742858715146]
    if target.id in firstEverGame:
      Badges.append("first_game")
    """
    centurions= await ctx.bot.fetchall("SELECT DISTINCT batterId FROM (SELECT batterId FROM deliveries GROUP BY matchId, inningId, batterId HAVING SUM(runs) >= 100);")
    centurions = [p[0] for p in centurions]
    if target.id in centurions:
      Badges.append("Century Maker")
    """
    rows=await ctx.bot.fetchall("SELECT DISTINCT bowlerId FROM (SELECT bowlerId,CASE WHEN isWicket=1 AND (LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp)=0 OR LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp) IS NULL) AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_hattrick FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL) t WHERE is_hattrick=1;",())
    hattrickTakers=[r[0] for r in rows] 
    if target.id in hattrickTakers:
      Badges.append("hattrick_taker")
    is100games = await ctx.bot.fetchrow("SELECT COUNT(DISTINCT matchId) >= 100 AS has100Plus FROM deliveries WHERE batterId = ? OR bowlerId = ?;",(target.id,target.id))
    is100games = is100games[0]
    if is100games:
      Badges.append("100+_games")
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=discord.Colour.from_str("#0737b3"))
    section = ui.Section(f"## {target}'s Achievements", accessory= discord.ui.Thumbnail(f"https://wsrv.nl/?url={target.avatar.url}&mask=circle" if target.avatar else ctx.bot.user.avatar.url))
    container.add_item(section)
    container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
    for b in Badges:
      container.add_item(ui.Section(f"- {ctx.bot.staticData['achievements'][b]['description']}", accessory= discord.ui.Thumbnail(f"https://wsrv.nl/?url={ctx.bot.staticData['achievements'][b]['img_url']}&w=128&h=128&fit=contain")))
      container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
    view.add_item(container)
    return await ctx.send(view=view)
  @commands.command(aliases= [], description= 'Compare two players')
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def compare(self, ctx, player1: NonBotUser, player2: NonBotUser = None):
    if not player2:
      player2 = ctx.author
    if player2.id == player1.id:
      return await ctx.send("You have provide two distinct players to compare.")
    metrics = ['MATCHES', 'RUNS', 'Batting AVG', 'BATTING S/R', 'WICKETS', 'BOWLING AVG']
    q_bat = "SELECT (SELECT COALESCE(COUNT(DISTINCT matchId),0) FROM deliveries d2 WHERE d2.batterId=d.batterId OR d2.bowlerId=d.batterId),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END),COALESCE(SUM(isWicket),0) FROM deliveries d WHERE batterId=?"
    q_bowl = "SELECT COALESCE(SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN isWicket ELSE 0 END),0),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END) FROM deliveries WHERE bowlerId=?"
    p1_bat = await ctx.bot.fetchrow(q_bat, (player1.id,)) or (0, 0, 0, 0)
    p1_bowl = await ctx.bot.fetchrow(q_bowl, (player1.id,)) or (0, 0, 0)
    player1_vals = np.array([p1_bat[0], p1_bat[1], round(p1_bat[1]/p1_bat[3], 2) if p1_bat[3] else p1_bat[1], round((p1_bat[1]/p1_bat[2])*100, 2) if p1_bat[2] else 0.00, p1_bowl[0], round(p1_bowl[1]/p1_bowl[0], 2) if p1_bowl[0] else 0.00], dtype=float)
    p2_bat = await ctx.bot.fetchrow(q_bat, (player2.id,)) or (0, 0, 0, 0)
    p2_bowl = await ctx.bot.fetchrow(q_bowl, (player2.id,)) or (0, 0, 0)
    player2_vals = np.array([p2_bat[0], p2_bat[1], round(p2_bat[1]/p2_bat[3], 2) if p2_bat[3] else p2_bat[1], round((p2_bat[1]/p2_bat[2])*100, 2) if p2_bat[2] else 0.00, p2_bowl[0], round(p2_bowl[1]/p2_bowl[0], 2) if p2_bowl[0] else 0.00], dtype=float)
    n_metrics = len(metrics)
    totals = player1_vals + player2_vals
    with np.errstate(divide='ignore', invalid='ignore'):
      player1_props = np.where(totals == 0, 0.5, player1_vals / totals)
      player2_props = np.where(totals == 0, 0.5, player2_vals / totals)
    fig, ax = plt.subplots(figsize=(8, n_metrics * 0.8333333333333334), facecolor='#04151f', layout='tight', subplot_kw={'xticks': [], 'yticks': [], 'frame_on': False})
    y_positions = np.arange(n_metrics - 1, -1, -1)
    ax.text(0.20, n_metrics + 0.2, player1.name, color="#d90429", ha="center", va="center", fontsize=16, fontweight="bold")
    ax.text(0.80, n_metrics + 0.2, player2.name, color="white", ha="center", va="center", fontsize=16, fontweight="bold")
    ax.barh(y_positions, player1_props, height=0.25, color='#d90429')
    ax.barh(y_positions, player2_props, height=0.25, left=player1_props, color='#ffffff')
    for y, val1, val2, metric in zip(y_positions, player1_vals, player2_vals, metrics):
      s1 = f"{val1:.2f}" if val1 % 1 else str(int(val1))
      s2 = f"{val2:.2f}" if val2 % 1 else str(int(val2))
      ax.text(-0.05, y, s1, color='white', ha='right', va='center', fontweight='bold', fontsize=12)
      ax.text(1.05, y, s2, color='white', ha='left', va='center', fontweight='bold', fontsize=12)
      ax.text(0.5, y + 0.35, metric, color='white', ha='center', va='center', fontweight='bold', fontsize=12)
    ax.set_xlim(0, 1)
    buffer = io.BytesIO()
    plt.savefig(buffer, format="png", dpi=300)
    plt.close()
    buffer.seek(0)
    await ctx.send(file=discord.File(buffer, filename="compare.png"))
    buffer.close()

async def setup(bot):await bot.add_cog(Statistics(bot))