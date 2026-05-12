from os import getenv
from dotenv import load_dotenv
import discord
from discord import app_commands
import trueskill as ts

import views
import config
import db

# ---------------------------- Setup

load_dotenv()
token = getenv("TOKEN")

class Client(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.all())
        self.tree = app_commands.CommandTree(self)
        self.config = {}

    async def setup_hook(self):
        await self.tree.sync()
        print("[setup_hook] Command tree synced")

        self.config = await config.get_cfg()
        print("[setup_hook] Configuration loaded")

        self.env = ts.TrueSkill(
            self.config["default-rating"],
            self.config["default-rating"] / 3,
            self.config["default-rating"] / 6,
            self.config["default-rating"] / 300,
            0.0
        )
        print("[setup_hook] TrueSkill environment set (based on config's default-rating)")

    async def on_ready(self):
        print(f'Logged on as {self.user}!')

client = Client()

# ---------------------------- Extra Functions

async def format_text(template: str, **kwargs):
    try:
        return template.format(**kwargs)
    except KeyError, IndexError:
        return "This text is not supposed to show. The text template was formatted wrong, please contact the bot hoster who manages the configuration file with the command you used."

# ---------------------------- Commands

@client.tree.command(name="info", description="Provides information about this bot.")
async def info(interaction: discord.Interaction):
    cfg = client.config["info"]
    embed = discord.Embed(
        title=cfg["title"],
        description=cfg["description"],
        color=discord.Color.from_rgb(*cfg["color"])
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)

@client.tree.command(name="opt", description="Enter the ranked system in this server.")
async def opt(interaction: discord.Interaction):
    cfg = client.config["opt"]
    newRating = client.env.Rating(500, 160)
    result = await db.get_rating(interaction.guild.id, interaction.user.id)
    if not result:
        await db.set_rating(interaction.guild.id, interaction.user.id, newRating.mu, newRating.sigma)
        msgContent = await format_text(cfg["success"], rating=f"{int(newRating.mu)}±{int(newRating.sigma)}")
        await interaction.response.send_message(msgContent, ephemeral=True)
    else:
        await interaction.response.send_message(cfg["fail"], ephemeral=True)

@client.tree.command(name="check", description="Check your or another player's current rating in this server.")
async def check(interaction: discord.Interaction, member: discord.Member = None):
    cfg = client.config["check"]
    member = interaction.user if member is None else member
    result = await db.get_rating(interaction.guild.id, member.id)
    matchData = await db.get_match_data(interaction.guild.id, member.id)
    character = await db.get_character(interaction.guild.id, member.id)
    if character is None:
        character = cfg["no-character-value"]

    winRate = cfg["no-winrate-value"]
    if not matchData is None:
        wins = 0
        losses = 0
        for match in matchData:
            if match[0] == 0: wins += 1
            elif match[0] == 1: losses += 1
        if wins != 0 or losses != 0:
            winRate = f"{wins/(wins+losses)*100:.1f}%"

    if result:
        descriptionText = await format_text(cfg["description"], mention=member.mention)
        embed = discord.Embed(
            title=cfg["title"],
            description=descriptionText,
            color=discord.Color.from_rgb(*cfg["color"])
        )
        embed.set_thumbnail(url=member.avatar.url)

        ratingText = await format_text(client.config["rating-format"], rating=int(result[0]), uncertainty=int(result[1]))
        embed.add_field(name=cfg["rating"], value=ratingText)
        embed.add_field(name=cfg["matches"], value=f"{len(matchData)} " + (cfg["plural-match"] if len(matchData) != 1 else cfg["single-match"]))
        embed.add_field(name=cfg["winrate"], value=winRate)
        embed.add_field(name=cfg["char"], value=character)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        if member.id == interaction.user.id:
            await interaction.response.send_message(cfg["self-fail"], ephemeral=True)
        else:
            await interaction.response.send_message(cfg["other-fail"], ephemeral=True)

