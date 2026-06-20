
from flask import Flask, render_template, request, redirect

from database import get_db

app = Flask(__name__)


next_id = 1
matches = []
next_match_id = 1


@app.route("/")
def home():

	conn = get_db()
	
	# Get Players
	players = conn.execute(
		"""
		SELECT players.*, teams.name AS team_name
		FROM players
		JOIN teams
		ON players.team_id = teams.id
		"""

	).fetchall()
	
	# Get Teams
	teams = conn.execute(
		"SELECT * FROM teams"
	).fetchall()

	total_matches = len(matches)
	total_goals = sum(match["team_goals"] for match in matches)

	# stats
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
	
	
	
	top_scorers = conn.execute(
		"""
		SELECT *
		FROM players
		ORDER BY goals DESC
		LIMIT 5
		"""
	).fetchall()
	
	

	top_assisters = conn.execute(
		"""
		SELECT * 
		FROM players
		ORDER by assists DESC
		LIMIT 5
		"""
	).fetchall()

	conn.close()

	return render_template("index.html", players=players, teams=teams, matches=matches, total_matches=total_matches, total_goals=total_goals, goal_differential=goal_differential, 
win_percentage=win_percentage, top_scorers=top_scorers, top_assisters=top_assisters)


@app.route("/team/<int:team_id>")
def team_page(team_id):
	conn = get_db()
	
	team = conn.execute(
		"""
		SELECT *
		FROM teams
		WHERE id = ?
		""",
		(team_id,)
	).fetchone()

	players = conn.execute(
		"""
		SELECT *
		FROM players
		WHERE team_id = ?
		""",
		(team_id,)
	).fetchall()
	
	conn.close()

	return render_template(
		"team.html",
		team=team,
		players=players
	)


@app.route("/add_player", methods=["POST"])
def add_player():
	global next_id, players

	name = request.form["name"]
	goals = int(request.form["goals"])
	assists = int(request.form["assists"])
	team_id = request.form["team_id"]

	conn = get_db()

	conn.execute(
		"""
		INSERT INTO players (team_id, name, goals, assists)
		VALUES (?, ?, ?, ?)
		""",
		(	
			team_id,
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

@app.route("/edit/<int:player_id>", methods=["GET", "POST"])
def edit_player(player_id):
	
	conn = get_db()
	
	if request.method == "POST":

		name = request.form["name"]
		team_id = request.form["team_id"]
		goals = request.form["goals"]
		assists = request.form["assists"]
		
	
		conn.execute(
			"""
			UPDATE players
			SET name = ?, team_id = ?, goals = ?, assists = ?
			WHERE id = ?
			""",
			(name, team_id, goals, assists, player_id)
		)
		
		conn.commit()
		conn.close()
		
		return redirect("/")

	player = conn.execute(
		"SELECT * FROM players WHERE id = ?",
		(player_id,)
	).fetchone()

	teams = conn.execute(
		"SELECT * FROM teams"
	).fetchall()

	conn.close()
	
	


	return render_template("edit.html", player=player, teams=teams)

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
