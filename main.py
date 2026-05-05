from os import getenv
from dotenv import load_dotenv
import discord
from discord import app_commands
import trueskill as ts
import db

load_dotenv()
token = getenv("TOKEN")

class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()  # Register slash commands on startup

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

class ChallengeView(discord.ui.View):
    def __init__(self, challenger: discord.Member, opponent: discord.Member):
        super().__init__(timeout=60)
        self.challenger = challenger
        self.opponent = opponent
        self.message = None  # set after sending so on_timeout can edit it

    @discord.ui.button(label="Accept", style=discord.ButtonStyle.green)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.opponent:
            await interaction.response.send_message("Only the challenged member can interact with this.", ephemeral=True)
            return
        self.disable_all()
        await interaction.message.edit(view=self)
        await interaction.response.send_message("Challenge accepted!")

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

client = Client()

@client.tree.command(name="hello", description="Say hello") # Example command
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello, {interaction.user.name}!", ephemeral=True)

@client.tree.command(name="opt", description="Enter the ranked system in this server.")
async def opt(interaction: discord.Interaction):
    newRating = ts.Rating(500, 160) # DEFAULT RATING, FIRST NUMBER IS BASE AND SECOND IS ± CONFIDENCE
    result = await db.set_rating(interaction.guild.id, interaction.user.id, newRating.mu, newRating.sigma)
    if result:
        await interaction.response.send_message(f"Opted in successfully, you start at {int(newRating.mu)}±{int(newRating.sigma)}", ephemeral=True)
    else:
        await interaction.response.send_message(f"You cannot opt in, you have already done so.", ephemeral=True)

@client.tree.command(name="check", description="Check your current rating in this server.")
async def check(interaction: discord.Interaction):
    result = await db.get_rating(interaction.guild.id, interaction.user.id)
    if result:
        await interaction.response.send_message(f"Your current rating in this server is {int(result[0])}±{int(result[1])}.", ephemeral=True)
    else:
        await interaction.response.send_message("You do not have a rating for this server, use /opt to enter the system.", ephemeral=True)

@client.tree.command(name="leaderboard", description="See your placement along the top 10 players in the server.")
async def leaderboard(interaction: discord.Interaction):
    ratings = await db.get_all_ratings(interaction.guild.id)
    if ratings is None:
        return

    embed = discord.Embed(
        title="Leaderboard",
        color=discord.Color.from_rgb(0,0,255)
    )

    index = 1
    rankedList = dict(sorted(ratings.items(), key=lambda item: item[1][0]-item[1][1], reverse=True))
    for user in rankedList:
        member = await interaction.guild.fetch_member(int(user))
        embed.add_field(name=f"{index}: {member.display_name}", value=f"{int(rankedList[user][0])}±{int(rankedList[user][1])}")

        if index == 1:
            embed.set_thumbnail(url=member.display_avatar.url)
        index += 1

    await interaction.response.send_message(embed=embed, ephemeral=True)

@client.tree.command(name="challenge", description="Find an optimal opponent to challenge or manually select someone to challenge.")
async def challenge(interaction: discord.Interaction, opponent: discord.Member = None):
    if opponent:
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("You can't challenge yourself!", ephemeral=True)
            return

        oppRating = await db.get_rating(interaction.guild.id, opponent.id)
        selfRating = await db.get_rating(interaction.guild.id, interaction.user.id)

        embed = discord.Embed(
            title="CHALLENGE REQUEST",
            description=f"{interaction.user.mention} ({int(selfRating[0])}±{int(selfRating[1])}) has requested to challenge {opponent.mention} ({int(oppRating[0])}±{int(oppRating[1])}).",
            color=discord.Color.from_rgb(255,0,0)
        )

        view = ChallengeView(interaction.user, opponent)
        await interaction.response.send_message(content=f"You've been challenged, {opponent.mention}", embed=embed, view=view)
        view.message = await interaction.original_response()
    else:
        ratings = await db.get_all_ratings(interaction.guild.id)

client.run(token)