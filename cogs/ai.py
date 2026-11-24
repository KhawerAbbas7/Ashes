import os, re, asyncio, aiosqlite, discord
from discord.ext import commands
from openai import AsyncOpenAI

MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
SQL_PROMPT = "Write one read-only SQLite SELECT query for this cricket match database.\nSchema:\n{schema}\nNotes: player ids are Discord user ids. deliveries.runs is runs per ball, isWicket=1 is a wicket, only count balls where batterNum IS NOT NULL AND bowlerNum IS NOT NULL. Return only the SQL, no explanation. If the question cannot be answered from the schema, return exactly NO."
ANSWER_PROMPT = "Answer the question briefly using only the query result. Write player ids as <@id>. If the result is empty, say no data was found."

class AskDB(commands.Cog, name="AskDB"):
  def __init__(self, bot):
    self.bot = bot
    self.ai = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
    self.schema = ""
  async def cog_load(self):
    path = os.path.join(os.getcwd(), "databases", "ashes.db")
    self.conn = await aiosqlite.connect(f"file:{path}?mode=ro", uri=True)
    await self.conn.execute("PRAGMA query_only = ON")
    async with self.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") as c:
      self.schema = "\n".join(r[0] for r in await c.fetchall())
  async def cog_unload(self):
    await self.conn.close()
  async def llm(self, system, user):
    r = await self.ai.chat.completions.create(model=MODEL, max_tokens=4000, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return (r.choices[0].message.content or "").strip()
  @commands.command(aliases=["ask"], description="Ask a question about match data in plain English.")
  @commands.cooldown(1, 20, commands.BucketType.user)
  @commands.is_owner()
  async def askdb(self, ctx, *, question: str):
    async with ctx.typing():
      try:
        sql = re.sub(r"^```(?:sql)?|```$", "", await self.llm(SQL_PROMPT.format(schema=self.schema), question), flags=re.M).strip().rstrip(";")
        if not re.match(r"(?is)^(select|with)\b", sql) or ";" in sql:
          return await ctx.send("I couldn't turn that into a valid query.")
        cur = await asyncio.wait_for(self.conn.execute(f"SELECT * FROM ({sql}) LIMIT 25"), 10)
        rows = await cur.fetchall()
        answer = await self.llm(ANSWER_PROMPT, f"Question: {question}\nColumns: {[d[0] for d in cur.description]}\nRows: {rows}")
      except Exception:
        self.conn.interrupt()
        return await ctx.send("Couldn't answer that right now. Try rephrasing or try again later.")
    await ctx.send(answer[:1900] or "No result.", allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):await bot.add_cog(AskDB(bot))