@client.tree.command(name="leaderboard", description="See the leaderboard for the server.")
async def leaderboard(interaction: discord.Interaction):
    cfg = client.config["leaderboard"]
    ratings = await db.get_all_ratings(interaction.guild.id)
    if ratings is None:
        return

    embed = discord.Embed(
        title=cfg["title"],
        color=discord.Color.from_rgb(*cfg["color"])
    )

    index = 1
    rankedList = dict(sorted(ratings.items(), key=lambda item: item[1][0]-item[1][1], reverse=True))
    for user in rankedList:
        member = await interaction.guild.fetch_member(int(user))
        ratingText = await format_text(client.config["rating-format"], rating=int(rankedList[user][0]), uncertainty=int(rankedList[user][1]))
        embed.add_field(name=f"{index}: {member.display_name}", value=ratingText)

        if index == 1:
            embed.set_thumbnail(url=member.display_avatar.url)
        index += 1

    await interaction.response.send_message(embed=embed, ephemeral=True)

challenges = []

@client.tree.command(name="challenge", description="Find an optimal opponent to challenge or manually select someone to challenge.")
async def challenge(interaction: discord.Interaction, opponent: discord.Member = None):
    cfg = client.config["challenge"]
    async def on_accept(m1: discord.Member, m2: discord.Member, acceptInteraction: discord.Interaction):
        for c in challenges:
            cNew = str.split(c, "-")
            if str(m1.id) in cNew or str(m2.id) in cNew:
                await acceptInteraction.response.send_message(cfg["already-in-active"], ephemeral=True)
                return
        
        challengerRating = await db.get_rating(interaction.guild.id, m1.id)
        oppRating = await db.get_rating(interaction.guild.id, m2.id)
        rating1 = await format_text(client.config["rating-format"], rating=int(challengerRating[0]), uncertainty=int(challengerRating[1]))
        rating2 = await format_text(client.config["rating-format"], rating=int(oppRating[0]), uncertainty=int(oppRating[1]))
        descriptionText = await format_text(cfg["accept-embed"]["description"], mention1=m1.mention, mention2=m2.mention, rating1=rating1, rating2=rating2)
        embed = discord.Embed(
            title=cfg["accept-embed"]["title"],
            description=descriptionText,
            color=discord.Color.from_rgb(*cfg["accept-embed"]["color"])
        )
        embed.set_footer(text=cfg["accept-embed"]["footer"])
        responseContent = await format_text(cfg["accept-content"], mention=m1.mention)
        await acceptInteraction.response.send_message(responseContent, embed=embed)

        challenges.append(f"{m1.id}-{m2.id}")

    for c in challenges:
        cNew = str.split(c, "-")
        if str(interaction.user.id) in cNew:
            opponentFromActiveChallengeID = cNew[0] if int(cNew[0]) != interaction.user.id else cNew[1]
            opponentFromActiveChallenge = await interaction.guild.fetch_member(int(opponentFromActiveChallengeID))
            msgContent = await format_text(cfg["self-active-fail"], mention=opponentFromActiveChallenge.mention)
            await interaction.response.send_message(msgContent, ephemeral=True)
            return
        if opponent: # doing this to avoid errors, might not be necessary
            if str(opponent.id) in cNew:
                await interaction.response.send_message(cfg["opponent-active-fail"], ephemeral=True)
                return

    if opponent:
        if opponent.id == interaction.user.id:
            await interaction.response.send_message(cfg["cant-challenge-self"], ephemeral=True)
            return
        if opponent.id == client.user.id:
            await interaction.response.send_message(cfg["cant-challenge-bot"], ephemeral=True)
            return

        oppRating = await db.get_rating(interaction.guild.id, opponent.id)
        selfRating = await db.get_rating(interaction.guild.id, interaction.user.id)

        if oppRating == None or selfRating == None:
            await interaction.response.send_message(cfg["not-opted"], ephemeral=True)
            return

        rating1 = await format_text(client.config["rating-format"], rating=int(selfRating[0]), uncertainty=int(selfRating[1]))
        rating2 = await format_text(client.config["rating-format"], rating=int(oppRating[0]), uncertainty=int(oppRating[1]))
        descriptionText = await format_text(cfg["request-embed"]["description"], mention1=interaction.user.mention, mention2=opponent.mention, rating1=rating1, rating2=rating2)
        footerText = await format_text(cfg["request-embed"]["opponent-selected-footer"], quality=client.env.quality_1vs1(client.env.Rating(selfRating[0],selfRating[1]),client.env.Rating(oppRating[0],oppRating[1]))*100)
        embed = discord.Embed(
            title=cfg["request-embed"]["title"],
            description=descriptionText,
            color=discord.Color.from_rgb(*cfg["request-embed"]["color"])
        )
        embed.set_footer(text=footerText)
        
        view = views.ChallengeView(interaction.user, opponent, on_accept)
        msgContent = await format_text(cfg["request-content"], mention=opponent.mention)
        await interaction.response.send_message(content=msgContent, embed=embed, view=view)
        view.message = await interaction.original_response()
    else:
        ratings = await db.get_all_ratings(interaction.guild.id)
        selfRating = await db.get_rating(interaction.guild.id, interaction.user.id)
        if selfRating is None:
            await interaction.response.send_message(cfg["self-not-opted"])
            return

        currentChoice = [0.0, None]
        for key in ratings:
            if key == str(interaction.user.id):
                continue
            for c in challenges:
                if key in c.split("-"):
                    continue
            quality = client.env.quality_1vs1(client.env.Rating(selfRating[0], selfRating[1]), client.env.Rating(ratings[key][0], ratings[key][1]))
            if quality > currentChoice[0]:
                currentChoice = [quality, key]
        if currentChoice[1] is None:
            await interaction.response.send_message(cfg["no-available-players"], ephemeral=True)
            return

        member = await interaction.guild.fetch_member(int(currentChoice[1]))
        memberRating = await db.get_rating(interaction.guild.id, member.id)
        descriptionText = await format_text(cfg["request-embed"]["description"], mention1=interaction.user.mention, mention2=member.mention, rating1=rating1, rating2=rating2)
        footerText = await format_text(cfg["request-embed"]["matchmade-footer"], quality=currentChoice[0]*100)
        embed = discord.Embed(
            title=cfg["request-embed"]["title"],
            description=descriptionText,
            color=discord.Color.from_rgb(*cfg["request-embed"]["color"])
        )
        embed.set_footer(text=footerText)
        
        view = views.ChallengeView(interaction.user, member, on_accept)
        msgContent = await format_text(cfg["request-content"], mention=member.mention)
        await interaction.response.send_message(content=msgContent, embed=embed, view=view)
        view.message = await interaction.original_response()

