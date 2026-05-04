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

client = Client()

@client.tree.command(name="hello", description="Say hello") # Example command
async def hello(interaction: discord.Interaction):
    await interaction.response.send_message(f"Hello, {interaction.user.name}!")

@client.tree.command(name="opt", description="Enter the ranked system in this server.")
async def opt(interaction: discord.Interaction):
    newRating = ts.Rating(500, 160)
    result = await db.set_rating(interaction.guild.id, interaction.user.id, newRating.mu, newRating.sigma)
    if result:
        await interaction.response.send_message(f"Opted in successfully, you start at {int(newRating.mu)}±{int(newRating.sigma)}")
    else:
        await interaction.response.send_message(f"You cannot opt in, you have already done so.")

@client.tree.command(name="check", description="Check your current rating in this server.")
async def check(interaction: discord.Interaction):
    result = await db.get_rating(interaction.guild.id, interaction.user.id)
    if result:
        await interaction.response.send_message(f"Your current rating in this server is {int(result[0])}±{int(result[1])}.")
    else:
        await interaction.response.send_message("You do not have a rating for this server, use /opt to enter the system.")

@client.tree.command(name="leaderboard", description="See your placement along the top 10 players in the server.")
async def leaderboard(interaction: discord.Interaction):
    ratings = await db.get_all_ratings(interaction.guild.id)
    embed = discord.Embed(
        title="Leaderboard",
        color=discord.Color.from_rgb(0,0,255)
    )
    await interaction.response.send_message(embed=embed)

client.run(token)