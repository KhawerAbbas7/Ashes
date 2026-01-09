import discord
from discord import ui 
class Selection(ui.Select):
  def __init__(self, userId, options, maxselect, placeholder: str= 'Select'):
    self.userId = userId 
    options = [discord.SelectOption(label= b['name'], value = b['id']) for b in options]
    super().__init__(placeholder= placeholder, min_values=maxselect, max_values=maxselect, options=options)
  async def callback(self, interaction: discord.Interaction):
    if interaction.user.id != self.userId: return
    await interaction.response.defer()
    if len(self.values) == 1: self.view.value = int(self.values[0])
    else: self.view.value = [int(o) for o in self.values]
    self.view.stop()
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
class BasicView(ui.LayoutView):
  def __init__(self, topText: str = '', buttons = [], embedText = '', timeout=None) -> None:
    super().__init__(timeout= None)
    container = ui.Container(accent_color = 0x7289da)
    text = ui.TextDisplay(topText)
    self.add_item(text)
    container.add_item(ui.TextDisplay(embedText))
    actionRow = ui.ActionRow()
    for b in buttons: actionRow.add_item(b)
    container.add_item(actionRow)
    self.add_item(container)