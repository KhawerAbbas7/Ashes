import os, re, asyncio, aiosqlite, discord
from cachetools import LRUCache
from discord.ext import commands
from openai import AsyncOpenAI

MODEL = os.getenv("ASK_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
SQL_PROMPT = "Write one read-only SQLite SELECT query for this cricket match database.\nSchema:\n{schema}\nNotes: player ids are Discord user ids. deliveries.runs is runs per ball, isWicket=1 is a wicket, only count balls where batterNum IS NOT NULL AND bowlerNum IS NOT NULL. Use clear column aliases. Name every player id column so it ends with Id (batterId, bowlerId, mvpId) and any match id column matchId. Return only the SQL, no explanation. If the question cannot be answered from the schema, return exactly NO."
HIDDEN = {"inningid", "ballid"}

def cell(col, v):
  c = col.lower()
  if c == "matchid":return f"[match](<https://ashesdb.vercel.app/match/{v}>)"
  if c.endswith("id") and isinstance(v, int):return f"<@{v}>"
  return str(v)

class AskDB(commands.Cog, name="AskDB"):
  def __init__(self, bot):
    self.bot = bot
    self.ai = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    self.cache = LRUCache(256)
  async def cog_load(self):
    path = os.path.join(os.getcwd(), "databases", "ashes.db")
    self.conn = await aiosqlite.connect(f"file:{path}?mode=ro", uri=True)
    await self.conn.execute("PRAGMA query_only = ON")
    async with self.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") as c:
      self.prompt = SQL_PROMPT.format(schema="\n".join(r[0] for r in await c.fetchall()))
  async def cog_unload(self):
    await self.conn.close()
  async def makeSql(self, question):
    key = question.lower()
    if key in self.cache:return self.cache[key]
    r = await self.ai.chat.completions.create(model=MODEL, max_tokens=600, temperature=0, extra_body={"reasoning": {"effort": "low"}}, messages=[{"role": "system", "content": self.prompt}, {"role": "user", "content": question}])
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