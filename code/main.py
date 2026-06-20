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
        print(f'PELOB v1.0.0 started as {self.user}!')

client = Client()

challenges = []
afkList = []
queueList = []

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
    newRating = client.env.Rating(client.env.mu, client.env.sigma)
    result = await db.get_rating(interaction.user.id)
    if not result:
        await db.set_rating(interaction.user.id, newRating.mu, newRating.sigma)
        ratingText = await format_text(client.config["rating-format"], rating=int(newRating.mu), uncertainty=int(newRating.sigma))
        msgContent = await format_text(cfg["success"], rating=ratingText)
        await interaction.response.send_message(msgContent, ephemeral=True)
    else:
        await interaction.response.send_message(cfg["fail"], ephemeral=True)

@client.tree.command(name="check", description="Check your or another player's current rating in this server.")
async def check(interaction: discord.Interaction, member: discord.Member = None):
    cfg = client.config["check"]
    member = interaction.user if member is None else member
    result = await db.get_rating(member.id)
    matchData = await db.get_match_data(member.id)
    character = await db.get_character(member.id)
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
    ratings = await db.get_all_ratings()
    if ratings == {}:
        await interaction.response.send_message(cfg["no-data"], ephemeral=True)
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

@client.tree.command(name="challenge", description="Find an optimal opponent to challenge or manually select someone to challenge.")
async def challenge(interaction: discord.Interaction, opponent: discord.Member = None):
    cfg = client.config["challenge"]
    async def on_accept(m1: discord.Member, m2: discord.Member, acceptInteraction: discord.Interaction):
        for c in challenges:
            cNew = str.split(c, "-")
            if str(m1.id) in cNew or str(m2.id) in cNew:
                await acceptInteraction.response.send_message(cfg["already-in-active"], ephemeral=True)
                return
        
        challengerRating = await db.get_rating(m1.id)
        oppRating = await db.get_rating(m2.id)
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
        if opponent.id in afkList:
            await interaction.response.send_message(cfg["opponent-afk"], ephemeral=True)
            return

        oppRating = await db.get_rating(opponent.id)
        selfRating = await db.get_rating(interaction.user.id)

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
        ratings = await db.get_all_ratings()
        selfRating = await db.get_rating(interaction.user.id)
        if selfRating is None:
            await interaction.response.send_message(cfg["self-not-opted"])
            return

        currentChoice = [0.0, None]
        for key in ratings:
            if key == interaction.user.id or int(key) in afkList:
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
        memberRating = await db.get_rating(member.id)
        rating1 = await format_text(client.config["rating-format"], rating=int(selfRating[0]), uncertainty=int(selfRating[1]))
        rating2 = await format_text(client.config["rating-format"], rating=int(memberRating[0]), uncertainty=int(memberRating[1]))
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
    cfg = client.config["report"]
    async def on_confirm(interaction: discord.Interaction, reporter: discord.Member, confirmer: discord.Member, score: list[int]):
        for c in challenges:
            if str(reporter.id) in c.split("-"):
                challenges.remove(c)
        
        reporterRatingValues = await db.get_rating(reporter.id)
        confirmerRatingValues = await db.get_rating(confirmer.id)
        reporterRating = client.env.Rating(reporterRatingValues[0], reporterRatingValues[1])
        confirmerRating = client.env.Rating(confirmerRatingValues[0], confirmerRatingValues[1])
        reporterNewRating = client.env.Rating()
        confirmerNewRating = client.env.Rating()

        if score[0] == score[1]: # score[0] is the reporter's, score[1] is the confirmer's
            reporterNewRating, confirmerNewRating = client.env.rate_1vs1(reporterRating, confirmerRating, drawn=True)
            await db.add_match_data(reporter.id, confirmer.id, 2, [score[0], score[1]])
            await db.add_match_data(confirmer.id, reporter.id, 2, [score[1], score[0]])
        elif score[0] > score[1]:
            reporterNewRating, confirmerNewRating = client.env.rate_1vs1(reporterRating, confirmerRating)
            await db.add_match_data(reporter.id, confirmer.id, 0, [score[0], score[1]])
            await db.add_match_data(confirmer.id, reporter.id, 1, [score[1], score[0]])
        elif score[0] < score[1]:
            confirmerNewRating, reporterNewRating = client.env.rate_1vs1(confirmerRating, reporterRating)
            await db.add_match_data(reporter.id, confirmer.id, 1, [score[0], score[1]])
            await db.add_match_data(confirmer.id, reporter.id, 0, [score[1], score[0]])

        await db.set_rating(reporter.id, reporterNewRating.mu, reporterNewRating.sigma)
        await db.set_rating(confirmer.id, confirmerNewRating.mu, confirmerNewRating.sigma)

        embed = discord.Embed(
            title=cfg["confirm-embed"]["title"],
            color=discord.Color.from_rgb(*cfg["confirm-embed"]["color"])
        )

        confirmerRatingBeforeText = await format_text(client.config["rating-format"], rating=int(confirmerRating.mu), uncertainty=int(confirmerRating.sigma))
        confirmerRatingAfterText = await format_text(client.config["rating-format"], rating=int(confirmerNewRating.mu), uncertainty=int(confirmerNewRating.sigma))
        confirmerFieldText = await format_text(client.config["rating-change"], rating1=confirmerRatingBeforeText, rating2=confirmerRatingAfterText)
        embed.add_field(name=confirmer.display_name, value=confirmerFieldText)

        reporterRatingBeforeText = await format_text(client.config["rating-format"], rating=int(reporterRating.mu), uncertainty=int(reporterRating.sigma))
        reporterRatingAfterText = await format_text(client.config["rating-format"], rating=int(reporterNewRating.mu), uncertainty=int(reporterNewRating.sigma))
        reporterFieldText = await format_text(client.config["rating-change"], rating1=reporterRatingBeforeText, rating2=reporterRatingAfterText)
        embed.add_field(name=reporter.display_name, value=reporterFieldText)
        
        msgContent = await format_text(cfg["confirm-content"], mention1=reporter.mention, mention2=confirmer.mention)
        await interaction.response.send_message(msgContent, embed=embed)

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
        await interaction.response.send_message(cfg["no-active-challenge"], ephemeral=True)
        return
    
    try:
        if activeChallenge[2] == "await":
            await interaction.response.send_message(cfg["pre-existing-report"], ephemeral=True)
            return
    except IndexError: pass
    
    challenges[index] += "-await"

    otherMemberID = activeChallenge[0] if int(activeChallenge[0]) != interaction.user.id else activeChallenge[1]
    otherMember = await interaction.guild.fetch_member(int(otherMemberID))
    yourRating = await db.get_rating(interaction.user.id)
    theirRating = await db.get_rating(int(otherMemberID))

    result = "result-lose"
    if your_score > their_score: result = "result-win"
    if your_score == their_score: result = "result-draw"

    rating1 = await format_text(client.config["rating-format"], rating=int(yourRating[0]), uncertainty=int(yourRating[1]))
    rating2 = await format_text(client.config["rating-format"], rating=int(theirRating[0]), uncertainty=int(theirRating[1]))
    descriptionText = await format_text(cfg[result], mention1=interaction.user.mention, mention2=otherMember.mention, rating1=rating1, rating2=rating2)
    embed = discord.Embed(
        title=cfg["title"],
        description=descriptionText,
        color=discord.Color.from_rgb(*cfg["color"])
    )
    scoreValue = await format_text(client.config["score-format"], score1=your_score, score2=their_score)
    embed.add_field(name=cfg["score"], value=scoreValue)

    view = views.ReportView(interaction.user, otherMember, [your_score, their_score], on_confirm, on_dispute)
    msgContent = await format_text(cfg["content"], mention=otherMember.mention)
    await interaction.response.send_message(msgContent, embed=embed, view=view)
    view.message = await interaction.original_response()