@client.tree.command(name="report", description="Report the results of your active challenge.")
async def report(interaction: discord.Interaction, your_score: int, their_score: int):
    async def on_confirm(interaction: discord.Interaction, reporter: discord.Member, confirmer: discord.Member, score: [int]):
        for c in challenges:
            if str(reporter.id) in c.split("-"):
                challenges.remove(c)
        
        reporterRatingValues = await db.get_rating(interaction.guild.id, reporter.id)
        confirmerRatingValues = await db.get_rating(interaction.guild.id, confirmer.id)
        reporterRating = client.env.Rating(reporterRatingValues[0], reporterRatingValues[1])
        confirmerRating = client.env.Rating(confirmerRatingValues[0], confirmerRatingValues[1])
        reporterNewRating = client.env.Rating()
        confirmerNewRating = client.env.Rating()

        if score[0] == score[1]:
            reporterNewRating, confirmerNewRating = client.env.rate_1vs1(reporterRating, confirmerRating, drawn=True)
            await db.add_match_data(interaction.guild.id, reporter.id, confirmer.id, 2)
            await db.add_match_data(interaction.guild.id, confirmer.id, reporter.id, 2)
        elif score[0] > score[1]:
            reporterNewRating, confirmerNewRating = client.env.rate_1vs1(reporterRating, confirmerRating)
            await db.add_match_data(interaction.guild.id, reporter.id, confirmer.id, 0)
            await db.add_match_data(interaction.guild.id, confirmer.id, reporter.id, 1)
        elif score[0] < score[1]:
            confirmerNewRating, reporterNewRating = client.env.rate_1vs1(confirmerRating, reporterRating)
            await db.add_match_data(interaction.guild.id, reporter.id, confirmer.id, 1)
            await db.add_match_data(interaction.guild.id, confirmer.id, reporter.id, 0)

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

@client.tree.command(name="character", description="Set your favorite character to show on your player report.")
async def character(interaction: discord.Interaction, character: str):
    await db.set_character(interaction.guild.id, interaction.user.id, character)
    await interaction.response.send_message(f"Your character has been successfully set to \"{character}\".", ephemeral=True)

