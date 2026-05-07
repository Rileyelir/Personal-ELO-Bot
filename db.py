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

# testing
if __name__ == "__main__":
    pass