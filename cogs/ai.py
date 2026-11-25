import os, re, asyncio, aiosqlite, discord
from discord.ext import commands
from openai import AsyncOpenAI
from google import genai
from google.genai import types, errors

GEMINI_MODEL = "gemini-2.5-flash"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
SQL_PROMPT = "Write one read-only SQLite SELECT query for this cricket match database.\nSchema:\n{schema}\nNotes: player ids are Discord user ids. deliveries.runs is runs per ball, isWicket=1 is a wicket, only count balls where batterNum IS NOT NULL AND bowlerNum IS NOT NULL. format is either test or t15, if user doesn't mention a specific format, use test. Return only the SQL, no explanation. If the question cannot be answered from the schema, return exactly NO."
ANSWER_PROMPT = "Answer the question briefly using only the query result. Write player ids as <@id>, do not include inning id, ball id.If the answer has match id write it like [match](<https://ashesdb.vercel.app/match/matchId>) If the result is empty, say no data was found."
class AskDB(commands.Cog, name="AskDB"):
  def __init__(self, bot):
    self.bot = bot
    self.gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
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
    try:
      r = await self.gemini.aio.models.generate_content(
        model=GEMINI_MODEL,
        contents=user,
        config=types.GenerateContentConfig(system_instruction=system, max_output_tokens=4000)
      )
      if r.text:
        return r.text.strip()
    except errors.APIError as e:
      if e.code not in (429, 503):
        raise
    r = await self.ai.chat.completions.create(model=OPENROUTER_MODEL, max_tokens=4000, messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return (r.choices[0].message.content or "").strip()
  @commands.command(aliases=["ask"], description="Ask a question about match data in plain English.")
  @commands.cooldown(1, 20, commands.BucketType.user)
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
