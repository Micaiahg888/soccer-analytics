CREATE TABLE IF NOT EXISTS teams (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS players (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER REFERENCES teams(id),
    name TEXT NOT NULL,
    position TEXT NOT NULL,
    number INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    team_id INTEGER REFERENCES teams(id),
    opponent TEXT NOT NULL,
    date TEXT,
    season TEXT,
    location TEXT,
    team_score INTEGER,
    opponent_score INTEGER
);

CREATE TABLE IF NOT EXISTS player_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id INTEGER REFERENCES players(id),
    match_id INTEGER REFERENCES matches(id),
    goals INTEGER DEFAULT 0,
    assists INTEGER DEFAULT 0,
    minutes INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS accounts (
    id INTEGER PRIMARY KEY,
    display_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS memberships (
    account_id INTEGER PRIMARY KEY REFERENCES accounts(id),
    team_id INTEGER NOT NULL REFERENCES teams(id),
    role TEXT NOT NULL CHECK (role IN ('coach', 'player')),
    player_id INTEGER UNIQUE REFERENCES players(id),
    CHECK ((role = 'coach' AND player_id IS NULL) OR
           (role = 'player' AND player_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS invitations (
    token_hash TEXT PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(id),
    player_id INTEGER NOT NULL UNIQUE REFERENCES players(id),
    expires_at INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS recaps (
    id INTEGER PRIMARY KEY,
    match_id INTEGER NOT NULL REFERENCES matches(id),
    team_id INTEGER NOT NULL REFERENCES teams(id),
    team_note TEXT NOT NULL DEFAULT '',
    published_at TEXT,
    revision INTEGER NOT NULL DEFAULT 1,
    UNIQUE (match_id, team_id)
);

CREATE TABLE IF NOT EXISTS recap_entries (
    recap_id INTEGER NOT NULL REFERENCES recaps(id),
    player_id INTEGER NOT NULL REFERENCES players(id),
    minutes INTEGER CHECK (minutes BETWEEN 0 AND 150),
    goals INTEGER CHECK (goals BETWEEN 0 AND 99),
    assists INTEGER CHECK (assists BETWEEN 0 AND 99),
    feedback TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (recap_id, player_id)
);

CREATE INDEX IF NOT EXISTS players_team ON players(team_id);
CREATE INDEX IF NOT EXISTS recaps_team ON recaps(team_id);
