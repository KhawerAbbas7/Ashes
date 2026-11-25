import os, re, asyncio, inspect, aiosqlite, discord, time
from discord.ext import commands
from openai import AsyncOpenAI
from google import genai
from google.genai import types, errors

GEMINI_MODEL = "gemini-3.1-flash-lite"
OPENROUTER_MODEL = "nvidia/nemotron-3-ultra-550b-a55b:free"
SQL_PROMPT = "Write one read-only SQLite SELECT query for this cricket match database.\nSchema:\n{schema}\nNotes: player ids are Discord user ids, and players in the question appear as <@id>, so use the number. deliveries.runs is runs per ball, isWicket=1 is a wicket, only count balls where batterNum IS NOT NULL AND bowlerNum IS NOT NULL. format is either test or t15, if user doesn't mention a specific format, use test. Name player id columns so they end with Id and the match column matchId. Return only the SQL, no explanation. If the question cannot be answered from the schema, return exactly NO.\nExamples:\n{examples}\notes: A hattrick is a bowler taking wickets on 3 consecutive balls. A WoW moment is a wicket, then a dot ball, then another wicket. Balls to 50 means the number of balls a batter faced when their running total first reached 50."
ANSWER_PROMPT = "Answer the question briefly using only the query result. Write player ids as <@id>, do not include inning id, ball id. If the answer has match id write it like [match](<https://ashesdb.vercel.app/match/matchId>). If the result is empty, say no data was found."
EXAMPLES = [
  ("most runs", "SELECT batterId, SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY batterId ORDER BY runs DESC LIMIT 10"),
  ("top 5 run scorers in t15", "SELECT batterId, SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE matchId IN (SELECT matchId FROM matches WHERE format='t15') GROUP BY batterId ORDER BY runs DESC LIMIT 5"),
  ("most wickets", "SELECT bowlerId, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN isWicket ELSE 0 END) AS wkts, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY bowlerId ORDER BY wkts DESC LIMIT 10"),
  ("who has the most mvps in t15", "SELECT mvpId, COUNT(*) AS mvps FROM matches WHERE mvpId IS NOT NULL AND format='t15' GROUP BY mvpId ORDER BY mvps DESC LIMIT 1"),
  ("most ducks", "WITH inning_totals AS (SELECT matchId, inningId, batterId, SUM(runs) AS total_runs, MAX(isWicket) AS got_out FROM deliveries WHERE batterId IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY matchId, inningId, batterId) SELECT batterId, COUNT(*) AS ducks FROM inning_totals WHERE total_runs=0 AND got_out=1 GROUP BY batterId ORDER BY ducks DESC LIMIT 10"),
  ("nervous 40s", "SELECT batterId, COUNT(*) AS nervousDismissals FROM (SELECT batterId, inningId, SUM(runs) AS totalRuns, MAX(isWicket) AS out FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY batterId, inningId HAVING out=1 AND totalRuns BETWEEN 40 AND 49) t GROUP BY batterId ORDER BY nervousDismissals DESC LIMIT 10"),
  ("best bowling innings", "SELECT bowlerId, w AS wickets, r AS runs, b AS balls FROM (SELECT bowlerId, SUM(isWicket) w, SUM(runs) r, COUNT(*) b FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY bowlerId, inningId ORDER BY w DESC, r ASC, b ASC LIMIT 10)"),
  ("highest match aggregates", "SELECT m.matchId, m.teamAName, m.teamBName, SUM(i.runs) AS totalRuns FROM matches m JOIN innings i ON m.matchId=i.matchId WHERE m.format='test' GROUP BY m.matchId ORDER BY totalRuns DESC LIMIT 10"),
  ("best partnerships in an inning", "SELECT inningId, CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END AS batter1Id, CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END AS batter2Id, SUM(runs) partnershipRuns, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) balls FROM deliveries WHERE nonStrikerId IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY inningId, CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END, CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END ORDER BY partnershipRuns DESC LIMIT 10"),
  ("how many runs has <@123> scored", "SELECT SUM(runs) AS runs FROM deliveries WHERE batterId=123 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test')"),
  ("what are <@123> best bowling figures", "SELECT SUM(isWicket) AS wickets, SUM(runs) AS runs FROM deliveries WHERE bowlerId=123 AND batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test') GROUP BY inningId ORDER BY wickets DESC, runs ASC LIMIT 1"),
  ("quickest 50s", "SELECT batterId, MIN(balls) AS balls_to_50, inningId FROM (SELECT batterId, inningId, ballId, SUM(runs) OVER(PARTITION BY inningId, batterId ORDER BY timestamp) AS cr, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) OVER(PARTITION BY inningId, batterId ORDER BY timestamp) AS balls FROM deliveries WHERE batterId IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test')) t WHERE cr>=50 GROUP BY batterId, inningId ORDER BY balls_to_50 ASC LIMIT 10"),
  ("most hattricks", "SELECT bowlerId, COUNT(*) AS hattricks FROM (SELECT bowlerId, matchId, inningId, InningBalls, isWicket, CASE WHEN isWicket=1 AND (LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp)=0 OR LAG(isWicket) OVER(PARTITION BY bowlerId ORDER BY timestamp) IS NULL) AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_hattrick FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='test')) t WHERE is_hattrick=1 GROUP BY bowlerId ORDER BY hattricks DESC LIMIT 10"),
  ("most wow moments in t15", "SELECT bowlerId, COUNT(*) AS wows FROM (SELECT bowlerId, CASE WHEN isWicket=1 AND LEAD(runs,1) OVER(PARTITION BY bowlerId, inningId ORDER BY timestamp)=0 AND LEAD(isWicket,1) OVER(PARTITION BY bowlerId, inningId ORDER BY timestamp)=0 AND LEAD(isWicket,2) OVER(PARTITION BY bowlerId, inningId ORDER BY timestamp)=1 THEN 1 ELSE 0 END AS is_wow FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL AND matchId IN (SELECT matchId FROM matches WHERE format='t15')) t WHERE is_wow=1 GROUP BY bowlerId ORDER BY wows DESC LIMIT 10")
]

