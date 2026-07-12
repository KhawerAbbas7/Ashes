import discord, io, time
from discord import Embed, Colour
from discord import ui 
from discord.ext import commands, tasks
from cogs.views import *
import random 
from datetime import datetime, timezone, timedelta
from discord.ext.commands.cooldowns import BucketType
class K_Converter(commands.Converter):
  async def convert(self, ctx, argument):
    argument = argument.lower()
    if argument.endswith('k'):
      argument = argument.rstrip('k')
      if argument.isdigit():
        if int(argument) < 1: 
          raise commands.BadArgument('Invalid Amount, Minimum amount should be 1')
        else: return int(argument)*1000
      else:
        raise commands.BadArgument('Invalid Amount')
    else:
      if argument.isdigit():
        if int(argument) < 1: raise commands.BadArgument('Invalid Amount, Minimum amount should be 1')
        else: return int(argument)
      else:
        raise commands.BadArgument('Invalid Amount')
class Currency(commands.Cog, name= "Currency"):
  def __init__(self, bot):
    self.bot = bot
  @commands.command(aliases= ['market'], description= 'View shop')
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def shop(self, ctx):
    bal = await ctx.bot.cfetchrow("SELECT coins FROM users WHERE userId = ?", (ctx.author.id,))
    bal = bal[0] if bal else 0
    inv = await ctx.bot.cfetchall("SELECT item FROM inventory WHERE userId =?", (ctx.author.id,))
    items = [row[0] for row in inv]
    v = ShopView(ctx, bal, items)
    await ctx.send(view=v)
  @commands.command(aliases= ['v'], description= 'Vote for bot and earn some money.')
  async def vote(self, ctx):
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    container.add_item(ui.TextDisplay(f"Vote here -> [TOPGG](https://top.gg/bot/1443165621100740668/vote)"))
    view.add_item(container)
    await ctx.send(view=view)
  @commands.command(aliases= [], description= '')
  @commands.is_owner()
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def rembal(self, ctx, target: discord.User, amount: K_Converter):
    buttons = [Button('Yes',discord.ButtonStyle.green,ctx.author.id), Button('No',discord.ButtonStyle.red ,ctx.author.id)]
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"Ok ok!! but legal reasons i have to ask one more time, do you really want to remove the amount {amount:,}{ctx.bot.AshesCoin} from {target}?"))
    container.add_item(actionRow)
    view.add_item(container)
    await ctx.send(view=view)
    await view.wait()
    if view.value == "Yes":
      await ctx.bot.cexecute("INSERT INTO users (userId, coins) VALUES (?,?) ON CONFLICT(userId) DO UPDATE SET coins =coins -excluded.coins ", (target.id, amount))
      view=ui.LayoutView(timeout=30)
      container=ui.Container(accent_color=Colour.from_str("#56804c"))
      container.add_item(ui.TextDisplay(f"Removed {amount:,} from {target}."))
      view.add_item(container)
      await ctx.send(view= view)
  @commands.command(aliases= [], description= '')
  @commands.is_owner()
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def addbal(self, ctx, target: discord.User, amount: K_Converter):
    buttons = [Button('Yes',discord.ButtonStyle.green,ctx.author.id), Button('No',discord.ButtonStyle.red ,ctx.author.id)]
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"Ok ok!! but legal reasons i have to ask one more time, do you really want to give {amount:,} to {target}?"))
    container.add_item(actionRow)
    view.add_item(container)
    await ctx.send(view=view)
    await view.wait()
    if view.value == "Yes":
      await ctx.bot.cexecute("INSERT INTO users (userId, coins) VALUES (?,?) ON CONFLICT(userId) DO UPDATE SET coins =excluded.coins + coins", (target.id, amount))
      view=ui.LayoutView(timeout=30)
      container=ui.Container(accent_color=Colour.from_str("#56804c"))
      container.add_item(ui.TextDisplay(f"{target.mention} bro you won at life!! {ctx.author} have decided to give you {amount:,}."))
      view.add_item(container)
      await ctx.send(view= view)
  @commands.command(aliases= ['transfer'], description= 'Feeling generous?, give some money to someone.')
  @commands.max_concurrency(1, per=BucketType.user, wait=False)
  async def give(self, ctx, target: discord.User, amount: K_Converter):
    if ctx.author.id == target.id:
      return await ctx.send(embed= Embed(title='Look!', description=f'I think you wanna marry yourself but this won\'t end your virginity.', color=Colour.from_str('#b30707')))
    bal = await ctx.bot.cfetchrow("SELECT coins FROM users WHERE userId = ?", (ctx.author.id,))
    bal = bal[0] if bal else 0
    if amount > bal:
      return await ctx.send(embed= Embed(title='Nuh uh', description=f'Look I respect your generousity but I can\'t let this happen, paying more than you have nuh uh.', color=Colour.from_str('#b30707')))
    buttons = [Button('Yes',discord.ButtonStyle.green,ctx.author.id), Button('No',discord.ButtonStyle.red ,ctx.author.id)]
    view = ui.LayoutView(timeout= 60)
    view.value = None
    container = ui.Container(accent_color = discord.Colour.from_str("#0a7a9b"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"Ok ok!! but legal reasons i have to ask one more time, do you really want to give {amount:,}{ctx.bot.AshesCoin} to {target}?"))
    container.add_item(actionRow)
    view.add_item(container)
    await ctx.send(view=view)
    await view.wait()
    if view.value == "Yes":
      await ctx.bot.cexecute("UPDATE users SET coins = coins - ? WHERE userId = ?", (amount, ctx.author.id))
      await ctx.bot.cexecute("INSERT INTO users (userId, coins) VALUES (?,?) ON CONFLICT(userId) DO UPDATE SET coins =excluded.coins + coins", (target.id, amount))
      view=ui.LayoutView(timeout=30)
      container=ui.Container(accent_color=Colour.from_str("#56804c"))
      container.add_item(ui.TextDisplay(f"{target.mention} bro you won at life!! {ctx.author} have decided to give you {amount:,}{ctx.bot.AshesCoin}."))
      view.add_item(container)
      await ctx.send(view= view)
  @commands.command(aliases=['cd'], description='View all your current cooldowns.')
  async def cooldowns(self, ctx):
    rows = await ctx.bot.cfetchall("SELECT command, expiresAt FROM cooldowns WHERE userId = ?", (ctx.author.id,))
    user_cds = {r[0]: r[1] for r in rows}
    now = time.time()
    texts = []
    for cmd in ['daily', 'weekly', 'monthly', 'vote', 'claim']:
      exp = user_cds.get(cmd, 0)
      if cmd == 'vote' and exp < now:
        texts.append(f"**{cmd.title()}**: <t:{exp}:R>" if exp > now else f"**{cmd.title()}**: Ready! -> [Vote](https://top.gg/bot/1443165621100740668/vote)")
      else:
        texts.append(f"**{cmd.title()}**: <t:{exp}:R>" if exp > now else f"**{cmd.title()}**: Ready!")
    view = ui.LayoutView(timeout=30)
    container = ui.Container(accent_color=ctx.author.color)
    container.add_item(ui.TextDisplay(f"### {ctx.author.name}'s Cooldowns\n" + "\n".join(texts)))
    view.add_item(container)
    await ctx.send(view=view)
    
  @commands.command(aliases= ['bal'], description= 'View the balance of yourself or others.')
  async def wallet(self, ctx, target: discord.User = None):
    if not target: target=ctx.author
    bal = await ctx.bot.cfetchrow("SELECT coins FROM users WHERE userId = ?", (target.id,))
    bal = bal[0] if bal else 0
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=target.color)
    container.add_item(ui.Section(f"### {target.name}'s Coins\n{ctx.bot.AshesCoin}{bal}", accessory= discord.ui.Thumbnail(target.avatar.url if target.avatar else bot.user.avatar.url)))
    view.add_item(container)
    await ctx.send(view= view)
  @commands.command(aliases= [], description= 'Claim the money after every hour but only in Official server and if you have played today.')
  async def claim(self, ctx):
    if not ctx.guild or ctx.guild.id != 1459434908932902914:
      return await ctx.send(embed= Embed(title='Command can\'t be run', description=f'This command can only be run in [Official Server]({ctx.bot.supportServerLink}).', color=Colour.from_str('#b30707')))
    pkt = timezone(timedelta(hours=5))
    now = datetime.now(pkt)
    today_start = int(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()) 
    q = "SELECT EXISTS(SELECT 1 FROM deliveries WHERE (batterId = ? OR bowlerId = ?) AND timestamp >= ?)"
    row = await ctx.bot.fetchrow(q, (ctx.author.id, ctx.author.id, today_start))
    c = row[0] if row else False
    if not c:
      return await ctx.send(embed= Embed(title='Command can\'t be run', description=f'To be able to run this command you have to play at least one game today (Starting the day from 12 AM PKT).', color=Colour.from_str('#b30707')))
    cooldown = await ctx.bot.cfetchrow("SELECT expiresAt,lastClaimAt FROM cooldowns WHERE userId = ? AND command = ?", (ctx.author.id, 'claim'))
    streak = 1
    if cooldown and cooldown[0] >= time.time():
      return await ctx.send(embed= Embed(title='Command on cooldown', description=f'The command is on cooldown, please try again later at <t:{cooldown[0]}:F>.', color=Colour.from_str('#b30707')))
    reward = random.randint(100, 3000)
    claimTime = int(time.time())
    expires = claimTime+ 3600
    await ctx.bot.cexecute("INSERT INTO cooldowns (userId, command, lastClaimAt, expiresAt) VALUES (?,?,?,?) ON CONFLICT(userId, command) DO UPDATE SET lastClaimAt=excluded.lastClaimAt, expiresAt = excluded.expiresAt", (ctx.author.id, 'claim', claimTime, expires))
    bal = await ctx.bot.cfetchrow("SELECT coins FROM users WHERE userId = ?", (ctx.author.id,))
    bal = bal[0] if bal else 0
    await ctx.bot.cexecute("INSERT INTO users (userId, coins) VALUES (?,?) ON CONFLICT(userId) DO UPDATE SET coins =excluded.coins + coins", (ctx.author.id, reward))
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=ctx.author.color)
    container.add_item(ui.TextDisplay(f"### {ctx.author.name} Claimed {reward}\n{bal} + {reward} = {bal + reward}{ctx.bot.AshesCoin}"))
    view.add_item(container)
    await ctx.send(view= view)
  @commands.command(aliases= ['d'], description= 'Claim the daily money.')
  async def daily(self, ctx):
    cooldown = await ctx.bot.cfetchrow("SELECT expiresAt,lastClaimAt FROM cooldowns WHERE userId = ? AND command = ?", (ctx.author.id, 'daily'))
    streak = 1
    if cooldown and cooldown[0] >= time.time():
      return await ctx.send(embed= Embed(title='Command on cooldown', description=f'The command is on cooldown, please try again later at <t:{cooldown[0]}:F>.', color=Colour.from_str('#b30707')))
    if cooldown:
      streakRetained = False
      streak = await ctx.bot.cfetchrow("SELECT streak FROM streaks WHERE userId = ? AND command = ?", (ctx.author.id, 'daily'))
      lastClaimAt = cooldown[1]
      if (time.time()- lastClaimAt) <= 48 * 60 * 60:
        streakRetained = True
      streak = streak[0] +1 if streak and streakRetained else 1
    effective_streak = min(30, streak)
    reward = 1000 + (effective_streak - 1) * 200 
    claimTime = int(time.time())
    expires = claimTime+ 86400
    await ctx.bot.cexecute("INSERT INTO cooldowns (userId, command, lastClaimAt, expiresAt) VALUES (?,?,?,?) ON CONFLICT(userId, command) DO UPDATE SET lastClaimAt=excluded.lastClaimAt, expiresAt = excluded.expiresAt", (ctx.author.id, 'daily', claimTime, expires))
    bal = await ctx.bot.cfetchrow("SELECT coins FROM users WHERE userId = ?", (ctx.author.id,))
    bal = bal[0] if bal else 0
    await ctx.bot.cexecute("INSERT INTO users (userId, coins) VALUES (?,?) ON CONFLICT(userId) DO UPDATE SET coins =excluded.coins + coins", (ctx.author.id, reward))
    await ctx.bot.cexecute("INSERT INTO streaks (userId, command, streak) VALUES (?,?, ?) ON CONFLICT(userId, command) DO UPDATE SET streak =excluded.streak", (ctx.author.id, 'daily',streak))
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=ctx.author.color)
    container.add_item(ui.TextDisplay(f"### {ctx.author.name} Claimed Daily\n{bal} + {reward} = {bal + reward}{ctx.bot.AshesCoin}\n-# Streak: {streak}"))
    view.add_item(container)
    await ctx.send(view= view)
  @commands.command(aliases= ['wk'], description= 'Claim the weekly money.')
  async def weekly(self, ctx):
    cooldown = await ctx.bot.cfetchrow("SELECT expiresAt,lastClaimAt FROM cooldowns WHERE userId = ? AND command = ?", (ctx.author.id, 'weekly'))
    streak = 1
    if cooldown and cooldown[0] >= time.time():
      return await ctx.send(embed= Embed(title='Command on cooldown', description=f'The command is on cooldown, please try again later at <t:{cooldown[0]}:F>.', color=Colour.from_str('#b30707')))
    if cooldown:
      streakRetained = False
      streak = await ctx.bot.cfetchrow("SELECT streak FROM streaks WHERE userId = ? AND command = ?", (ctx.author.id, 'weekly'))
      lastClaimAt = cooldown[1]
      if (time.time()- lastClaimAt) <= 336 * 60 * 60:
        streakRetained = True
      streak = streak[0] +1 if streak and streakRetained else 1
    effective_streak = min(10, streak)
    reward = 7000 + (effective_streak - 1) * 1000 
    claimTime = int(time.time())
    expires = claimTime+ 604800
    await ctx.bot.cexecute("INSERT INTO cooldowns (userId, command, lastClaimAt, expiresAt) VALUES (?,?,?,?) ON CONFLICT(userId, command) DO UPDATE SET lastClaimAt=excluded.lastClaimAt, expiresAt = excluded.expiresAt", (ctx.author.id, 'weekly', claimTime, expires))
    bal = await ctx.bot.cfetchrow("SELECT coins FROM users WHERE userId = ?", (ctx.author.id,))
    bal = bal[0] if bal else 0
    await ctx.bot.cexecute("INSERT INTO users (userId, coins) VALUES (?,?) ON CONFLICT(userId) DO UPDATE SET coins =excluded.coins + coins", (ctx.author.id, reward))
    await ctx.bot.cexecute("INSERT INTO streaks (userId, command, streak) VALUES (?,?, ?) ON CONFLICT(userId, command) DO UPDATE SET streak =excluded.streak", (ctx.author.id, 'weekly',streak))
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=ctx.author.color)
    container.add_item(ui.TextDisplay(f"### {ctx.author.name} Claimed Weekly\n{bal} + {reward} = {bal + reward}{ctx.bot.AshesCoin}\n-# Streak: {streak}"))
    view.add_item(container)
    await ctx.send(view= view)
  @commands.command(aliases= ['m'], description= 'Claim the monthly money.')
  async def monthly(self, ctx):
    cooldown = await ctx.bot.cfetchrow("SELECT expiresAt,lastClaimAt FROM cooldowns WHERE userId = ? AND command = ?", (ctx.author.id, 'monthly'))
    streak = 1
    if cooldown and cooldown[0] >= time.time():
      return await ctx.send(embed= Embed(title='Command on cooldown', description=f'The command is on cooldown, please try again later at <t:{cooldown[0]}:F>.', color=Colour.from_str('#b30707')))
    if cooldown:
      streakRetained = False
      streak = await ctx.bot.cfetchrow("SELECT streak FROM streaks WHERE userId = ? AND command = ?", (ctx.author.id, 'monthly'))
      lastClaimAt = cooldown[1]
      if (time.time()- lastClaimAt) <= 1440* 60 * 60:
        streakRetained = True
      streak = streak[0] +1 if streak and streakRetained else 1
    effective_streak = min(12, streak)
    reward = 20000 + (effective_streak - 1) * 5000 
    claimTime = int(time.time())
    expires = claimTime+ 2592000
    await ctx.bot.cexecute("INSERT INTO cooldowns (userId, command, lastClaimAt, expiresAt) VALUES (?,?,?,?) ON CONFLICT(userId, command) DO UPDATE SET lastClaimAt=excluded.lastClaimAt, expiresAt = excluded.expiresAt", (ctx.author.id, 'monthly', claimTime, expires))
    bal = await ctx.bot.cfetchrow("SELECT coins FROM users WHERE userId = ?", (ctx.author.id,))
    bal = bal[0] if bal else 0
    await ctx.bot.cexecute("INSERT INTO users (userId, coins) VALUES (?,?) ON CONFLICT(userId) DO UPDATE SET coins =excluded.coins + coins", (ctx.author.id, reward))
    await ctx.bot.cexecute("INSERT INTO streaks (userId, command, streak) VALUES (?,?, ?) ON CONFLICT(userId, command) DO UPDATE SET streak =excluded.streak", (ctx.author.id, 'monthly',streak))
    view=ui.LayoutView(timeout=30)
    container=ui.Container(accent_color=ctx.author.color)
    container.add_item(ui.TextDisplay(f"### {ctx.author.name} Claimed Monthly\n{bal} + {reward} = {bal + reward}{ctx.bot.AshesCoin}\n-# Streak: {streak}"))
    view.add_item(container)
    await ctx.send(view= view)
async def setup(bot):await bot.add_cog(Currency(bot))