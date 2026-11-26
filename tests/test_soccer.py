import re
import sqlite3

import pytest
from werkzeug.security import generate_password_hash

from soccer import create_app
from soccer.database import get_db

PASSWORD = "example-password-2026"


@pytest.fixture(scope="module")
def hashed():
    return generate_password_hash(PASSWORD)


@pytest.fixture
def app(tmp_path, hashed):
    app = create_app({"DATABASE": str(tmp_path / "test.db"), "SECRET_KEY": "test-key", "TESTING": True})
    with app.app_context():
        db = get_db()
        with db:
            db.executemany("INSERT INTO teams VALUES (?, ?)", [(1, "Harbor FC"), (2, "Summit FC")])
            db.executemany(
                "INSERT INTO players (id, team_id, name, position, number) VALUES (?, ?, ?, ?, ?)",
                [(1, 1, "Alice Example", "GK", 1), (2, 1, "Ben Example", "DF", 4),
                 (3, 2, "Cruz Example", "FW", 9), (4, 1, "Dana Example", "MF", 8)],
            )
            db.executemany(
                "INSERT INTO accounts VALUES (?, ?, ?, ?)",
                [(i, name, f"{name.lower()}@example.test", hashed)
                 for i, name in enumerate(("Harbor", "Summit", "Alice", "Ben", "Cruz"), 1)],
            )
            db.executemany(
                "INSERT INTO memberships VALUES (?, ?, ?, ?)",
                [(1, 1, "coach", None), (2, 2, "coach", None), (3, 1, "player", 1),
                 (4, 1, "player", 2), (5, 2, "player", 3)],
            )
            db.execute(
                """INSERT INTO matches (id, team_id, opponent_team_id, opponent, date, season)
                   VALUES (1, 1, 2, 'Summit FC', '2026-12-07', 'Fall 2026')"""
            )
    return app


def text(response):
    return response.get_data(as_text=True)


def hidden(response, name):
    return re.search(rf'name="{name}" value="([^"]*)"', text(response)).group(1)


def post(client, url, data, *, form=None):
    source = client.get(form or url)
    return client.post(url, data={**data, "csrf_token": hidden(source, "csrf_token")})


def sign_in(app, name):
    client = app.test_client()
    response = post(client, "/login", {"email": f"{name}@example.test", "password": PASSWORD})
    assert response.status_code == 302
    return client


RECAP = "/my-team/matches/1/recap"
SCORE = "/my-team/matches/1/score"
PLAYER = "/my-team/players/1/edit"


def save_recap(client, action, **fields):
    page = client.get(RECAP)
    return client.post(
        RECAP,
        data={
            "action": action, "csrf_token": hidden(page, "csrf_token"),
            "revision": hidden(page, "revision"), **fields,
        },
    )


def test_public_feed_filters_and_hides_team_material(app):
    visitor = app.test_client()
    home = visitor.get("/?team=2&season=Fall+2026")
    assert home.status_code == 200
    assert "Upcoming fixtures" in text(home)
    assert "Harbor FC" in text(home)
    assert "Alice Example" not in text(home)
    assert "no-store" in home.headers["Cache-Control"]
    assert "No matches found" in text(visitor.get("/?season=Spring+2026"))
    assert visitor.get("/my-team").status_code == 302
    assert visitor.get("/player/1").status_code == 302
    assert visitor.get("/match/1").status_code == 200


