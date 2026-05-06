import discord
import trueskill as ts

import config
import db

class ChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member, on_accept):
        super().__init__(timeout=120)
        self.challenger = challenger
        self.opponent = opponent
        self.message = None  # set after sending so on_timeout can edit it
        self.on_accept = on_accept

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("Only the challenged member can interact with this.", ephemeral=True)
            return
        self.disable_all()
        await interaction.message.edit(view=self)
        
        challengerRating = await db.get_rating(interaction.guild.id, self.challenger.id)
        oppRating = await db.get_rating(interaction.guild.id, self.opponent.id)
        embed = discord.Embed(
            title="CHALLENGE INITIATED",
            description=f"{self.challenger.mention} ({int(challengerRating[0])}±{int(challengerRating[1])}) VS {self.opponent.mention} ({int(oppRating[0])}±{int(oppRating[1])})",
            color=discord.Color.from_rgb(255,0,0)
        )
        embed.set_footer(text="Use /report to finalize challenge with set results.")

        await interaction.response.send_message(f"{self.challenger.mention}, your challenge has been accepted.", embed=embed)
        await self.on_accept(self.challenger, self.opponent)

    @discord.ui.button(label="Decline", style=discord.ButtonStyle.red)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("Only the challenged member can interact with this.", ephemeral=True)
            return
        self.disable_all()
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Challenge declined.")

    async def on_timeout(self):
        self.disable_all()
        if self.message:
            await self.message.edit(view=self)

    def disable_all(self):
        for item in self.children:
            item.disabled = True