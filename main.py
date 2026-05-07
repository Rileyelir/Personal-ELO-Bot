from os import getenv
from dotenv import load_dotenv
import discord
from discord import app_commands
import trueskill as ts

import views
import config
import db

load_dotenv()
token = getenv("TOKEN")

env = config.tsenv

class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()  # Register slash commands on startup

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

client = Client()

@client.tree.command(name="opt", description="Enter the ranked system in this server.")
async def opt(interaction: discord.Interaction):
    newRating = env.Rating(500, 160)
    result = await db.get_rating(interaction.guild.id, interaction.user.id)
    if not result:
        await db.set_rating(interaction.guild.id, interaction.user.id, newRating.mu, newRating.sigma)
        await interaction.response.send_message(f"Opted in successfully, you start at {int(newRating.mu)}±{int(newRating.sigma)}", ephemeral=True)
    else:
        await interaction.response.send_message(f"You cannot opt in, you have already done so.", ephemeral=True)

@client.tree.command(name="check", description="Check your current rating in this server.")
async def check(interaction: discord.Interaction):
    result = await db.get_rating(interaction.guild.id, interaction.user.id)
    if result:
        await interaction.response.send_message(f"Your current rating in this server is {int(result[0])}±{int(result[1])}.", ephemeral=True)
    else:
        await interaction.response.send_message("You are not currently opted into the rating system, use /opt to begin!", ephemeral=True)

@client.tree.command(name="leaderboard", description="See the leaderboard for the server.")
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

challenges = []

@client.tree.command(name="challenge", description="Find an optimal opponent to challenge or manually select someone to challenge.")
async def challenge(interaction: discord.Interaction, opponent: discord.Member = None):
    async def on_accept(m1: discord.Member, m2: discord.Member):
        for c in challenges:
            cNew = str.split(c, "-")
            if str(m1.id) in cNew or str(m2.id) in cNew:
                await interaction.response.send_message("One or both members of the accepted challenge are already in an active challenge.", ephemeral=True)
                return
        challenges.append(f"{m1.id}-{m2.id}")

    for c in challenges:
        cNew = str.split(c, "-")
        if str(interaction.user.id) in cNew:
            opponentFromActiveChallengeID = cNew[0] if int(cNew[0]) != interaction.user.id else cNew[1]
            opponentFromActiveChallenge = await interaction.guild.fetch_member(int(opponentFromActiveChallengeID))
            await interaction.response.send_message(f"You already have an active challenge out with {opponentFromActiveChallenge.mention}.", ephemeral=True)
            return

    if opponent:
        if opponent.id == interaction.user.id:
            await interaction.response.send_message("You can't challenge yourself!", ephemeral=True)
            return
        if opponent.id == client.user.id:
            await interaction.response.send_message("You can't challenge me, I'm too strong.", ephemeral=True)
            return

        oppRating = await db.get_rating(interaction.guild.id, opponent.id)
        selfRating = await db.get_rating(interaction.guild.id, interaction.user.id)

        if oppRating == None or selfRating == None:
            await interaction.response.send_message("One or both members involved in the challenge are not yet opted into the rating system.", ephemeral=True)
            return

        embed = discord.Embed(
            title="CHALLENGE REQUEST",
            description=f"{interaction.user.mention} ({int(selfRating[0])}±{int(selfRating[1])}) has requested to challenge {opponent.mention} ({int(oppRating[0])}±{int(oppRating[1])}).",
            color=discord.Color.from_rgb(255,0,100)
        )
        embed.set_footer(text=f"This challenge has a quality of {env.quality_1vs1(env.Rating(selfRating[0],selfRating[1]),env.Rating(oppRating[0],oppRating[1]))*100:.1f}%.")
        
        view = views.ChallengeView(interaction.user, opponent, on_accept)
        await interaction.response.send_message(content=f"You've been challenged, {opponent.mention}!", embed=embed, view=view)
        view.message = await interaction.original_response()
    else:
        ratings = await db.get_all_ratings(interaction.guild.id)
        selfRating = await db.get_rating(interaction.guild.id, interaction.user.id)
        if selfRating is None:
            await interaction.response.send_message("You are not currently opted into the rating system, use /opt to begin!")
            return

        currentChoice = [0.0, None]
        for key in ratings:
            if key == str(interaction.user.id):
                continue
            quality = env.quality_1vs1(env.Rating(selfRating[0], selfRating[1]), env.Rating(ratings[key][0], ratings[key][1]))
            if quality > currentChoice[0]:
                currentChoice = [quality, key]

        member = await interaction.guild.fetch_member(int(currentChoice[1]))
        memberRating = await db.get_rating(interaction.guild.id, member.id)
        embed = discord.Embed(
            title="CHALLENGE REQUEST",
            description=f"{interaction.user.mention} ({int(selfRating[0])}±{int(selfRating[1])}) has requested to challenge {member.mention} ({int(memberRating[0])}±{int(memberRating[1])}).",
            color=discord.Color.from_rgb(255,0,0)
        )
        embed.set_footer(text=f"This challenge was matchmade with a quality of {currentChoice[0]*100:.1f}%.")
        
        view = views.ChallengeView(interaction.user, member, on_accept)
        await interaction.response.send_message(content=f"You've been challenged, {member.mention}!", embed=embed, view=view)
        view.message = await interaction.original_response()

