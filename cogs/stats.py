import discord
from discord import Embed, Color
from discord import ui 
class Statistics(commands.Cog, name= "Statistics"):
  def __init__(self, bot):
    self.bot = bot
  def ballsToOvers(self,balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
  @commands.command(aliases= ['me'])
  async def profile(self, ctx, target: discord.User = None):
    if not target: target=ctx.author
    cr.execute("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId) FROM deliveries WHERE batterId=? OR bowlerId=?", (uid,uid))
    row=cr.fetchone()
    if not row or row[0]==0: return await ctx.send(f"{target} has not played any games yet.")
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=discord.Colour.from_str("#0a9b65"))
    uid=target.id
    cr=ctx.bot.crsr
    cr.execute("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END),COALESCE(SUM(isWicket),0) FROM deliveries WHERE batterId=?", (uid,))
    matches,innings,total_runs,balls_faced,wickets=row=cr.fetchone()
    cr.execute("SELECT MAX(runs) FROM (SELECT SUM(runs) runs FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId)", (uid,))
    best_batting=cr.fetchone()[0] or 0
    cr.execute("SELECT partnerId,MAX(runs) FROM (SELECT CASE WHEN batterId=? THEN nonStrikerId ELSE batterId END partnerId,SUM(runs) runs FROM deliveries WHERE (batterId=? OR nonStrikerId=?) AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND batterId IS NOT NULL AND nonStrikerId IS NOT NULL GROUP BY partnerId)", (uid,uid,uid,))
    best_partner=cr.fetchone()
    cr.execute("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId),COALESCE(SUM(isWicket),0),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END) FROM deliveries WHERE bowlerId=?", (uid,))
    bowl_matches,bowl_innings,wkts,conceded,balls_bowled=cr.fetchone()
    cr.execute("SELECT w,r,b FROM (SELECT SUM(isWicket) w,SUM(runs) r,COUNT(*) b FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId ORDER BY w DESC,r ASC,b ASC LIMIT 1)", (uid,))
    bb=cr.fetchone()
    best_bowling=f"{bb[0]}/{bb[1]} ({self.ballsToOvers(bb[2])})" if bb else "—"
    nums=[0,1,2,3,4,6]
    bat_pct={}
    bowl_pct={}
    for n in nums:
      cr.execute("SELECT COUNT(*) FROM deliveries WHERE batterId=? AND batterNum=? AND bowlerNum IS NOT NULL", (uid,n))
      c=cr.fetchone()[0]
      bat_pct[n]=round((c/balls_faced)*100,2) if balls_faced else 0
      cr.execute("SELECT COUNT(*) FROM deliveries WHERE bowlerId=? AND bowlerNum=? AND batterNum IS NOT NULL", (uid,n))
      c=cr.fetchone()[0]
      bowl_pct[n]=round((c/balls_bowled)*100,2) if balls_bowled else 0
    bat_sr=round((total_runs*100/balls_faced),2) if balls_faced else 0
    bat_avg=round((total_runs/wickets),2) if wickets else total_runs
    overs=balls_bowled/6
    bowl_econ=round((conceded/overs),2) if overs else 0
    bowl_sr=round((balls_bowled/wkts),2) if wkts else 0
    container.add(ui.TextDisplay(f" | "))
    container.add(ui.TextDisplay(f"### Batting Stats\nMatches: {matches} | Runs: {total_runs} | Innings: {innings}\nBalls: {balls_faced} | Best Batting: {best_batting} "))
    if best_partner and best_partner[0]:
      container.add(ui.TextDisplay(f"Best Partner: {ctx.bot.get_user(best_partner[0])} ({best_partner[1]} runs)"))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add(ui.TextDisplay(f"Bowling Innings: {bowl_innings} | Wickets: {wkts} | Runs Conceded: {conceded}"))
    container.add(ui.TextDisplay(f"Best Bowling: {best_bowling} wickets"))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add(ui.TextDisplay("Batting Num %: "+" ".join([f"{n}:{bat_pct[n]}%" for n in nums])))
    container.add_item(ui.Separator(visible=True, spacing=discord.SeparatorSpacing.small))
    container.add(ui.TextDisplay("Bowling Num %: "+" ".join([f"{n}:{bowl_pct[n]}%" for n in nums])))
    view.add_item(container)
    await ctx.send(view=view)
      
async def setup(bot):await bot.add_cog(Statistics(bot))