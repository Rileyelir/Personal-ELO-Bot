import json
import asyncio

async def set_json(path: str, data):
    """Creates or overwrites the .json file path specified."""
    with open(path, "w") as file:
        json.dump(data, file, indent=4)

async def get_json(path: str):
    """Returns the result of json.load() from the specified .json file."""
    try:
        with open(path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None

# Program Specific
async def set_rating(serverID: int, userID: int, mu: float, sigma: float):
    serverID = str(serverID)
    userID = str(userID)

    ratings = await get_json("skill-ratings.json")
    if ratings is None:
        await set_json("skill-ratings.json", {})
        ratings = {}

    if serverID not in ratings:
        ratings[serverID] = {}
    
    ratings[serverID][userID] = [mu, sigma]
    await set_json("skill-ratings.json", ratings)

async def set_all_ratings(serverID: int, mu: float, sigma: float):
    serverID = str(serverID)

    ratings = await get_json("skill-ratings.json")
    if ratings is None:
        await set_json("skill-ratings.json", {})
        ratings = {}
    else:
        await set_json("backup-skill-ratings.json", ratings)
        print("Skill rating backup created due to mass rating set.")

    if serverID not in ratings:
        ratings[serverID] = {}
    
    for entry in ratings[serverID]:
        ratings[serverID][entry] = [mu, sigma]

    await set_json("skill-ratings.json", ratings)

async def restore_ratings(serverID: int):
    serverID = str(serverID)
    backup = await get_json("backup-skill-ratings.json")
    if backup:
        ratings = await get_json("skill-ratings.json")
        if ratings is None:
            await set_json("skill-ratings.json", {})
            ratings = {}
        ratings[serverID] = backup[serverID]
        await set_json("skill-ratings.json", ratings)
        return True
    else:
        return False

async def get_rating(serverID: int, userID: int):
    serverID = str(serverID)
    userID = str(userID)

    ratings = await get_json("skill-ratings.json")
    try:
        return ratings[serverID][userID]
    except KeyError, TypeError:
        return None

async def get_all_ratings(serverID: int):
    serverID = str(serverID)
    ratings = await get_json("skill-ratings.json")
    try:
        return ratings[serverID]
    except KeyError, TypeError:
        return None

async def add_match_data(serverID: int, userID: int, opponentID: int, winLossDraw: int): # winLossDraw is 0 for win, 1 for loss, and 2 for draw
    serverID = str(serverID)
    userID = str(userID)
    
    matchData = await get_json("match-data.json")
    if matchData is None:
        matchData = {}
    if serverID not in matchData:
        matchData[serverID] = {}
    if userID not in matchData[serverID]:
        matchData[serverID][userID] = []
    
    matchData[serverID][userID].append([winLossDraw, opponentID])
    await set_json("match-data.json", matchData)

async def get_match_data(serverID: int, userID: int):
    serverID = str(serverID)
    userID = str(userID)

    matchData = await get_json("match-data.json")
    if matchData is None:
        matchData = {}
    if serverID not in matchData:
        matchData[serverID] = {}
    if userID not in matchData[serverID]:
        matchData[serverID][userID] = []

    return matchData[serverID][userID]

async def set_character(serverID: int, userID: int, character: str):
    serverID = str(serverID)
    userID = str(userID)

    characters = await get_json("characters.json")
    if characters is None:
        characters = {}
    if serverID not in characters:
        characters[serverID] = {}
    
    characters[serverID][userID] = character
    await set_json("characters.json", characters)

async def get_character(serverID: int, userID: int):
    serverID = str(serverID)
    userID = str(userID)

    characters = await get_json("characters.json")
    if characters is None:
        characters = {}
    if serverID not in characters:
        characters[serverID] = {}
    
    try:
        return characters[serverID][userID]
    except KeyError:
        return None