# ---------------------------- Admin Commands

@client.tree.command(name="reset", description="ADMIN ONLY: Resets every player's rating to default.")
@app_commands.default_permissions(administrator=True)
async def reset(interaction: discord.Interaction):
    await interaction.response.defer()
    await db.set_all_ratings(interaction.guild.id, client.env.mu, client.env.sigma)
    embed = discord.Embed(
        title="RATING RESET",
        description=f"Everyone's ratings have been reset to {client.env.mu}±{client.env.sigma}. This reset was initiated by {interaction.user.mention}. If this was a mistake, a backup is available with /restore.",
        color=discord.Color.from_rgb(255, 0, 255)
    )
    await interaction.followup.send("@everyone", embed=embed)

@client.tree.command(name="restore", description="ADMIN ONLY: Restores ratings from this server if a backup is available.")
@app_commands.default_permissions(administrator=True)
async def restore(interaction: discord.Interaction):
    result = await db.restore_ratings(interaction.guild.id)
    if result:
        embed = discord.Embed(
            title="RATINGS RESTORED",
            description=f"Everyone's ratings have been rolled back to the previous backup, most likely from the time before a reset occured. Make sure to check your ratings! This rollback was initiated by {interaction.user.mention}.",
            color=discord.Color.from_rgb(255, 0, 255)
        )
        await interaction.response.send_message("@everyone", embed=embed)
    else:
        await interaction.response.send_message("No backup could be found. If one does exist, make sure it is named \"backup-skill-ratings.json\".", ephemeral=True)

@client.tree.command(name="decide", description="ADMIN ONLY: Make the decision on an ongoing challenge, used for disputes.")
@app_commands.default_permissions(administrator=True)
async def decide(interaction: discord.Interaction, winner: discord.Member, drawn: bool = False):
    selectedChallenge = None
    otherMember: discord.Member = None
    for c in challenges:
        cNew = c.split("-")
        if str(winner.id) in cNew:
            selectedChallenge = c
            otherMemberID = int(cNew[0]) if cNew[0] != str(winner.id) else int(cNew[1])
            otherMember = await interaction.guild.fetch_member(otherMemberID)
            break
    
    if selectedChallenge:
        challenges.remove(selectedChallenge)

        winnerRatingValues = await db.get_rating(interaction.guild.id, winner.id)
        otherRatingValues = await db.get_rating(interaction.guild.id, otherMember.id)
        winnerRating = client.env.Rating(winnerRatingValues[0], winnerRatingValues[1])
        otherRating = client.env.Rating(otherRatingValues[0], otherRatingValues[1])
        winnerNewRating, otherNewRating = client.env.rate_1vs1(winnerRating, otherRating, drawn=drawn)

        await db.set_rating(interaction.guild.id, winner.id, winnerNewRating.mu, winnerNewRating.sigma)
        await db.set_rating(interaction.guild.id, otherMember.id, otherNewRating.mu, otherNewRating.sigma)
        await db.add_match_data(interaction.guild.id, winner.id, otherMember.id, 0 if not drawn else 2)
        await db.add_match_data(interaction.guild.id, otherMember.id, winner.id, 1 if not drawn else 2)

        resultText = "won" if not drawn else "tied"
        embed = discord.Embed(
            title="CHALLENGE DECISION",
            description=f"An admin ({interaction.user.mention}) has decided a challenge. {winner.mention} has {resultText} against {otherMember.mention}!",
            color=discord.Color.from_rgb(255,0,255)
        )
        embed.add_field(name=winner.display_name, value=f"({int(winnerRating.mu)}±{int(winnerRating.sigma)}) -> ({int(winnerNewRating.mu)}±{int(winnerNewRating.sigma)})")
        embed.add_field(name=otherMember.display_name, value=f"({int(otherRating.mu)}±{int(otherRating.sigma)}) -> ({int(otherNewRating.mu)}±{int(otherNewRating.sigma)})")

        await interaction.response.send_message(f"{winner.mention} and {otherMember.mention}, your challenge has been decided.", embed=embed)
    else:
        await interaction.response.send_message("Could not find an active challenge for the specified winner.", ephemeral=True)

# ---------------------------- RUN!!!

client.run(token)