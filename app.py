from flask import Flask, render_template, request, redirect

from database import get_db


app = Flask(__name__)




@app.route("/")
def home():

    conn = get_db()

    players = conn.execute("""

    SELECT

    players.id,
    players.name,
    players.position,
    players.number,
    teams.name AS team_name,

    COALESCE(SUM(player_stats.goals), 0) AS goals,
    COALESCE(SUM(player_stats.assists), 0) AS assists

    FROM players

    JOIN teams
    ON players.team_id = teams.id

    LEFT JOIN player_stats
    ON players.id = player_stats.player_id

    GROUP BY players.id

    """).fetchall()



    teams = conn.execute(
        "SELECT * FROM teams"
    ).fetchall()



    matches = conn.execute("""

    SELECT

    matches.*,

    teams.name AS team_name


    FROM matches


    JOIN teams

    ON matches.team_id = teams.id


    """).fetchall()



    conn.close()



    return render_template(

        "index.html",

        players=players,

        teams=teams,

        matches=matches

    )





@app.route("/add_team", methods=["POST"])
def add_team():

    conn=get_db()


    conn.execute(

    "INSERT INTO teams(name) VALUES(?)",

    (request.form["name"],)

    )


    conn.commit()

    conn.close()


    return redirect("/")





@app.route("/add_player", methods=["POST"])
def add_player():

    conn=get_db()


    conn.execute(

    """

    INSERT INTO players

    (team_id,name,position,number)

    VALUES(?,?,?,?)

    """,

    (

    request.form["team_id"],

    request.form["name"],

    request.form["position"],

    request.form["number"]

    )

    )


    conn.commit()

    conn.close()


    return redirect("/")


@app.route("/add_match", methods=["POST"])
def add_match():

    conn=get_db()


    conn.execute(

    """

    INSERT INTO matches

    (

    team_id,

    opponent,

    date,

    season,

    location,

    team_score,

    opponent_score

    )


    VALUES(?,?,?,?,?,?,?)


    """,

    (

    request.form["team_id"],

    request.form["opponent"],

    request.form["date"],

    request.form["season"],

    request.form["location"],

    request.form["team_score"],

    request.form["opponent_score"]

    )

    )


    conn.commit()

    conn.close()


    return redirect("/")





@app.route("/team/<int:team_id>")
def team_page(team_id):

    conn = get_db()

    team = conn.execute(
        "SELECT * FROM teams WHERE id=?",
        (team_id,)
    ).fetchone()

    players = conn.execute(
        """
        SELECT

        players.id,
        players.name,
        players.position,
        players.number,

        COALESCE(SUM(player_stats.goals), 0) AS goals,
        COALESCE(SUM(player_stats.assists), 0) AS assists,
        COALESCE(SUM(player_stats.minutes), 0) AS minutes

        FROM players

        LEFT JOIN player_stats
        ON players.id = player_stats.player_id

        WHERE players.team_id = ?

        GROUP BY players.id

        """,
        (team_id,)
    ).fetchall()

    matches = conn.execute(
        """
        SELECT *
        FROM matches
        WHERE team_id=?
        """,
        (team_id,)
    ).fetchall()

    # ---------------------------
    # SAFE ADDITION: TEAM STATS
    # ---------------------------

    wins = 0
    losses = 0
    draws = 0
    goals = 0

    for m in matches:
        # safe access (prevents crashes if NULL)
        team_score = m["team_score"] or 0
        opponent_score = m["opponent_score"] or 0

        goals += team_score

        if team_score > opponent_score:
            wins += 1
        elif team_score < opponent_score:
            losses += 1
        else:
            draws += 1

    total_games = len(matches)

    win_percentage = (
        (wins / total_games) * 100
        if total_games > 0
        else 0
    )

    conn.close()

    return render_template(
        "team.html",
        team=team,
        players=players,
        matches=matches,
        wins=wins,
        losses=losses,
        draws=draws,
        goals=goals,
        win_percentage=win_percentage
    )




