
from flask import Flask, render_template, request, redirect

from database import get_db

app = Flask(__name__)


next_id = 1
teams = ["Team A", "Team B"]
matches = []
next_match_id = 1


@app.route("/")
def home():

	conn = get_db()
	
	players = conn.execute(
		"SELECT * FROM players"
	).fetchall()
	
	conn.close

	total_matches = len(matches)
	total_goals = sum(match["team_goals"] for match in matches)

	wins = 0
	losses = 0
	draws = 0

	for match in matches:
		if match["team_goals"] > match["opponent_goals"]:
			wins += 1
		elif match["team_goals"] < match["opponent_goals"]:
			losses += 1
		else:
			draws += 1

	goal_differential = sum(match["team_goals"]-match["opponent_goals"] for match in matches)

	if total_matches > 0:
		win_percentage = (wins/total_matches) * 100
	else:
		win_percentage = 0
	
	
	
	if players:
		max_goals = max(p["goals"] for p in players) 
		top_scorers = [p for p in players if p["goals"] == max_goals]
	else: 
		top_scorers = []
	
	

	if players:
		max_assists = max(p["assists"] for p in players) 
		top_assisters = [p for p in players if p["assists"] == max_assists]
	else: 
		top_assisters = []

	return render_template("index.html", players=players, matches=matches, total_matches=total_matches, total_goals=total_goals, goal_differential=goal_differential, 
win_percentage=win_percentage, top_scorers=top_scorers, top_assisters=top_assisters)

@app.route("/add", methods=["POST"])
def add_player():
	global next_id, players

	name = request.form["name"]
	goals = int(request.form["goals"])
	assists = int(request.form["assists"])
	team = request.form["team"]

	conn = get_db()

	conn.execute(
		"""
		INSERT INTO players (name, goals, assists)
		VALUES (?, ?, ?)
		""",
		(
			name,
			goals,
			assists
		)
	)
	conn.commit()
	conn.close()
	
	return redirect("/")

@app.route("/delete/<int:player_id>")
def delete_player(player_id):
	
	conn = get_db()
	
	conn.execute(
		"DELETE FROM players WHERE id = ?",
		(player_id,)
	)

	conn.commit()
	conn.close()

	return redirect("/")

@app.route("/edit/<int:player_id>")
def edit_player(player_id):
	
	conn = get_db()
	
	player = conn.execute(
		"SELECT * FROM players WHERE id = ?",
		(player_id,)
	).fetchone()

	conn.close()


	return render_template("edit.html", player=player)

@app.route("/update/<int:player_id>", methods=["POST"])
def update_player(player_id):
	name = request.form["name"]
	goals = request.form["goals"]
	assists = request.form["assists"]

	conn = get_db()

	conn.execute(
		"""
		UPDATE players
		SET name = ?, goals = ?, assists = ?
		WHERE id = ?
		""", 
		(name, goals, assists, player_id)
	)

	conn.commit()
	conn.close()


	return redirect("/")

@app.route("/add_match", methods=["POST"])
def add_match():
	global next_match_id
	
	matches.append({
		"id" : next_match_id,
		"opponent" : request.form["opponent"],
		"team_goals" : int(request.form["team_goals"]),
		"opponent_goals" : int(request.form["opponent_goals"])
	})
	next_match_id += 1
			
	return redirect("/")

@app.route("/add_team", methods=["POST"])
def add_team():
	
	name = request.form["name"]
	conn = get_db()

	conn.execute(
		"INSERT INTO teams (name) VALUES (?)",
		(name,)
	)

	conn.commit()
	conn.close()

	return redirect("/")



if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, debug=True)
