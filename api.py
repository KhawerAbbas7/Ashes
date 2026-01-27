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
    app.add_routes([web.get('/rankings/batting', self.get_batting),web.get('/rankings/bowling', self.get_bowling),web.get('/rankings/allrounder', self.get_allrounder),web.get('/', self.health_check)])
    self.runner = web.AppRunner(app)
    await self.runner.setup()
    self.site = web.TCPSite(self.runner, '0.0.0.0', 20375)
    await self.site.start()
    print("Rankings API running on http://0.0.0.0:20375")

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
    now = datetime.utcnow() + timedelta(hours=5)  # PKT
    days_since_wed = (now.weekday() - 2) % 7
    cutoff_end = (now - timedelta(days=days_since_wed)).replace(hour=0, minute=0, second=0, microsecond=0)
    cutoff_end_utc = cutoff_end -timedelta(hours=5)
    return int(cutoff_end.timestamp()), int(cutoff_end_utc.timestamp())

  async def health_check(self, request):
    return web.json_response({"status": "online"}, headers=self.get_cors_headers())

  async def get_batting(self, request):
    try:
      page = int(request.query.get('page', 1))
      limit = int(request.query.get('limit', 10))
      limit = min(50, max(1, limit))
      offset = (page - 1) * limit
      cutoff_end_ts, cutoff_end_utc = self.get_cutoff_end()
      sql = f"SELECT batterId AS playerId, SUM((runs-CASE WHEN isWicket=1 THEN 10 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-7*86400} THEN 1 WHEN timestamp>={cutoff_end_ts-14*86400} THEN 0.8 WHEN timestamp>={cutoff_end_ts-21*86400} THEN 0.6 WHEN timestamp>={cutoff_end_ts-28*86400} THEN 0.4 ELSE 0 END) AS rating FROM deliveries WHERE batterId IS NOT NULL AND timestamp < {cutoff_end_ts} GROUP BY batterId HAVING rating>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
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
      limit = int(request.query.get('limit', 10))
      limit = min(50, max(1, limit))
      offset = (page - 1) * limit
      cutoff_end_ts,cutoff_end_utc = self.get_cutoff_end()
      sql = f"SELECT bowlerId AS playerId, SUM((CASE WHEN isWicket=1 THEN 25 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-7*86400} THEN 1 WHEN timestamp>={cutoff_end_ts-14*86400} THEN 0.8 WHEN timestamp>={cutoff_end_ts-21*86400} THEN 0.6 WHEN timestamp>={cutoff_end_ts-28*86400} THEN 0.4 ELSE 0 END) AS rating FROM deliveries WHERE bowlerId IS NOT NULL AND timestamp < {cutoff_end_ts} GROUP BY bowlerId HAVING rating>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
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
      limit = int(request.query.get('limit', 10))
      limit = min(50, max(1, limit))
      offset = (page - 1) * limit
      cutoff_end_ts, cutoff_end_utc = self.get_cutoff_end()
      sql = f"SELECT playerId, SQRT(battingScore*bowlingScore) AS rating FROM (SELECT playerId, SUM(bat)*1.0 AS battingScore, SUM(bowl)*1.0 AS bowlingScore FROM (SELECT batterId AS playerId, (runs-CASE WHEN isWicket=1 THEN 10 ELSE 0 END)*CASE WHEN timestamp>={cutoff_end_ts-7*86400} THEN 1 WHEN timestamp>={cutoff_end_ts-14*86400} THEN 0.8 WHEN timestamp>={cutoff_end_ts-21*86400} THEN 0.6 WHEN timestamp>={cutoff_end_ts-28*86400} THEN 0.4 ELSE 0 END AS bat, 0 AS bowl FROM deliveries WHERE batterId IS NOT NULL AND timestamp < {cutoff_end_ts} UNION ALL SELECT bowlerId AS playerId, 0 AS bat, (CASE WHEN isWicket=1 THEN 25 ELSE 0 END+0.2)*CASE WHEN timestamp>={cutoff_end_ts-7*86400} THEN 1 WHEN timestamp>={cutoff_end_ts-14*86400} THEN 0.8 WHEN timestamp>={cutoff_end_ts-21*86400} THEN 0.6 WHEN timestamp>={cutoff_end_ts-28*86400} THEN 0.4 ELSE 0 END AS bowl FROM deliveries WHERE bowlerId IS NOT NULL AND timestamp < {cutoff_end_ts}) GROUP BY playerId) WHERE battingScore>0 AND bowlingScore>0 ORDER BY rating DESC LIMIT {limit} OFFSET {offset}"
      rows = await self.bot.fetchall(sql)
      data = []
      for row in rows:
        u = await self.fetch_user_data(row[0])
        data.append({"playerId": str(row[0]), "playerName": u['name'], "profileImageUrl": u['avatar'], "rating": round(row[1] or 0, 2)})
      return web.json_response({"data": data, "page": page, "limit": limit, "cutoff": cutoff_end_utc}, headers=self.get_cors_headers())
    except Exception as e:
      return web.json_response({"error": str(e)}, status=500, headers=self.get_cors_headers())

async def setup(bot):
  await bot.add_cog(RankingCog(bot))