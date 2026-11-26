from datetime import date

from flask import Blueprint, abort, flash, g, redirect, render_template, request, url_for

from .database import get_db
from .forms import field, number
from .league import FIXTURE_SELECT, fixture_by_id
from .permissions import own_fixture, roster_player, team_access
from .reporting import edit_state, save_recap

bp = Blueprint("team_space", __name__)

PLAYER_TOTALS = """
    SELECT COUNT(CASE WHEN e.recap_id IS NOT NULL AND
              (e.minutes IS NOT NULL OR e.goals IS NOT NULL OR e.assists IS NOT NULL) THEN 1 END) AS games,
           COALESCE(SUM(e.minutes), 0) AS minutes,
           COALESCE(SUM(e.goals), 0) AS goals,
           COALESCE(SUM(e.assists), 0) AS assists
    FROM recaps r JOIN recap_entries e ON r.id = e.recap_id
    JOIN players p ON p.id = e.player_id AND p.team_id = r.team_id
    WHERE r.published_at IS NOT NULL AND e.player_id = ? AND r.team_id = ?
"""


@bp.get("/my-team")
@team_access()
def home():
    member = g.member
    team_id = member["team_id"]
    is_coach = member["role"] == "coach"
    db = get_db()
    players = db.execute(
        """SELECT p.id, p.name, p.number, p.position, m.account_id
           FROM players p LEFT JOIN memberships m ON p.id = m.player_id
           WHERE p.team_id = ? AND p.archived = 0 ORDER BY p.number, p.name""",
        (team_id,),
    ).fetchall()
    fixtures = db.execute(
        FIXTURE_SELECT +
        " WHERE m.team_id = ? OR m.opponent_team_id = ? ORDER BY m.date DESC, m.id DESC",
        (team_id, team_id),
    ).fetchall()
    record = {"Played": 0, "Wins": 0, "Draws": 0, "Losses": 0}
    for fixture in fixtures:
        if not fixture["is_final"]:
            continue
        home, away = fixture["team_score"], fixture["opponent_score"]
        points, conceded = (home, away) if fixture["team_id"] == team_id else (away, home)
        record["Played"] += 1
        record["Wins" if points > conceded else "Losses" if points < conceded else "Draws"] += 1
    statuses = {
        row["match_id"]: "Published" if row["published_at"] else "Draft"
        for row in db.execute(
            "SELECT match_id, published_at FROM recaps WHERE team_id = ? AND (published_at IS NOT NULL OR ?)",
            (team_id, is_coach),
        )
    }
    return render_template(
        "my_team.html", players=players, fixtures=fixtures, record=record,
        statuses=statuses, coach=is_coach,
    )


@bp.get("/team/<int(min=1,max=9223372036854775807):team_id>")
@team_access()
def team_page(team_id):
    if team_id != g.member["team_id"]:
        abort(404)
    return redirect(url_for(".home"))


@bp.get("/player/<int(min=1,max=9223372036854775807):player_id>")
@team_access()
def player_page(player_id):
    player = roster_player(player_id)
    totals = get_db().execute(PLAYER_TOTALS, (player_id, g.member["team_id"])).fetchone()
    return render_template("player.html", player=player, totals=totals)


@bp.get("/compare")
@team_access()
def compare():
    team_id = g.member["team_id"]
    db = get_db()
    players = db.execute(
        "SELECT id, name FROM players WHERE team_id = ? AND archived = 0 ORDER BY name",
        (team_id,),
    ).fetchall()
    choices = {p["id"]: p for p in players}
    selected = [request.args.get(key, type=int) for key in ("first", "second")]
    results = []
    if any(value is not None for value in selected):
        if any(value not in choices for value in selected):
            abort(404)
        results = [
            (choices[player_id], db.execute(PLAYER_TOTALS, (player_id, team_id)).fetchone())
            for player_id in selected
        ]
    return render_template("compare.html", players=players, selected=selected, results=results)


