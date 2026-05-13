import trueskill as ts
import asyncio

import db

async def return_default(): # Returns configuration.json to the default configuration (called by db.py)
    return {
        "default-rating": 500,
        "rating-format": "({rating}±{uncertainty})",
        "rating-change": "{rating1} -> {rating2}",
        "score-format": "{score1} - {score2}",
        "info": {
            "title": "Information",
            "description": "I am a PELOB, or Personal ELO Bot.\nI am designed to provide a self-hostable open-source simple and customizable ELO rating system powered by TrueSkill™ for Discord servers.\nTo opt into the rating system, use /opt and begin your journey!",
            "color": [255, 255, 255]
        },
        "opt": {
            "success": "Opted in successfully, you start at {rating}.",
            "fail": "You cannot opt in, you have already done so."
        },
        "check": {
            "no-character-value": "N/A",
            "no-winrate-value": "N/A",
            "title": "PLAYER REPORT",
            "description": "Here is the report for {mention}.",
            "color": [0, 0, 255],
            "rating": "Rating",
            "matches": "Matches Played",
            "plural-match": "matches",
            "single-match": "match",
            "winrate": "Win Rate",
            "char": "Character",
            "self-fail": "You are not currently opted into the rating system. Use /opt to get started!",
            "other-fail": "The player you checked is not currently opted into the rating system."
        },
        "leaderboard": {
            "title": "Leaderboard",
            "color": [0, 0, 255]
        },
        "challenge": {
            "already-in-active": "One or both players of the accepted challenge are already in an active challenge.",
            "opponent-afk": "The player you challenged is currently AFK.",
            "self-active-fail": "You already have an active challenge out with {mention}.",
            "opponent-active-fail": "The selected opponent is already in a challenge.",
            "no-available-players": "No available players could be found to challenge.",
            "not-opted": "One or both players involved in the challenge are not yet opted into the rating system.",
            "self-not-opted": "You are not currently opted into the rating system, use /opt to get started!",
            "cant-challenge-self": "You can't challenge yourself!",
            "cant-challenge-bot": "You can't challenge me, I'm too strong.",
            "accept-content": "{mention}, your challenge has been accepted.",
            "accept-embed": {
                "title": "CHALLENGE INITIATED",
                "description": "{mention1} {rating1} VS {mention2} {rating2}",
                "color": [255, 0, 0],
                "footer": "Use /report to finalize challenge with set results."
            },
            "request-content": "You've been challenged, {mention}!",
            "request-embed": {
                "title": "CHALLENGE REQUEST",
                "description": "{mention1} {rating1} has requested to challenge {mention2} {rating2}.",
                "color": [255, 0, 100],
                "opponent-selected-footer": "This challenge has a quality of {quality:.1f}%.",
                "matchmade-footer": "This challenge was matchmade with a quality of {quality:.1f}%."
            }
        },
        "challenge-view": {
            "outside-interaction": "Only the challenged member can interact with this.",
            "decline": "Challenge declined."
        },
        "report": {
            "confirm-content": "{mention1} and {mention2} have finished.",
            "confirm-embed": {
                "title": "CHALLENGE FINISHED",
                "color": [0, 255, 0]
            },
            "no-active-challenge": "You have no active challenge to report at this time. If you do, you might have to confirm a pre-existing report.",
            "pre-existing-report": "There is a report active for your challenge already.",
            "title": "CHALLENGE REPORT",
            "result-win": "{mention1} {rating1} has won against {mention2} {rating2}!",
            "result-lose": "{mention1} {rating1} has lost against {mention2} {rating2}.",
            "result-draw": "{mention1} {rating1} and {mention2} {rating2} have drawn.",
            "color": [255, 255, 0],
            "score": "Score",
            "content": "{mention} must confirm the report."
        },
        "report-view": {
            "not-confirmer": "Only the person involved in the challenge who didn't start the report can confirm the report.",
            "outside-dispute": "Only someone involved with the challenge can dispute the report.",
            "dispute-success": "The report has been disputed, {mention1} and {mention2} should submit a new, more accurate report or contact an admin or the hoster of the bot."
        },
        "reset": {
            "title": "RATING RESET",
            "description": "Everyone's ratings have been reset to {rating}. This reset was initiated by {mention}. If this was a mistake, a backup is available with /restore.",
            "color": [255, 0, 255],
            "content": "Ratings have been reset @everyone."
        },
        "restore": {
            "title": "RATINGS RESTORED",
            "description": "Everyone's ratings have been rolled back to the previous backup, most likely from the time before a reset occured. Make sure to check your ratings! This rollback was initiated by {mention}.",
            "color": [255, 0, 255],
            "content": "All ratings have been restored @everyone.",
            "no-backup": "No backup could be found. If one does exist, make sure it is named \"backup-skill-ratings.json\"."
        },
        "decide": {
            "title": "CHALLENGE DECISION",
            "result-win": "An admin ({admin}) has decided a challenge. {winner} has won against {loser}!",
            "result-draw": "An admin ({admin}) has decided a challenge. {winner} and {loser} have drawn.",
            "color": [255, 0, 255],
            "content": "{mention1} and {mention2}, your challenge has been decided.",
            "challenge-not-found": "Could not find an active challenge for the specified winner."
        },
        "character": "Your character has been successfully set to \"{character}\".",
        "afk": {
            "on": "AFK has been turned on. Enjoy your peace!",
            "off": "AFK has been turned off. Get to fighting!"
        }
    }

async def get_cfg():
    return await db.get_config(return_default)
