import discord
from discord.ext import commands
from aiohttp import web
import json
from datetime import datetime, timedelta

class RankingCog(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot
    self.site = None
    self.runner = None
  async def cog_load(self):
    app = web.Application()
    app.add_routes([web.get('/rankings/batting', self.get_batting),web.get('/rankings/bowling', self.get_bowling),web.get('/rankings/allrounder', self.get_allrounder),web.get('/matches/getrecent',self.get_recent_matches),web.get('/matches/live', self.get_live_matches),web.get('/leaderboard', self.get_leaderboard),web.get('/', self.health_check),web.get('/matches/{matchId}/scorecard', self.get_scorecard),web.get('/matches/{matchId}/live', self.get_live_match),web.get('/matches/{matchId}', self.get_match),web.get('/users', self.get_userApi)])
    self.runner = web.AppRunner(app)
    await self.runner.setup()
    self.site = web.TCPSite(self.runner, '0.0.0.0', 8000)
    await self.site.start()
    print("Rankings API running on http://0.0.0.0:8000")
  async def get_match(self, request):
    try:
      match_id = request.match_info['matchId']
      match_row = await self.bot.fetchrow(
        "SELECT matchId,channelId,guildId,teamAName,teamBName,winner,mvpId FROM matches WHERE matchId=?",
        [match_id]
      )
      if not match_row:
        return web.json_response({"error": "Match not found"}, status=404, headers=self.get_cors_headers())
      matchId, channelId, guildId, teamAName, teamBName, winner, mvpId = match_row
      channel = self.bot.get_channel(channelId)
      guild = self.bot.get_guild(guildId)
      innings_rows = await self.bot.fetchall(
        "SELECT inningId,inningNo,battingTeam,bowlingTeam,runs,wickets,balls,isDeclared,isFollowOn FROM innings WHERE matchId=? ORDER BY inningNo",
        [match_id]
      )
      innings = []
      for row in innings_rows:
        inningId, inningNo, battingTeam, bowlingTeam, runs, wickets, balls, isDeclared, isFollowOn = row
        overs = f"{balls // 6}.{balls % 6}"
        innings.append({
          "inningId": inningId,
          "inningNo": inningNo,
          "battingTeam": battingTeam,
          "bowlingTeam": bowlingTeam,
          "runs": runs,
          "wickets": wickets,
          "balls": balls,
          "overs": overs,
          "isDeclared": bool(isDeclared),
          "isFollowOn": bool(isFollowOn),
        })
      mvp = None
      if mvpId:
        mvp = await self.fetch_user_data(mvpId)
        mvp["id"] = str(mvpId)
      ts = await self.bot.fetchrow("SELECT MAX(timestamp) FROM deliveries WHERE matchId = ?", (matchId,))
      return web.json_response({
        "matchId": matchId,
        "channelName": channel.name if channel else str(channelId),
        "guildName": guild.name if guild else str(guildId),
        "teamAName": teamAName,
        "teamBName": teamBName,
        "winner": winner,
        "mvp": mvp,
        "innings": innings,
        "timestamp": ts
      }, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_scorecard(self, request):
    try:
      match_id = request.match_info['matchId']
      match_row = await self.bot.fetchrow(
        "SELECT matchId,channelId,guildId,teamAName,teamBName,winner,mvpId,matchMaximumBalls,drawByAgreement FROM matches WHERE matchId=?",
        [match_id]
      )
      matchId, channelId, guildId, teamAName, teamBName, winner, mvpId,matchMaximumBalls,drawByAgreement = match_row
      if not match_row:return web.json_response({"error": "No innings found"}, status=404, headers=self.get_cors_headers())
      innings_rows = await self.bot.fetchall(
        "SELECT inningId,inningNo,battingTeam,bowlingTeam,runs,wickets,balls,isFollowOn FROM innings WHERE matchId=? ORDER BY inningNo",
        [match_id]
      )
      if not match_row:return web.json_response({"error": "No innings found"}, status=404, headers=self.get_cors_headers())
      result = []
      for inning in innings_rows:
        inningId, inningNo, battingTeam, bowlingTeam, totalRuns, totalWickets, totalBalls, isFollowOn,isDeclared = inning
        # --- batting: group deliveries by batterId ---
        bat_rows = await self.bot.fetchall("SELECT batterId, SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls, SUM(CASE WHEN runs=4 THEN 1 ELSE 0 END) AS fours, SUM(CASE WHEN runs=6 THEN 1 ELSE 0 END) AS sixes, MAX(timestamp) AS batting_order, MAX(CASE WHEN isWicket=1 THEN 1 ELSE 0 END) AS dismissed, MAX(CASE WHEN isWicket=1 THEN bowlerId ELSE NULL END) AS dismissedBy FROM deliveries WHERE inningId=? AND batterId IS NOT NULL GROUP BY batterId ORDER BY batting_order", [inningId])
        batters = []
        for row in bat_rows:
          batterId, runs, balls, fours, sixes, batting_order, dismissed, dismissedBy = row
          sr = round((runs / balls) * 100, 2) if balls else 0
          u = await self.fetch_user_data(batterId)
          dismissedByU = await self.fetch_user_data(dismissedBy) if bool(dismissed) else "NOT OUT" 
          batters.append({
            "playerId": str(batterId),
            "playerName": u["name"],
            "avatar": u["avatar"],
            "runs": runs or 0,
            "balls": balls or 0,
            "fours": fours or 0,
            "sixes": sixes or 0,
            "strikeRate": sr,
            "dismissed": bool(dismissed),
            "dismissedBy": f"b. {dismissedByU['name']}" if 'name' in dismissedByU else dismissedByU
          })
        # --- bowling: group deliveries by bowlerId ---
        bowl_rows = await self.bot.fetchall("""
          SELECT bowlerId,
                 SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls,
                 SUM(runs) AS runs,
                 SUM(isWicket) AS wickets,
                 MAX(timestamp) AS bowling_order
          FROM deliveries
          WHERE inningId=? AND bowlerId IS NOT NULL
          GROUP BY bowlerId
          ORDER BY bowling_order
        """, [inningId])
        bowlers = []
        for row in bowl_rows:
          bowlerId, balls, runs, wickets, bowling_order = row
          overs_num = balls // 6
          overs_rem = balls % 6
          overs_str = f"{overs_num}.{overs_rem}"
          economy = round((runs / balls) * 6, 2) if balls else 0
          u = await self.fetch_user_data(bowlerId)
          bowlers.append({
            "playerId": str(bowlerId),
            "playerName": u["name"],
            "avatar": u["avatar"],
            "overs": overs_str,
            "balls": balls or 0,
            "runs": runs or 0,
            "wickets": wickets or 0,
            "economy": economy,
          })
        result.append({
          "inningNo": inningNo,
          "battingTeam": battingTeam,
          "bowlingTeam": bowlingTeam,
          "total": totalRuns,
          "wickets": totalWickets,
          "balls": totalBalls,
          "overs": f"{totalBalls // 6}.{totalBalls % 6}",
          "batters": batters,
          "bowlers": bowlers,
          "winner": winner,
          'isFollowOn': bool(isFollowOn),
          'isDeclared': bool(isDeclared)
        })
      
      return web.json_response({"matchId": match_id, "innings": result, "winner": winner,'drawByAgreement': bool(drawByAgreement), 'matchMaximumBalls': matchMaximumBalls}, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_live_matches(self, request):
    try:
      matches = []
      for channel_id, game in self.bot.games.items():
        channel = self.bot.get_channel(channel_id)
        guild = self.bot.get_guild(game.ctx.guild.id)
        state = "live" if game.started else "lobby"
        innings_summary = []
        for inn in game.innings:
          innings_summary.append({
            "battingTeam": inn.battingTeam.name if inn.battingTeam else None,
            "bowlingTeam": inn.bowlingTeam.name if inn.bowlingTeam else None,
            "runs": inn.runs,
            "wickets": inn.wickets,
            "overs": f"{inn.balls // 6}.{inn.balls % 6}",
            "isDeclared": inn.declared,
          })
        team_a_players = [{"id": p.id, "name": p.name} for p in game.teama.players]
        team_b_players = [{"id": p.id, "name": p.name} for p in game.teamb.players]
        matches.append({
          "id": game.gameId,
          "state": state,
          "channelId": str(channel_id),
          "channelName": channel.name if channel else str(channel_id),
          "guildName": guild.name if guild else str(game.ctx.guild.id),
          "teamAName": game.teama.name,
          "teamBName": game.teamb.name,
          "teamAPlayers": team_a_players,
          "teamBPlayers": team_b_players,
          "innings": innings_summary,
        })
      return web.json_response({"matches": matches}, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_live_match(self, request):
    try:
      match_id = request.match_info['matchId']
      game = next((g for g in self.bot.games.values() if g.gameId == match_id), None)
      if not game:
        return web.json_response({"error": "Live match not found"}, status=404, headers=self.get_cors_headers())
      channel = self.bot.get_channel(game.ctx.channel.id)
      guild = self.bot.get_guild(game.ctx.guild.id)
      state = "live" if game.started else "lobby"

      innings_out = []
      for inn in game.innings:
        # Batters seen so far this inning
        batters_out = []
        for player, b in inn.batters.items():
          batters_out.append({
            "playerId": str(player.id),
            "playerName": player.name,
            "runs": b.runs,
            "balls": b.balls,
            "fours": b.fours,
            "sixes": b.sixes,
            "strikeRate": b.sr,
            "dismissed": b.dismissed,
            "dismissedBy": b.dismissedBy if b.dismissed else "not out",
          })
        # Bowlers seen so far this inning
        bowlers_out = []
        for player, b in inn.bowlers.items():
          economy = round((b.runsConceded / b.balls) * 6, 2) if b.balls else 0.0
          bowlers_out.append({
            "playerId": str(player.id),
            "playerName": player.name,
            "overs": f"{b.balls // 6}.{b.balls % 6}",
            "runs": b.runsConceded,
            "wickets": b.wickets,
            "economy": economy,
          })
        innings_out.append({
          "battingTeam": inn.battingTeam.name if inn.battingTeam else None,
          "bowlingTeam": inn.bowlingTeam.name if inn.bowlingTeam else None,
          "runs": inn.runs,
          "wickets": inn.wickets,
          "overs": f"{inn.balls // 6}.{inn.balls % 6}",
          "isDeclared": inn.declared,
          "batters": batters_out,
          "bowlers": bowlers_out,
        })

      # Current in-play batters and bowlers (only meaningful when live)
      current_batters = []
      current_bowlers = []
      if game.started and game.innings:
        ci = game.currentInning
        for i, p in enumerate(ci.currentBatters):
          b = ci.batters.get(p)
          current_batters.append({
            "playerId": str(p.id),
            "playerName": p.name,
            "runs": b.runs if b else 0,
            "balls": b.balls if b else 0,
            "strikeRate": b.sr if b else 0.0,
            "onStrike": i == 0,
          })
        for p in ci.currentBowlers:
          b = ci.bowlers.get(p)
          current_bowlers.append({
            "playerId": str(p.id),
            "playerName": p.name,
            "overs": f"{b.balls // 6}.{b.balls % 6}" if b else "0.0",
            "runs": b.runsConceded if b else 0,
            "wickets": b.wickets if b else 0,
            "isBowling": True,
          })

      return web.json_response({
        "id": game.gameId,
        "state": state,
        "channelName": channel.name if channel else str(game.ctx.channel.id),
        "guildName": guild.name if guild else str(game.ctx.guild.id),
        "teamAName": game.teama.name,
        "teamBName": game.teamb.name,
        "innings": innings_out,
        "currentBatters": current_batters,
        "currentBowlers": current_bowlers,
        "commentary": game.currentInning.commentary if game.currentInning.commentary else None
      }, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_leaderboard(self, request):
    try:
      category = request.query.get('category', 'most_runs')
      limit = min(25, max(1, int(request.query.get('limit', 10))))

      CATEGORIES = {
        'most_runs': {
          'title': 'Most Runs', 'note': None,
          'sql': "SELECT batterId,SUM(runs) AS runs,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries GROUP BY batterId ORDER BY runs DESC LIMIT ?",
          'cols': ['player','runs','balls'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'runs': r[1], 'balls': r[2]}
        },
        'most_wickets': {
          'title': 'Most Wickets', 'note': None,
          'sql': "SELECT bowlerId,SUM(isWicket) AS wkts,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries GROUP BY bowlerId ORDER BY wkts DESC LIMIT ?",
          'cols': ['player','wickets','balls'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'wickets': r[1], 'balls': r[2]}
        },
        'most_matches': {
          'title': 'Most Matches', 'note': None,
          'sql': "SELECT playerId,COUNT(*) AS matches FROM (SELECT DISTINCT batterId AS playerId,matchId FROM deliveries WHERE batterId IS NOT NULL UNION SELECT DISTINCT bowlerId AS playerId,matchId FROM deliveries WHERE bowlerId IS NOT NULL) t GROUP BY playerId ORDER BY matches DESC LIMIT ?",
          'cols': ['player','matches'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'matches': r[1]}
        },
        'most_mvps': {
          'title': 'Most MVPs', 'note': None,
          'sql': "SELECT mvpId,COUNT(*) AS mvps FROM matches WHERE mvpId IS NOT NULL GROUP BY mvpId ORDER BY mvps DESC LIMIT ?",
          'cols': ['player','mvps'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'mvps': r[1]}
        },
        'most_30s': {
          'title': 'Most 30s', 'note': None,
          'sql': "SELECT b,SUM(CASE WHEN r>=30 THEN 1 ELSE 0 END) AS thirties FROM (SELECT batterId AS b,inningId,SUM(runs) AS r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId,inningId) t GROUP BY b ORDER BY thirties DESC LIMIT ?",
          'cols': ['player','30s'],
          'resolve': [0], 'format': lambda r: {'player': r[0], '30s': r[1]}
        },
        'most_50s': {
          'title': 'Most 50s', 'note': None,
          'sql': "SELECT b,SUM(CASE WHEN r>=50 THEN 1 ELSE 0 END) AS fifties FROM (SELECT batterId AS b,inningId,SUM(runs) AS r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId,inningId) t GROUP BY b ORDER BY fifties DESC LIMIT ?",
          'cols': ['player','50s'],
          'resolve': [0], 'format': lambda r: {'player': r[0], '50s': r[1]}
        },
        'most_4s': {
          'title': 'Most 4s', 'note': None,
          'sql': "SELECT batterId,SUM(CASE WHEN batterNum=4 THEN 1 ELSE 0 END) AS fours FROM deliveries WHERE isWicket!=1 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId ORDER BY fours DESC LIMIT ?",
          'cols': ['player','4s'],
          'resolve': [0], 'format': lambda r: {'player': r[0], '4s': r[1]}
        },
        'most_6s': {
          'title': 'Most 6s', 'note': None,
          'sql': "SELECT batterId,SUM(CASE WHEN batterNum=6 THEN 1 ELSE 0 END) AS sixes FROM deliveries WHERE isWicket!=1 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId ORDER BY sixes DESC LIMIT ?",
          'cols': ['player','6s'],
          'resolve': [0], 'format': lambda r: {'player': r[0], '6s': r[1]}
        },
        'most_3fers': {
          'title': 'Most 3-fers', 'note': None,
          'sql': "SELECT bowlerId,COUNT(*) AS threefers FROM (SELECT inningId,bowlerId,SUM(isWicket) AS wkts FROM deliveries WHERE bowlerId IS NOT NULL GROUP BY inningId,bowlerId HAVING wkts>=3) t GROUP BY bowlerId ORDER BY threefers DESC LIMIT ?",
          'cols': ['player','3fers'],
          'resolve': [0], 'format': lambda r: {'player': r[0], '3fers': r[1]}
        },
        'most_5fers': {
          'title': 'Most 5-fers', 'note': None,
          'sql': "SELECT bowlerId,COUNT(*) AS fivefers FROM (SELECT inningId,bowlerId,SUM(isWicket) AS wkts FROM deliveries WHERE bowlerId IS NOT NULL GROUP BY inningId,bowlerId HAVING wkts>=5) t GROUP BY bowlerId ORDER BY fivefers DESC LIMIT ?",
          'cols': ['player','5fers'],
          'resolve': [0], 'format': lambda r: {'player': r[0], '5fers': r[1]}
        },
        'most_hattricks': {
          'title': 'Most Hattricks', 'note': None,
          'sql': "SELECT bowlerId,COUNT(*) AS hattricks FROM (SELECT bowlerId,CASE WHEN isWicket=1 AND (LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp)=0 OR LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp) IS NULL) AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_hattrick FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL) t WHERE is_hattrick=1 GROUP BY bowlerId ORDER BY hattricks DESC LIMIT ?",
          'cols': ['player','hattricks'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'hattricks': r[1]}
        },
        'highest_bat_avg': {
          'title': 'Highest Batting AVG', 'note': 'Min. 10 innings',
          'sql': "SELECT batterId,CASE WHEN SUM(isWicket)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/SUM(isWicket) END AS avg,COUNT(DISTINCT inningId) AS inns FROM deliveries GROUP BY batterId HAVING inns>=10 ORDER BY avg DESC LIMIT ?",
          'cols': ['player','avg','innings'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'avg': round(r[1],2), 'innings': r[2]}
        },
        'highest_bat_sr': {
          'title': 'Highest Batting SR', 'note': 'Min. 100 balls',
          'sql': "SELECT batterId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 100.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN runs ELSE 0 END)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS sr FROM deliveries GROUP BY batterId HAVING SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)>=100 ORDER BY sr DESC LIMIT ?",
          'cols': ['player','sr'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'sr': round(r[1],2)}
        },
        'best_bowl_avg': {
          'title': 'Best Bowling AVG', 'note': 'Min. 10 innings',
          'sql': "SELECT bowlerId,CASE WHEN SUM(isWicket)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/SUM(isWicket) END AS avg,SUM(isWicket) AS wkts FROM deliveries GROUP BY bowlerId HAVING COUNT(DISTINCT inningId)>=10 ORDER BY avg ASC LIMIT ?",
          'cols': ['player','avg','wickets'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'avg': round(r[1],2), 'wickets': r[2]}
        },
        'best_bowl_eco': {
          'title': 'Best Bowling ECO', 'note': 'Min. 10 innings',
          'sql': "SELECT bowlerId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 6.0*SUM(runs)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS eco,COUNT(DISTINCT inningId) AS inns FROM deliveries GROUP BY bowlerId HAVING inns>=10 ORDER BY eco ASC LIMIT ?",
          'cols': ['player','eco','innings'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'eco': round(r[1],2), 'innings': r[2]}
        },
        'best_bowl_sr': {
          'title': 'Best Bowling SR', 'note': 'Min. 10 innings',
          'sql': "SELECT bowlerId,CASE WHEN SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 1.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)/SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END) END AS sr,COUNT(DISTINCT inningId) AS inns FROM deliveries GROUP BY bowlerId HAVING inns>=10 AND SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END)>0 ORDER BY sr ASC LIMIT ?",
          'cols': ['player','sr','innings'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'sr': round(r[1],2), 'innings': r[2]}
        },
        'fastest_50s': {
          'title': 'Fastest 50s', 'note': None,
          'sql': "SELECT batterId,MIN(balls) AS balls_to_50 FROM (SELECT batterId,inningId,SUM(runs) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS cr,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS balls FROM deliveries WHERE batterId IS NOT NULL) t WHERE cr>=50 GROUP BY batterId,inningId ORDER BY balls_to_50 ASC LIMIT ?",
          'cols': ['player','balls'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'balls': r[1]}
        },
        'fastest_30s': {
          'title': 'Fastest 30s', 'note': None,
          'sql': "SELECT batterId,MIN(balls) AS balls_to_30 FROM (SELECT batterId,inningId,SUM(runs) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS cr,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS balls FROM deliveries WHERE batterId IS NOT NULL) t WHERE cr>=30 GROUP BY batterId,inningId ORDER BY balls_to_30 ASC LIMIT ?",
          'cols': ['player','balls'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'balls': r[1]}
        },
        'best_bat_inning': {
          'title': 'Best Batting Inning', 'note': None,
          'sql': "SELECT batterId,SUM(runs) AS r,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS b,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END AS notout FROM deliveries GROUP BY batterId,inningId ORDER BY r DESC,b ASC LIMIT ?",
          'cols': ['player','score'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'score': f"{r[1]}({'*' if r[3] else ''}{r[2]})"}
        },
        'best_bowl_inning': {
          'title': 'Best Bowling Inning', 'note': None,
          'sql': "SELECT bowlerId,SUM(isWicket) AS w,SUM(runs) AS r,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS b FROM deliveries WHERE bowlerId IS NOT NULL GROUP BY bowlerId,inningId ORDER BY w DESC,r ASC,b ASC LIMIT ?",
          'cols': ['player','figures'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'figures': f"{r[1]}/{r[2]} ({r[3]//6}.{r[3]%6})"}
        },
        'best_partnerships_inning': {
          'title': 'Best Partnerships (Inning)', 'note': None,
          'sql': "SELECT CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END AS p1,CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END AS p2,SUM(runs) AS runs,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE nonStrikerId IS NOT NULL GROUP BY inningId,p1,p2 ORDER BY runs DESC LIMIT ?",
          'cols': ['batters','runs','balls'],
          'resolve': [0,1], 'format': lambda r: {'player': r[0], 'player2': r[1], 'runs': r[2], 'balls': r[3]}
        },
        'best_partnerships_overall': {
          'title': 'Best Partnerships (Overall)', 'note': None,
          'sql': "SELECT CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END AS p1,CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END AS p2,SUM(runs) AS runs,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE nonStrikerId IS NOT NULL GROUP BY p1,p2 ORDER BY runs DESC LIMIT ?",
          'cols': ['batters','runs','balls'],
          'resolve': [0,1], 'format': lambda r: {'player': r[0], 'player2': r[1], 'runs': r[2], 'balls': r[3]}
        },
        'highest_match_aggregate': {
          'title': 'Highest Match Aggregates', 'note': None,
          'sql': "SELECT matchId,SUM(runs) AS total FROM innings GROUP BY matchId ORDER BY total DESC LIMIT ?",
          'cols': ['match','runs'],
          'resolve': [], 'format': lambda r: {'matchId': r[0], 'runs': r[1]}
        },
        'highest_sr_inning': {
          'title': 'Highest SR in an Inning', 'note': 'Min. 10 balls',
          'sql': "SELECT batterId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 100.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN runs ELSE 0 END)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS sr,SUM(runs) AS r,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS b FROM deliveries GROUP BY batterId,inningId HAVING b>=10 ORDER BY sr DESC LIMIT ?",
          'cols': ['player','sr','inning'],
          'resolve': [0], 'format': lambda r: {'player': r[0], 'sr': round(r[1],2), 'inning': f"{r[2]} ({r[3]})"}
        },
      }

      if category not in CATEGORIES:
        return web.json_response({"error": f"Unknown category. Valid: {list(CATEGORIES.keys())}"}, status=400, headers=self.get_cors_headers())

      cfg = CATEGORIES[category]
      rows = await self.bot.fetchall(cfg['sql'], [limit])

      data = []
      for rank, row in enumerate(rows, 1):
        entry = cfg['format'](row)
        entry['rank'] = rank
        # Resolve Discord user IDs to names/avatars
        for idx in cfg['resolve']:
          uid = row[idx]
          if uid:
            u = await self.fetch_user_data(int(uid))
            key = 'player' if idx == 0 else 'player2'
            entry[key] = u['name']
            entry[key + 'Avatar'] = u['avatar']
        data.append(entry)

      return web.json_response({
        'category': category,
        'title': cfg['title'],
        'note': cfg['note'],
        'cols': cfg['cols'],
        'data': data,
      }, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_userApi(self, request):
    try: 
      users =request.query.get('userIds')
      if not users:
        return web.json_response({"error": 'Failed to get users'}, status=500, headers=self.get_cors_headers())
      users= [int(u) for u in users.split(",")]
      usersData= {}
      for u in users:
        userData = await self.fetch_user_data(u)
        usersData[str(u)]= userData
      return web.json_response(usersData, headers=self.get_cors_headers())
    except:
      return web.json_response({"error": 'Failed to get users'}, status=500, headers=self.get_cors_headers())
  async def cog_unload(self):
    if self.runner:
      await self.runner.cleanup()
  async def fetch_user_data(self, user_id):
    user = self.bot.get_user(user_id)
    if not user:
      try:
        user = await self.bot.fetch_user(user_id)
      except:
        return {"name": "Unknown Player", "avatar": ""}
    return {"displayName": user.display_name,"name": user.name, "avatar": str(user.display_avatar.url) if user.display_avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.id}"}
  def get_cors_headers(self):
    return {'Access-Control-Allow-Origin': '*','Access-Control-Allow-Methods': 'GET, OPTIONS','Access-Control-Allow-Headers': 'Content-Type'}
  def get_cutoff_end(self):
    now = datetime.utcnow() + timedelta(hours=5)
    days_since_wed = (now.weekday() - 2) % 7
    cutoff_end = (now - timedelta(days=days_since_wed)).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_end_utc = cutoff_end -timedelta(hours=5)
    return int(cutoff_end.timestamp()), int(cutoff_end_utc.timestamp())
  async def health_check(self, request):
    return web.json_response({"status": "online"}, headers=self.get_cors_headers())
  async def get_batting(self, request):
    try:
      page = int(request.query.get('page', 1))
      limit = min(50, max(1, int(request.query.get('limit', 10))))
      offset = (page - 1) * limit
      cutoff_end_ts, cutoff_end_utc = self.get_cutoff_end()
      min_ts = cutoff_end_ts - 2419200
      sql = f"SELECT batterId AS playerId, SUM((runs-CASE WHEN isWicket=1 THEN 5 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END) AS rating FROM deliveries WHERE batterId IS NOT NULL AND timestamp >= {min_ts} AND timestamp < {cutoff_end_ts} GROUP BY batterId HAVING rating>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
      rows = await self.bot.fetchall(sql)
      data = []
      for row in rows:
        u = await self.fetch_user_data(row[0])
        data.append({"playerId": str(row[0]), "playerName": u['name'], "profileImageUrl": u['avatar'], "rating": round(row[1] or 0, 2)})
      return web.json_response({"data": data, "page": page, "limit": limit, "cutoff": cutoff_end_utc}, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_bowling(self, request):
    try:
      page = int(request.query.get('page', 1))
      limit = min(50, max(1, int(request.query.get('limit', 10))))
      offset = (page - 1) * limit
      cutoff_end_ts, cutoff_end_utc = self.get_cutoff_end()
      min_ts = cutoff_end_ts - 2419200
      sql = f"SELECT bowlerId AS playerId, SUM(((CASE WHEN isWicket=1 THEN 25 ELSE 0 END)-runs/5.0)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END) AS rating FROM deliveries WHERE bowlerId IS NOT NULL AND timestamp >= {min_ts} AND timestamp < {cutoff_end_ts} GROUP BY bowlerId HAVING rating>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
      rows = await self.bot.fetchall(sql)
      data = []
      for row in rows:
        u = await self.fetch_user_data(row[0])
        data.append({"playerId": str(row[0]), "playerName": u['name'], "profileImageUrl": u['avatar'], "rating": round(row[1] or 0, 2)})
      return web.json_response({"data": data, "page": page, "limit": limit, "cutoff": cutoff_end_utc}, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_allrounder(self, request):
    try:
      page = int(request.query.get('page', 1))
      limit = min(50, max(1, int(request.query.get('limit', 10))))
      offset = (page - 1) * limit
      cutoff_end_ts, cutoff_end_utc = self.get_cutoff_end()
      min_ts = cutoff_end_ts - 2419200
      sql = f"SELECT playerId,SQRT(SUM(bat)*SUM(bowl)) AS rating FROM (SELECT batterId AS playerId,(runs-CASE WHEN isWicket=1 THEN 5 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END AS bat,0 AS bowl FROM deliveries WHERE batterId IS NOT NULL AND timestamp >= {min_ts} AND timestamp < {cutoff_end_ts} UNION ALL SELECT bowlerId AS playerId,0 AS bat,((CASE WHEN isWicket=1 THEN 25 ELSE 0 END)-runs/5.0)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END AS bowl FROM deliveries WHERE bowlerId IS NOT NULL AND timestamp >= {min_ts} AND timestamp < {cutoff_end_ts}) GROUP BY playerId HAVING SUM(bat)>0 AND SUM(bowl)>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
      rows = await self.bot.fetchall(sql)
      data = []
      for row in rows:
        u = await self.fetch_user_data(row[0])
        data.append({"playerId": str(row[0]), "playerName": u['name'], "profileImageUrl": u['avatar'], "rating": round(row[1] or 0, 2)})
      return web.json_response({"data": data, "page": page, "limit": limit, "cutoff": cutoff_end_utc}, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_recent_matches(self, request):
    recent = int(request.query.get('recent', 10))
    query = request.query.get('query', '').strip().lower()
    channel_id = request.query.get('channelId')
    guild_id = request.query.get('guildId')
    player_id = request.query.get('playerId')
    sql = "SELECT m.matchId, m.channelId, m.guildId, m.teamAName, m.teamBName, m.winner, MAX(d.timestamp) AS lastTimestamp FROM matches m JOIN deliveries d ON d.matchId = m.matchId"
    conditions = []
    params = []
    if query:
      conditions.append("(LOWER(m.matchId) LIKE ? OR LOWER(m.teamAName) LIKE ? OR LOWER(m.teamBName) LIKE ? OR LOWER(m.winner) LIKE ?)")
      q = f"%{query}%"
      params.extend([q, q, q, q])
    if channel_id:
      conditions.append("m.channelId = ?")
      params.append(int(channel_id))
    if guild_id:
      conditions.append("m.guildId = ?")
      params.append(int(guild_id))
    if player_id:
      conditions.append("(d.batterId = ? OR d.nonStrikerId = ? OR d.bowlerId = ?)")
      pid = int(player_id)
      params.extend([pid, pid, pid])
    if conditions:
      sql += " WHERE " + " AND ".join(conditions)
    sql += " GROUP BY m.matchId ORDER BY lastTimestamp DESC LIMIT ?"
    params.append(recent)
    rows = await self.bot.fetchall(sql, params)
    data = {'Matches': []}
    for row in rows:
      matchId, channelId, guildId, teamAName, teamBName, winner, timestamp = row
      channel = self.bot.get_channel(channelId)
      channelName = channel.name if channel else str(channelId)
      guild = self.bot.get_guild(guildId)
      guildName = guild.name if guild else str(guildId)
      data['Matches'].append({'id': matchId, 'channelName': channelName, 'guildName': guildName, 'teamAName': teamAName, 'teamBName': teamBName, 'winner': winner, 'timestamp': timestamp})
    return web.json_response(data, headers=self.get_cors_headers())

async def setup(bot):
  await bot.add_cog(RankingCog(bot))