class AskDB(commands.Cog, name="AskDB"):
  def __init__(self, bot):
    self.bot = bot
    self.cooldownMap = {}
    self.tasks= {}
    self.gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    self.ai = AsyncOpenAI(base_url="https://openrouter.ai/api/v1", api_key=os.getenv("OPENROUTER_API_KEY"))
  async def cog_load(self):
    path = os.path.join(os.getcwd(), "databases", "ashes.db")
    self.conn = await aiosqlite.connect(f"file:{path}?mode=ro", uri=True)
    await self.conn.execute("PRAGMA query_only = ON")
    async with self.conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'") as c:
      schema = "\n".join(r[0] for r in await c.fetchall())
    self.prompt = SQL_PROMPT.format(schema=schema, examples="\n".join(f"Q: {q}\nSQL: {s}" for q, s in EXAMPLES))
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
  @commands.Cog.listener('on_message')
  async def AIHandler(self, message):
    if message.channel and message.channel.id == 1575090043054329867 and message.author and not message.author.bot:
      if message.author.id in self.cooldownMap and time.time() - self.cooldownMap[message.author.id] < 30:
        cd = 30 - (time.time() - self.cooldownMap[message.author.id)
        return await message.reply(f"You are on cooldown. Please try again in {int(cd)}s")
      if len(self.tasks) >= 3: return await message.reply("Please wait for other questions to be processed.")
      if len(message.content) <= 10: return await message.reply("Your question has to more richer than that.")  
      try:
        self.tasks[message.id] = message.content
        sql = re.sub(r"^```(?:sql)?|```$", "", await self.llm(self.prompt, message.content), flags=re.M).strip().rstrip(";")
        if not re.match(r"(?is)^(select|with)\b", sql) or ";" in sql:return await message.reply("I couldn't turn that into a valid query.")
        cur = await asyncio.wait_for(self.conn.execute(f"SELECT * FROM ({sql}) LIMIT 25"), 10)
        answer = await self.llm(ANSWER_PROMPT, f"Question: {question}\nColumns: {[d[0] for d in cur.description]}\nRows: {rows}")
        await message.reply(answer[:1900] or "No result.", allowed_mentions=discord.AllowedMentions.none())
        self.tasks.pop(message.id)
      except:
        self.tasks.pop(message.id)
        await message.reply("I am sorry I couldn't answer that.")
  @commands.command(aliases=["ask"], description="Ask a question about match data in plain English.")
  @commands.cooldown(1, 20, commands.BucketType.user)
  async def askdb(self, ctx, *, question: str):
    async with ctx.typing():
      try:
        sql = re.sub(r"^```(?:sql)?|```$", "", await self.llm(self.prompt, question), flags=re.M).strip().rstrip(";")
        if not re.match(r"(?is)^(select|with)\b", sql) or ";" in sql:
          return await ctx.send("I couldn't turn that into a valid query.")
        await ctx.send(sql)
        cur = await asyncio.wait_for(self.conn.execute(f"SELECT * FROM ({sql}) LIMIT 25"), 10)
        rows = await cur.fetchall()
        answer = await self.llm(ANSWER_PROMPT, f"Question: {question}\nColumns: {[d[0] for d in cur.description]}\nRows: {rows}")
      except Exception as e:
        stop = self.conn.interrupt()
        if inspect.isawaitable(stop):await stop
        return await ctx.send(f" {e}, Couldn't answer that right now. Try rephrasing or try again later.")
    await ctx.send(answer[:1900] or "No result.", allowed_mentions=discord.AllowedMentions.none())

async def setup(bot):await bot.add_cog(AskDB(bot))