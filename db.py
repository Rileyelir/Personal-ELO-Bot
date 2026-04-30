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
    
async def set_value(path: str, key: str, value):
    """Sets a value within the specified .json file."""
    new = await get_json(path)
    if new == None:
        return
        
    new[key] = value
    await set_json(path, new)

async def get_value(path: str, keys: [str]):
    """Safely retrieves a value from the specified .json file. Creates the .json if not found."""
    data = await get_json(path)
    if data == None:
        await set_json(path, {})
        return None

    current = data
    for key in keys:
        try:
            if current[key] != None:
                current = current[key]
            else:
                break
        except KeyError:
            print("Key Error!")
    return current

# Program-specific functions


# testing
if __name__ == "__main__":
    pass