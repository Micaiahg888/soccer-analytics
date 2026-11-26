from flask import request

from .database import get_db
from .forms import field, number


def visible_recap(match_id, member):
    db = get_db()
    coach = member["role"] == "coach"
    recap = db.execute(
        """SELECT id, team_note, published_at FROM recaps
           WHERE match_id = ? AND team_id = ? AND (published_at IS NOT NULL OR ?)""",
        (match_id, member["team_id"], coach),
    ).fetchone()
    if recap is None:
        return None
    entries = db.execute(
        """SELECT p.name, e.minutes, e.goals, e.assists,
                  CASE WHEN ? OR e.player_id = ? THEN e.feedback ELSE '' END AS feedback
           FROM recap_entries e JOIN players p ON p.id = e.player_id AND p.team_id = ?
           WHERE e.recap_id = ? AND
                 (e.minutes IS NOT NULL OR e.goals IS NOT NULL OR e.assists IS NOT NULL
                  OR ? OR e.player_id = ?)
           ORDER BY p.name, p.id""",
        (coach, member["player_id"], member["team_id"], recap["id"], coach, member["player_id"]),
    ).fetchall()
    return {"record": recap, "entries": entries}


def edit_state(match_id, team_id):
    db = get_db()
    recap = db.execute(
        "SELECT id, team_note, published_at, revision FROM recaps WHERE match_id = ? AND team_id = ?",
        (match_id, team_id),
    ).fetchone()
    rows = db.execute(
        """SELECT p.id, p.name, p.number, p.position, e.minutes, e.goals, e.assists, e.feedback
           FROM players p LEFT JOIN recap_entries e ON e.player_id = p.id AND e.recap_id = ?
           WHERE p.team_id = ? AND (p.archived = 0 OR e.recap_id IS NOT NULL)
           ORDER BY p.number, p.name, p.id""",
        (recap["id"] if recap else None, team_id),
    ).fetchall()
    return recap, rows


def save_recap(match_id, team_id):
    action = request.form.get("action")
    if action not in ("draft", "publish"):
        raise ValueError("Choose Save draft or Publish recap.")
    note = field("team_note", "Team note", 4000, optional=True)
    submitted_revision = request.form.get("revision", type=int)
    db = get_db()
    with db:
        db.execute("BEGIN IMMEDIATE")
        recap, roster = edit_state(match_id, team_id)
        current_revision = recap["revision"] if recap else 0
        if submitted_revision != current_revision:
            raise ValueError("This recap changed in another session. Copy your edits, reload, and try again.")
        if action == "draft" and recap and recap["published_at"]:
            raise ValueError("This recap is already published. Use Publish updates to change it.")
        valid_fields = {
            f"{prefix}_{player['id']}"
            for player in roster for prefix in ("minutes", "goals", "assists", "feedback")
        }
        if any(
            name.startswith(("minutes_", "goals_", "assists_", "feedback_")) and name not in valid_fields
            for name in request.form
        ):
            raise ValueError("The roster changed or contains a player outside this team. Reload the page and try again.")
        entries = []
        for player in roster:
            player_id = player["id"]
            minutes = number(f"minutes_{player_id}", "Minutes", 150, optional=True)
            goals = number(f"goals_{player_id}", "Goals", 99, optional=True)
            assists = number(f"assists_{player_id}", "Assists", 99, optional=True)
            feedback = field(f"feedback_{player_id}", "Individual feedback", 2000, optional=True)
            if any(value is not None for value in (minutes, goals, assists)) or feedback:
                entries.append((player_id, minutes, goals, assists, feedback))

        recap_id = db.execute(
            """INSERT INTO recaps (match_id, team_id, team_note, published_at)
               VALUES (?, ?, ?, CASE WHEN ? THEN CURRENT_TIMESTAMP END)
               ON CONFLICT(match_id, team_id) DO UPDATE SET
                   team_note = excluded.team_note,
                   revision = recaps.revision + 1,
                   published_at = COALESCE(recaps.published_at, excluded.published_at)
               RETURNING id""",
            (match_id, team_id, note, action == "publish"),
        ).fetchone()["id"]
        db.execute("DELETE FROM recap_entries WHERE recap_id = ?", (recap_id,))
        db.executemany(
            """INSERT INTO recap_entries (recap_id, player_id, minutes, goals, assists, feedback)
               VALUES (?, ?, ?, ?, ?, ?)""",
            [(recap_id, *entry) for entry in entries],
        )
    return action
