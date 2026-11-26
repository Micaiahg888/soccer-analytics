from flask import Blueprint, abort, g, render_template, request, url_for

from .database import get_db
from .permissions import participates
from .reporting import visible_recap

bp = Blueprint("league", __name__)

FIXTURE_SELECT = """
    SELECT m.id, m.team_id, m.opponent_team_id, m.date, m.season, m.location,
           m.is_final, m.team_score, m.opponent_score,
           home.name AS home_name, COALESCE(away.name, m.opponent) AS away_name
    FROM matches m JOIN teams home ON home.id = m.team_id
    LEFT JOIN teams away ON away.id = m.opponent_team_id
"""


def fixture_by_id(match_id):
    fixture = get_db().execute(FIXTURE_SELECT + " WHERE m.id = ?", (match_id,)).fetchone()
    if fixture is None:
        abort(404)
    return fixture


@bp.get("/")
def feed():
    db = get_db()
    selected_team = request.args.get("team", type=int)
    selected_season = request.args.get("season", "").strip()[:40]
    page = max(1, min(request.args.get("page", 1, type=int), 1_000_000))
    conditions = []
    values = []

    if selected_team is not None:
        # Keep the value within SQLite's signed integer range.
        if not 1 <= selected_team <= 2**63 - 1:
            abort(400)
        conditions.append("(m.team_id = ? OR m.opponent_team_id = ?)")
        values.extend((selected_team, selected_team))
    if selected_season:
        conditions.append("m.season = ?")
        values.append(selected_season)

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    fixtures = db.execute(
        FIXTURE_SELECT + where +
        """ ORDER BY m.is_final, CASE WHEN m.is_final = 0 THEN m.date END ASC,
                                 CASE WHEN m.is_final = 1 THEN m.date END DESC,
                                 m.id DESC LIMIT 25 OFFSET ?""",
        (*values, (page - 1) * 24),
    ).fetchall()
    teams = db.execute("SELECT id, name FROM teams ORDER BY name").fetchall()
    seasons = db.execute(
        "SELECT DISTINCT season FROM matches WHERE season IS NOT NULL AND season <> '' ORDER BY season DESC"
    ).fetchall()
    next_page = url_for(".feed", team=selected_team, season=selected_season, page=page + 1) if len(fixtures) > 24 else None
    previous = url_for(".feed", team=selected_team, season=selected_season, page=page - 1) if page > 1 else None
    return render_template(
        "league.html", fixtures=fixtures[:24], teams=teams, seasons=seasons,
        selected_team=selected_team, selected_season=selected_season, next_page=next_page, previous=previous,
    )


@bp.get("/match/<int(min=1,max=9223372036854775807):match_id>")
def match(match_id):
    fixture = fixture_by_id(match_id)
    member = g.member
    recap = None
    can_edit = False
    if member and participates(fixture, member["team_id"]):
        can_edit = member["role"] == "coach"
        recap = visible_recap(match_id, member)
    return render_template("match.html", fixture=fixture, recap=recap, can_edit=can_edit)
