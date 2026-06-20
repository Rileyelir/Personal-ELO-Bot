import asyncio
import json
import sqlite3 as sql

plrDataCreate = """
CREATE TABLE IF NOT EXISTS player_data (
    id INTEGER PRIMARY KEY,
    mu REAL NOT NULL,
    sigma REAL NOT NULL,
    backup_mu REAL,
    backup_sigma REAL,
    char TEXT
);
"""
matchDataCreate = """
CREATE TABLE IF NOT EXISTS match_data (
    plr_id INTEGER NOT NULL,
    opp_id INTEGER NOT NULL,
    outcome_code INTEGER NOT NULL,
    plr_score INTEGER,
    opp_score INTEGER,

    FOREIGN KEY (plr_id) REFERENCES player_data(id),
    FOREIGN KEY (opp_id) REFERENCES player_data(id)
);
"""

# Program Specific
async def set_rating(userID: int, mu: float, sigma: float):
    conn = sql.connect("data.db")
    conn.execute(plrDataCreate)
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
    conn = sql.connect("data.db")
    conn.execute(plrDataCreate)
    conn.execute(f"UPDATE player_data SET backup_mu = mu, backup_sigma = sigma, mu = {mu}, sigma = {sigma}")
    conn.commit()
    conn.close()

async def restore_ratings():
    conn = sql.connect("data.db")
    conn.execute(plrDataCreate)
    conn.execute(f"UPDATE player_data SET mu = COALESCE(backup_mu, mu), sigma = COALESCE(backup_sigma, sigma)")
    conn.commit()
    conn.close()

async def get_rating(userID: int):
    conn = sql.connect("data.db")
    conn.execute(plrDataCreate)
    cursor = conn.cursor()
    cursor.execute(f"SELECT mu, sigma FROM player_data WHERE id = {userID};")
    result = cursor.fetchone()
    conn.close()
    return result

async def get_all_ratings():
    conn = sql.connect("data.db")
    conn.execute(plrDataCreate)
    cursor = conn.cursor()
    conn.row_factory = sql.Row
    cursor = conn.execute("SELECT id, mu, sigma FROM player_data")
    result = {row["id"]: (row["mu"], row["sigma"]) for row in cursor}
    conn.close()
    return result

async def add_match_data(userID: int, opponentID: int, winLossDraw: int, score: list[int] = None): # winLossDraw is 0 for win, 1 for loss, and 2 for draw
    conn = sql.connect("data.db")
    conn.execute(matchDataCreate)
    conn.execute(f"INSERT INTO match_data (plr_id, opp_id, outcome_code) VALUES ({userID}, {opponentID}, {winLossDraw})")
    if score:
        conn.execute(f"UPDATE match_data SET plr_score = {score[0]}, opp_score = {score[1]} WHERE plr_id = {userID}")
    conn.commit()
    conn.close()

async def get_match_data(userID: int):
    conn = sql.connect("data.db")
    conn.execute(matchDataCreate)
    cursor = conn.cursor()
    cursor.execute(f"SELECT outcome_code, opp_id, plr_score, opp_score FROM match_data WHERE plr_id = {userID}")
    result = [list(row) for row in cursor]
    conn.close()
    return result

async def set_character(userID: int, character: str):
    conn = sql.connect("data.db")
    conn.execute("UPDATE player_data SET char = ? WHERE id = ?", (character, userID))
    conn.commit()
    conn.close()

async def get_character(userID: int):
    conn = sql.connect("data.db")
    cursor = conn.cursor()
    cursor.execute(f"SELECT char FROM player_data WHERE id = {userID}")
    result = cursor.fetchone()
    conn.close()
    return result[0]

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