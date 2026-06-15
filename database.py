import sqlite3

def get_db():
	conn = sqlite3.connect("soccer.db")
	conn.row_factory = sqlite3.Row
	return conn

def create_tables():
	conn = get_db()
	
	conn.execute("""
	CREATE TABLE IF NOT EXISTS players (
		id INTEGER PRIMARY KEY AUTOINCREMENT,
		name TEXT NOT NULL,
		goals INTEGER,
		assists INTEGER
	)
	""")

	conn.commit()
	conn.close()

create_tables()
