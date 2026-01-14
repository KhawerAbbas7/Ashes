import discord
from discord import ui 
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
class InputView(ui.LayoutView):
  def __init__(self,scoreComtainer, consecutiveDots = None) -> None:
    super().__init__(timeout= None)
    container = ui.Container(accent_color = 0x7289da)
    container.add_item(ui.TextDisplay(embedText))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(actionRow)
    self.add_item(container)