@app.route("/player/<int:player_id>")
def player_page(player_id):

    conn=get_db()



    player=conn.execute(

    """

    SELECT

    players.*,

    teams.name AS team_name


    FROM players


    JOIN teams

    ON players.team_id=teams.id


    WHERE players.id=?


    """,

    (player_id,)

    ).fetchone()




    stats=conn.execute(

    """

    SELECT


    player_stats.*,


    matches.opponent,

    matches.date,

    matches.season,

    matches.location



    FROM player_stats



    JOIN matches


    ON player_stats.match_id=matches.id



    WHERE player_stats.player_id=?


    """,

    (player_id,)

    ).fetchall()




    totals=conn.execute(

    """

    SELECT


    COUNT(*) AS games,


    SUM(goals) AS goals,


    SUM(assists) AS assists,


    SUM(minutes) AS minutes



    FROM player_stats


    WHERE player_id=?


    """,

    (player_id,)

    ).fetchone()



    conn.close()



    return render_template(

    "player.html",

    player=player,

    stats=stats,

    totals=totals

    )






@app.route("/add_stat", methods=["GET","POST"])
def add_stat():

    conn=get_db()



    if request.method=="POST":


        conn.execute(

        """

        INSERT INTO player_stats

        (

        player_id,

        match_id,

        goals,

        assists,

        minutes

        )


        VALUES(?,?,?,?,?)


        """,

        (

        request.form["player_id"],

        request.form["match_id"],

        request.form["goals"],

        request.form["assists"],

        request.form["minutes"]

        )

        )


        conn.commit()

        conn.close()


        return redirect("/")




    players=conn.execute(
        "SELECT * FROM players"
    ).fetchall()



    matches=conn.execute(
        "SELECT * FROM matches"
    ).fetchall()



    conn.close()



    return render_template(

    "add_stat.html",

    players=players,

    matches=matches

    )







@app.route("/edit/<int:player_id>", methods=["GET","POST"])
def edit_player(player_id):

    conn=get_db()


    if request.method=="POST":


        conn.execute(

        """

        UPDATE players


        SET name=?, team_id=?


        WHERE id=?


        """,

        (

        request.form["name"],

        request.form["team_id"],

        player_id

        )

        )


        conn.commit()

        conn.close()


        return redirect(f"/player/{player_id}")



    player=conn.execute(

    "SELECT * FROM players WHERE id=?",

    (player_id,)

    ).fetchone()



    teams=conn.execute(
        "SELECT * FROM teams"
    ).fetchall()


    conn.close()


    return render_template(

    "edit_player.html",

    player=player,

    teams=teams

    )





@app.route("/edit_stat/<int:stat_id>", methods=["GET","POST"])
def edit_stat(stat_id):

    conn=get_db()


    if request.method=="POST":


        conn.execute(

        """

        UPDATE player_stats


        SET goals=?,

        assists=?,

        minutes=?


        WHERE id=?


        """,

        (

        request.form["goals"],

        request.form["assists"],

        request.form["minutes"],

        stat_id

        )

        )


        conn.commit()

        conn.close()


        return redirect("/")




    stat=conn.execute(

    "SELECT * FROM player_stats WHERE id=?",

    (stat_id,)

    ).fetchone()



    conn.close()


    return render_template(

    "edit_stat.html",

    stat=stat

    )



@app.route("/delete_player/<int:player_id>")
def delete_player(player_id):

    conn = get_db()

    # delete stats first (important for database integrity)
    conn.execute(
        "DELETE FROM player_stats WHERE player_id=?",
        (player_id,)
    )

    conn.execute(
        "DELETE FROM players WHERE id=?",
        (player_id,)
    )

    conn.commit()
    conn.close()

    return redirect("/")

@app.route("/delete_stat/<int:stat_id>")
def delete_stat(stat_id):

    conn=get_db()


    conn.execute(

    "DELETE FROM player_stats WHERE id=?",

    (stat_id,)

    )


    conn.commit()

    conn.close()


    return redirect("/")






if __name__=="__main__":

    app.run(debug=True)