def test_postgame_visibility_across_both_teams(app):
    harbor = sign_in(app, "harbor")
    summit = sign_in(app, "summit")
    alice = sign_in(app, "alice")
    ben = sign_in(app, "ben")
    cruz = sign_in(app, "cruz")
    guest = app.test_client()

    report = {"team_note": "Harbor team talk", "minutes_1": "90", "feedback_1": "Alice feedback",
              "minutes_2": "65", "feedback_2": "Ben feedback"}
    assert save_recap(harbor, "draft", **report).status_code == 302
    assert "Harbor team talk" in text(harbor.get("/match/1"))
    assert "Harbor team talk" not in text(alice.get("/match/1"))
    assert "Draft" not in text(alice.get("/my-team"))

    score = post(harbor, SCORE, {"home_score": "2", "away_score": "1"}, form=RECAP)
    assert score.status_code == 302
    assert 'aria-label="Final score"' in text(guest.get("/match/1"))
    assert "Harbor team talk" not in text(alice.get("/match/1"))
    assert save_recap(harbor, "publish", **report).status_code == 302

    assert "Alice feedback" in text(alice.get("/match/1"))
    assert "Ben feedback" not in text(alice.get("/match/1"))
    assert "Ben feedback" in text(ben.get("/match/1"))
    assert "Alice feedback" not in text(ben.get("/match/1"))
    assert "Ben Example" in text(alice.get("/match/1"))
    for viewer in (guest, cruz, summit):
        page = text(viewer.get("/match/1"))
        assert "Harbor team talk" not in page
        assert "Alice feedback" not in page
        assert "Alice Example" not in page

    assert save_recap(summit, "publish", team_note="Summit only", minutes_3="90").status_code == 302
    assert "Summit only" in text(cruz.get("/match/1"))
    assert "Summit only" not in text(alice.get("/match/1"))
    assert "Summit only" not in text(harbor.get("/match/1"))
    assert post(summit, SCORE, {"home_score": "9", "away_score": "9"}, form=RECAP).status_code == 404


def test_server_checks_coach_role_and_roster_team(app):
    harbor = sign_in(app, "harbor")
    summit = sign_in(app, "summit")
    alice = sign_in(app, "alice")
    assert alice.get(RECAP).status_code == 403
    assert post(alice, PLAYER, {"name": "Change"}, form="/my-team").status_code == 403
    assert summit.get(PLAYER).status_code == 404
    values = {"name": "New name", "position": "GK", "number": "1", "team_id": "2"}
    assert post(summit, PLAYER, values, form="/my-team").status_code == 404
    assert post(harbor, PLAYER, values).status_code == 302
    assert "New name" in text(harbor.get("/my-team"))
    assert "New name" not in text(summit.get("/my-team"))
    assert alice.get("/player/3").status_code == 404
    assert harbor.get("/compare?first=1&second=3").status_code == 404
    assert harbor.get("/compare?first=1&second=2").status_code == 200
    assert harbor.get("/team/2").status_code == 404


def test_public_fixture_creation_uses_coach_team(app):
    harbor = sign_in(app, "harbor")
    response = post(harbor, "/my-team/matches/new", {
        "team_id": "2", "opponent_team_id": "2", "external_opponent": "",
        "date": "2026-12-12", "season": "Winter 2026", "location": "Field 4",
    })
    assert response.status_code == 302
    with app.app_context():
        fixture = get_db().execute("SELECT team_id, opponent_team_id FROM matches WHERE id = 2").fetchone()
        assert tuple(fixture) == (1, 2)
    assert "Winter 2026" in text(app.test_client().get("/?team=2"))
    assert "Enter match stats" in text(sign_in(app, "summit").get("/my-team/matches/2/recap"))


def test_markup_escapes_and_apostrophes_are_saved_as_values(app):
    harbor = sign_in(app, "harbor")
    alice = sign_in(app, "alice")
    note = "<b>great save</b> at O’Brien's end"
    assert save_recap(harbor, "publish", team_note=note, feedback_1="<em>Keep going</em>").status_code == 302
    page = text(alice.get("/match/1"))
    assert "&lt;b&gt;great save&lt;/b&gt;" in page
    assert "&lt;em&gt;Keep going&lt;/em&gt;" in page
    assert "<b>great save</b>" not in page
    assert "<em>Keep going</em>" not in page
    with app.app_context():
        assert get_db().execute("SELECT team_note FROM recaps").fetchone()[0] == note


def test_invalid_or_stale_recaps_leave_published_data_intact(app):
    harbor = sign_in(app, "harbor")
    initial = harbor.get(RECAP)
    old_form = {"csrf_token": hidden(initial, "csrf_token"), "revision": hidden(initial, "revision")}
    assert save_recap(harbor, "publish", team_note="First version", goals_1="1").status_code == 302
    assert save_recap(harbor, "publish", team_note="Wrong roster", goals_3="1").status_code == 400
    assert save_recap(harbor, "publish", team_note="Invalid minutes", minutes_1="151").status_code == 400
    assert save_recap(harbor, "draft", team_note="Try reverting").status_code == 400
    assert harbor.post(RECAP, data={**old_form, "action": "publish", "team_note": "Stale"}).status_code == 400
    assert "First version" in text(sign_in(app, "alice").get("/match/1"))