@client.tree.command(name="report", description="Report the results of your active challenge.")
async def report(interaction: discord.Interaction, your_score: int, their_score: int):
    async def on_confirm(interaction: discord.Interaction, reporter: discord.Member, confirmer: discord.Member, score: [int]):
        for c in challenges:
            if str(reporter.id) in c.split("-"):
                challenges.remove(c)
        
        reporterRatingValues = await db.get_rating(interaction.guild.id, reporter.id)
        confirmerRatingValues = await db.get_rating(interaction.guild.id, confirmer.id)
        reporterRating = env.Rating(reporterRatingValues[0], reporterRatingValues[1])
        confirmerRating = env.Rating(confirmerRatingValues[0], confirmerRatingValues[1])
        reporterNewRating = env.Rating()
        confirmerNewRating = env.Rating()

        if score[0] == score[1]:
            reporterNewRating, confirmerNewRating = env.rate_1vs1(reporterRating, confirmerRating, drawn=True)
        elif score[0] > score[1]:
            reporterNewRating, confirmerNewRating = env.rate_1vs1(reporterRating, confirmerRating)
        elif score[0] < score[1]:
            confirmerNewRating, reporterNewRating = env.rate_1vs1(confirmerRating, reporterRating)

        await db.set_rating(interaction.guild.id, reporter.id, reporterNewRating.mu, reporterNewRating.sigma)
        await db.set_rating(interaction.guild.id, confirmer.id, confirmerNewRating.mu, confirmerNewRating.sigma)

        embed = discord.Embed(
            title="CHALLENGE FINISHED",
            color=discord.Color.from_rgb(0, 255, 0)
        )
        embed.add_field(name=confirmer.display_name, value=f"({int(confirmerRating.mu)}±{int(confirmerRating.sigma)}) -> ({int(confirmerNewRating.mu)}±{int(confirmerNewRating.sigma)})")
        embed.add_field(name=reporter.display_name, value=f"({int(reporterRating.mu)}±{int(reporterRating.sigma)}) -> ({int(reporterNewRating.mu)}±{int(reporterNewRating.sigma)})")
        
        await interaction.response.send_message(f"{reporter.mention} and {confirmer.mention} have finished.", embed=embed)

    async def on_dispute(memberID: int):
        index = 0
        for c in challenges:
            cNew = c.split("-")
            if str(memberID) in cNew:
                challenges[index] = f"{cNew[0]}-{cNew[1]}"
                break
            index += 1

    activeChallenge = None

    index = 0
    for c in challenges:
        cNew = str.split(c, "-")
        if str(interaction.user.id) in cNew:
            activeChallenge = cNew
            break
        index += 1

    if activeChallenge is None:
        await interaction.response.send_message("You have no active challenge to report at this time. If you do, you might have to confirm a pre-existing report.", ephemeral=True)
        return
    
    try:
        if activeChallenge[2] == "await":
            await interaction.response.send_message("There is a report active for your challenge already.", ephemeral=True)
            return
    except IndexError: pass
    
    challenges[index] += "-await"

    otherMemberID = activeChallenge[0] if int(activeChallenge[0]) != interaction.user.id else activeChallenge[1]
    otherMember = await interaction.guild.fetch_member(int(otherMemberID))
    yourRating = await db.get_rating(interaction.guild.id, interaction.user.id)
    theirRating = await db.get_rating(interaction.guild.id, int(otherMemberID))

    result = "lost"
    if your_score > their_score: result = "won"
    if your_score == their_score: result = "tied"

    embed = discord.Embed(
        title="CHALLENGE REPORT",
        description=f"{interaction.user.mention} ({int(yourRating[0])}±{int(yourRating[1])}) has {result} against {otherMember.mention} ({int(theirRating[0])}±{int(theirRating[1])}).",
        color=discord.Color.from_rgb(255,255,0)
    )
    embed.add_field(name="Score", value=f"{your_score} - {their_score}")

    view = views.ReportView(interaction.user, otherMember, [your_score, their_score], on_confirm, on_dispute)
    await interaction.response.send_message(f"{otherMember.mention} must confirm the report.", embed=embed, view=view)
    view.message = await interaction.original_response()

client.run(token)