import discord
from discord import Embed, Color
from discord import ui 
from prettytable import PrettyTable
from discord.ext import commands, tasks
from cogs.views import *
def ballsToOvers(balls: int) -> float: return float(f"{balls//6}.{balls % 6}")

class Statistics(commands.Cog, name= "Statistics"):
  def __init__(self, bot):
    self.bot = bot
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @commands.command(aliases= ['me'], description= 'View statistics for yourself or others.')
  async def profile(self, ctx, target: discord.User = None):
    if not target: target=ctx.author
    v = await makeProfileView(target,ctx)
    if v == "No Games":
      return await ctx.send("Ask this bozo to play games.")
    await ctx.send(view= v)
  @commands.command(aliases= ['vs'], description= 'View statistics for any individual versus another.')
  async def matchup(self, ctx, player1: discord.User = None, player2: discord.User = None):
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
  @commands.command(aliases= ['shamelb'], description= 'View the leading performer across shameful categories.')
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
async def setup(bot):await bot.add_cog(Statistics(bot))