@bp.route("/my-team/players/new", methods=("GET", "POST"))
@bp.route("/my-team/players/<int(min=1,max=9223372036854775807):player_id>/edit", methods=("GET", "POST"))
@team_access(coach=True)
def edit_player(player_id=None):
    player = roster_player(player_id) if player_id is not None else None
    error = None
    if request.method == "POST":
        try:
            name = field("name", "Player name", 100)
            position = field("position", "Position", 40)
            jersey = number("number", "Jersey number", 999)
            db = get_db()
            team_id = g.member["team_id"]
            with db:
                if player is None:
                    player_id = db.execute(
                        "INSERT INTO players (team_id, name, position, number) VALUES (?, ?, ?, ?)",
                        (team_id, name, position, jersey),
                    ).lastrowid
                else:
                    db.execute(
                        "UPDATE players SET name = ?, position = ?, number = ? WHERE id = ? AND team_id = ?",
                        (name, position, jersey, player_id, team_id),
                    )
            flash("Player saved.")
            return redirect(url_for(".home"))
        except ValueError as problem:
            error = str(problem)
    return render_template("player_edit.html", player=player, error=error)


@bp.post("/my-team/players/<int(min=1,max=9223372036854775807):player_id>/archive")
@team_access(coach=True)
def archive_player(player_id):
    db = get_db()
    player = roster_player(player_id)
    with db:
        db.execute("UPDATE players SET archived = 1 WHERE id = ? AND team_id = ?", (player_id, player["team_id"]))
        db.execute("DELETE FROM memberships WHERE player_id = ?", (player_id,))
        db.execute("DELETE FROM invitations WHERE player_id = ?", (player_id,))
    flash("Player archived and team access revoked.")
    return redirect(url_for(".home"))


@bp.route("/my-team/matches/new", methods=("GET", "POST"))
@team_access(coach=True)
def create_match():
    team_id = g.member["team_id"]
    db = get_db()
    opponents = db.execute("SELECT id, name FROM teams WHERE id <> ? ORDER BY name", (team_id,)).fetchall()
    options = {team["id"]: team["name"] for team in opponents}
    error = None
    if request.method == "POST":
        try:
            away_id = request.form.get("opponent_team_id", type=int)
            if request.form.get("opponent_team_id") and away_id is None:
                raise ValueError("Choose a valid league opponent.")
            external = field("external_opponent", "External opponent", 100, optional=True)
            if (away_id is not None) == bool(external) or (away_id is not None and away_id not in options):
                raise ValueError("Select a league opponent or enter the name of an external opponent.")
            day = field("date", "Match date", 10)
            try:
                day = date.fromisoformat(day).isoformat()
            except ValueError:
                raise ValueError("Enter a valid match date.") from None
            season = field("season", "Season", 40)
            location = field("location", "Venue", 120, optional=True)
            with db:
                match_id = db.execute(
                    """INSERT INTO matches (team_id, opponent, opponent_team_id, date, season, location)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (team_id, options[away_id] if away_id is not None else external, away_id, day, season, location),
                ).lastrowid
            flash("Fixture added to the league feed.")
            return redirect(url_for(".recap", match_id=match_id))
        except ValueError as problem:
            error = str(problem)
    return render_template("fixture_edit.html", opponents=opponents, error=error)


@bp.route("/my-team/matches/<int(min=1,max=9223372036854775807):match_id>/recap", methods=("GET", "POST"))
@team_access(coach=True)
def recap(match_id):
    fixture = fixture_by_id(match_id)
    team_id = own_fixture(fixture)
    error = None
    if request.method == "POST":
        try:
            action = save_recap(match_id, team_id)
            flash("Recap published to your team." if action == "publish" else "Draft saved for coaches.")
            return redirect(url_for(".recap", match_id=match_id))
        except ValueError as problem:
            error = str(problem)
    record, rows = edit_state(match_id, team_id)
    return render_template(
        "recap_edit.html", fixture=fixture, record=record, rows=rows, error=error,
        can_score=fixture["team_id"] == team_id,
    ), (400 if error else 200)


@bp.post("/my-team/matches/<int(min=1,max=9223372036854775807):match_id>/score")
@team_access(coach=True)
def score(match_id):
    fixture = fixture_by_id(match_id)
    team_id = own_fixture(fixture, score=True)
    try:
        home_score = number("home_score", "Home score", 99)
        away_score = number("away_score", "Away score", 99)
    except ValueError as problem:
        flash(str(problem), "error")
        return redirect(url_for(".recap", match_id=match_id))
    db = get_db()
    with db:
        db.execute(
            """UPDATE matches SET team_score = ?, opponent_score = ?, is_final = 1
               WHERE id = ? AND team_id = ?""",
            (home_score, away_score, match_id, team_id),
        )
    flash("Final score saved to the public league feed.")
    return redirect(url_for(".recap", match_id=match_id))
