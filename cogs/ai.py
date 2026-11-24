import os, re, asyncio, aiosqlite, discord
from cachetools import LRUCache
from discord.ext import commands
from openai import AsyncOpenAI

MODEL = os.getenv("ASK_MODEL", "nvidia/nemotron-3.5-lightning:free")
SQL_PROMPT = "Write one read-only SQLite SELECT query for this cricket match database.\nSchema:\n{schema}\nNotes: player ids are Discord user ids, and players in the question appear as <@id>, so use the number. deliveries.runs is runs per ball, isWicket=1 is a wicket, only count balls where batterNum IS NOT NULL AND bowlerNum IS NOT NULL. matches.format defaults to 'test'. Use clear column aliases. Name player id columns batterId, bowlerId or mvpId and the match column matchId. Return only the SQL, no explanation. If the question cannot be answered from the schema, return exactly NO.\nExamples:\n{examples}"
EXAMPLES = [
  ("most runs", "SELECT batterId, SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY batterId ORDER BY runs DESC LIMIT 10"),
  ("most ducks", "WITH inning_totals AS (SELECT matchId, inningId, batterId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY matchId, inningId, batterId) SELECT batterId, COUNT(*) AS ducks FROM inning_totals WHERE total_runs=0 AND got_out=1 GROUP BY batterId ORDER BY ducks DESC LIMIT 10"),
  ("which bowler got the same batter out the most", "SELECT bowlerId, batterId, COUNT(*) AS wickets FROM deliveries WHERE isWicket=1 AND matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY bowlerId, batterId ORDER BY wickets DESC LIMIT 10"),
  ("worst bowling figures in an inning", "SELECT bowlerId, SUM(isWicket) AS wickets, SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY inningId, bowlerId ORDER BY runs DESC LIMIT 10"),
  ("who gets out most in the nervous 40s", "SELECT batterId, COUNT(*) AS dismissals FROM (SELECT batterId, inningId, SUM(runs) AS totalRuns, MAX(isWicket) AS out FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY batterId, inningId HAVING out=1 AND totalRuns BETWEEN 40 AND 49) t GROUP BY batterId ORDER BY dismissals DESC LIMIT 10"),
  ("how many runs has <@123> scored", "SELECT SUM(runs) AS runs FROM deliveries WHERE batterId=123 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL")
]
HIDDEN = {"inningid", "ballid"}

def cell(col, v):
  c = col.lower()
  if c == "matchid":return f"[match](<https://ashesdb.vercel.app/match/{v}>)"
  if c.endswith("id") and isinstance(v, int):return f"<@{v}>"
  return str(v)

class AskDB(commands.Cog, name="AskDB"):
  def __init__(self, bot):
    self.bot = bot
    self.ai = AsyncOpenAI(base_url=os.getenv("ASK_BASE_URL", "https://openrouter.ai/api/v1"), api_key=os.getenv("ASK_API_KEY") or os.getenv("OPENROUTER_API_KEY"))
    self.cache = LRUCache(256)
  async def cog_load(self):
    path = os.path.join(os.getcwd(), "databases", "ashes.db")
    self.conn = await aiosqlite.connect(f"file:{path}?mode=ro", uri=True)
    await self.conn.execute("PRAGMA query_only = ON")
    async with self.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") as c:
      schema = "\n".join(r[0] for r in await c.fetchall())
    self.prompt = SQL_PROMPT.format(schema=schema, examples="\n".join(f"Q: {q}\nSQL: {s}" for q, s in EXAMPLES))
  async def cog_unload(self):
    await self.conn.close()
  async def makeSql(self, question):
    key = question.lower()
    if key in self.cache:return self.cache[key]
    r = await self.ai.chat.completions.create(model=MODEL, max_tokens=700, temperature=0, messages=[{"role": "system", "content": self.prompt}, {"role": "user", "content": question}])
    sql = re.sub(r"^```(?:sql)?|```$", "", (r.choices[0].message.content or "").strip(), flags=re.M).strip().rstrip(";")
    if re.match(r"(?is)^(select|with)\b", sql) and ";" not in sql:self.cache[key] = sql
    return sql
  @commands.command(aliases=["ask"], description="Ask a question about match data in plain English.")
  @commands.cooldown(1, 10, commands.BucketType.user)
  @commands.is_owner()
  async def askdb(self, ctx, *, question: str):
    async with ctx.typing():
      try:
        sql = await asyncio.wait_for(self.makeSql(question), 45)
        if not re.match(r"(?is)^(select|with)\b", sql) or ";" in sql:
          return await ctx.send("I couldn't turn that into a valid query.")
        cur = await asyncio.wait_for(self.conn.execute(f"SELECT * FROM ({sql}) LIMIT 25"), 10)
        rows = await cur.fetchall()
      except Exception:
        self.conn.interrupt()
        return await ctx.send("Couldn't answer that right now. Try rephrasing or try again later.")
    if not rows:return await ctx.send("No data found.")
    cols = [d[0] for d in cur.description]
    keep = [i for i, c in enumerate(cols) if c.lower() not in HIDDEN]
    header = " | ".join(cols[i] for i in keep)
    lines = "\n".join(" | ".join(cell(cols[i], r[i]) for i in keep) for r in rows)
    await ctx.send(f"**{header}**\n{lines}"[:1900], allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):await bot.add_cog(AskDB(bot))