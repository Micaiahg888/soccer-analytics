



from flask import Flask, render_template, request, redirect

app = Flask(__name__)

players = []
next_id = 1
teams = ["Team A", "Team B"]
matches = []
next_match_id = 1


@app.route("/")
def home():
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
	
	top_scorer = None
	
	if players:
		top_scorer = max(players, key=lambda p: p["goals"])
	
	return render_template("index.html", players=players, matches=matches, total_matches=total_matches, total_goals=total_goals, goal_differential=goal_differential, 
win_percentage=win_percentage, top_scorer =top_scorer)

@app.route("/add", methods=["POST"])
def add_player():
	global next_id, players

	name = request.form["name"]
	goals = int(request.form["goals"])
	assists = int(request.form["assists"])
	team = request.form["team"]

	players.append({
		"id" : next_id,
		"name" : name,
		"goals" : goals,
		"assists" : assists,
		"team" : team
	})

	next_id += 1
	print(players)


	return redirect("/")

@app.route("/delete/<int:player_id>")
def delete_player(player_id):
	global players
	
	new_list = []

	for p in players:
		if p["id"] != player_id:
			new_list.append(p)
	players = new_list	

	return redirect("/")

@app.route("/edit/<int:player_id>")
def edit_player(player_id):
	player_to_edit = None

	for p in players:
		if p["id"] == player_id:
			player_to_edit = p
			break

	return render_template("edit.html", player=player_to_edit)

@app.route("/update/<int:player_id>", methods=["POST"])
def update_player(player_id):
	for p in players:
		if p["id"] == player_id:
			p["name"] = request.form["name"]
			p["goals"] = int(request.form["goals"])
			p["assists"] = int(request.form["assists"])
			p["team"] = request.form["team"]


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


if __name__ == "__main__":
	app.run(host="0.0.0.0", port=5000, debug=True)
