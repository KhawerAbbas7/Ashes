import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import json
import hmac
import hashlib, os, time
from discord import Embed, Colour
from discord import ui 
from discord.ext import commands, tasks
from datetime import datetime, timedelta,timezone
TEST_ONLY = "matchId IN (SELECT matchId FROM matches WHERE format='test')"
class RankingCog(commands.Cog):
  def __init__(self, bot: commands.Bot):
    self.bot = bot
    self.site = None
    self.runner = None
  async def cog_load(self):
    app = web.Application()
    app.add_routes([web.get('/staff', self.get_staff),web.get('/rankings/batting', self.get_batting),web.get('/rankings/bowling', self.get_bowling),web.get('/rankings/allrounder', self.get_allrounder),web.get('/matches/getrecent',self.get_recent_matches),web.get('/matches/live', self.get_live_matches),web.get('/leaderboard', self.get_leaderboard),web.get('/', self.health_check),web.get('/matches/{matchId}/scorecard', self.get_scorecard),web.get('/matches/{matchId}/deliveries', self.get_deliveries),web.get('/matches/{matchId}/live', self.get_live_match),web.get('/matches/{matchId}', self.get_match),web.get('/users', self.get_userApi),web.get('/players/search', self.search_players),web.get('/players/{playerId}/stats', self.get_player_stats),web.post('/dbl', self.dbl)])
    self.runner = web.AppRunner(app)
    await self.runner.setup()
    self.site = web.TCPSite(self.runner, '0.0.0.0', 8000)
    await self.site.start()
  async def get_staff(self, request):
    try:
      official_guild = self.bot.get_guild(1459434908932902914)
      mods = []
      if official_guild:
        mod_role = official_guild.get_role(1462101976983535721)
        if mod_role:
          for m in mod_role.members:
            if not m.bot:
              mods.append({
                "id": str(m.id),
                "name": m.name,
                "displayName": m.display_name,
                "avatar": str(m.display_avatar.url) if m.display_avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={m.id}",
                "role": "Official Moderator"
              })
      return web.json_response({"moderators": mods}, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"moderators": [], "error": str(e)}, headers=self.get_cors_headers())
    
  async def dbl(self, request):
    signature = request.headers.get('x-topgg-signature')
    if not signature: return web.json_response({"status": "unauthorized"}, status=401)
    raw_body = await request.text()
    try:
      t_part, v1_part = signature.split(',')
      timestamp = t_part.split('=')[1]
      received_sig = v1_part.split('=')[1]
    except ValueError: return web.json_response({"status": "unauthorized"}, status=401)
    secret = os.getenv("TOPGGToken")
    message = f"{timestamp}.{raw_body}".encode('utf-8')
    expected = hmac.new(secret.encode('utf-8'), message, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, received_sig): return web.json_response({"status": "unauthorized"}, status=401)
    data = json.loads(raw_body) if raw_body else {}
    if data:
      user = self.bot.get_user(int(data['data']['user']['platform_id']))
      if user:
        cooldown = await self.bot.cfetchrow("SELECT expiresAt,lastClaimAt FROM cooldowns WHERE userId = ? AND command = ?", (user.id, 'vote'))
        streak = 1
        if cooldown:
          streakRetained = False
          streak = await self.bot.cfetchrow("SELECT streak FROM streaks WHERE userId = ? AND command = ?", (user.id, 'vote'))
          lastClaimAt = cooldown[1]
          if (time.time()- lastClaimAt) <= 24* 60 * 60:
            streakRetained = True
          streak = streak[0] +1 if streak and streakRetained else 1
        effective_streak = min(24, streak)
        reward = 2000 + (effective_streak - 1) * 1000
        claimTime = int(time.time())
        expires = claimTime+ 43200 
        await self.bot.cexecute("INSERT INTO cooldowns (userId, command, lastClaimAt, expiresAt,reminded) VALUES (?,?,?,?,?) ON CONFLICT(userId, command) DO UPDATE SET lastClaimAt=excluded.lastClaimAt, expiresAt = excluded.expiresAt, reminded= excluded.reminded", (user.id, 'vote', claimTime, expires, 0))
        bal = await self.bot.cfetchrow("SELECT coins FROM users WHERE userId = ?", (user.id,))
        bal = bal[0] if bal else 0
        await self.bot.cexecute("INSERT INTO users (userId, coins) VALUES (?,?) ON CONFLICT(userId) DO UPDATE SET coins =excluded.coins + coins", (user.id, reward))
        await self.bot.cexecute("INSERT INTO streaks (userId, command, streak) VALUES (?,?, ?) ON CONFLICT(userId, command) DO UPDATE SET streak =excluded.streak", (user.id, 'vote',streak))
        view=ui.LayoutView(timeout=30)
        container=ui.Container(accent_color=Colour.from_str("#277de4"))
        container.add_item(ui.TextDisplay(f"### Thank You for voting\n{bal} + {reward} = {bal + reward}{self.bot.AshesCoin}\n-# Streak: {streak}"))
        view.add_item(container)
        try:
          await user.send(view= view)
        except: pass
    return web.json_response({"status": "success"}, status=200)
  async def search_players(self, request):
    try:
      query = request.query.get('q', '').strip().lower()
      matched = []
      if not query: return web.json_response({"players": []}, headers=self.get_cors_headers())
      if query.isdigit():
        users = list(filter(lambda x: query in str(x.id), self.bot.users))
        if not users and len(query) >= 17:
          user = await self.bot.fetch_user(int(query))
          users = [user] if user else []
      else:
        users = list(filter(lambda x: query in str(x.name) or query.lower() in x.display_name.lower(), self.bot.users))
      for user in users[:20]:
        matched.append({"id": str(user.id), "name": user.name, "avatar": user.display_avatar.url if user.display_avatar else f"https://api.dicebear.com/7.x/avataaars/svg?seed={user.id}"})
        if len(matched) >= 20: break
      return web.json_response({"players": matched}, headers=self.get_cors_headers())
    except Exception as e: return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  def _format_filter(self, match_format, alias=""):
    if match_format == "all":
      return ""
    column = f"{alias}matchId" if alias else "matchId"
    return f" AND {column} IN (SELECT matchId FROM matches WHERE format='{match_format}')"

  def t15_phase(self, game):
    if game.format != "t15" or not game.innings:
      return None
    phase_no = game.phase(game.currentInning.balls)
    balls_left = max(0, phase_no * 30 - game.currentInning.balls)
    return {
      "number": phase_no,
      "name": game.PHASES[phase_no]["name"],
      "boundaries": game.PHASES[phase_no]["boundaries"],
      "ballsLeft": balls_left,
      "oversLeft": f"{balls_left // 6}.{balls_left % 6}",
      "totalBalls": game.maxBalls
    }

  async def _career_stats(self, pid, match_format="all"):
    fc = self._format_filter(match_format)
    fc_alias = self._format_filter(match_format, "d2.")
    bat_basic = await self.bot.fetchrow(f"SELECT (SELECT COUNT(DISTINCT matchId) FROM deliveries d2 WHERE (d2.batterId=d.batterId OR d2.bowlerId=d.batterId){fc_alias}),COUNT(DISTINCT inningId),COALESCE(SUM(runs),0),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END),COALESCE(SUM(isWicket),0),COALESCE(SUM(CASE WHEN runs=4 THEN 1 END),0),COALESCE(SUM(CASE WHEN runs=6 THEN 1 END),0),COALESCE(SUM(CASE WHEN runs=0 AND isWicket=0 THEN 1 END),0), COALESCE(SUM(CASE WHEN batterNum IS NULL THEN 1 END),0) FROM deliveries d WHERE batterId=?{fc}", [pid])
    b_match, b_inn, b_runs, b_balls, b_outs, b_fours, b_sixes, b_dots , b_afks = bat_basic if bat_basic else (0,0,0,0,0,0,0,0, 0)
    b_afkperc = round((b_afks / b_balls) *100, 2) if b_balls else 0.00
    bat_miles = await self.bot.fetchrow(f"SELECT COALESCE(SUM(CASE WHEN r>=30 AND r<50 THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN r>=50 AND r<100 THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN r>=100 AND r<200 THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN r>=200 THEN 1 ELSE 0 END),0) FROM (SELECT SUM(runs) r FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL{fc} GROUP BY inningId)", [pid])
    thirties, fifties, hundreds, two_hundreds = bat_miles if bat_miles else (0,0,0,0)
    bbi_row = await self.bot.fetchrow(f"SELECT r,notout FROM (SELECT SUM(runs) r,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END notout FROM deliveries WHERE batterId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL{fc} GROUP BY inningId ORDER BY r DESC,COUNT(*) ASC LIMIT 1)", [pid])
    hs = f"{bbi_row[0]}{'*' if bbi_row[1]==1 else ''}" if bbi_row else "0"
    ducks_row = await self.bot.fetchrow(f"SELECT COUNT(*) FROM (SELECT matchId, inningId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId=?{fc} GROUP BY matchId, inningId) WHERE total_runs=0 AND got_out=1", [pid])
    ducks = ducks_row[0] if ducks_row else 0
    not_outs = b_inn - b_outs if b_inn > b_outs else 0
    bat_avg = round(b_runs/b_outs, 2) if b_outs > 0 else b_runs
    bat_sr = round((b_runs/b_balls)*100, 2) if b_balls > 0 else 0.0
    bound_pct = round(((b_fours*4 + b_sixes*6) / b_runs) * 100, 2) if b_runs > 0 else 0.0
    batting = {"matches": b_match or 0, "innings": b_inn or 0, "notOuts": not_outs, "runs": b_runs or 0, "balls": b_balls or 0, "highestScore": hs, "average": bat_avg, "strikeRate": bat_sr, "twoHundreds": two_hundreds, "hundreds": hundreds, "fifties": fifties, "thirties": thirties, "ducks": ducks, "fours": b_fours or 0, "sixes": b_sixes or 0, "dotBalls": b_dots or 0, "boundaryPct": bound_pct, "afkPct": b_afkperc}
    bowl_basic = await self.bot.fetchrow(f"SELECT COUNT(DISTINCT matchId),COUNT(DISTINCT inningId),COUNT(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 END),COALESCE(SUM(runs),0),COALESCE(SUM(isWicket),0),COALESCE(SUM(CASE WHEN runs=0 THEN 1 END),0),COALESCE(SUM(CASE WHEN runs=4 THEN 1 END),0),COALESCE(SUM(CASE WHEN runs=6 THEN 1 END),0), COALESCE(SUM(CASE WHEN bowlerNum IS NULL THEN 1 END),0) FROM deliveries WHERE bowlerId=?{fc}", [pid])
    bw_match, bw_inn, bw_balls, bw_runs, bw_wkts, bw_dots, bw_fours, bw_sixes, bw_afks = bowl_basic if bowl_basic else (0,0,0,0,0,0,0,0)
    best_bowl = await self.bot.fetchrow(f"SELECT w,r FROM (SELECT SUM(isWicket) w,SUM(runs) r,COUNT(*) b FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL{fc} GROUP BY inningId ORDER BY w DESC,r ASC,b ASC LIMIT 1)", [pid])
    bbi = f"{best_bowl[0]}/{best_bowl[1]}" if best_bowl else "0/0"
    bowl_miles = await self.bot.fetchrow(f"SELECT COALESCE(SUM(CASE WHEN w>=3 AND w<5 THEN 1 ELSE 0 END),0),COALESCE(SUM(CASE WHEN w>=5 THEN 1 ELSE 0 END),0) FROM (SELECT SUM(isWicket) w FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL{fc} GROUP BY inningId)", [pid])
    three_w, five_w = bowl_miles if bowl_miles else (0,0)
    ten_w_row = await self.bot.fetchrow(f"SELECT COUNT(*) FROM (SELECT SUM(isWicket) w FROM deliveries WHERE bowlerId=?{fc} GROUP BY matchId) WHERE w>=10", [pid])
    ten_w_match = ten_w_row[0] if ten_w_row else 0
    hattrick_row = await self.bot.fetchrow(f"SELECT COUNT(*) FROM (SELECT CASE WHEN isWicket=1 AND (LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp)=0 OR LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp) IS NULL) AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_hattrick FROM deliveries WHERE bowlerId=? AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL{fc}) t WHERE is_hattrick=1", [pid])
    hattricks = hattrick_row[0] if hattrick_row else 0
    b_avg = round(bw_runs/bw_wkts, 2) if bw_wkts > 0 else 0.0
    b_eco = round((bw_runs/bw_balls)*6, 2) if bw_balls > 0 else 0.0
    b_sr = round(bw_balls/bw_wkts, 2) if bw_wkts > 0 else 0.0
    dot_pct = round((bw_dots/bw_balls) * 100, 2) if bw_balls > 0 else 0.0
    bw_afkPCT= round((bw_afks / bw_balls) *100, 2) if bw_balls else 0.00
    bowling = {"matches": b_match or 0, "innings": bw_inn or 0, "balls": bw_balls or 0, "runs": bw_runs or 0, "wickets": bw_wkts or 0, "bbi": bbi, "average": b_avg, "economy": b_eco, "strikeRate": b_sr, "threeWickets": three_w, "fiveWickets": five_w, "tenWickets": ten_w_match, "dotBalls": bw_dots or 0, "dotPct": dot_pct, "foursConceded": bw_fours or 0, "sixesConceded": bw_sixes or 0, "hattricks": hattricks, "afkPct": bw_afkPCT}
    mvp_filter = "" if match_format == "all" else f" AND format='{match_format}'"
    mvp_row = await self.bot.fetchrow(f"SELECT COUNT(*) FROM matches WHERE mvpId=?{mvp_filter}", [pid])
    mvps = mvp_row[0] if mvp_row else 0
    return {"batting": batting, "bowling": bowling, "general": {"mvps": mvps}}

  async def get_player_stats(self, request):
    try:
      pid = int(request.match_info['playerId'])
      recent_limit = min(50, max(1, int(request.query.get('recent', 5))))
      requested_format = (request.query.get('format') or 'all').lower()
      match_format = requested_format if requested_format in ('all', 'test', 't15') else 'all'
      u = await self.fetch_user_data(pid)
      stats = await self._career_stats(pid, match_format)
      recent_match_sql="SELECT m.matchId, MAX(d.timestamp), m.format FROM matches m JOIN deliveries d ON d.matchId=m.matchId WHERE (d.batterId=? OR d.bowlerId=?)"
      recent_params=[pid, pid]
      if match_format != "all":
        recent_match_sql += " AND m.format=?"
        recent_params.append(match_format)
      recent_match_sql += " GROUP BY m.matchId ORDER BY MAX(d.timestamp) DESC LIMIT ?"
      recent_params.append(recent_limit)
      recent_matches=await self.bot.fetchall(recent_match_sql, recent_params)
      recent=[]
      for mid, ts, fmt in recent_matches:
        bat_sql="SELECT SUM(runs),SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END),SUM(isWicket) FROM deliveries WHERE matchId=? AND batterId=? GROUP BY inningId ORDER BY MIN(timestamp) ASC"
        bat_rows=await self.bot.fetchall(bat_sql, [mid, pid])
        bat_strs=[f"{r[0]}({r[1]}){'*' if not r[2] else ''}" for r in bat_rows]
        bowl_sql="SELECT SUM(isWicket),SUM(runs),SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) FROM deliveries WHERE matchId=? AND bowlerId=? GROUP BY inningId ORDER BY MIN(timestamp) ASC"
        bowl_rows=await self.bot.fetchall(bowl_sql, [mid, pid])
        bowl_strs=[f"{r[0]}-{r[1]}({r[2]//6}.{r[2]%6})" for r in bowl_rows]
        bat_str="&".join(bat_strs) if bat_strs else "DNB"
        bowl_str="&".join(bowl_strs) if bowl_strs else "DNB"
        recent.append({"bat": bat_str, "bowl": bowl_str, "timestamp": ts, "matchId": mid, "format": fmt or "test"})
      cutoff_end_ts, _ = self.get_cutoff_end()
      min_ts = cutoff_end_ts - 2419200
      bat_sql = f"WITH r AS (SELECT batterId AS id, SUM((runs-CASE WHEN isWicket=1 THEN 5 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END) AS rt FROM deliveries WHERE batterId IS NOT NULL AND timestamp>={min_ts} AND timestamp<{cutoff_end_ts} GROUP BY batterId HAVING rt>0) SELECT rank, rt FROM (SELECT id, rt, ROW_NUMBER() OVER(ORDER BY rt DESC) AS rank FROM r) WHERE id=?"
      bat_rank_row = await self.bot.fetchrow(bat_sql, [pid])
      bowl_sql = f"WITH r AS (SELECT bowlerId AS id, SUM(((CASE WHEN isWicket=1 THEN 25 ELSE 0 END)-runs/5.0)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END) AS rt FROM deliveries WHERE bowlerId IS NOT NULL AND timestamp>={min_ts} AND timestamp<{cutoff_end_ts} GROUP BY bowlerId HAVING rt>0) SELECT rank, rt FROM (SELECT id, rt, ROW_NUMBER() OVER(ORDER BY rt DESC) AS rank FROM r) WHERE id=?"
      bowl_rank_row = await self.bot.fetchrow(bowl_sql, [pid])
      ar_sql = f"WITH r AS (SELECT id, SQRT(SUM(bat)*SUM(bowl)) AS rt FROM (SELECT batterId AS id, (runs-CASE WHEN isWicket=1 THEN 5 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END AS bat, 0 AS bowl FROM deliveries WHERE batterId IS NOT NULL AND timestamp>={min_ts} AND timestamp<{cutoff_end_ts} UNION ALL SELECT bowlerId AS id, 0 AS bat, ((CASE WHEN isWicket=1 THEN 25 ELSE 0 END)-runs/5.0)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END AS bowl FROM deliveries WHERE bowlerId IS NOT NULL AND timestamp>={min_ts} AND timestamp<{cutoff_end_ts}) GROUP BY id HAVING SUM(bat)>0 AND SUM(bowl)>0) SELECT rank, rt FROM (SELECT id, rt, ROW_NUMBER() OVER(ORDER BY rt DESC) AS rank FROM r) WHERE id=?"
      ar_rank_row = await self.bot.fetchrow(ar_sql, [pid])
      rankings = {"batting": {"rank": bat_rank_row[0] if bat_rank_row else None, "rating": round(bat_rank_row[1], 2) if bat_rank_row else 0}, "bowling": {"rank": bowl_rank_row[0] if bowl_rank_row else None, "rating": round(bowl_rank_row[1], 2) if bowl_rank_row else 0}, "allrounder": {"rank": ar_rank_row[0] if ar_rank_row else None, "rating": round(ar_rank_row[1], 2) if ar_rank_row else 0}}
      return web.json_response({"player": {"id": str(pid), "name": u['name'], "avatar": u['avatar']}, "format": match_format, "batting": stats["batting"], "bowling": stats["bowling"], "general": stats["general"], "recentPerformances": recent, "rankings": rankings}, headers=self.get_cors_headers())
    except Exception as e: return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_match(self, request):
    try:
      match_id = request.match_info['matchId']
      match_row = await self.bot.fetchrow(
        "SELECT matchId,channelId,guildId,teamAName,teamBName,winner,mvpId,matchMaximumBalls,drawByAgreement,format FROM matches WHERE matchId=?",
        [match_id]
      )
      if not match_row:
        return web.json_response({"error": "Match not found"}, status=404, headers=self.get_cors_headers())
      matchId, channelId, guildId, teamAName, teamBName, winner, mvpId, matchMaximumBalls, drawByAgreement, matchFormat = match_row
      channel = self.bot.get_channel(channelId)
      guild = self.bot.get_guild(guildId)
      innings_rows = await self.bot.fetchall(
        "SELECT inningId,inningNo,battingTeam,bowlingTeam,runs,wickets,balls,isDeclared,isFollowOn FROM innings WHERE matchId=? ORDER BY inningNo",
        [match_id]
      )
      innings = []
      total_balls = 0
      for row in innings_rows:
        inningId, inningNo, battingTeam, bowlingTeam, runs, wickets, balls, isDeclared, isFollowOn = row
        total_balls += (balls or 0)
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
          "isFollowOn": bool(isFollowOn)
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
        "matchMaximumBalls": matchMaximumBalls or 180,
        "maxBalls": matchMaximumBalls or 180,
        "matchTotalBalls": total_balls,
        "drawByAgreement": bool(drawByAgreement),
        "format": matchFormat or "test",
        "timestamp": ts[0] if ts and ts[0] else 0
      }, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())

  async def get_scorecard(self, request):
    try:
      match_id = request.match_info['matchId']
      match_row = await self.bot.fetchrow(
        "SELECT matchId,channelId,guildId,teamAName,teamBName,winner,mvpId,matchMaximumBalls,drawByAgreement,format FROM matches WHERE matchId=?",
        [match_id]
      )
      if not match_row:
        return web.json_response({"error": "No innings found"}, status=404, headers=self.get_cors_headers())
      matchId, channelId, guildId, teamAName, teamBName, winner, mvpId, matchMaximumBalls, drawByAgreement, matchFormat= match_row
      matchFormat = (matchFormat or "test").lower()
      score_max_balls = matchMaximumBalls or (90 if matchFormat == "t15" else 180)
      innings_rows = await self.bot.fetchall(
        "SELECT inningId,inningNo,battingTeam,bowlingTeam,runs,wickets,balls,isFollowOn,isDeclared FROM innings WHERE matchId=? ORDER BY inningNo",
        [match_id]
      )
      innings_ctx = [
        {
          "inningNo": row[1],
          "battingTeam": row[2],
          "bowlingTeam": row[3],
          "runs": row[4] or 0
        }
        for row in innings_rows
      ]
      result = []
      match_total_balls = 0
      for inning in innings_rows:
        inningId, inningNo, battingTeam, bowlingTeam, totalRuns, totalWickets, totalBalls, isFollowOn, isDeclared = inning
        match_total_balls += (totalBalls or 0)
        bat_rows = await self.bot.fetchall(
          "SELECT batterId, SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls, SUM(CASE WHEN runs=4 THEN 1 ELSE 0 END) AS fours, SUM(CASE WHEN runs=6 THEN 1 ELSE 0 END) AS sixes, SUM(CASE WHEN runs=0 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS dots, MIN(timestamp) AS batting_order, MAX(CASE WHEN isWicket=1 THEN 1 ELSE 0 END) AS dismissed, MAX(CASE WHEN isWicket=1 THEN bowlerId ELSE NULL END) AS dismissedBy FROM deliveries WHERE inningId=? AND batterId IS NOT NULL GROUP BY batterId ORDER BY batting_order",
          [inningId]
        )
        wicket_rows = await self.bot.fetchall(
          "SELECT batterId,InningBalls,batterNum,bowlerNum,runs,canDo0,canDoBoundary,InningRuns,InningWickets FROM deliveries WHERE inningId=? AND isWicket=1 AND batterId IS NOT NULL ORDER BY timestamp, rowid",
          [inningId]
        )
        dismissal_map = {}
        for wicket in wicket_rows:
          if wicket[0] not in dismissal_map:
            dismissal_map[wicket[0]] = wicket
        batters = []
        for row in bat_rows:
          batterId, runs, balls, fours, sixes, dots, batting_order, dismissed, dismissedBy = row
          sr = round((runs / balls) * 100, 2) if balls else 0
          u = await self.fetch_user_data(batterId)
          dismissal = None
          if bool(dismissed):
            wicket = dismissal_map.get(batterId)
            if wicket:
              ball_no = wicket[1] or 0
              batter_num = wicket[2]
              bowler_num = wicket[3]
              is_afk = batter_num is None or bowler_num is None
              if batter_num is None and bowler_num is None:
                afk_side = "both"
              elif batter_num is None:
                afk_side = "batter"
              elif bowler_num is None:
                afk_side = "bowler"
              else:
                afk_side = None
              dismissal_runs = wicket[7] or 0
              dismissal_wickets = wicket[8] or 0
              dismissal = {
                "ball": f"{ball_no // 6}.{ball_no % 6}",
                "batterNum": batter_num,
                "bowlerNum": bowler_num,
                "runs": wicket[4] or 0,
                "batterCanDo0": bool(wicket[5]),
                "batterCanDoBoundary": bool(wicket[6]),
                "isAfk": is_afk,
                "afkSide": afk_side,
                "inningScore": f"{dismissal_runs}/{dismissal_wickets}",
                "matchStatus": self._delivery_status(
                  innings_ctx, matchFormat, score_max_balls, inningNo,
                  dismissal_runs, dismissal_wickets, ball_no
                )
              }
            if dismissal and dismissal["isAfk"]:
              dismissed_str = "AFK / Out"
            elif dismissedBy:
              dismissedByU = await self.fetch_user_data(dismissedBy)
              dismissed_str = f"b. {dismissedByU['name']}"
            else:
              dismissed_str = "AFK / Out"
          else:
            dismissed_str = "not out"
          batters.append({
            "playerId": str(batterId),
            "playerName": u["name"],
            "avatar": u["avatar"],
            "runs": runs or 0,
            "balls": balls or 0,
            "fours": fours or 0,
            "sixes": sixes or 0,
            "dots": dots or 0,
            "strikeRate": sr,
            "dismissed": bool(dismissed),
            "dismissedBy": dismissed_str,
            "dismissal": dismissal
          })
        bowl_rows = await self.bot.fetchall(
          "SELECT bowlerId, COUNT(*) AS balls, SUM(runs) AS runs, SUM(isWicket) AS wickets, MIN(timestamp) AS bowling_order FROM deliveries WHERE inningId=? AND bowlerId IS NOT NULL AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY bowlerId ORDER BY bowling_order",
          [inningId]
        )
        bowlers = []
        for row in bowl_rows:
          bowlerId, balls, runs, wickets, bowling_order = row
          overs_str = f"{balls // 6}.{balls % 6}"
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
            "economy": economy
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
          "isFollowOn": bool(isFollowOn),
          "isDeclared": bool(isDeclared)
        })
      return web.json_response({
        "matchId": match_id,
        "teamAName": teamAName,
        "teamBName": teamBName,
        "innings": result,
        "winner": winner,
        "drawByAgreement": bool(drawByAgreement),
        "matchMaximumBalls": matchMaximumBalls or 180,
        "maxBalls": matchMaximumBalls or 180,
        "matchTotalBalls": match_total_balls,
        "format": matchFormat or "test"
      }, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  def _delivery_status(self, innings, match_format, max_balls, inning_no, runs, wickets, balls):
    current = next((i for i in innings if i["inningNo"] == inning_no), None)
    if not current:
      return ""
    bat = current["battingTeam"]
    bowl = current["bowlingTeam"]
    bat_prev = sum((i["runs"] or 0) for i in innings if i["battingTeam"] == bat and i["inningNo"] != inning_no)
    bowl_total = sum((i["runs"] or 0) for i in innings if i["battingTeam"] == bowl)
    bat_total = bat_prev + runs
    is_chase = (match_format == "t15" and inning_no == 2) or (match_format == "test" and inning_no == 4)
    if is_chase:
      target = (bowl_total - bat_prev) + 1
      need = target - runs
      if need <= 0:
        return f"{bat} have won"
      if match_format == "t15":
        balls_left = max(0, max_balls - balls)
        if balls_left == 0:
          return "Match tied" if need == 1 else f"{bowl} have won"
        return f"{bat} need {need} runs from {balls_left} balls"
      return f"{bat} need {need} runs to win"
    if match_format == "test" and inning_no in (2, 3):
      diff = bat_total - bowl_total
      if diff > 0:
        return f"{bat} lead by {diff} runs"
      if diff < 0:
        return f"{bat} trail by {abs(diff)} runs"
      return "Scores are level"
    return f"{bat} {runs}/{wickets} ({balls // 6}.{balls % 6})"

  async def get_deliveries(self, request):
    try:
      match_id = request.match_info['matchId']
      match_row = await self.bot.fetchrow(
        "SELECT teamAName,teamBName,winner,matchMaximumBalls,format FROM matches WHERE matchId=?",
        [match_id]
      )
      if not match_row:
        return web.json_response({"error": "Match not found"}, status=404, headers=self.get_cors_headers())
      team_a_name, team_b_name, winner, match_max_balls, match_format = match_row
      match_format = (match_format or "test").lower()
      max_balls = match_max_balls or (90 if match_format == "t15" else 180)
      try:
        inning_no = int(request.query.get('inningNo', 1))
      except ValueError:
        inning_no = 1
      try:
        page = max(1, int(request.query.get('page', 1)))
      except ValueError:
        page = 1
      try:
        limit = min(50, max(1, int(request.query.get('limit', 20))))
      except ValueError:
        limit = 20
      delivery_filter = request.query.get('filter', 'all')
      allowed_filters = {
        'all', 'batter-can-do-0', 'batter-cant-do-0', 'bowler-can-do-0',
        'fours', 'sixes', 'wickets', 'afk', 'non-afk'
      }
      if delivery_filter not in allowed_filters:
        delivery_filter = 'all'
      batter_filter = request.query.get('batterId') or None
      if batter_filter and not batter_filter.isdigit():
        batter_filter = None
      bowler_filter = request.query.get('bowlerId') or None
      if bowler_filter and not bowler_filter.isdigit():
        bowler_filter = None

      innings_rows = await self.bot.fetchall(
        "SELECT inningId,inningNo,battingTeam,bowlingTeam,runs,wickets,balls,isDeclared,isFollowOn FROM innings WHERE matchId=? ORDER BY inningNo",
        [match_id]
      )
      innings = []
      for row in innings_rows:
        innings.append({
          "inningId": row[0],
          "inningNo": row[1],
          "battingTeam": row[2],
          "bowlingTeam": row[3],
          "runs": row[4] or 0,
          "wickets": row[5] or 0,
          "balls": row[6] or 0,
          "isDeclared": bool(row[7]),
          "isFollowOn": bool(row[8])
        })
      current_inning = next((i for i in innings if i["inningNo"] == inning_no), None)
      if not current_inning:
        return web.json_response({"error": "Innings not found"}, status=404, headers=self.get_cors_headers())

      rows = await self.bot.fetchall(
        "SELECT ballId,batterId,nonStrikerId,bowlerId,canDo0,canDoBoundary,isWicket,runs,InningRuns,InningBalls,InningOvers,InningWickets,batterNum,bowlerNum,timestamp,day,session FROM deliveries WHERE inningId=? ORDER BY timestamp, rowid",
        [current_inning["inningId"]]
      )

      bowler_over_runs = {}
      for row in rows:
        batter_num, bowler_num = row[12], row[13]
        if batter_num is None or bowler_num is None:
          continue
        over_no = (row[9] + 5) // 6
        key = (row[3], over_no)
        bowler_over_runs[key] = bowler_over_runs.get(key, 0) + (row[7] or 0)
      bowler_over_numbers = {}
      for (bowler_id, over_no) in bowler_over_runs.keys():
        bowler_over_numbers.setdefault(bowler_id, []).append(over_no)
      for over_numbers in bowler_over_numbers.values():
        over_numbers.sort()

      deliveries = []
      bowler_history = {}
      zero_in_over = {}
      for row in rows:
        (ball_id, batter_id, non_striker_id, bowler_id, can_do_0, can_do_boundary,
         is_wicket, runs, inning_runs, inning_balls, inning_overs, inning_wickets,
         batter_num, bowler_num, timestamp, day, session) = row
        runs = runs or 0
        inning_runs = inning_runs or 0
        inning_balls = inning_balls or 0
        inning_wickets = inning_wickets or 0
        legal = batter_num is not None and bowler_num is not None
        if legal:
          over_no = (inning_balls + 5) // 6
          pre_balls = max(0, inning_balls - 1)
        else:
          over_no = inning_balls // 6 + 1
          pre_balls = inning_balls

        history = bowler_history.get(bowler_id, [])
        is_on_hattrick = (
          len(history) >= 2
          and history[-1] == 1
          and history[-2] == 1
          and (len(history) == 2 or history[-3] != 1)
        )
        previous_overs = [o for o in bowler_over_numbers.get(bowler_id, []) if o < over_no]
        last_over_maiden = bool(previous_overs) and bowler_over_runs.get((bowler_id, previous_overs[-1]), 0) == 0
        zero_before = zero_in_over.get(over_no, False)
        bowler_can_do_0 = bool(
          is_on_hattrick or (pre_balls >= 6 and last_over_maiden and not zero_before)
        )

        if legal:
          bowler_history.setdefault(bowler_id, []).append(1 if is_wicket else 0)
          if bowler_num == 0:
            zero_in_over[over_no] = True

        if batter_num is None and bowler_num is None:
          afk_side = "both"
        elif batter_num is None:
          afk_side = "batter"
        elif bowler_num is None:
          afk_side = "bowler"
        else:
          afk_side = None

        deliveries.append({
          "ballId": ball_id,
          "ball": f"{inning_balls // 6}.{inning_balls % 6}",
          "over": over_no,
          "runs": runs,
          "isWicket": bool(is_wicket),
          "isFour": runs == 4,
          "isSix": runs == 6,
          "isAfk": not legal,
          "afkSide": afk_side,
          "batterId": str(batter_id) if batter_id is not None else None,
          "bowlerId": str(bowler_id) if bowler_id is not None else None,
          "batterNum": batter_num,
          "bowlerNum": bowler_num,
          "inningRuns": inning_runs,
          "inningWickets": inning_wickets,
          "inningBalls": inning_balls,
          "inningScore": f"{inning_runs}/{inning_wickets}",
          "inningOvers": f"{inning_balls // 6}.{inning_balls % 6}",
          "matchStatus": self._delivery_status(
            innings, match_format, max_balls, inning_no, inning_runs, inning_wickets, inning_balls
          ),
          "batterCanDo0": bool(can_do_0),
          "batterCanDoBoundary": bool(can_do_boundary),
          "bowlerCanDo0": bowler_can_do_0,
          "day": day,
          "session": session,
          "timestamp": timestamp
        })

      if delivery_filter == 'batter-can-do-0':
        filtered = [d for d in deliveries if not d["isAfk"] and d["batterCanDo0"]]
      elif delivery_filter == 'batter-cant-do-0':
        filtered = [d for d in deliveries if not d["isAfk"] and not d["batterCanDo0"]]
      elif delivery_filter == 'bowler-can-do-0':
        filtered = [d for d in deliveries if not d["isAfk"] and d["bowlerCanDo0"]]
      elif delivery_filter == 'fours':
        filtered = [d for d in deliveries if d["isFour"]]
      elif delivery_filter == 'sixes':
        filtered = [d for d in deliveries if d["isSix"]]
      elif delivery_filter == 'wickets':
        filtered = [d for d in deliveries if d["isWicket"]]
      elif delivery_filter == 'afk':
        filtered = [d for d in deliveries if d["isAfk"]]
      elif delivery_filter == 'non-afk':
        filtered = [d for d in deliveries if not d["isAfk"]]
      else:
        filtered = deliveries

      if batter_filter:
        filtered = [d for d in filtered if d["batterId"] == batter_filter]
      if bowler_filter:
        filtered = [d for d in filtered if d["bowlerId"] == bowler_filter]

      filtered.reverse()
      total = len(filtered)
      start = (page - 1) * limit
      page_rows = filtered[start:start + limit]

      player_ids = set()
      for d in page_rows:
        if d["batterId"]:
          player_ids.add(int(d["batterId"]))
        if d["bowlerId"]:
          player_ids.add(int(d["bowlerId"]))
      player_map = {}
      if player_ids:
        player_id_list = list(player_ids)
        users = await asyncio.gather(*[self.fetch_user_data(pid) for pid in player_id_list])
        for pid, user in zip(player_id_list, users):
          player_map[pid] = user

      for d in page_rows:
        batter = player_map.get(int(d["batterId"])) if d["batterId"] else None
        bowler = player_map.get(int(d["bowlerId"])) if d["bowlerId"] else None
        d["batter"] = {"id": d["batterId"], "name": batter["name"] if batter else "Unknown Player"}
        d["bowler"] = {"id": d["bowlerId"], "name": bowler["name"] if bowler else "Unknown Player"}

      return web.json_response({
        "matchId": match_id,
        "teamAName": team_a_name,
        "teamBName": team_b_name,
        "winner": winner,
        "format": match_format,
        "maxBalls": max_balls,
        "inningNo": inning_no,
        "filter": delivery_filter,
        "batterId": batter_filter,
        "bowlerId": bowler_filter,
        "page": page,
        "limit": limit,
        "total": total,
        "hasMore": start + limit < total,
        "innings": innings,
        "deliveries": page_rows
      }, headers=self.get_cors_headers())
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
            "balls": inn.balls,
            "overs": f"{inn.balls // 6}.{inn.balls % 6}",
            "runRate": round(inn.runs / (inn.balls / 6), 2) if inn.balls else 0.0,
            "isDeclared": inn.declared,
            "isFollowOn": inn.followOn
          })
        team_a_players = [{"id": str(p.id), "name": p.name} for p in game.teama.players]
        team_b_players = [{"id": str(p.id), "name": p.name} for p in game.teamb.players]
        day, session = game.getDaysAndSessions() if game.started else (1, 1)
        phase = self.t15_phase(game) if game.started else None
        matches.append({
          "id": game.gameId,
          "state": state,
          "format": "T15" if game.format == "t15" else "Test",
          "phase": phase,
          "channelId": str(channel_id),
          "channelName": channel.name if channel else str(channel_id),
          "guildName": guild.name if guild else str(game.ctx.guild.id),
          "teamAName": game.teama.name,
          "teamBName": game.teamb.name,
          "teamAPlayers": team_a_players,
          "teamBPlayers": team_b_players,
          "innings": innings_summary,
          "maxBalls": game.maxBalls,
          "matchTotalBalls": game.matchTotalBalls,
          "day": day,
          "session": session,
          "statusText": game.matchStatus() if game.started and game.innings else "Waiting in Lobby"
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
        batters_out = []
        def get_order(player):
          try:
            return inn.cantBat.index(player.id)
          except ValueError:
            try:
              return len(inn.cantBat) + inn.battingTeam.players.index(player)
            except:
              return len(inn.cantBat) + len(inn.battingTeam.players)
        ordered_batters = sorted(inn.batters.items(), key=lambda x: get_order(x[0]))
        for player, b in ordered_batters:
          can_do_0 = b.consecutiveDots != 3
          can_do_boundary = not game.cantBoundary(b, inn)
          boundary_limit = game.PHASES[game.phase(inn.balls)]["boundaries"] if game.format == "t15" else (2 if b.balls >= 15 else 1)
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
            "consecutiveDots": b.consecutiveDots,
            "boundaryThisOver": b.BoundaryThisOver,
            "canDo0": can_do_0,
            "canDoBoundary": can_do_boundary,
            "boundaryLimit": boundary_limit,
            "timeline": list(b.timeline)
          })
        bowlers_out = []
        for player, b in inn.bowlers.items():
          economy = round((b.runsConceded / b.balls) * 6, 2) if b.balls else 0.0
          bowlers_out.append({
            "playerId": str(player.id),
            "playerName": player.name,
            "overs": f"{b.balls // 6}.{b.balls % 6}",
            "balls": b.balls,
            "maidens": b.maidens,
            "runs": b.runsConceded,
            "wickets": b.wickets,
            "economy": economy,
            "timeline": list(b.timeline)
          })
        innings_out.append({
          "inningNo": inn.inningNo,
          "battingTeam": inn.battingTeam.name if inn.battingTeam else None,
          "bowlingTeam": inn.bowlingTeam.name if inn.bowlingTeam else None,
          "runs": inn.runs,
          "wickets": inn.wickets,
          "balls": inn.balls,
          "overs": f"{inn.balls // 6}.{inn.balls % 6}",
          "isDeclared": inn.declared,
          "isFollowOn": inn.followOn,
          "fallOfWickets": inn.fallOfWickets,
          "timeline": list(inn.timeline),
          "batters": batters_out,
          "bowlers": bowlers_out
        })
      current_batters = []
      current_bowlers = []
      current_inning = None
      phase = None
      partnership = None
      timeline = []
      if game.started and game.innings:
        ci = game.currentInning
        timeline = list(ci.timeline)
        partnership = ci.currentPartnership
        for i, p in enumerate(ci.currentBatters):
          b = ci.batters.get(p)
          can_do_0 = (b.consecutiveDots != 3) if b else True
          can_do_boundary = (not game.cantBoundary(b, ci)) if b else True
          boundary_limit = (game.PHASES[game.phase(ci.balls)]["boundaries"] if game.format == "t15" else (2 if (b and b.balls >= 15) else 1))
          current_batters.append({
            "playerId": str(p.id),
            "playerName": p.name,
            "runs": b.runs if b else 0,
            "balls": b.balls if b else 0,
            "fours": b.fours if b else 0,
            "sixes": b.sixes if b else 0,
            "strikeRate": b.sr if b else 0.0,
            "onStrike": i == 0,
            "consecutiveDots": b.consecutiveDots if b else 0,
            "boundaryThisOver": b.BoundaryThisOver if b else 0,
            "canDo0": can_do_0,
            "canDoBoundary": can_do_boundary,
            "boundaryLimit": boundary_limit
          })
        for i, p in enumerate(ci.currentBowlers):
          b = ci.bowlers.get(p)
          bowler_can_do_0 = bool(
            b and (b.isOnHattrick or (ci.balls >= 6 and b.lastOverMaiden and not ci.zeroByBowler))
          )
          current_bowlers.append({
            "playerId": str(p.id),
            "playerName": p.name,
            "overs": f"{b.balls // 6}.{b.balls % 6}" if b else "0.0",
            "maidens": b.maidens if b else 0,
            "runs": b.runsConceded if b else 0,
            "wickets": b.wickets if b else 0,
            "economy": round((b.runsConceded / b.balls) * 6, 2) if (b and b.balls) else 0.0,
            "isBowling": i == 0,
            "isOnHattrick": b.isOnHattrick if b else False,
            "lastOverMaiden": b.lastOverMaiden if b else False,
            "canDo0": bowler_can_do_0
          })
        phase = self.t15_phase(game)
        chase = (game.format == "t15" and ci.inningNo == 2) or (game.format == "test" and ci.inningNo == 4)
        target = None
        runs_needed = None
        balls_remaining = None
        required_rate = None
        if chase:
          bat_total = game.teamTotal(ci.battingTeam)
          bowl_total = game.teamTotal(ci.bowlingTeam)
          bat_prev = bat_total - ci.runs
          target = (bowl_total - bat_prev) + 1
          runs_needed = max(0, target - ci.runs)
          if game.format == "t15":
            balls_remaining = max(0, game.maxBalls - ci.balls)
            required_rate = round((runs_needed / balls_remaining) * 6, 2) if balls_remaining > 0 else None
        current_inning = {
          "inningNo": ci.inningNo,
          "battingTeam": ci.battingTeam.name if ci.battingTeam else None,
          "bowlingTeam": ci.bowlingTeam.name if ci.bowlingTeam else None,
          "runs": ci.runs,
          "wickets": ci.wickets,
          "balls": ci.balls,
          "overs": f"{ci.balls // 6}.{ci.balls % 6}",
          "runRate": round(ci.runs / (ci.balls / 6), 2) if ci.balls else 0.0,
          "target": target,
          "runsNeeded": runs_needed,
          "ballsRemaining": balls_remaining,
          "requiredRate": required_rate,
          "isDeclared": ci.declared,
          "isFollowOn": ci.followOn,
          "phase": phase,
          "partnership": partnership,
          "currentOverRuns": ci.currentOverRuns,
          "lastOverRuns": ci.lastOverRuns,
          "zeroByBowler": ci.zeroByBowler,
          "timeline": list(ci.timeline),
          "fallOfWickets": ci.fallOfWickets
        }
      day, session = game.getDaysAndSessions() if game.started else (1, 1)
      return web.json_response({
        "id": game.gameId,
        "state": state,
        "format": "T15" if game.format == "t15" else "Test",
        "phase": phase,
        "channelName": channel.name if channel else str(game.ctx.channel.id),
        "guildName": guild.name if guild else str(game.ctx.guild.id),
        "teamAName": game.teama.name,
        "teamBName": game.teamb.name,
        "maxBalls": game.maxBalls,
        "matchTotalBalls": game.matchTotalBalls,
        "followOnLimit": game.followOnLimit,
        "repLimit": game.repLimit,
        "day": day,
        "session": session,
        "tossStatus": game.tossStatus,
        "statusText": game.matchStatus() if game.started and game.innings else "Waiting in Lobby",
        "innings": innings_out,
        "currentInning": current_inning,
        "currentBatters": current_batters,
        "currentBowlers": current_bowlers,
        "partnership": partnership,
        "timeline": timeline,
        "commentary": list(game.currentInning.commentary) if (game.innings and game.currentInning.commentary) else []
      }, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())
  async def get_leaderboard(self, request):
    try:
      category = request.query.get('category', 'most_runs')
      limit = min(25, max(1, int(request.query.get('limit', 10))))
      CATEGORIES = {
        'most_runs': {'title': 'Most Runs', 'note': None, 'sql': "SELECT batterId,SUM(runs) AS runs,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries GROUP BY batterId ORDER BY runs DESC LIMIT ?", 'cols': ['player','runs','balls'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'runs': r[1], 'balls': r[2]}},
        'most_wickets': {'title': 'Most Wickets', 'note': None, 'sql': "SELECT bowlerId,SUM(isWicket) AS wkts,COUNT(*) AS balls FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY bowlerId ORDER BY wkts DESC LIMIT ?", 'cols': ['player','wickets','balls'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'wickets': r[1], 'balls': r[2]}},
        'lowest_deviation_as_a_bowler': {'title': 'Lowest Deviation As a Bowler', 'note': "Deviation = Difference between batter number and bowler number; Minimum 100 balls", 'sql': "SELECT bowlerId, AVG(ABS(batterNum - bowlerNum)) AS avg_absolute_deviation FROM deliveries WHERE bowlerNum IS NOT NULL AND batterNum IS NOT NULL GROUP BY bowlerId HAVING  SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) >= 100 ORDER BY avg_absolute_deviation LIMIT ?", 'cols': ['Bowler','Deviation'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'Deviation': round(r[1],2)}},
        'most_matches': {'title': 'Most Matches', 'note': None, 'sql': "SELECT playerId,COUNT(*) AS matches FROM (SELECT DISTINCT batterId AS playerId,matchId FROM deliveries WHERE batterId IS NOT NULL UNION SELECT DISTINCT bowlerId AS playerId,matchId FROM deliveries WHERE bowlerId IS NOT NULL) t GROUP BY playerId ORDER BY matches DESC LIMIT ?", 'cols': ['player','matches'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'matches': r[1]}},
        'most_mvps': {'title': 'Most MVPs', 'note': None, 'sql': "SELECT mvpId,COUNT(*) AS mvps FROM matches WHERE mvpId IS NOT NULL GROUP BY mvpId ORDER BY mvps DESC LIMIT ?", 'cols': ['player','mvps'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'mvps': r[1]}},
        'most_30s': {'title': 'Most 30s', 'note': None, 'sql': "SELECT b,SUM(CASE WHEN r>=30 THEN 1 ELSE 0 END) AS thirties FROM (SELECT batterId AS b,inningId,SUM(runs) AS r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId,inningId) t GROUP BY b ORDER BY thirties DESC LIMIT ?", 'cols': ['player','30s'], 'resolve': [0], 'format': lambda r: {'player': r[0], '30s': r[1]}},
        'most_50s': {'title': 'Most 50s', 'note': None, 'sql': "SELECT b,SUM(CASE WHEN r>=50 THEN 1 ELSE 0 END) AS fifties FROM (SELECT batterId AS b,inningId,SUM(runs) AS r FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId,inningId) t GROUP BY b ORDER BY fifties DESC LIMIT ?", 'cols': ['player','50s'], 'resolve': [0], 'format': lambda r: {'player': r[0], '50s': r[1]}},
        'most_4s': {'title': 'Most 4s', 'note': None, 'sql': "SELECT batterId,SUM(CASE WHEN batterNum=4 THEN 1 ELSE 0 END) AS fours FROM deliveries WHERE isWicket!=1 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId ORDER BY fours DESC LIMIT ?", 'cols': ['player','4s'], 'resolve': [0], 'format': lambda r: {'player': r[0], '4s': r[1]}},
        'most_6s': {'title': 'Most 6s', 'note': None, 'sql': "SELECT batterId,SUM(CASE WHEN batterNum=6 THEN 1 ELSE 0 END) AS sixes FROM deliveries WHERE isWicket!=1 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId ORDER BY sixes DESC LIMIT ?", 'cols': ['player','6s'], 'resolve': [0], 'format': lambda r: {'player': r[0], '6s': r[1]}},
        'most_3fers': {'title': 'Most 3-fers', 'note': None, 'sql': "SELECT bowlerId,COUNT(*) AS threefers FROM (SELECT inningId,bowlerId,SUM(isWicket) AS wkts FROM deliveries WHERE bowlerId IS NOT NULL GROUP BY inningId,bowlerId HAVING wkts>=3) t GROUP BY bowlerId ORDER BY threefers DESC LIMIT ?", 'cols': ['player','3fers'], 'resolve': [0], 'format': lambda r: {'player': r[0], '3fers': r[1]}},
        'most_5fers': {'title': 'Most 5-fers', 'note': None, 'sql': "SELECT bowlerId,COUNT(*) AS fivefers FROM (SELECT inningId,bowlerId,SUM(isWicket) AS wkts FROM deliveries WHERE bowlerId IS NOT NULL GROUP BY inningId,bowlerId HAVING wkts>=5) t GROUP BY bowlerId ORDER BY fivefers DESC LIMIT ?", 'cols': ['player','5fers'], 'resolve': [0], 'format': lambda r: {'player': r[0], '5fers': r[1]}},
        'most_hattricks': {'title': 'Most Hattricks', 'note': None, 'sql': "SELECT bowlerId,COUNT(*) AS hattricks FROM (SELECT bowlerId,CASE WHEN isWicket=1 AND (LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp)=0 OR LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp) IS NULL) AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_hattrick FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL) t WHERE is_hattrick=1 GROUP BY bowlerId ORDER BY hattricks DESC LIMIT ?", 'cols': ['player','hattricks'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'hattricks': r[1]}},
        'highest_bat_avg': {'title': 'Highest Batting AVG', 'note': 'Min. 10 innings', 'sql': "SELECT batterId,CASE WHEN SUM(isWicket)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/SUM(isWicket) END AS avg,COUNT(DISTINCT inningId) AS inns FROM deliveries GROUP BY batterId HAVING inns>=10 ORDER BY avg DESC LIMIT ?", 'cols': ['player','avg','innings'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'avg': round(r[1],2), 'innings': r[2]}},
        'highest_bat_sr': {'title': 'Highest Batting SR', 'note': 'Min. 100 balls', 'sql': "SELECT batterId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 100.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN runs ELSE 0 END)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS sr FROM deliveries GROUP BY batterId HAVING SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)>=100 ORDER BY sr DESC LIMIT ?", 'cols': ['player','sr'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'sr': round(r[1],2)}},
        'best_bowl_avg': {'title': 'Best Bowling AVG', 'note': 'Min. 10 innings', 'sql': "SELECT bowlerId,CASE WHEN SUM(isWicket)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/SUM(isWicket) END AS avg,SUM(isWicket) AS wkts FROM deliveries GROUP BY bowlerId HAVING COUNT(DISTINCT inningId)>=10 ORDER BY avg ASC LIMIT ?", 'cols': ['player','avg','wickets'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'avg': round(r[1],2), 'wickets': r[2]}},
        'best_bowl_eco': {'title': 'Best Bowling ECO', 'note': 'Min. 10 innings', 'sql': "SELECT bowlerId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 6.0*SUM(runs)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS eco,COUNT(DISTINCT inningId) AS inns FROM deliveries GROUP BY bowlerId HAVING inns>=10 ORDER BY eco ASC LIMIT ?", 'cols': ['player','eco','innings'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'eco': round(r[1],2), 'innings': r[2]}},
        'best_bowl_sr': {'title': 'Best Bowling SR', 'note': 'Min. 10 innings', 'sql': "SELECT bowlerId,CASE WHEN SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 1.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)/SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END) END AS sr,COUNT(DISTINCT inningId) AS inns FROM deliveries GROUP BY bowlerId HAVING inns>=10 AND SUM(CASE WHEN isWicket=1 THEN 1 ELSE 0 END)>0 ORDER BY sr ASC LIMIT ?", 'cols': ['player','sr','innings'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'sr': round(r[1],2), 'innings': r[2]}},
        'fastest_50s': {'title': 'Fastest 50s', 'note': None, 'sql': "SELECT batterId,MIN(balls) AS balls_to_50 FROM (SELECT batterId,inningId,SUM(runs) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS cr,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS balls FROM deliveries WHERE batterId IS NOT NULL) t WHERE cr>=50 GROUP BY batterId,inningId ORDER BY balls_to_50 ASC LIMIT ?", 'cols': ['player','balls'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'balls': r[1]}},
        'fastest_30s': {'title': 'Fastest 30s', 'note': None, 'sql': "SELECT batterId,MIN(balls) AS balls_to_30 FROM (SELECT batterId,inningId,SUM(runs) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS cr,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) OVER(PARTITION BY inningId,batterId ORDER BY timestamp) AS balls FROM deliveries WHERE batterId IS NOT NULL) t WHERE cr>=30 GROUP BY batterId,inningId ORDER BY balls_to_30 ASC LIMIT ?", 'cols': ['player','balls'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'balls': r[1]}},
        'best_bat_inning': {'title': 'Best Batting Inning', 'note': None, 'sql': "SELECT batterId,SUM(runs) AS r,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS b,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END AS notout FROM deliveries GROUP BY batterId,inningId ORDER BY r DESC,b ASC LIMIT ?", 'cols': ['player','score'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'score': f"{r[1]}({'*' if r[3] else ''}{r[2]})"}},
        'best_bowl_inning': {'title': 'Best Bowling Inning', 'note': None, 'sql': "SELECT bowlerId,SUM(isWicket) AS w,SUM(runs) AS r,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS b FROM deliveries WHERE bowlerId IS NOT NULL GROUP BY bowlerId,inningId ORDER BY w DESC,r ASC,b ASC LIMIT ?", 'cols': ['player','figures'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'figures': f"{r[1]}/{r[2]} ({r[3]//6}.{r[3]%6})"}},
        'best_partnerships_inning': {'title': 'Best Partnerships (Inning)', 'note': None, 'sql': "SELECT CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END AS p1,CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END AS p2,SUM(runs) AS runs,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE nonStrikerId IS NOT NULL GROUP BY inningId,p1,p2 ORDER BY runs DESC LIMIT ?", 'cols': ['batters','runs','balls'], 'resolve': [0,1], 'format': lambda r: {'player': r[0], 'player2': r[1], 'runs': r[2], 'balls': r[3]}},
        'best_partnerships_overall': {'title': 'Best Partnerships (Overall)', 'note': None, 'sql': "SELECT CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END AS p1,CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END AS p2,SUM(runs) AS runs,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE nonStrikerId IS NOT NULL GROUP BY p1,p2 ORDER BY runs DESC LIMIT ?", 'cols': ['batters','runs','balls'], 'resolve': [0,1], 'format': lambda r: {'player': r[0], 'player2': r[1], 'runs': r[2], 'balls': r[3]}},
        'highest_match_aggregate': {'title': 'Highest Match Aggregates', 'note': None, 'sql': "SELECT matchId,SUM(runs) AS total FROM innings GROUP BY matchId ORDER BY total DESC LIMIT ?", 'cols': ['match','runs'], 'resolve': [], 'format': lambda r: {'matchId': r[0], 'runs': r[1]}},
        'highest_sr_inning': {'title': 'Highest SR in an Inning', 'note': 'Min. 10 balls', 'sql': "SELECT batterId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 100.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN runs ELSE 0 END)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS sr,SUM(runs) AS r,SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS b FROM deliveries GROUP BY batterId,inningId HAVING b>=10 ORDER BY sr DESC LIMIT ?", 'cols': ['player','sr','inning'], 'resolve': [0], 'format': lambda r: {'player': r[0], 'sr': round(r[1],2), 'inning': f"{r[2]} ({r[3]})"}},
      }
      if category not in CATEGORIES:
        return web.json_response({"error": f"Unknown category. Valid: {list(CATEGORIES.keys())}"}, status=400, headers=self.get_cors_headers())
      cfg = CATEGORIES[category]
      rows = await self.bot.fetchall(cfg['sql'], [limit])
      data = []
      for rank, row in enumerate(rows, 1):
        entry = cfg['format'](row)
        entry['rank'] = rank
        for idx in cfg['resolve']:
          uid = row[idx]
          if uid:
            u = await self.fetch_user_data(int(uid))
            key = 'player' if idx == 0 else 'player2'
            entry[key] = u['name']
            entry[key + 'Avatar'] = u['avatar']
        data.append(entry)
      return web.json_response({'category': category, 'title': cfg['title'], 'note': cfg['note'], 'cols': cfg['cols'], 'data': data}, headers=self.get_cors_headers())
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
    pkt = timezone(timedelta(hours=5))
    now = datetime.now(pkt)
    days_since_wed = (now.weekday() - 2) % 7
    cutoff_end = (now - timedelta(days=days_since_wed)).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_end_utc = cutoff_end.astimezone(timezone.utc)
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
      sql = f"SELECT batterId AS playerId, SUM((runs-CASE WHEN isWicket=1 THEN 5 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END) AS rating FROM deliveries WHERE {TEST_ONLY} AND batterId IS NOT NULL AND timestamp >= {min_ts} AND timestamp < {cutoff_end_ts} GROUP BY batterId HAVING rating>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
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
      sql = f"SELECT bowlerId AS playerId, SUM(((CASE WHEN isWicket=1 THEN 25 ELSE 0 END)-runs/5.0)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END) AS rating FROM deliveries WHERE {TEST_ONLY} AND bowlerId IS NOT NULL AND timestamp >= {min_ts} AND timestamp < {cutoff_end_ts} GROUP BY bowlerId HAVING rating>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
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
      sql = f"SELECT playerId,SQRT(SUM(bat)*SUM(bowl)) AS rating FROM (SELECT batterId AS playerId,(runs-CASE WHEN isWicket=1 THEN 5 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END AS bat,0 AS bowl FROM deliveries WHERE {TEST_ONLY} AND batterId IS NOT NULL AND timestamp >= {min_ts} AND timestamp < {cutoff_end_ts} UNION ALL SELECT bowlerId AS playerId,0 AS bat,((CASE WHEN isWicket=1 THEN 25 ELSE 0 END)-runs/5.0)*CASE WHEN timestamp>={cutoff_end_ts-604800} THEN 1 WHEN timestamp>={cutoff_end_ts-1209600} THEN 0.8 WHEN timestamp>={cutoff_end_ts-1814400} THEN 0.6 ELSE 0.4 END AS bowl FROM deliveries WHERE {TEST_ONLY} AND bowlerId IS NOT NULL AND timestamp >= {min_ts} AND timestamp < {cutoff_end_ts}) GROUP BY playerId HAVING SUM(bat)>0 AND SUM(bowl)>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
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
    sql = "SELECT m.matchId, m.channelId, m.guildId, m.teamAName, m.teamBName, m.winner, m.matchMaximumBalls, m.drawByAgreement, m.format, MAX(d.timestamp) AS lastTimestamp FROM matches m JOIN deliveries d ON d.matchId = m.matchId"
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
      matchId, channelId, guildId, teamAName, teamBName, winner, matchMaximumBalls, drawByAgreement, matchFormat, timestamp = row
      channel = self.bot.get_channel(channelId)
      channelName = channel.name if channel else str(channelId)
      guild = self.bot.get_guild(guildId)
      guildName = guild.name if guild else str(guildId)
      inn_rows = await self.bot.fetchall(
        "SELECT inningNo, battingTeam, runs, wickets, balls, isDeclared, isFollowOn FROM innings WHERE matchId=? ORDER BY inningNo",
        [matchId]
      )
      innings_summary = [
        {
          "inningNo": r[0],
          "battingTeam": r[1],
          "runs": r[2],
          "wickets": r[3],
          "balls": r[4],
          "overs": f"{(r[4] or 0)//6}.{(r[4] or 0)%6}",
          "isDeclared": bool(r[5]),
          "isFollowOn": bool(r[6])
        }
        for r in inn_rows
      ]
      data['Matches'].append({
        'id': matchId,
        'channelName': channelName,
        'guildName': guildName,
        'teamAName': teamAName,
        'teamBName': teamBName,
        'winner': winner,
        'maxBalls': matchMaximumBalls or 180,
        'drawByAgreement': bool(drawByAgreement),
        'format': matchFormat or 'test',
        'innings': innings_summary,
        'timestamp': timestamp
      })
    return web.json_response(data, headers=self.get_cors_headers())
async def setup(bot):
  await bot.add_cog(RankingCog(bot))
