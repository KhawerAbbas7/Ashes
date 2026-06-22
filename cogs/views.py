import discord
from discord import ui
from prettytable import PrettyTable
from datetime import datetime, timezone, timedelta
def ballsToOvers(balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
def timestampToPKT(ts):
  return (datetime.fromtimestamp(ts,timezone(timedelta(hours=5))).strftime('%-H:%M %d-%b-%y'))
async def build_filters(uid,lastNMatches=0,lastNBatInnings=0,lastNBowlInnings=0,fromTs=0,toTs=0):
  where_bat_main=[];params_bat_main=[];where_bow_main=[];params_bow_main=[]
  where_bat_d=[];params_bat_d=[];where_bow_d=[];params_bow_d=[]
  footer=[]
  if lastNBatInnings>0:
    where_bat_main.append("inningId IN (SELECT inningId FROM (SELECT inningId,MAX(timestamp) ts FROM deliveries WHERE batterId=? GROUP BY inningId ORDER BY ts DESC LIMIT ?))")
    where_bat_d.append("d.inningId IN (SELECT inningId FROM (SELECT inningId,MAX(timestamp) ts FROM deliveries WHERE batterId=? GROUP BY inningId ORDER BY ts DESC LIMIT ?))")
    params_bat_main+=[uid,lastNBatInnings];params_bat_d+=[uid,lastNBatInnings];footer.append(f"Last {lastNBatInnings} batting innings")
  if lastNBowlInnings>0:
    where_bow_main.append("inningId IN (SELECT inningId FROM (SELECT inningId,MAX(timestamp) ts FROM deliveries WHERE bowlerId=? GROUP BY inningId ORDER BY ts DESC LIMIT ?))")
    where_bow_d.append("d.inningId IN (SELECT inningId FROM (SELECT inningId,MAX(timestamp) ts FROM deliveries WHERE bowlerId=? GROUP BY inningId ORDER BY ts DESC LIMIT ?))")
    params_bow_main+=[uid,lastNBowlInnings];params_bow_d+=[uid,lastNBowlInnings];footer.append(f"Last {lastNBowlInnings} bowling innings")
  if lastNMatches>0:
    where_bat_main.append("matchId IN (SELECT matchId FROM deliveries WHERE batterId=? GROUP BY matchId ORDER BY MAX(timestamp) DESC LIMIT ?)")
    where_bow_main.append("matchId IN (SELECT matchId FROM deliveries WHERE bowlerId=? GROUP BY matchId ORDER BY MAX(timestamp) DESC LIMIT ?)")
    where_bat_d.append("d.matchId IN (SELECT matchId FROM deliveries WHERE batterId=? GROUP BY matchId ORDER BY MAX(timestamp) DESC LIMIT ?)")
    where_bow_d.append("d.matchId IN (SELECT matchId FROM deliveries WHERE bowlerId=? GROUP BY matchId ORDER BY MAX(timestamp) DESC LIMIT ?)")
    params_bat_main+=[uid,lastNMatches];params_bow_main+=[uid,lastNMatches];params_bat_d+=[uid,lastNMatches];params_bow_d+=[uid,lastNMatches];footer.append(f"Last {lastNMatches} matches")
  if fromTs and toTs:
    where_bat_main.append("timestamp BETWEEN ? AND ?");where_bow_main.append("timestamp BETWEEN ? AND ?")
    where_bat_d.append("d.timestamp BETWEEN ? AND ?");where_bow_d.append("d.timestamp BETWEEN ? AND ?")
    params_bat_main+=[fromTs,toTs];params_bow_main+=[fromTs,toTs];params_bat_d+=[fromTs,toTs];params_bow_d+=[fromTs,toTs];footer.append(f"From <t:{fromTs}:d> to <t:{toTs}:d>")
  elif fromTs:
    where_bat_main.append("timestamp>=?");where_bow_main.append("timestamp>=?")
    where_bat_d.append("d.timestamp>=?");where_bow_d.append("d.timestamp>=?")
    params_bat_main+=[fromTs];params_bow_main+=[fromTs];params_bat_d+=[fromTs];params_bow_d+=[fromTs];footer.append(f"From <t:{fromTs}:d>")
  elif toTs:
    where_bat_main.append("timestamp<=?");where_bow_main.append("timestamp<=?")
    where_bat_d.append("d.timestamp<=?");where_bow_d.append("d.timestamp<=?")
    params_bat_main+=[toTs];params_bow_main+=[toTs];params_bat_d+=[toTs];params_bow_d+=[toTs];footer.append(f"Up to <t:{toTs}:d>")
  filter_sql_bat=" AND ".join(where_bat_main) if where_bat_main else ""
  filter_sql_bow=" AND ".join(where_bow_main) if where_bow_main else ""
  filter_sql_d_bat=" AND ".join(where_bat_d) if where_bat_d else ""
  filter_sql_d_bow=" AND ".join(where_bow_d) if where_bow_d else ""
  footer_txt=" | ".join(footer) if footer else "All-time"
  return filter_sql_bat,params_bat_main,filter_sql_bow,params_bow_main,filter_sql_d_bat,params_bat_d,filter_sql_d_bow,params_bow_d,footer_txt
async def makeProfileView(target,ctx,lastNMatches=0,lastNInnings=0,lastNBatInnings=0,lastNBowlInnings=0,fromTs=0,toTs=0):
  uid=target.id
  if lastNBatInnings==0 and lastNBowlInnings==0 and lastNInnings>0:
    lastNBatInnings=lastNBowlInnings=lastNInnings
  if isinstance(ctx, discord.ext.commands.Context):
    bot = ctx.bot
    author = ctx.author
  else:
    bot = ctx.client
    author = ctx.user
  row=await bot.fetchrow("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId) FROM deliveries WHERE batterId=? OR bowlerId=?",(uid,uid))
  ogEmoji="<:OG:1463581581984792669>"
  if not row or row[0]==0: return "No Games"
  row=await bot.fetchrow("SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId) FROM deliveries WHERE (batterId=? OR bowlerId=?) AND timestamp<=?",(uid,uid,1768935600))
  og=row[0]!=0
  filter_sql_bat,filter_params_bat,filter_sql_bow,filter_params_bow,filter_sql_d_bat,filter_params_d_bat,filter_sql_d_bow,filter_params_d_bow,footer_txt=await build_filters(uid,lastNMatches,lastNBatInnings,lastNBowlInnings,fromTs,toTs)
  view=ui.LayoutView(timeout=30);view.target=target;view.ctx=ctx
  container=ui.Container(accent_color=discord.Colour.from_str("#0a9b65"))
  container.add_item(ui.Section(f"### {target}'s Stats", accessory= discord.ui.Thumbnail(target.avatar.url if target.avatar else bot.user.avatar.url)))
  container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
  if og or uid in [882988325810614353]:
    container.add_item(ui.TextDisplay(f"{ogEmoji}\n-# I have played a key role in the development and success of this bot."))
    container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
  if uid in bot.staticData['Tournaments']['1459434908932902914']['WTC SEASON 1']['Winning Players']:
    container.add_item(ui.TextDisplay(f"**WTC SEASON 1 WINNER 🏆**" if uid != 1021706711003832352 else "**WTC SEASON 1 WINNER 🏆** as Captain 🥶"))
  q="SELECT (SELECT COUNT(DISTINCT matchId) FROM deliveries d2 WHERE d2.batterId=d.batterId OR d2.bowlerId=d.batterId),COUNT(DISTINCT inningId),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END),COALESCE(SUM(isWicket),0) FROM deliveries d WHERE batterId=?"
  q_params=[uid]
  if filter_sql_bat:
    q+=" AND "+filter_sql_bat;q_params+=filter_params_bat
  matches,innings,total_runs,balls_faced,wickets= await bot.fetchrow(q, tuple(q_params))
  q="SELECT COUNT(*) FROM matches WHERE mvpId=?"
  q_params=[uid]
  if filter_sql_bat:
    q="SELECT COUNT(*) FROM matches WHERE mvpId=? AND matchId IN (SELECT matchId FROM deliveries WHERE batterId=? AND "+filter_sql_bat+")"
    q_params=[uid,uid]+filter_params_bat
  mvps=await bot.fetchrow(q,tuple(q_params));mvps=mvps[0]
  q="SELECT r,b,notout FROM (SELECT SUM(runs) r,COUNT(*) b,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END notout FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId ORDER BY r DESC,b ASC LIMIT 1)"
  q_params=[uid]
  if filter_sql_bat:
    q="SELECT r,b,notout FROM (SELECT SUM(runs) r,COUNT(*) b,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END notout FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bat+" GROUP BY inningId ORDER BY r DESC,b ASC LIMIT 1)"
    q_params=[uid]+filter_params_bat
  bb=await bot.fetchrow(q, tuple(q_params))
  best_batting=f"{bb[0]}({bb[1]}){'*' if bb[2]==1 else ''}" if bb else "—"
  q="SELECT bowlerId, SUM(isWicket) w, COUNT(*) b FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY bowlerId ORDER BY w DESC, b ASC LIMIT 1"
  q_params=[uid]
  if filter_sql_bat:
    q="SELECT bowlerId, SUM(isWicket) w, COUNT(*) b FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bat+" GROUP BY bowlerId ORDER BY w DESC, b ASC LIMIT 1"
    q_params=[uid]+filter_params_bat
  bo=await bot.fetchrow(q, tuple(q_params))
  bunny=f"{bot.get_user(bo[0])} ({bo[1]} times in {bo[2]} balls)" if bo else "—"
  q="SELECT bowlerId, SUM(runs) r, COUNT(*) b FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY bowlerId ORDER BY r DESC, b ASC LIMIT 1"
  
  q_params=[uid]
  if filter_sql_bat:
    q="SELECT bowlerId, SUM(runs) r, COUNT(*) b FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bat+" GROUP BY bowlerId ORDER BY r DESC, b ASC LIMIT 1"
    q_params=[uid]+filter_params_bat
  bo=await bot.fetchrow(q, tuple(q_params))
  ownerOf=f"{bot.get_user(bo[0])} ({bo[1]} runs off {bo[2]} balls)" if bo else "—"
  q="SELECT COUNT(*) FROM (SELECT matchId FROM (SELECT matchId, inningId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId=? GROUP BY matchId, inningId) WHERE total_runs=0 AND got_out=1 GROUP BY matchId HAVING COUNT(*)>=2)"
  q_params=[uid]
  if filter_sql_bat:
    q="SELECT COUNT(*) FROM (SELECT matchId FROM (SELECT matchId, inningId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId=? AND "+filter_sql_bat+" GROUP BY matchId, inningId) WHERE total_runs=0 AND got_out=1 GROUP BY matchId HAVING COUNT(*)>=2)"
    q_params=[uid]+filter_params_bat
  pairs_row=await bot.fetchrow(q, tuple(q_params))
  pairs=pairs_row[0] if pairs_row else 0
  q="SELECT partnerId,MAX(runs) FROM (SELECT CASE WHEN batterId=? THEN nonStrikerId ELSE batterId END partnerId,SUM(runs) runs FROM deliveries WHERE (batterId=? OR nonStrikerId=?) AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND batterId IS NOT NULL AND nonStrikerId IS NOT NULL GROUP BY partnerId)"
  q_params=[uid,uid,uid]
  if filter_sql_bat:
    q="SELECT partnerId,MAX(runs) FROM (SELECT CASE WHEN batterId=? THEN nonStrikerId ELSE batterId END partnerId,SUM(runs) runs FROM deliveries WHERE (batterId=? OR nonStrikerId=?) AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND batterId IS NOT NULL AND nonStrikerId IS NOT NULL AND "+filter_sql_bat+" GROUP BY partnerId)"
    q_params=[uid,uid,uid]+filter_params_bat
  best_partner= await bot.fetchrow(q, tuple(q_params))
  q="SELECT COUNT(*) FROM (SELECT matchId, inningId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId=? GROUP BY matchId, inningId) WHERE total_runs=0 AND got_out=1"
  q_params=[uid]
  if filter_sql_bat:
    q="SELECT COUNT(*) FROM (SELECT matchId, inningId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId=? AND "+filter_sql_bat+" GROUP BY matchId, inningId) WHERE total_runs=0 AND got_out=1"
    q_params=[uid]+filter_params_bat
  ducks_row=await bot.fetchrow(q, tuple(q_params))
  ducks=ducks_row[0] if ducks_row else 0
  q="SELECT COUNT(DISTINCT partnerId) FROM (SELECT CASE WHEN batterId=? THEN nonStrikerId ELSE batterId END partnerId FROM deliveries WHERE (batterId=? OR nonStrikerId=?) AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND batterId IS NOT NULL AND nonStrikerId IS NOT NULL)"
  q_params=[uid,uid,uid]
  if filter_sql_bat:
    q="SELECT COUNT(DISTINCT partnerId) FROM (SELECT CASE WHEN batterId=? THEN nonStrikerId ELSE batterId END partnerId FROM deliveries WHERE (batterId=? OR nonStrikerId=?) AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND batterId IS NOT NULL AND nonStrikerId IS NOT NULL AND "+filter_sql_bat+")"
    q_params=[uid,uid,uid]+filter_params_bat
  unique_partners = await bot.fetchrow(q, tuple(q_params))
  unique_partners = unique_partners[0] if unique_partners else 0
  q="SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId),COALESCE(SUM(isWicket),0),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END) FROM deliveries WHERE bowlerId=?"
  q_params=[uid]
  if filter_sql_bow:
    q="SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId),COALESCE(SUM(isWicket),0),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END) FROM deliveries WHERE bowlerId=? AND "+filter_sql_bow
    q_params=[uid]+filter_params_bow
  bowl_matches,bowl_innings,wkts,conceded,balls_bowled=await bot.fetchrow(q, tuple(q_params))
  q="SELECT w,r,b FROM (SELECT SUM(isWicket) w,SUM(runs) r,COUNT(*) b FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId ORDER BY w DESC,r ASC,b ASC LIMIT 1)"
  q_params=[uid]
  if filter_sql_bow:
    q="SELECT w,r,b FROM (SELECT SUM(isWicket) w,SUM(runs) r,COUNT(*) b FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bow+" GROUP BY inningId ORDER BY w DESC,r ASC,b ASC LIMIT 1)"
    q_params=[uid]+filter_params_bow
  bb=await bot.fetchrow(q, tuple(q_params))
  best_bowling=f"{bb[0]}/{bb[1]} ({ballsToOvers(bb[2])})" if bb else "—"
  q="SELECT SUM(CASE WHEN r>=50 AND r<100 THEN 1 ELSE 0 END),SUM(CASE WHEN r>=100 THEN 1 ELSE 0 END) FROM (SELECT SUM(runs) r FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId)"
  q_params=[uid]
  if filter_sql_bat:
    q="SELECT SUM(CASE WHEN r>=50 AND r<100 THEN 1 ELSE 0 END),SUM(CASE WHEN r>=100 THEN 1 ELSE 0 END) FROM (SELECT SUM(runs) r FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bat+" GROUP BY inningId)"
    q_params=[uid]+filter_params_bat
  fifties,hundreds=await bot.fetchrow(q, tuple(q_params))
  q="SELECT COUNT(*) FROM (SELECT inningId,batterId,SUM(runs) r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId,batterId) t JOIN (SELECT inningId,MAX(r) mr FROM (SELECT inningId,batterId,SUM(runs) r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId,batterId) x GROUP BY inningId) m ON t.inningId=m.inningId AND t.r=m.mr WHERE t.batterId=?"
  q_params=[uid]
  if filter_sql_bat:
    q="SELECT COUNT(*) FROM (SELECT inningId,batterId,SUM(runs) r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bat+" GROUP BY inningId,batterId) t JOIN (SELECT inningId,MAX(r) mr FROM (SELECT inningId,batterId,SUM(runs) r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bat+" GROUP BY inningId,batterId) x GROUP BY inningId) m ON t.inningId=m.inningId AND t.r=m.mr WHERE t.batterId=?"
    q_params=filter_params_bat+filter_params_bat+[uid] if filter_params_bat else [uid]
  top_scores=await bot.fetchrow(q, tuple(q_params));top_scores = top_scores[0]
  q="SELECT ROUND(SUM(pr)*100.0/SUM(tr),2) FROM (SELECT d.inningId,SUM(CASE WHEN d.batterId=? THEN d.runs ELSE 0 END) pr,SUM(d.runs) tr FROM deliveries d JOIN innings i ON d.inningId=i.inningId WHERE d.batterNum IS NOT NULL AND d.bowlerNum IS NOT NULL GROUP BY d.inningId)"
  q_params=[uid]
  if filter_sql_d_bat:
    q="SELECT ROUND(SUM(pr)*100.0/SUM(tr),2) FROM (SELECT d.inningId,SUM(CASE WHEN d.batterId=? THEN d.runs ELSE 0 END) pr,SUM(d.runs) tr FROM deliveries d JOIN innings i ON d.inningId=i.inningId WHERE d.batterNum IS NOT NULL AND d.bowlerNum IS NOT NULL AND "+filter_sql_d_bat+" GROUP BY d.inningId)"
    q_params=[uid]+filter_params_d_bat
  team_pct=await bot.fetchrow(q, tuple(q_params));team_pct=team_pct[0] or 0
  q="SELECT SUM(CASE WHEN w>=3 AND w<5 THEN 1 ELSE 0 END),SUM(CASE WHEN w>=5 THEN 1 ELSE 0 END) FROM (SELECT SUM(isWicket) w FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId)"
  q_params=[uid]
  if filter_sql_bow:
    q="SELECT SUM(CASE WHEN w>=3 AND w<5 THEN 1 ELSE 0 END),SUM(CASE WHEN w>=5 THEN 1 ELSE 0 END) FROM (SELECT SUM(isWicket) w FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bow+" GROUP BY inningId)"
    q_params=[uid]+filter_params_bow
  threefers,fivefers=await bot.fetchrow(q, tuple(q_params))
  q="SELECT COUNT(*) FROM (SELECT CASE WHEN isWicket=1 AND (LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp)=0 OR LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp) IS NULL) AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_hattrick FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL) t WHERE is_hattrick=1"
  q_params=[uid]
  if filter_sql_bow:
    q="SELECT COUNT(*) FROM (SELECT CASE WHEN isWicket=1 AND (LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp)=0 OR LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp) IS NULL) AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_hattrick FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND "+filter_sql_bow+") t WHERE is_hattrick=1"
    q_params=[uid]+filter_params_bow
  hattricks_row=await bot.fetchrow(q, tuple(q_params))
  hattricks=hattricks_row[0] if hattricks_row else 0
  q="SELECT COALESCE(SUM(CASE WHEN m.winner=t.team THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN m.winner!=t.team AND m.winner NOT IN ('Drawn','Tied') THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN m.winner='Drawn' THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN m.winner='Tied' THEN 1 ELSE 0 END),0) FROM matches m JOIN (SELECT d.matchId,MAX(CASE WHEN d.batterId=? THEN i.battingTeam ELSE i.bowlingTeam END) team FROM deliveries d JOIN innings i ON d.inningId=i.inningId WHERE (d.batterId=? OR d.bowlerId=?) GROUP BY d.matchId) t ON m.matchId=t.matchId"
  q_params=[uid,uid,uid]
  if filter_sql_d_bat:
    q="SELECT COALESCE(SUM(CASE WHEN m.winner=t.team THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN m.winner!=t.team AND m.winner NOT IN ('Drawn','Tied') THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN m.winner='Drawn' THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN m.winner='Tied' THEN 1 ELSE 0 END),0) FROM matches m JOIN (SELECT d.matchId,MAX(CASE WHEN d.batterId=? THEN i.battingTeam ELSE i.bowlingTeam END) team FROM deliveries d JOIN innings i ON d.inningId=i.inningId WHERE (d.batterId=? OR d.bowlerId=?) AND "+filter_sql_d_bat+" GROUP BY d.matchId) t ON m.matchId=t.matchId"
    q_params=[uid,uid,uid]+filter_params_d_bat
  won,lost,drawn,tied=await bot.fetchrow(q,tuple(q_params))
  nums=[0,1,2,3,4,6]
  bat_pct={};bowl_pct={}
  for n in nums:
    q="SELECT COUNT(*) FROM deliveries WHERE batterId=? AND batterNum=? AND bowlerNum IS NOT NULL"
    q_params=[uid,n]
    if filter_sql_bat:
      q="SELECT COUNT(*) FROM deliveries WHERE batterId=? AND batterNum=? AND bowlerNum IS NOT NULL AND "+filter_sql_bat
      q_params=[uid,n]+filter_params_bat
    c= await bot.fetchrow(q, tuple(q_params));c=c[0]
    bat_pct[n]=round((c/balls_faced)*100,2) if balls_faced else 0
    q="SELECT COUNT(*) FROM deliveries WHERE bowlerId=? AND bowlerNum=? AND batterNum IS NOT NULL"
    q_params=[uid,n]
    if filter_sql_bow:
      q="SELECT COUNT(*) FROM deliveries WHERE bowlerId=? AND bowlerNum=? AND batterNum IS NOT NULL AND "+filter_sql_bow
      q_params=[uid,n]+filter_params_bow
    c=await bot.fetchrow(q, tuple(q_params));c=c[0]
    bowl_pct[n]=round((c/balls_bowled)*100,2) if balls_bowled else 0
  bat_sr=round((total_runs*100/balls_faced),2) if balls_faced else 0.00
  bat_avg=round((total_runs/wickets),2) if wickets else total_runs
  overs=balls_bowled/6
  bowl_econ=round((conceded/overs),2) if overs else 0
  bowl_avg = round((conceded/wkts),2) if wkts else 0.00
  bowl_sr=round((balls_bowled/wkts),2) if wkts else 0.00
  battingStatsDict={"Innings":innings,"Runs":total_runs,"Balls Played":balls_faced,"Batting Avg": bat_avg,"Strike Rate":bat_sr,"Not Outs": innings - wickets,"Body Count": unique_partners,"Team Runs %": f"{team_pct}","50s": fifties,"100s": hundreds,"Top Scored": top_scores,"BBI": best_batting,"Best Partner": f"{bot.get_user(best_partner[0])} ({best_partner[1]} Runs)","Bunny Of": bunny, "Owner Of": ownerOf,"MVPs": mvps, 'Ducks': ducks, 'Pairs': pairs}
  battxt="\n".join(f"**`{k.ljust(22)}{v}`**" for k,v in battingStatsDict.items())
  container.add_item(ui.TextDisplay("### Batting Stats\n"+battxt))
  container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
  bowlStatsDict={"Innings": bowl_innings,"wickets": wkts,"Balls Bowled": balls_bowled,"Runs Conceded": conceded,"3fers": threefers,"5fers": fivefers,"Hat-tricks": hattricks,"Bowling Avg": bowl_avg,"Bowling SR": bowl_sr,"Economy": bowl_econ,"Best Bowling": best_bowling, "Matches": matches,"Matches Won": won, "Matches Lost": lost, "Matches Drawn": drawn, "Matches Tied": tied}
  bowltxt="\n".join(f"**`{k.ljust(22)}{v}`**" for k,v in bowlStatsDict.items())
  container.add_item(ui.TextDisplay(f"### Bowling Stats\n{bowltxt}"))
  container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
  keys=sorted(set(bat_pct)|set(bowl_pct))
  b="\n".join(f"{str(k).ljust(7)}{str(bat_pct.get(k,'')).ljust(7)}{bowl_pct.get(k,'')}" for k in keys)
  container.add_item(ui.TextDisplay(f"**Num%:**\n```py\n{'Num'.ljust(7)}{'Bat%'.ljust(7)}Bowl%\n{b}\n```"))
  container.add_item(ui.TextDisplay(f"**Num%:**\n```py\n{'Num'.ljust(7)}{'Bat%'.ljust(7)}Bowl%\n{b}\n```"))
  container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
  container.add_item(ui.Section(ui.TextDisplay(f"-# Filters: {footer_txt}"),accessory=FiltersBtn(author.id)))
  container.add_item(ui.TextDisplay(f"-# For more enhanced view and stats visit https://ashesdb.vercel.app/player/{target.id}"))
  view.add_item(container)
  return view
class PlayersSwapSelection(ui.Select):
  def __init__(self, players):
    options = [
      discord.SelectOption(label= v['playerName'], description= v['teamName'], value = k) for k,v in players.items()
      ]
    super().__init__(placeholder= "Swap", min_values=2, max_values=2, options=options)
  async def callback(self, interaction: discord.Interaction):
    g = interaction.client.games[interaction.channel.id]
    if interaction.user.id != g.hostId:
      return await interaction.response.send_message("Only usable by host.", ephemeral= True)
    elif g.started: return
    idx1, idx2 = self.values
    g.swap(int(idx1), int(idx2))
    await interaction.response.edit_message(view= g.showPlayers())
class OversSelection(ui.Select):
  def __init__(self):
    options = [
      discord.SelectOption(label= "90 Overs", description= 'Follow-on: 75', value = 90),
      discord.SelectOption(label= "60 Overs", description= 'Follow-on: 50', value = 60),
      discord.SelectOption(label= "30 Overs", description= 'Follow-on: 25', value = 30),
      ]
    super().__init__(placeholder= "Select Overs", min_values=1, max_values=1, options=options)
  async def callback(self, interaction: discord.Interaction):
    g = interaction.client.games[interaction.channel.id]
    if interaction.user.id != g.hostId:
      return await interaction.response.send_message("Only usable by host.", ephemeral= True)
    elif g.started: return
    g.maxBalls = int(self.values[0])*6
    await interaction.response.edit_message(view= g.showPlayers())
class ShamefulLBSelection(ui.Select):
  def __init__(self, v):
    currentlySelected = v.statType
    options = ["Most AFKs", "Most Ducks","Most Pairs", "Most Runs Conceded In An Inning", "Most Runs Conceded In An Over","Out On Same Number", "Most Wickets Taken Off A Single Batter", "Most Consecutive Innings Without Scoring 10"]
    options = [discord.SelectOption(label= b, value = b) for b in options]
    super().__init__(placeholder= "Select Category", min_values=1, max_values=1, options=options)
  async def callback(self, interaction: discord.Interaction):
    if self.view.ctx.author.id != interaction.user.id: return
    await interaction.response.defer()
    bot = interaction.client
    v = self.values[0]
    if v == 'Most AFKs':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "AFKs"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT playerId, SUM(batter_afk+bowler_afk) AS total_afks FROM (SELECT batterId AS playerId, CASE WHEN batterNum IS NULL THEN 1 ELSE 0 END AS batter_afk, 0 AS bowler_afk FROM deliveries WHERE batterId IS NOT NULL UNION ALL SELECT bowlerId AS playerId, 0 AS batter_afk, CASE WHEN bowlerNum IS NULL THEN 1 ELSE 0 END AS bowler_afk FROM deliveries WHERE bowlerId IS NOT NULL) t GROUP BY playerId ORDER BY total_afks DESC LIMIT 10;", ())
      for i,r in enumerate(rows,1):
        playerId, x = r
        player = bot.get_user(playerId ) or playerId 
        table.add_row([f"{i}. {player}", x])
      self.view.stop()
      v = ShamefulLBview(self.view.ctx, table,self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Ducks':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Ducks"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("WITH inning_totals AS (SELECT matchId, inningId, batterId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId IS NOT NULL GROUP BY matchId, inningId, batterId) SELECT batterId, COUNT(*) AS ducks FROM inning_totals WHERE total_runs=0 AND got_out=1 GROUP BY batterId ORDER BY ducks DESC LIMIT 10;", ())
      for i,r in enumerate(rows,1):
        playerId, x = r
        player = bot.get_user(playerId ) or playerId 
        table.add_row([f"{i}. {player}", x])
      self.view.stop()
      v = ShamefulLBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Out On Same Number':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Num", "Outs"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId,batterNum, count(*) outs FROM deliveries WHERE isWicket=1 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId, batterNum ORDER BY outs desc limit 10", ())
      for i,r in enumerate(rows,1):
        playerId, x, y= r
        player = bot.get_user(playerId ) or playerId 
        table.add_row([f"{i}. {player}", x,y])
      self.view.stop()
      v = ShamefulLBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Pairs':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Pairs"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("WITH inning_totals AS (SELECT matchId, inningId, batterId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId IS NOT NULL GROUP BY matchId, inningId, batterId), ducks AS (SELECT matchId, batterId FROM inning_totals WHERE total_runs=0 AND got_out=1) SELECT batterId, COUNT(*) AS numop FROM (SELECT matchId, batterId FROM ducks GROUP BY matchId, batterId HAVING COUNT(*)>=2) t GROUP BY batterId ORDER BY numop DESC LIMIT 10;", ())
      for i,r in enumerate(rows,1):
        playerId, x = r
        player = bot.get_user(playerId ) or playerId 
        table.add_row([f"{i}. {player}", x])
      self.view.stop()
      v = ShamefulLBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Runs Conceded In An Over':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Bowler", "Runs", "Batters"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT  bowlerId, GROUP_CONCAT(DISTINCT batterId) AS batters, SUM(runs) AS runsConceded FROM deliveries GROUP BY matchId, inningId, CAST(((InningBalls-1)/6) AS INTEGER), bowlerId ORDER BY runsConceded DESC LIMIT 10;", ())
      for i,r in enumerate(rows,1):
        playerId, x, y = r
        batters = x.split(',')
        batters = ' & '.join([(u.name if (u := bot.get_user(int(b))) else b) for b in batters])
        player = bot.get_user(playerId ) or playerId 
        table.add_row([f"{i}. {player}", y, batters])
      self.view.stop()
      v = ShamefulLBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Wickets Taken Off A Single Batter':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Bowler", "Batter", "Outs"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId,batterId,COUNT(*) AS wickets FROM deliveries WHERE isWicket=1 GROUP BY bowlerId,batterId ORDER BY wickets DESC LIMIT 10;", ())
      for i,r in enumerate(rows,1):
        playerId, x, y = r
        player = bot.get_user(playerId ) or playerId 
        player2 = bot.get_user(x ) or x 
        table.add_row([f"{i}. {player}", player2, y])
      self.view.stop()
      v = ShamefulLBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Runs Conceded In An Inning':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Score"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId, SUM(isWicket),SUM(runs) AS r, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) FROM deliveries GROUP BY inningId, bowlerId ORDER BY r DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        playerId, x,y,z = r
        score = f"{y}/{x} ({ballsToOvers(z)})"
        player = bot.get_user(playerId ) or playerId 
        table.add_row([f"{i}. {player}", score])
      self.view.stop()
      v = ShamefulLBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Consecutive Innings Without Scoring 10':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Inns", "Start", "End"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("WITH bi AS (SELECT batterId,inningId,SUM(runs) r,MIN(timestamp) ts FROM deliveries GROUP BY batterId,inningId), ord AS (SELECT batterId,r,ts,MAX(ts) OVER (PARTITION BY batterId) lts,ROW_NUMBER() OVER (PARTITION BY batterId ORDER BY ts) rn,SUM(CASE WHEN r<10 THEN 1 ELSE 0 END) OVER (PARTITION BY batterId ORDER BY ts) rc FROM bi), isl AS (SELECT batterId,ts,lts,rn-rc grp FROM ord WHERE r<10), grp AS (SELECT batterId,COUNT(*) cnt,MIN(ts) start_ts,MAX(ts) end_ts,MAX(lts) gl_end FROM isl GROUP BY batterId,grp) SELECT batterId,cnt,start_ts,CASE WHEN end_ts=gl_end THEN NULL ELSE end_ts END end_ts FROM grp ORDER BY cnt DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        playerId, x,y,z = r
        player = bot.get_user(playerId ) or playerId 
        st = f"{timestampToPKT(y)}"
        en = f"{timestampToPKT(z)}" if z else "*"
        table.add_row([f"{i}. {player}", x,st, en])
      self.view.stop()
      v = ShamefulLBview(self.view.ctx, table, self.values[0], 'All times are in Pakistan Standard Time')
      v.m = await self.view.m.edit(view=v)
class LBSelection(ui.Select):
  def __init__(self, v):
    currentlySelected = v.statType
    options = [
      "Most Matches","Most Runs","Most Wickets", "Highest Batting AVG", "Highest Batting SR",'Best Partnerships (Inning)', 'Best Partnerships (Overall)',"Highest SR in an Inning", "Most 30s","Most 50s", "Most 4s", "Most 6s","Fastest 50s","Fastest 30s", "Highest Match Aggregates","Most MVPs",'Best Bowling AVG', 'Best Bowling ECO', "Most 3fers","Most 5fers","Best Batting Inning","Best Bowling Inning", "Best Bowling SR","Most Hattricks"
      ]
    options = [discord.SelectOption(label= b, value = b) for b in options]
    super().__init__(placeholder= "Select Category", min_values=1, max_values=1, options=options)
  async def callback(self, interaction: discord.Interaction):
    if self.view.ctx.author.id != interaction.user.id: return
    await interaction.response.defer()
    bot = interaction.client
    v = self.values[0]
    if v == 'Most Runs':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Runs", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId,SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) FROM deliveries GROUP BY batterId ORDER BY runs DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs,balls])
      self.view.stop()
      v = LBview(self.view.ctx, table)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most MVPs':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "MVPs"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT mvpId, count(*) as mvps FROM matches WHERE mvpId IS NOT NULL GROUP BY mvpId ORDER BY mvps DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Hattricks':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Hattricks"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId,COUNT(*) AS hattricks FROM (SELECT bowlerId,matchId,inningId,InningBalls,isWicket,CASE WHEN isWicket=1 AND (LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp)=0 OR LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp) IS NULL) AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_hattrick FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL) t WHERE is_hattrick=1 GROUP BY bowlerId ORDER BY hattricks DESC LIMIT 10;", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most 30s':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "30s"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT b, SUM(CASE WHEN r>=30 THEN 1 ELSE 0 END) AS thirty_count FROM (SELECT batterId AS b, inningId, SUM(runs) AS r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId, inningId) t GROUP BY b ORDER BY thirty_count DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most 50s':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "50s"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT b, SUM(CASE WHEN r>=50 THEN 1 ELSE 0 END) AS thirty_count FROM (SELECT batterId AS b, inningId, SUM(runs) AS r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId, inningId) t GROUP BY b ORDER BY thirty_count DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most 4s':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "4s"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId, SUM(CASE WHEN batterNum = 4 THEN 1 ELSE 0 END) fours FROM deliveries WHERE isWicket != 1 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId ORDER BY fours DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most 6s':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "6s"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId, SUM(CASE WHEN batterNum = 6 THEN 1 ELSE 0 END) fours FROM deliveries WHERE isWicket != 1 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId ORDER BY fours DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Fastest 50s':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId, MIN(balls) AS balls_to_50, inningId FROM (SELECT batterId, inningId, ballId, SUM(runs) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS cr, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS balls FROM deliveries WHERE batterId IS NOT NULL) t WHERE cr>=50 GROUP BY batterId, inningId ORDER BY balls_to_50 ASC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, x = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Fastest 30s':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId, MIN(balls) AS balls_to_30,inningId FROM (SELECT batterId, inningId, ballId, SUM(runs) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS cr, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS balls FROM deliveries WHERE batterId IS NOT NULL) t WHERE cr>=30 GROUP BY batterId, inningId ORDER BY balls_to_30 ASC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, x = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most 3fers':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "3fers"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId, COUNT(*) AS three_fers FROM (SELECT inningId, bowlerId, SUM(isWicket) AS wkts FROM deliveries WHERE bowlerId IS NOT NULL GROUP BY inningId, bowlerId HAVING wkts>=3) t GROUP BY bowlerId ORDER BY three_fers DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most 5fers':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "5fers"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId, COUNT(*) AS three_fers FROM (SELECT inningId, bowlerId, SUM(isWicket) AS wkts FROM deliveries WHERE bowlerId IS NOT NULL GROUP BY inningId, bowlerId HAVING wkts>=5) t GROUP BY bowlerId ORDER BY three_fers DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, self.values[0])
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Matches':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Matches"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT playerId, COUNT(*) AS matches FROM (SELECT DISTINCT batterId AS playerId, matchId FROM deliveries WHERE batterId IS NOT NULL UNION SELECT DISTINCT bowlerId AS playerId, matchId FROM deliveries WHERE bowlerId IS NOT NULL) t GROUP BY playerId ORDER BY matches DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, "Most Matches")
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Wickets':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Wickets", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId,SUM(isWicket) AS wkts, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) FROM deliveries GROUP BY bowlerId ORDER BY wkts DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs,balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, "Most Wickets")
      v.m = await self.view.m.edit(view=v)
    elif v == 'Highest Batting AVG':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "AVG", "Inns"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId, CASE WHEN SUM(isWicket)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/SUM(isWicket) END AS AVG, COUNT(DISTINCT inningId) as Inns FROM deliveries GROUP BY batterId HAVING COUNT(DISTINCT inningId) >= 10 ORDER BY AVG DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2),balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v, "MINIMUM 10 INNINGS")
      v.m = await self.view.m.edit(view=v)
    elif v == 'Highest Batting SR':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "SR"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 100.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN runs ELSE 0 END)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS batting_avg FROM deliveries GROUP BY batterId HAVING SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) >= 100 ORDER BY batting_avg DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2)])
      self.view.stop()
      v = LBview(self.view.ctx, table, v, "MINIMUM 100 BALLS")
      v.m = await self.view.m.edit(view=v)
    elif v == 'Highest SR in an Inning':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "SR", "Inning"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 100.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN runs ELSE 0 END)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS batting_sr, SUM(runs), SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) FROM deliveries GROUP BY batterId,inningId HAVING SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) >= 10 ORDER BY batting_sr DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, x,y = r
        inn = f"{x} ({y})"
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2), inn])
      self.view.stop()
      v = LBview(self.view.ctx, table, v, 'Minimum 10 Balls')
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Bowling AVG':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "AVG", "WKTS"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId, CASE WHEN SUM(isWicket)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/SUM(isWicket) END AS AVG, SUM(isWicket) as wkts FROM deliveries GROUP BY bowlerId HAVING COUNT(DISTINCT inningId)>= 10 ORDER BY AVG ASC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2),balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v, "MINIMUM 10 INNINGS")
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Bowling ECO':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "ECO", "Inns"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 6.0*SUM(runs)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS economy,COUNT(DISTINCT inningId) AS Inns FROM deliveries GROUP BY bowlerId HAVING COUNT(DISTINCT inningId) >= 10 ORDER BY economy ASC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2),balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v, "MINIMUM 10 INNINGS")
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Bowling SR':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "SR", "Inns"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId,CASE WHEN SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 1.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)/SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END) END AS strikeRate,COUNT(DISTINCT inningId) AS Inns FROM deliveries GROUP BY bowlerId HAVING COUNT(DISTINCT inningId)>=10 AND SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END)>0 ORDER BY strikeRate ASC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2),balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v, "MINIMUM 10 INNINGS")
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Partnerships (Inning)':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Batters", "Runs", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT inningId,CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END AS batter1,CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END AS batter2,SUM(runs) partnershipRuns,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) balls FROM deliveries WHERE nonStrikerId IS NOT NULL GROUP BY inningId,CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END,CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END ORDER BY partnershipRuns DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        _,batterId, batterId2, runs, balls = r
        batter1 = bot.get_user(batterId ) or batterId 
        batter2 = bot.get_user(batterId2) or batterId2
        batter = f"{batter1} & {batter2}"
        table.add_row([f"{i}. {batter}",runs,balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Partnerships (Overall)':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Batters", "Runs", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT inningId,CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END AS batter1,CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END AS batter2,SUM(runs) partnershipRuns,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) balls FROM deliveries WHERE nonStrikerId IS NOT NULL GROUP BY CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END,CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END ORDER BY partnershipRuns DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        _,batterId, batterId2, runs, balls = r
        batter1 = bot.get_user(batterId ) or batterId 
        batter2 = bot.get_user(batterId2) or batterId2
        batter = f"{batter1} & {batter2}"
        table.add_row([f"{i}. {batter}",runs,balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Batting Inning':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Batters", "Inning"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId,r,b,notout FROM (SELECT batterId,SUM(runs) r,COUNT(*) b,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END notout FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId,inningId ORDER BY r DESC,b ASC LIMIT 10)", ())
      for i,r in enumerate(rows,1):
        batterId, r, b, n = r
        batter = bot.get_user(batterId ) or batterId 
        score = f"{r} ({b}){'*' if n == 1 else ''}"
        table.add_row([f"{i}. {batter}",score])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Bowling Inning':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Bowler", "Inning"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId,w,r,b FROM (SELECT bowlerId,SUM(isWicket) w,SUM(runs) r,COUNT(*) b FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY bowlerId,inningId ORDER BY w DESC,r ASC,b ASC LIMIT 10)", ())
      for i,r in enumerate(rows,1):
        batterId, w, r, b = r
        batter = bot.get_user(batterId ) or batterId 
        score = f"{w}/{r} ({ballsToOvers(b)})"
        table.add_row([f"{i}. {batter}",score])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Highest Match Aggregates':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Match", "Aggregate"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT m.matchId, m.teamAName, m.teamBName, SUM(i.runs) AS totalRuns FROM matches m JOIN innings i ON m.matchId = i.matchId GROUP BY m.matchId ORDER BY totalRuns DESC LIMIT 10;", ())
      for i,r in enumerate(rows,1):
        matchId, teamAName, teamBName, runs= r
        batter = f"{teamAName} VS {teamBName}"
        table.add_row([f"{i}. {batter}",runs])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
class Selection(ui.Select):
  def __init__(self, userId, options, maxselect, placeholder: str= 'Select'):
    self.userId = userId 
    self.opts = options
    options = [discord.SelectOption(label= b['name'], value = b['id'], description = b.get('description')) for b in options]
    super().__init__(placeholder= placeholder, min_values=maxselect, max_values=maxselect, options=options)
  async def callback(self, interaction: discord.Interaction):
    if interaction.user.id != self.userId: return
    await interaction.response.defer()
    if len(self.values) == 1:
      self.view.value = int(self.values[0])
      selected= next(o for o in self.opts if o['id'] == self.view.value)['name']
    else:
      self.view.value = [int(o) for o in self.values]
      selected=[next(o['name'] for o in self.opts if o['id'] == self.view.value[k]) for k in range(len(self.view.value))]
    if hasattr(self.view,'m'):
      view = ui.LayoutView(timeout= 20)
      view.add_item(ui.TextDisplay(f"Selected {' & '.join(selected) if isinstance(selected,list) else selected}"))
      await self.view.m.edit(view= view)
    self.view.stop()
class ProfileFilters(ui.Modal, title="Profile Filters"):
  lastNMatches = ui.Label(text= "Insert the number of last N games to filter ",description= "0 = All Time", component= ui.TextInput(placeholder="0", required= False, default = 0,style=discord.TextStyle.short,max_length=2),)
  lastNInnings = ui.Label(text= "Insert the number of last N innings to filter ",description= "0 = All Time, Must not be used with Last N matches", component= ui.TextInput(placeholder="0", required= False, default = 0,style=discord.TextStyle.short,max_length=2),)
  fromTime = ui.Label(text= "Insert the from time to filter ",description= "Must be strictly as placeholder suggests", component= ui.TextInput(placeholder="i.e DD/MM/YYYY", required= False, default = 0,style=discord.TextStyle.short,max_length=10),)
  toTime = ui.Label(text= "Insert the to time to filter ",description= "Must be strictly as placeholder suggests", component= ui.TextInput(placeholder="i.e DD/MM/YYYY", required= False, default = 0,style=discord.TextStyle.short,max_length=10),)
  def __init__(self, target, ctx):
    self.target = target
    self.ctx = ctx
    super().__init__()
  async def on_submit(self, interaction: discord.Interaction):
    lastNMatches = int(self.lastNMatches.component.value) if self.lastNMatches.component.value else 0
    lastNInnings = int(self.lastNInnings.component.value) if self.lastNInnings.component.value != '' else 0
    lastBatNInnings = lastNInnings
    lastBowlNInnings = lastNInnings
    if lastNInnings > 0 and lastNMatches > 0:
      lastNInnings = 0
    fromTime = self.fromTime.component.value if self.fromTime.component.value != '' else 0
    toTime = self.toTime.component.value if self.toTime.component.value != '' else 0
    if str(fromTime) != "0":
      try:
        dt=datetime.strptime(fromTime,"%d/%m/%Y").replace(tzinfo=timezone.utc)
        fromTime=int(dt.timestamp())
      except: fromTime = 0
    if str(toTime) != "0":
      try:
        dt=datetime.strptime(fromTime,"%d/%m/%Y").replace(tzinfo=timezone.utc)
        toTime=int(dt.timestamp())
      except: toTime = 0
    v = await makeProfileView(self.target, self.ctx,lastNMatches, lastNInnings, lastBatNInnings, lastBowlNInnings,fromTime, toTime)
    await interaction.response.edit_message(view=v)
  async def on_error(self, interaction, error):await interaction.response.send_message(f'Oops! Something went wrong, {error}.', ephemeral=True)
class FiltersBtn(ui.Button):
  def __init__(self, userId):
    self.userId = userId
    super().__init__(label='Apply Filters', style=discord.ButtonStyle.green)
  async def callback(self, i):
    if i.user.id != self.userId: return
    await i.response.send_modal(ProfileFilters(self.view.target, self.view.ctx))
class DeclareBTN(ui.Button):
  def __init__(self):
    super().__init__(label='Declare', style=discord.ButtonStyle.danger)
  async def callback(self, i):
    c = i.client
    if i.channel.id not in c.games:
      return 
    g = c.games[i.channel.id]
    cid = g.currentInning.inningNo
    if i.user.id != g.currentInning.battingTeam.captain.id: 
      return await i.response.send_message("This can only be used by current batting captain", ephemeral= True)
    await i.response.defer(ephemeral=True)
    view=ui.LayoutView(timeout=60)
    view.value=None
    buttons = [Button('Yes',discord.ButtonStyle.green,g.currentInning.battingTeam.captain.id), Button('No',discord.ButtonStyle.red ,g.currentInning.battingTeam.captain.id)]
    container = ui.Container(accent_color = discord.Colour.from_str("#9b0a82"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"Are you sure to declare?"))
    container.add_item(actionRow)
    view.add_item(container)
    await i.followup.send(view=view, ephemeral= True)
    await view.wait()
    if view.value != 'Yes':return
    if g.currentInning.inningNo != cid:return
    if g.currentInning.declared:return
    if g.currentInning.balls == 0:return
    g.currentInning.declared = True
    await i.followup.send(content="Inning declared", ephemeral= True)
class Button(ui.Button):
  def __init__(self, label: str, style, userId: int):
    self.userId = userId
    self.lab= label
    super().__init__(label=label, style=style)
  async def callback(self, i):
    if i.user.id != self.userId: return 
    await i.response.defer()
    self.view.value = self.lab
    self.view.stop()
class ShowScoreButton(ui.Button):
  def __init__(self, Game, BatterIndex = None, BowlerIndex = None): 
    self.Game = Game
    self.BatterIndex = BatterIndex
    self.BowlerIndex = BowlerIndex 
    self.isBatter = True if self.BatterIndex is not None else False
    emoji = "🏏" if self.isBatter else "🥎"
    index = self.BatterIndex if self.BatterIndex is not None else self.BowlerIndex
    super().__init__(emoji = emoji, style=discord.ButtonStyle.primary if index == 0 else discord.ButtonStyle.secondary)
  async def callback(self, interaction):
    g = self.Game
    inn = g.currentInning
    if self.isBatter:
      user = inn.currentBatters[self.BatterIndex]
    else:
      user = inn.currentBowlers[self.BowlerIndex]
    bat=[]
    bowl=[]
    timeline=[]
    tookWickets = []
    player = next(p for p in g.players if p.id == user.id)
    for inn in g.innings:
      if player in inn.batters:
        tookWickets = []
        i=inn.batters[player]
        timeline = i.timeline
        if i.balls>0: bat.append(f"{i.runs}({i.balls}){'*' if not i.dismissed else ''}")
      if player in inn.bowlers:
        i=inn.bowlers[player]
        tookWickets = i.wicketsDigits
        timeline = i.timeline
        if i.balls>0: bowl.append(f"{i.runsConceded}/{i.wickets} ({ballsToOvers(i.balls)})")
    bat, bowl = " & ".join(bat), " & ".join(bowl)
    view = ui.LayoutView(timeout= 60)
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b")) 
    text = f"### {user}'s Score\n"
    if bat:text += f"**Batting:** {bat}\n"
    if bowl:text += f"**Bowling:** {bowl}"
    container.add_item(ui.TextDisplay(text))
    if timeline:
      container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
      container.add_item(ui.TextDisplay(" • ".join([f'**{t}**' for t in timeline])))
    if tookWickets:
      container.add_item(ui.Separator(visible=True,spacing=discord.SeparatorSpacing.small))
      w = " • ".join([f'**{t}**' for t in tookWickets])
      container.add_item(ui.TextDisplay(f"Wickets on: {w}"))
    view.add_item(container)
    await interaction.response.send_message(view=view, ephemeral = True)
class HelpButton(ui.Button):
  def __init__(self,lab, disabledd: bool):
    self.lab = lab
    super().__init__(label= lab, style=discord.ButtonStyle.green, disabled= disabledd)
  async def callback(self, i):
    if self.lab == 'Prev':
      v = Helpview(self.view.ctx, self.view.page-1)
      self.view.makePage()
      await i.response.edit_message(content=None,view=v)
    elif self.lab == 'Next':
      v = Helpview(self.view.ctx, self.view.page+1)
      await i.response.edit_message(content=None,view=v)
    elif self.lab == 'How To Play':
      self.view.page = 'How To Play'
      v = Helpview(self.view.ctx, 'How To Play')
      await i.response.edit_message(content=None,view=v)
    elif self.lab == 'Commands':
      v = Helpview(self.view.ctx)
      await i.response.edit_message(content=None,view=v)
class Helpview(ui.LayoutView):
  def __init__(self,ctx, page= 0) -> None:
    self.ctx = ctx = ctx 
    self.perPage = 10
    self.page = page
    super().__init__(timeout= 60)
    self.makePage()
  def makePage(self):
    self.clear_items()
    if self.page !=  "How To Play":
      commands = [c for c in self.ctx.bot.commands if c.hidden is False]
      start=self.page*self.perPage 
      end=start+self.perPage
      container = ui.Container(accent_color = discord.Colour.from_str("#a50ee7"))
      container.add_item(ui.TextDisplay(f"### Help"))
      if self.page == 0:
        container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
        container.add_item(ui.TextDisplay(f"Ashes is a fun bot inspired by Hand Cricket and enhanced with elements of Test cricket. It follows the basic idea of Test cricket.\nJoin the **[Official Server](https://discord.gg/uxchR7sKd2)**"))
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      for command in commands[start:end]:
        canOnlyBeUsedBy = f"\n**Only Usable By:{command.extras['usableBy']}**" if command.extras else ""
        extraTxt = f"\n**Description:** {command.description}" if command.description else ""
        extraTxt += canOnlyBeUsedBy
        container.add_item(ui.TextDisplay(f"{self.ctx.clean_prefix}{command.qualified_name} {command.signature}\n**Aliases:** {' • '.join(command.aliases)}{extraTxt}"))
        container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      actionRow = ui.ActionRow()
      actionRow.add_item(HelpButton('Prev', True if self.page == 0 else False))
      actionRow.add_item(HelpButton('Next', True if end >= len(commands) else False))
      actionRow.add_item(HelpButton('How To Play', False))
      container.add_item(actionRow)
      self.add_item(container)
    else:
      container = ui.Container(accent_color = discord.Colour.from_str("#07b326"))
      container.add_item(ui.TextDisplay(f"## How To Play"))
      container.add_item(ui.TextDisplay("### Basics\nBot will ask for a number from both batter & bowler, numbers may only be chosen from 0, 1, 2, 3, 4, and 6. If both put same number then it's out, otherwise, the batter is safe, and the number the batter chose is added to the score.\n**Examples**\n- The batter chose 2, and the bowler chose 3.\n  - Batter scored 2 runs.\n- The batter chose 3, and the bowler chose 3.\n  - The batter is out."))
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      container.add_item(ui.TextDisplay("### Advance Rules\n**Ashes** has special set of rules which are different from basics which follow as these:\n\n- Each game has 4 innings (if a team wins by an inning then 3).\n- Bowlers can't do 0.\n  - There are few exceptions to this rule, bowlers can do 0 if:\n  - Their last over was maiden.\n  - They're on hattrick.\n- The number 5 doesn't exist.\n- Batter may only use boundary numbers (4/6) once per over.\n  - There's an exception to this rule as well, if batter has played 15 or more balls then they can do 2 boundaries per over.\n  - This applies to one batter per over, e.g if striker does 4 and then rotates the strike, non striker can hit another boundary.\n- Batter can only do 3 consecutive 0s.\n  - This applies regardless of overs, eg. Khawi did 000 on 4.4, 4.5, 4.6 and then gets strike on 5.3, he will have to do a number (can't do 0)"))
      container.add_item(ui.TextDisplay("### How To Start A Game\nTo start a game you need 4 players. Start by creating a lobby with `create` command, you can now ask other players to join via `join` command. Once you have enough players (That can be viewed through `pl` command) you are ready to initiate toss by `toss` command. After that you can start the game by using `start` command. Remember all it takes is 4 commands, `create` -> `join` -> `toss` -> `start`. If you can't find the players you can always play in  **[Official Server](https://discord.gg/uxchR7sKd2)**\n-# you can ping 'regular players' role there."))
      actionRow = ui.ActionRow()
      actionRow.add_item(HelpButton('Commands', False))
      container.add_item(actionRow)
      self.add_item(container)
  async def interaction_check(self, interaction: discord.Interaction) -> bool:return self.ctx.author.id == interaction.user.id

class ShamefulLBview(ui.LayoutView):
  def __init__(self,ctx,table, title: str= "Most Runs", footer: str = None) -> None:
    super().__init__(timeout= 40)
    self.bot = bot = ctx.bot
    self.ctx = ctx = ctx
    self.m = None
    self.guild = guild = ctx.guild
    self.statType = title
    container = ui.Container(accent_color = discord.Colour.from_str("#0ebce7"))
    container.add_item(ui.TextDisplay(f"### {title}"))
    container.add_item(ui.TextDisplay(f"**`{table.get_string().splitlines()[0]}`**\n```py\n{'\n'.join(table.get_string().splitlines()[1:])}\n```"))
    actionRow = ui.ActionRow().add_item(ShamefulLBSelection(self))
    if footer:
      container.add_item(ui.TextDisplay(f"-# {footer}"))
    #for b in buttons: actionRow.add_item(b)
    container.add_item(actionRow)
    self.add_item(container)
  async def on_timeout(self, i):
    for child in self.walk_children():
      if hasattr(child, "disabled"):
        child.disabled = True
    #await self.ctx.message.edit(content=None, view=self.view)
  async def interaction_check(self, interaction: discord.Interaction) -> bool:return self.ctx.author.id == interaction.user.id
class LBview(ui.LayoutView):
  def __init__(self,ctx,table, title: str= "Most Runs", footer: str = None) -> None:
    super().__init__(timeout= 40)
    self.bot = bot = ctx.bot
    self.ctx = ctx = ctx
    self.m = None
    self.guild = guild = ctx.guild
    self.statType = title
    container = ui.Container(accent_color = discord.Colour.from_str("#0ebce7"))
    container.add_item(ui.TextDisplay(f"### {title}\n-# For better view visit our [website](https://ashesdb.vercel.app/leaderboard)"))
    container.add_item(ui.TextDisplay(f"**`{table.get_string().splitlines()[0]}`**\n```py\n{'\n'.join(table.get_string().splitlines()[1:])}\n```"))
    actionRow = ui.ActionRow().add_item(LBSelection(self))
    if footer:
      container.add_item(ui.TextDisplay(f"-# {footer}"))
    #for b in buttons: actionRow.add_item(b)
    container.add_item(actionRow)
    self.add_item(container)
  async def on_timeout(self, i):
    for child in self.walk_children():
      if hasattr(child, "disabled"):
        child.disabled = True
    #await self.ctx.message.edit(content=None, view=self.view)
  async def interaction_check(self, interaction: discord.Interaction) -> bool:return self.ctx.author.id == interaction.user.id