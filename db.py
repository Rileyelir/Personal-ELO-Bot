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
    return True

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