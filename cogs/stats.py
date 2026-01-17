import discord
from discord import Embed, Color
from discord import ui 
from discord.ext import commands, tasks
class Statistics(commands.Cog, name= "Statistics"):
  def __init__(self, bot):
    self.bot = bot
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @commands.command(aliases= ['me'])
  async def profile(self, ctx, target: discord.User = None):
    if not target: target=ctx.author
    uid=target.id
    row=await ctx.bot.fetchrow("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId) FROM deliveries WHERE batterId=? OR bowlerId=?", (uid,uid))
    if not row or row[0]==0: return await ctx.send(f"{target} has not played any games yet.")
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=discord.Colour.from_str("#0a9b65"))
    matches,innings,total_runs,balls_faced,wickets= await ctx.bot.fetchrow("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END),COALESCE(SUM(isWicket),0) FROM deliveries WHERE batterId=?", (uid,))
    bb=await ctx.bot.fetchrow("SELECT r,b,notout FROM (SELECT SUM(runs) r,COUNT(*) b,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END notout FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId ORDER BY r DESC,b ASC LIMIT 1)", (uid,))
    best_batting=f"{bb[0]}({bb[1]}){'*' if bb[2]==1 else ''}" if bb else "—"
    bo=await ctx.bot.fetchrow("SELECT bowlerId, SUM(isWicket) w, COUNT(*) b FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY bowlerId ORDER BY w DESC, b ASC LIMIT 1", (uid,))
    bunny=f"{ctx.bot.get_user(bo[0])} ({bo[1]} times in {bo[2]} balls)" if bo else "—"
    best_partner= await ctx.bot.fetchrow("SELECT partnerId,MAX(runs) FROM (SELECT CASE WHEN batterId=? THEN nonStrikerId ELSE batterId END partnerId,SUM(runs) runs FROM deliveries WHERE (batterId=? OR nonStrikerId=?) AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND batterId IS NOT NULL AND nonStrikerId IS NOT NULL GROUP BY partnerId)", (uid,uid,uid,))
    bowl_matches,bowl_innings,wkts,conceded,balls_bowled=await ctx.bot.fetchrow("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId),COALESCE(SUM(isWicket),0),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END) FROM deliveries WHERE bowlerId=?", (uid,))
    bb=await ctx.bot.fetchrow("SELECT w,r,b FROM (SELECT SUM(isWicket) w,SUM(runs) r,COUNT(*) b FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId ORDER BY w DESC,r ASC,b ASC LIMIT 1)", (uid,))
    best_bowling=f"{bb[0]}/{bb[1]} ({self.ballsToOvers(bb[2])})" if bb else "—"
    fifties,hundreds=await ctx.bot.fetchrow("SELECT SUM(CASE WHEN r>=50 AND r<100 THEN 1 ELSE 0 END),SUM(CASE WHEN r>=100 THEN 1 ELSE 0 END) FROM (SELECT SUM(runs) r FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId)", (uid,))
    top_scores=await ctx.bot.fetchrow("SELECT COUNT(*) FROM (SELECT inningId,batterId,SUM(runs) r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId,batterId) t JOIN (SELECT inningId,MAX(r) mr FROM (SELECT inningId,batterId,SUM(runs) r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId,batterId) x GROUP BY inningId) m ON t.inningId=m.inningId AND t.r=m.mr WHERE t.batterId=?", (uid,))
    top_scores = top_scores[0]
    team_pct=await ctx.bot.fetchrow("SELECT ROUND(SUM(pr)*100.0/SUM(tr),2) FROM (SELECT d.inningId,SUM(CASE WHEN d.batterId=? THEN d.runs ELSE 0 END) pr,SUM(d.runs) tr FROM deliveries d JOIN innings i ON d.inningId=i.inningId WHERE d.batterNum IS NOT NULL AND d.bowlerNum IS NOT NULL GROUP BY d.inningId)", (uid,))
    team_pct=team_pct[0] or 0
    threefers,fivefers=await ctx.bot.fetchrow("SELECT SUM(CASE WHEN w>=3 AND w<5 THEN 1 ELSE 0 END),SUM(CASE WHEN w>=5 THEN 1 ELSE 0 END) FROM (SELECT SUM(isWicket) w FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId)", (uid,))
    nums=[0,1,2,3,4,6]
    bat_pct={}
    bowl_pct={}
    for n in nums:
      c= await ctx.bot.fetchrow("SELECT COUNT(*) FROM deliveries WHERE batterId=? AND batterNum=? AND bowlerNum IS NOT NULL", (uid,n))
      c=c[0]
      bat_pct[n]=round((c/balls_faced)*100,2) if balls_faced else 0
      c=await ctx.bot.fetchrow("SELECT COUNT(*) FROM deliveries WHERE bowlerId=? AND bowlerNum=? AND batterNum IS NOT NULL", (uid,n))
      c=c[0]
      bowl_pct[n]=round((c/balls_bowled)*100,2) if balls_bowled else 0
    bat_sr=round((total_runs*100/balls_faced),2) if balls_faced else 0.00
    bat_avg=round((total_runs/wickets),2) if wickets else total_runs
    overs=balls_bowled/6
    bowl_econ=round((conceded/overs),2) if overs else 0
    bowl_avg = round((conceded/wkts),2) if wkts else 0.00
    bowl_sr=round((balls_bowled/wkts),2) if wkts else 0.00
    battingStatsDict= {
      "Matches":matches,
      "Innings":innings,
      "Runs":total_runs,
      "Balls Played":balls_faced,
      "Batting Avg": bat_avg,
      "Strike Rate":bat_sr,
      "Team Runs %": f"{team_pct}",
      "50s": fifties,
      "100s": hundreds,
      "Top Scored": top_scores,
      "BBI": best_batting,
      "Best Partner": f"{ctx.bot.get_user(best_partner[0])} ({best_partner[1]} Runs)",
      "Bunny Of": bunny
    }
    battxt = "\n".join(f"**`{k.ljust(22)}{v}`**" for k,v in battingStatsDict.items())
    container.add_item(ui.TextDisplay("### Batting Stats\n"+battxt))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    bowlStatsDict = {
      "Innings": bowl_innings,
      "wickets": wkts,
      "Balls Bowled": balls_bowled,
      "Runs Conceded": conceded,
      "3fers": threefers,
      "5fers": fivefers,
      "Bowling Avg": bowl_avg,
      "Bowling SR": bowl_sr,
      "Economy": bowl_econ,
      "Best Bowling": best_bowling
    }
    bowltxt = "\n".join(f"**`{k.ljust(22)}{v}`**" for k,v in bowlStatsDict.items())
    container.add_item(ui.TextDisplay(f"### Bowling Stats\n{bowltxt}"))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    b="\n".join(f"{str(k).ljust(7)}{v}" for k,v in bat_pct.items())
    container.add_item(ui.TextDisplay(f"**Batting Num %:**\n```py\n{b}\n```"))
    b  = "\n".join(f"{str(k).ljust(7)}{v}" for k,v in bowl_pct.items() if k != 0)
    container.add_item(ui.TextDisplay(f"**Bowling Num %:**\n```py\n{b}\n```"))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    view.add_item(container)
    await ctx.send(view=view)
      
async def setup(bot):await bot.add_cog(Statistics(bot))