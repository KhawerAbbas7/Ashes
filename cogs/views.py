import discord
from discord import ui
from prettytable import PrettyTable
def ballsToOvers(balls: int) -> float: return float(f"{balls//6}.{balls % 6}")
class OversSelection(ui.Select):
  def __init__(self):
    options = [
      discord.SelectOption(label= "90 Overs", description= 'Follow-on: 75', value = 90),
      discord.SelectOption(label= "60 Overs", description= 'Follow-on: 50', value = 60),
      discord.SelectOption(label= "30 Overs", description= 'Follow-on: 25', value = 30),
      ]
    super().__init__(placeholder= "Select Overs", min_values=1, max_values=1, options=options)
  async def callback(self, interaction: discord.Interaction):
    g = interaction.client.games[interaction.channel.id]
    if interaction.user.id != g.hostId:
      return await interaction.response.send_message("Only usable by host.", ephemeral= True)
    elif g.started: return
    g.maxBalls = int(self.values[0])*6
    await interaction.response.edit_message(view= g.showPlayers(), ephemeral= True)
class LBSelection(ui.Select):
  def __init__(self, v):
    currentlySelected = v.statType
    options = [
      "Most Runs", "Highest Batting AVG", "Highest Batting SR","Most Wickets",'Best Bowling AVG', 'Best Bowling ECO', 'Best Partnerships', "Best Batting Inning","Best Bowling Inning"
      ]
    options = [discord.SelectOption(label= b, value = b) for b in options]
    super().__init__(placeholder= "Select Category", min_values=1, max_values=1, options=[o for o in options if o.label != currentlySelected])
  async def callback(self, interaction: discord.Interaction):
    if self.view.ctx.author.id != interaction.user.id: return
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
      rows=await bot.fetchall("SELECT batterId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 100.0*SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN runs ELSE 0 END)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS batting_avg FROM deliveries GROUP BY batterId ORDER BY batting_avg DESC LIMIT 10", ())
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
      rows=await bot.fetchall("SELECT bowlerId,CASE WHEN SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END)=0 THEN 0.0 ELSE 6.0*SUM(runs)/SUM(CASE WHEN batterNum IS NOT NULL AND bowlerNum IS NOT NULL THEN 1 ELSE 0 END) END AS economy,COUNT(DISTINCT inningId) AS Inns FROM deliveries GROUP BY bowlerId ORDER BY economy ASC LIMIT 10", ())
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
class Last5BTN(ui.Button):
  def __init__(self):
    super().__init__(label='Last 5 Innings', style=discord.ButtonStyle.green)
  async def callback(self, i):
    c = i.client
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
class HelpButton(ui.Button):
  def __init__(self,lab, disabledd: bool):
    self.lab = lab
    super().__init__(label= lab, style=discord.ButtonStyle.green, disabled= disabledd)
  async def callback(self, i):
    if self.lab == 'Prev':
      self.view.page -= 1 
      self.view.makePage()
      await i.response.edit_message(content=None,view=self.view)
    elif self.lab == 'Next':
      self.view.page += 1 
      self.view.makePage()
      await i.response.edit_message(content=None,view=self.view)
class Helpview(ui.LayoutView):
  def __init__(self,ctx) -> None:
    self.ctx = ctx = ctx 
    self.perPage = 10
    self.page = 0 
    super().__init__(timeout= 60)
    self.makePage()
  def makePage(self):
    self.clear_items()
    commands = [c for c in self.ctx.bot.commands if c.hidden is False]
    start=self.page*self.perPage 
    end=start+self.perPage
    container = ui.Container(accent_color = discord.Colour.from_str("#a50ee7"))
    container.add_item(ui.TextDisplay(f"### Help"))
    if self.page == 0:
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
      container.add_item(ui.TextDisplay(f"Ashes is a fun bot inspired by Hand Cricket and enhanced with elements of Test cricket. While it follows the basic idea of Test cricket, a few special rules apply:\n• The digit 5 is not used in the game\nA batter can score only one boundary (either 4 or 6) in an over\n• Bowlers are not allowed to bowl 0\n• A batter can play at most three 0s in a row\nThese rules make the game simple, balanced, and more strategic to play."))
    container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
    for command in commands[start:end]:
      canOnlyBeUsedBy = f"\n**Only Usable By:{command.extras['usableBy']}**" if command.extras else ""
      extraTxt = f"\n**Description:** {command.description}" if command.description else ""
      extraTxt += canOnlyBeUsedBy
      container.add_item(ui.TextDisplay(f"{self.ctx.clean_prefix}{command.qualified_name} {command.signature}\n**Aliases:** {' • '.join(command.aliases)}{extraTxt}"))
      container.add_item(ui.Separator(visible= True,spacing=discord.SeparatorSpacing.small))
    actionRow = ui.ActionRow()
    actionRow.add_item(HelpButton('Prev', True if self.page == 0 else False))
    actionRow.add_item(HelpButton('Next', True if end >= len(commands) else False))
    container.add_item(actionRow)
    self.add_item(container)
  async def interaction_check(self, interaction: discord.Interaction) -> bool:return self.ctx.author.id == interaction.user.id

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
  async def on_timeout(self, i):
    for child in self.walk_children():
      if hasattr(child, "disabled"):
        child.disabled = True
    #await self.ctx.message.edit(content=None, view=self.view)
  async def interaction_check(self, interaction: discord.Interaction) -> bool:return self.ctx.author.id == interaction.user.id