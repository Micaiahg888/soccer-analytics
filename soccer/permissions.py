from functools import wraps

from flask import abort, g, redirect, url_for

from .database import get_db


def load_member(account_id):
    if not account_id:
        return None
    return get_db().execute(
        """SELECT m.team_id, m.role, m.player_id, a.display_name, t.name AS team_name
           FROM memberships m JOIN accounts a ON a.id = m.account_id
           JOIN teams t ON t.id = m.team_id
           WHERE m.account_id = ?""",
        (account_id,),
    ).fetchone()


def team_access(*, coach=False):
    def decorate(view):
        @wraps(view)
        def protected(*args, **kwargs):
            if g.member is None:
                return redirect(url_for("accounts.login"))
            if coach and g.member["role"] != "coach":
                abort(403)
            return view(*args, **kwargs)

        return protected
    return decorate


def participates(fixture, team_id):
    return team_id in (fixture["team_id"], fixture["opponent_team_id"])


def own_fixture(fixture, *, score=False):
    team_id = g.member["team_id"]
    if not participates(fixture, team_id) or (score and fixture["team_id"] != team_id):
        abort(404)
    return team_id


def roster_player(player_id):
    player = get_db().execute(
        "SELECT * FROM players WHERE id = ? AND team_id = ?",
        (player_id, g.member["team_id"]),
    ).fetchone()
    if player is None:
        abort(404)
    return player
