import asyncio
import json
import sqlite3 as sql

plrTableExecute = """
CREATE TABLE IF NOT EXISTS player_data (
    id INTEGER PRIMARY KEY,
    mu REAL NOT NULL,
    sigma REAL NOT NULL,
    char TEXT
);
"""
matchTableExecute = """
CREATE TABLE IF NOT EXISTS match_data (
    plr_id INTEGER NOT NULL,
    opp_id INTEGER NOT NULL,
    outcome_code INTEGER NOT NULL,

    FOREIGN KEY (plr_id) REFERENCES player_data(id),
    FOREIGN KEY (opp_id) REFERENCES player_data(id)
);
"""


# Program Specific
async def set_rating(userID: int, mu: float, sigma: float):
    conn = sql.connect("data.db")
    conn.execute(plrTableExecute)
    conn.execute(f"""
    INSERT INTO player_data (id, mu, sigma)
    VALUES ({userID}, {mu}, {sigma})
    ON CONFLICT(id) DO UPDATE SET
        mu = excluded.mu,
        sigma = excluded.sigma;
    """)
    conn.commit()
    conn.close()

async def set_all_ratings(mu: float, sigma: float):
    pass

async def restore_ratings():
    pass

async def get_rating(userID: int):
    conn = sql.connect("data.db")
    conn.execute(plrTableExecute)
    cursor = conn.cursor()
    cursor.execute(f"SELECT mu, sigma FROM player_data WHERE id = {userID};")
    result = cursor.fetchone()
    conn.close()
    return result

async def get_all_ratings():
    pass

async def add_match_data(userID: int, opponentID: int, winLossDraw: int): # winLossDraw is 0 for win, 1 for loss, and 2 for draw
    userID = str(userID)

async def get_match_data(userID: int):
    userID = str(userID)

async def set_character(userID: int, character: str):
    userID = str(userID)

async def get_character(userID: int):
    userID = str(userID)

# Configuration loading
async def get_json(path: str):
    try:
        with open(path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return None
async def get_config(callback):
    cfg = await get_json("configuration.json")
    if cfg is None:
        default = await callback()
        with open("configuration.json", "w") as file:
            json.dump(default, file, indent=4)
        return default
    return cfg