@client.tree.command(name="character", description="Set your favorite character to show on your player report.")
async def character(interaction: discord.Interaction, character: str):
    await db.set_character(interaction.user.id, character)
    msgContent = await format_text(client.config["character"], character=character)
    await interaction.response.send_message(msgContent, ephemeral=True)

@client.tree.command(name="afk", description="Toggle afk status, turns off incoming challenges.")
async def afk(interaction: discord.Interaction):
    cfg = client.config["afk"]
    if interaction.user.id in afkList:
        afkList.remove(interaction.user.id)
        await interaction.response.send_message(cfg["off"], ephemeral=True)
    else:
        afkList.append(interaction.user.id)
        await interaction.response.send_message(cfg["on"], ephemeral=True)

@client.tree.command(name="queue", description="Enter a queue to challenge a player looking for a match.")
async def queue(interaction: discord.Interaction):
    cfg = client.config["queue"]
    if interaction.user in queueList:
        queueList.remove(interaction.user)
        await interaction.response.send_message(cfg["removed"], ephemeral=True)
        return

    if len(queueList) != 0: # Player found in queue
        opponent = queueList[0]
        queueList.remove(queueList[0])
        await challenge.callback(interaction, opponent)
    else: # Player not found in queue
        queueList.append(interaction.user)
        await interaction.response.send_message(cfg["added"], ephemeral=True)

