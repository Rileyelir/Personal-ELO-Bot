import trueskill as ts
import asyncio

import db

async def reset(): # Returns configuration.json to the default configuration (called by db.py)
    return {
        "default-rating": 500,
        "rating-format": "({rating}±{uncertainty})",
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
        }
    }

async def get_cfg():
    return await db.get_config(reset)
