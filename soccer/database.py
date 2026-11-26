import sqlite3
from pathlib import Path

from flask import current_app, g


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def initialize():
    db = get_db()
    if db.execute("PRAGMA user_version").fetchone()[0] >= 1:
        return
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    with db:
        db.executescript("BEGIN IMMEDIATE;\n" + schema)
        if db.execute("PRAGMA user_version").fetchone()[0] >= 1:
            return
        db.execute("ALTER TABLE matches ADD COLUMN opponent_team_id INTEGER REFERENCES teams(id)")
        db.execute("ALTER TABLE matches ADD COLUMN is_final INTEGER NOT NULL DEFAULT 0 CHECK (is_final IN (0, 1))")
        db.execute("ALTER TABLE players ADD COLUMN archived INTEGER NOT NULL DEFAULT 0 CHECK (archived IN (0, 1))")
        db.execute(
            """UPDATE matches SET is_final = 1
               WHERE typeof(team_score) = 'integer' AND typeof(opponent_score) = 'integer'
               AND team_score >= 0 AND opponent_score >= 0"""
        )
        db.execute("""
            INSERT INTO recaps (match_id, team_id)
            SELECT DISTINCT m.id, m.team_id
            FROM player_stats s JOIN matches m ON m.id = s.match_id
            JOIN players p ON p.id = s.player_id AND p.team_id = m.team_id
            JOIN teams t ON t.id = m.team_id
        """)
        db.execute("""
            INSERT INTO recap_entries (recap_id, player_id, minutes, goals, assists)
            SELECT r.id, s.player_id,
                   CASE WHEN typeof(s.minutes) = 'integer' AND s.minutes BETWEEN 0 AND 150 THEN s.minutes END,
                   CASE WHEN typeof(s.goals) = 'integer' AND s.goals BETWEEN 0 AND 99 THEN s.goals END,
                   CASE WHEN typeof(s.assists) = 'integer' AND s.assists BETWEEN 0 AND 99 THEN s.assists END
            FROM player_stats s
            JOIN recaps r ON r.match_id = s.match_id
            JOIN players p ON p.id = s.player_id AND p.team_id = r.team_id
            JOIN (SELECT MAX(id) AS id FROM player_stats GROUP BY match_id, player_id) latest
                 ON latest.id = s.id
        """)
        db.execute("PRAGMA user_version = 1")


def init_app(app):
    app.teardown_appcontext(close_db)
    with app.app_context():
        initialize()
