import sqlite3


def get_db():
    conn = sqlite3.connect("soccer.db")
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():

    conn = get_db()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS teams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )
    """)


    conn.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        name TEXT NOT NULL,
        goals INTEGER,
        assists INTEGER,
        FOREIGN KEY(team_id) REFERENCES teams(id)
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        team_id INTEGER,
        opponent TEXT NOT NULL,
        date TEXT,
        location TEXT,
        season TEXT,
        team_score INTEGER,
        opponent_score INTEGER,
        FOREIGN KEY(team_id) REFERENCES teams(id)

    )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS player_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            player_id INTEGER,
            match_id INTEGER,
            goals INTEGER DEFAULT 0,
            assists INTEGER DEFAULT 0,
            minutes INTEGER DEFAULT 0,
            FOREIGN KEY(player_id) REFERENCES players(id),
            FOREIGN KEY(match_id) REFERENCES matches(id)
        )
        """)


    conn.commit()
    conn.close()


create_tables()