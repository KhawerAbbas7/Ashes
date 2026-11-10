import io
import aiohttp
from datetime import datetime, timezone
import discord
from discord import Embed, Color,ui
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont
class OwnerOnly(commands.Cog):
  def __init__(self, bot):
    self.bot = bot
  async def cog_check(self, ctx): return await self.bot.is_owner(ctx.author)
  @commands.command(aliases=[], description='.')
  async def rankings(self, ctx):
    rankingsData = {}
    cutoff_ts = None
    async with aiohttp.ClientSession() as session:
      url = "http://0.0.0.0:8000/rankings/batting?limit=1"
      async with session.get(url) as response:
        data = await response.json()
        rankingsData["batting"] = data['data'][0]
        cutoff_ts = data.get('cutoff')
      url = "http://0.0.0.0:8000/rankings/allrounder?limit=1"
      async with session.get(url) as response:
        data = await response.json()
        rankingsData["allrounder"] = data['data'][0]
      url = "http://0.0.0.0:8000/rankings/bowling?limit=1"
      async with session.get(url) as response:
        data = await response.json()
        rankingsData["bowling"] = data['data'][0]
    date_str = datetime.fromtimestamp(cutoff_ts, tz=timezone.utc).strftime("%d %b %Y").upper() if cutoff_ts else "NOW"
    img = Image.open("templates/playersRanking.png").convert("RGBA")
    draw = ImageDraw.Draw(img)
    dateFont = ImageFont.truetype("fonts/CanvaSansBoldByCanva.woff2", 45)
    nameFont = ImageFont.truetype("fonts/CanvaSansBoldByCanva.woff2", 53)
    ratingFont = ImageFont.truetype("fonts/canvaSansRegular.woff2", 40)
    draw.text((975, 150), date_str, font=dateFont, fill="#35605a")
    categories = ["batting", "allrounder", "bowling"]
    positions = [485, 1285, 2085]
    picturePositions = [87.4, 487.4, 887.4]
    async with aiohttp.ClientSession() as session:
      for i, cat in enumerate(categories):
        item = rankingsData[cat]
        name = item['playerName'].upper()[:8]
        rating = str(item['rating'])
        pfp_url = item['profileImageUrl']
        x = positions[i]
        px = int(picturePositions[i])
        async with session.get(pfp_url) as resp:
          if resp.status == 200:
            pfp_bytes = await resp.read()
            pfp = Image.open(io.BytesIO(pfp_bytes)).convert("RGBA")
            pfp = pfp.resize((300, 229), Image.Resampling.LANCZOS)
            img.paste(pfp, (px, 490), pfp)
        draw.text(((x - nameFont.getlength(name)) / 2, 735), name, font=nameFont, fill="#ffffff")
        draw.text(((x - ratingFont.getlength(rating)) / 2, 845), rating, font=ratingFont, fill="#172c3c")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    buffer.seek(0)
    file=discord.File(fp=buffer,filename=f'Rankings ({date_str}).png')
    c =  ui.LayoutView(timeout= 60)
    container = ui.Container(accent_color=discord.Colour.from_str("#15a74a"))
    gallery = discord.ui.MediaGallery(discord.MediaGalleryItem(file, spoiler = False))
    container.add_item(ui.TextDisplay(f"**RANKINGS ARE HERE FOR {date_str}**\n-# For Full Rankings Visit (Website)[https://ashesdb.vercel.app/rankings]\n**Batting #1: <@{rankingsData['batting']['playerId']}>**\n**All-Rounder #1: <@{rankingsData['allrounder']['playerId']}>**\n**Bowling #1: <@{rankingsData['bowling']['playerId']}>**"))
    container.add_item(gallery)
    c.add_item(container)
    await ctx.send(file=file, view = c)
async def setup(bot): await bot.add_cog(OwnerOnly(bot))