def test_invitation_is_single_use_and_email_stays_in_own_profile(app):
    harbor = sign_in(app, "harbor")
    summit = sign_in(app, "summit")
    path = "/my-team/players/4/invite"
    assert post(summit, path, {}, form="/my-team").status_code == 404
    invite = post(harbor, path, {}, form="/my-team")
    code = re.search(r'<input type="text" value="([^"]+)" readonly', text(invite)).group(1)
    assert invite.headers["Cache-Control"] == "no-store"
    client = app.test_client()
    details = {"name": "Dana Example", "email": "dana@private.example",
               "password": PASSWORD, "code": code, "team_id": "2", "role": "coach"}
    assert post(client, "/register", details).status_code == 302
    assert "Harbor FC" in text(client.get("/my-team"))
    assert client.get(RECAP).status_code == 403
    assert "dana@private.example" in text(client.get("/profile"))
    assert "dana@private.example" not in text(harbor.get("/my-team"))
    assert "dana@private.example" not in text(harbor.get("/profile"))
    assert "dana@private.example" not in text(app.test_client().get("/"))
    retry = post(app.test_client(), "/register", {**details, "email": "retry@example.test"})
    assert "invalid or expired" in text(retry)


def test_archiving_revokes_an_existing_player_session(app):
    harbor = sign_in(app, "harbor")
    alice = sign_in(app, "alice")
    assert alice.get("/my-team").status_code == 200
    assert post(harbor, "/my-team/players/1/archive", {}, form=PLAYER).status_code == 302
    assert alice.get("/my-team").status_code == 302
    assert alice.get("/profile").status_code == 302
    assert "Alice Example" not in text(harbor.get("/my-team"))


def test_mutations_require_tokens_and_old_writes_are_retired(app):
    harbor = sign_in(app, "harbor")
    assert harbor.post(SCORE, data={"home_score": "2", "away_score": "1"}).status_code == 400
    assert harbor.get(SCORE).status_code == 405
    assert harbor.get("/delete_player/1").status_code == 404
    assert "Alice Example" in text(harbor.get("/my-team"))


def test_legacy_stats_migrate_to_drafts(tmp_path):
    path = tmp_path / "legacy.db"
    with sqlite3.connect(path) as db:
        db.executescript("""
            CREATE TABLE teams (id INTEGER PRIMARY KEY, name TEXT NOT NULL);
            CREATE TABLE players (id INTEGER PRIMARY KEY, team_id INTEGER, name TEXT,
                                  position TEXT, number INTEGER);
            CREATE TABLE matches (id INTEGER PRIMARY KEY, team_id INTEGER, opponent TEXT,
                                  date TEXT, season TEXT, location TEXT, team_score INTEGER,
                                  opponent_score INTEGER);
            CREATE TABLE player_stats (id INTEGER PRIMARY KEY, player_id INTEGER,
                                      match_id INTEGER, goals INTEGER, assists INTEGER, minutes INTEGER);
            INSERT INTO teams VALUES (1, 'Harbor FC'), (2, 'Summit FC');
            INSERT INTO players VALUES (1, 1, 'Alex', 'GK', 1), (2, 2, 'Sam', 'DF', 4);
            INSERT INTO matches VALUES (1, 1, 'Summit FC', '2026-10-01', 'Fall 2026', '', 2, 1);
            INSERT INTO player_stats VALUES (1, 1, 1, 0, 0, 45), (2, 1, 1, 0, 1, 90),
                                           (3, 2, 1, 0, 0, 85), (4, 1, 99, 0, 0, 60);
        """)
    config = {"DATABASE": str(path), "SECRET_KEY": "test-key", "TESTING": True}
    first = create_app(config)
    second = create_app(config)
    assert "Final score" in text(first.test_client().get("/match/1"))
    with second.app_context():
        db = get_db()
        assert db.execute("SELECT COUNT(*) FROM player_stats").fetchone()[0] == 4
        assert tuple(db.execute("SELECT team_id, published_at FROM recaps").fetchone()) == (1, None)
        assert tuple(db.execute("SELECT assists, minutes FROM recap_entries").fetchone()) == (1, 90)
        assert db.execute("SELECT COUNT(*) FROM recap_entries").fetchone()[0] == 1