@client.tree.command(name="history", description="Get match history for yourself or another player.")
async def history(interaction: discord.Interaction, member: discord.Member = None):
    cfg = client.config["history"]
    member = interaction.user if member is None else member
    matchData = await db.get_match_data(member.id)
    matchData.reverse()

    descriptionText = await format_text(cfg["description"], mention=member.mention)
    embed = discord.Embed(
        title=cfg["title"],
        description=descriptionText,
        color=discord.Color.from_rgb(*cfg["color"])
    )
    embed.set_thumbnail(url=member.avatar.url)

    for match in matchData: # reversed so newest matches are first
        result = None
        match match[0]:
            case 0:
                result = cfg["win"]
            case 1:
                result = cfg["loss"]
            case 2:
                result = cfg["draw"]
        
        if match[2] is None:
            result = result + " (Admin)"
        else:
            scoreFormatted = await format_text(client.config["score-format"], score1=match[2], score2=match[3])
            result = result + f" ({scoreFormatted})"
        opponent = await interaction.guild.fetch_member(match[1])
        embed.add_field(name=opponent.display_name, value=result)

    await interaction.response.send_message(embed=embed, ephemeral=True)

# ---------------------------- Admin Commands

@client.tree.command(name="reset", description="ADMIN ONLY: Resets every player's rating to default.")
@app_commands.default_permissions(administrator=True)
async def reset(interaction: discord.Interaction):
    cfg = client.config["reset"]
    await interaction.response.defer()
    await db.set_all_ratings(client.env.mu, client.env.sigma)

    rating = await format_text(client.config["rating-format"], rating=int(client.env.mu), uncertainty=int(client.env.sigma))
    descriptionText = await format_text(cfg["description"], rating=rating, mention=interaction.user.mention)
    embed = discord.Embed(
        title=cfg["title"],
        description=descriptionText,
        color=discord.Color.from_rgb(*cfg["color"])
    )
    await interaction.followup.send(cfg["content"], embed=embed)

@client.tree.command(name="restore", description="ADMIN ONLY: Restores ratings from this server if a backup is available.")
@app_commands.default_permissions(administrator=True)
async def restore(interaction: discord.Interaction):
    cfg = client.config["restore"]
    await db.restore_ratings()
    descriptionText = await format_text(cfg["description"], mention=interaction.user.mention)
    embed = discord.Embed(
        title=cfg["title"],
        description=descriptionText,
        color=discord.Color.from_rgb(*cfg["color"])
    )
    await interaction.response.send_message(cfg["content"], embed=embed)

@client.tree.command(name="decide", description="ADMIN ONLY: Make the decision on an ongoing challenge, used for disputes.")
@app_commands.default_permissions(administrator=True)
async def decide(interaction: discord.Interaction, winner: discord.Member, drawn: bool = False):
    cfg = client.config["decide"]
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

        winnerRatingValues = await db.get_rating(winner.id)
        otherRatingValues = await db.get_rating(otherMember.id)
        winnerRating = client.env.Rating(winnerRatingValues[0], winnerRatingValues[1])
        otherRating = client.env.Rating(otherRatingValues[0], otherRatingValues[1])
        winnerNewRating, otherNewRating = client.env.rate_1vs1(winnerRating, otherRating, drawn=drawn)

        await db.set_rating(winner.id, winnerNewRating.mu, winnerNewRating.sigma)
        await db.set_rating(otherMember.id, otherNewRating.mu, otherNewRating.sigma)
        await db.add_match_data(winner.id, otherMember.id, 0 if not drawn else 2)
        await db.add_match_data(otherMember.id, winner.id, 1 if not drawn else 2)

        result = "result-win" if not drawn else "result-draw"
        descriptionText = await format_text(cfg[result], admin=interaction.user.mention, winner=winner.mention, loser=otherMember.mention)
        embed = discord.Embed(
            title=cfg["title"],
            description=descriptionText,
            color=discord.Color.from_rgb(*cfg["color"])
        )

        rating1 = await format_text(client.config["rating-format"], rating=int(winnerRating.mu), uncertainty=int(winnerRating.sigma))
        rating2 = await format_text(client.config["rating-format"], rating=int(winnerNewRating.mu), uncertainty=int(winnerNewRating.sigma))
        fieldValue = await format_text(client.config["rating-change"], rating1=rating1, rating2=rating2)
        embed.add_field(name=winner.display_name, value=fieldValue)

        rating1 = await format_text(client.config["rating-format"], rating=int(otherRating.mu), uncertainty=int(otherRating.sigma))
        rating2 = await format_text(client.config["rating-format"], rating=int(otherNewRating.mu), uncertainty=int(otherNewRating.sigma))
        fieldValue = await format_text(client.config["rating-change"], rating1=rating1, rating2=rating2)
        embed.add_field(name=otherMember.display_name, value=fieldValue)

        msgContent = await format_text(cfg["content"], mention1=winner.mention, mention2=otherMember.mention)
        await interaction.response.send_message(msgContent, embed=embed)
    else:
        await interaction.response.send_message(cfg["challenge-not-found"], ephemeral=True)

# ---------------------------- RUN!!!

client.run(token)