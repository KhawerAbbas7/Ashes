import discord
from discord import ui
from prettytable import PrettyTable
def ballsToOvers(balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
class LBSelection(ui.Select):
  def __init__(self, v):
    currentlySelected = v.statType
    options = [
      "Most Runs", "Highest Batting AVG", "Highest Batting SR","Most Wickets",'Best Bowling AVG', 'Best Bowling ECO', 'Best Partnerships', "Best Batting Inning","Best Bowling Inning"
      ]
    options = [discord.SelectOption(label= b, value = b) for b in options]
    super().__init__(placeholder= "Select Category", min_values=1, max_values=1, options=[o for o in options if o.label != currentlySelected])
  async def callback(self, interaction: discord.Interaction):
    await interaction.response.defer()
    bot = interaction.client
    v = self.values[0]
    if v == 'Most Runs':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Runs", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId,SUM(runs) AS runs, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) FROM deliveries GROUP BY batterId ORDER BY runs DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs,balls])
      self.view.stop()
      v = LBview(self.view.ctx, table)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Most Wickets':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "Wickets", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId,SUM(isWicket) AS wkts, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) FROM deliveries GROUP BY bowlerId ORDER BY wkts DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", runs,balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, "Most Wickets")
      v.m = await self.view.m.edit(view=v)
    elif v == 'Highest Batting AVG':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "AVG", "Inns"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId, CASE WHEN SUM(isWicket)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/SUM(isWicket) END AS AVG, COUNT(DISTINCT inningId) as Inns FROM deliveries GROUP BY batterId ORDER BY AVG DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2),balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Highest Batting SR':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "SR"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId, CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 else ELSE 100.0*(SUM(runs)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)) END AS AVG FROM deliveries GROUP BY batterId ORDER BY AVG DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2)])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Bowling AVG':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "AVG", "WKTS"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId, CASE WHEN SUM(isWicket)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/SUM(isWicket) END AS AVG, SUM(isWicket) as wkts FROM deliveries GROUP BY bowlerId HAVING SUM(isWicket)>= 1 ORDER BY AVG ASC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2),balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Bowling ECO':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Player", "ECO", "Inns"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId, CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0)=0 THEN SUM(runs) ELSE 1.0*SUM(runs)/(SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)/6) AS AVG, COUNT(DISTINCT inningId) as Inns FROM deliveries GROUP BY bowlerId ORDER BY AVG ASC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, runs, balls = r
        batter = bot.get_user(batterId ) or batterId 
        table.add_row([f"{i}. {batter}", round(runs,2),balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Partnerships':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Batters", "Runs", "Balls"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END AS batter1, CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END AS batter2, SUM(runs) AS partnershipRuns, SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) AS balls FROM deliveries WHERE nonStrikerId IS NOT NULL GROUP BY CASE WHEN batterId<nonStrikerId THEN batterId ELSE nonStrikerId END, CASE WHEN batterId>nonStrikerId THEN batterId ELSE nonStrikerId END ORDER BY partnershipRuns DESC LIMIT 10", ())
      for i,r in enumerate(rows,1):
        batterId, batterId2, runs, balls = r
        batter1 = bot.get_user(batterId ) or batterId 
        batter2 = bot.get_user(batterId2) or batterId2
        batter = f"{batter1} & {batter2}"
        table.add_row([f"{i}. {batter}",runs,balls])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Batting Inning':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Batters", "Inning"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT batterId,r,b,notout FROM (SELECT batterId,SUM(runs) r,COUNT(*) b,CASE WHEN SUM(isWicket)=0 THEN 1 ELSE 0 END notout FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY batterId,inningId ORDER BY r DESC,b ASC LIMIT 10)", ())
      for i,r in enumerate(rows,1):
        batterId, r, b, n = r
        batter = bot.get_user(batterId ) or batterId 
        score = f"{r} ({b}){'*' if n == 1 else ''}"
        table.add_row([f"{i}. {batter}",score])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
    elif v == 'Best Bowling Inning':
      table = PrettyTable(padding_width=5)
      table.field_names = ["Bowler", "Inning"]
      table.align = "l"
      table.border=False
      table.header=True
      table.hrules=0
      table.vrules=0
      table.left_padding_width=0
      rows=await bot.fetchall("SELECT bowlerId,w,r,b FROM (SELECT bowlerId,SUM(isWicket) w,SUM(runs) r,COUNT(*) b FROM deliveries WHERE batterNum IS NOT NULL AND bowlerNum IS NOT NULL GROUP BY inningId ORDER BY w DESC,r ASC,b ASC LIMIT 10)", ())
      for i,r in enumerate(rows,1):
        batterId, w, r, b = r
        batter = bot.get_user(batterId ) or batterId 
        score = f"{w}/{r} ({ballsToOvers(b)})"
        table.add_row([f"{i}. {batter}",score])
      self.view.stop()
      v = LBview(self.view.ctx, table, v)
      v.m = await self.view.m.edit(view=v)
class Selection(ui.Select):
  def __init__(self, userId, options, maxselect, placeholder: str= 'Select'):
    self.userId = userId 
    self.opts = options
    options = [discord.SelectOption(label= b['name'], value = b['id']) for b in options]
    super().__init__(placeholder= placeholder, min_values=maxselect, max_values=maxselect, options=options)
  async def callback(self, interaction: discord.Interaction):
    if interaction.user.id != self.userId: return
    await interaction.response.defer()
    if len(self.values) == 1:
      self.view.value = int(self.values[0])
      selected= next(o for o in self.opts if o['id'] == self.view.value)['name']
    else:
      self.view.value = [int(o) for o in self.values]
      selected=[next(o['name'] for o in self.opts if o['id'] == self.view.value[k]) for k in range(len(self.view.value))]
    if hasattr(self.view,'m'):
      view = ui.LayoutView(timeout= 20)
      view.add_item(ui.TextDisplay(f"Selected {' & '.join(selected) if isinstance(selected,list) else selected}"))
      await self.view.m.edit(view= view)
    self.view.stop()
class DeclareBTN(ui.Button):
  def __init__(self):
    super().__init__(label='Declare', style=discord.ButtonStyle.danger)
  async def callback(self, i):
    c = i.client
    if i.channel.id not in c.games:
      return 
    g = c.games[i.channel.id]
    if i.user.id != g.currentInning.battingTeam.captain.id: 
      return await i.response.send_message("This can only be used by current batting captain", ephemeral= True)
    await i.response.defer(ephemeral=True)
    view=ui.LayoutView(timeout=60)
    view.value=None
    buttons = [Button('Yes',discord.ButtonStyle.green,g.currentInning.battingTeam.captain.id), Button('No',discord.ButtonStyle.red ,g.currentInning.battingTeam.captain.id)]
    container = ui.Container(accent_color = discord.Colour.from_str("#9b0a82"))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(ui.TextDisplay(f"Are you sure to declare?"))
    container.add_item(actionRow)
    view.add_item(container)
    await i.followup.send(view=view, ephemeral= True)
    await view.wait()
    if view.value in ['No', None]:
      return
    else:
      g.currentInning.declared = True
class Button(ui.Button):
  def __init__(self, label: str, style, userId: int):
    self.userId = userId
    self.lab= label
    super().__init__(label=label, style=style)
  async def callback(self, i):
    if i.user.id != self.userId: return 
    await i.response.defer()
    self.view.value = self.lab
    self.view.stop()
class LBview(ui.LayoutView):
  def __init__(self,ctx,table, title: str= "Most Runs") -> None:
    super().__init__(timeout= 40)
    self.bot = bot = ctx.bot
    self.ctx = ctx = ctx
    self.m = None
    self.guild = guild = ctx.guild
    self.statType = title
    container = ui.Container(accent_color = discord.Colour.from_str("#0ebce7"))
    container.add_item(ui.TextDisplay(f"### {title}"))
    container.add_item(ui.TextDisplay(f"**`{table.get_string().splitlines()[0]}`**\n```py\n{'\n'.join(table.get_string().splitlines()[1:])}\n```"))
    actionRow = ui.ActionRow().add_item(LBSelection(self))
    #for b in buttons: actionRow.add_item(b)
    container.add_item(actionRow)
    self.add_item(container)
  async def interaction_check(self, interaction: discord.Interaction) -> bool:return self.ctx.author.id == interaction.user.id