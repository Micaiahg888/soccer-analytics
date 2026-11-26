import hashlib
import re
import secrets
import sqlite3
import time

import click
from flask import Blueprint, abort, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash

from .database import get_db
from .forms import field
from .permissions import load_member, roster_player, team_access

bp = Blueprint("accounts", __name__, cli_group="accounts")
INVITE_LIFETIME = 48 * 60 * 60


@bp.before_app_request
def identify():
    g.member = load_member(session.get("account_id"))


def email_address(value):
    email = value.strip().casefold()
    if len(email) > 254 or not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email):
        raise ValueError("Enter a valid email address.")
    return email


def password_hash(password):
    if not 12 <= len(password) <= 128:
        raise ValueError("Use a password between 12 and 128 characters.")
    return generate_password_hash(password)


def token_hash(code):
    return hashlib.sha256(code.encode()).hexdigest()


@bp.route("/login", methods=("GET", "POST"))
def login():
    error = None
    if request.method == "POST":
        email = request.form.get("email", "").strip().casefold()
        password = request.form.get("password", "")
        account = None
        if len(email) <= 254 and len(password) <= 128:
            account = get_db().execute(
                "SELECT id, password_hash FROM accounts WHERE email = ?", (email,)
            ).fetchone()
        if account and check_password_hash(account["password_hash"], password):
            if load_member(account["id"]):
                session.clear()
                session["account_id"] = account["id"]
                return redirect(url_for("team_space.home"))
        error = "Email or password was incorrect."
    return render_template("account.html", mode="login", error=error)


@bp.post("/logout")
def logout():
    session.clear()
    return redirect(url_for("league.feed"))


@bp.route("/register", methods=("GET", "POST"))
def register():
    error = None
    if request.method == "POST":
        db = get_db()
        try:
            code = field("code", "Invitation code", 128)
            name = field("name", "Display name", 80)
            email = email_address(request.form.get("email", ""))
            hashed = password_hash(request.form.get("password", ""))
            with db:
                db.execute("BEGIN IMMEDIATE")
                invitation = db.execute(
                    """SELECT i.team_id, i.player_id FROM invitations i
                       JOIN players p ON p.id = i.player_id AND p.team_id = i.team_id
                       WHERE i.token_hash = ? AND i.expires_at > ? AND p.archived = 0""",
                    (token_hash(code), int(time.time())),
                ).fetchone()
                if invitation is None:
                    raise ValueError("This invitation is invalid or expired. Ask your coach for a new one.")
                account_id = db.execute(
                    "INSERT INTO accounts (display_name, email, password_hash) VALUES (?, ?, ?)",
                    (name, email, hashed),
                ).lastrowid
                db.execute(
                    "INSERT INTO memberships (account_id, team_id, role, player_id) VALUES (?, ?, 'player', ?)",
                    (account_id, invitation["team_id"], invitation["player_id"]),
                )
                db.execute("DELETE FROM invitations WHERE token_hash = ?", (token_hash(code),))
            session.clear()
            session["account_id"] = account_id
            return redirect(url_for("team_space.home"))
        except ValueError as problem:
            error = str(problem)
        except sqlite3.IntegrityError:
            error = "We couldn’t complete registration. Check your details or ask your coach for help."
    return render_template("account.html", mode="register", error=error)


@bp.get("/profile")
@team_access()
def profile():
    account = get_db().execute(
        "SELECT display_name, email FROM accounts WHERE id = ?", (session["account_id"],)
    ).fetchone()
    return render_template("account.html", mode="profile", account=account)


@bp.post("/my-team/players/<int(min=1,max=9223372036854775807):player_id>/invite")
@team_access(coach=True)
def invite(player_id):
    db = get_db()
    with db:
        db.execute("BEGIN IMMEDIATE")
        player = roster_player(player_id)
        if player["archived"] or db.execute(
            "SELECT 1 FROM memberships WHERE player_id = ?", (player_id,)
        ).fetchone():
            abort(409)
        code = secrets.token_urlsafe(24)
        db.execute(
            """INSERT INTO invitations (token_hash, team_id, player_id, expires_at)
               VALUES (?, ?, ?, ?)
               ON CONFLICT(player_id) DO UPDATE SET
                   token_hash = excluded.token_hash, expires_at = excluded.expires_at""",
            (token_hash(code), player["team_id"], player_id, int(time.time()) + INVITE_LIFETIME),
        )
    return render_template("account.html", mode="invite", code=code, player=player)


@bp.cli.command("add-team")
@click.argument("name")
def add_team(name):
    name = name.strip()
    if not 1 <= len(name) <= 100:
        raise click.ClickException("Use a team name between 1 and 100 characters.")
    db = get_db()
    with db:
        team_id = db.execute("INSERT INTO teams (name) VALUES (?)", (name,)).lastrowid
    click.echo(f"Created team {team_id}: {name}")


@bp.cli.command("teams")
def list_teams():
    for team in get_db().execute("SELECT id, name FROM teams ORDER BY id"):
        click.echo(f"{team['id']}: {team['name']}")


@bp.cli.command("add-coach")
@click.argument("team_id", type=int)
@click.option("--name", prompt="Coach display name")
@click.option("--email", prompt=True)
@click.password_option()
def add_coach(team_id, name, email, password):
    db = get_db()
    if db.execute("SELECT id FROM teams WHERE id = ?", (team_id,)).fetchone() is None:
        raise click.ClickException("Team does not exist. Run accounts teams to list teams.")
    name = name.strip()
    if not 1 <= len(name) <= 80:
        raise click.ClickException("Use a display name between 1 and 80 characters.")
    try:
        email = email_address(email)
        hashed = password_hash(password)
        with db:
            account_id = db.execute(
                "INSERT INTO accounts (display_name, email, password_hash) VALUES (?, ?, ?)",
                (name, email, hashed),
            ).lastrowid
            db.execute("INSERT INTO memberships VALUES (?, ?, 'coach', NULL)", (account_id, team_id))
    except ValueError as error:
        raise click.ClickException(str(error)) from error
    except sqlite3.IntegrityError as error:
        raise click.ClickException("A coach could not be created with those details.") from error
    click.echo(f"Created coach for team {team_id}.")
