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
    app.add_routes([web.get('/rankings/batting', self.get_batting),web.get('/rankings/bowling', self.get_bowling),web.get('/rankings/allrounder', self.get_allrounder),web.get('/matches/getrecent',self.get_recent_matches),web.get('/', self.health_check),web.get('/matches/{matchId}', self.get_match),web.get('/matches/{matchId}/scorecard', self.get_scorecard),])
    self.runner = web.AppRunner(app)
    await self.runner.setup()
    self.site = web.TCPSite(self.runner, '0.0.0.0', 20375)
    await self.site.start()
    print("Rankings API running on http://0.0.0.0:20375")
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
      return web.json_response({
        "matchId": matchId,
        "channelName": channel.name if channel else str(channelId),
        "guildName": guild.name if guild else str(guildId),
        "teamAName": teamAName,
        "teamBName": teamBName,
        "winner": winner,
        "mvp": mvp,
        "innings": innings,
      }, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_scorecard(self, request):
    try:
      match_id = request.match_info['matchId']
      innings_rows = await self.bot.fetchall(
        "SELECT inningId,inningNo,battingTeam,bowlingTeam,runs,wickets,balls FROM innings WHERE matchId=? ORDER BY inningNo",
        [match_id]
      )
      if not innings_rows:
        return web.json_response({"error": "No innings found"}, status=404, headers=self.get_cors_headers())
      result = []
      for inning in innings_rows:
        inningId, inningNo, battingTeam, bowlingTeam, totalRuns, totalWickets, totalBalls = inning
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
        })
      return web.json_response({"matchId": match_id, "innings": result}, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
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
    return {"name": user.name, "avatar": str(user.display_avatar.url) if user.display_avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.id}"}
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
