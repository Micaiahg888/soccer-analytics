import os
import secrets
from pathlib import Path

from flask import Flask, render_template
from flask_wtf.csrf import CSRFProtect

from . import accounts, database, league, team_space


def local_secret(instance_path):
    path = Path(instance_path) / "session-key"
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(path, "x", opener=_private_file) as file:
            file.write(secrets.token_hex(32))
    except FileExistsError:
        pass
    return path.read_text().strip()


def _private_file(path, flags):
    return os.open(path, flags, 0o600)


def create_app(config=None):
    root = Path(__file__).resolve().parent.parent
    app = Flask(
        __name__, template_folder=str(root / "templates"),
        static_folder=str(root / "static"), instance_path=str(root / "instance"),
    )
    app.config.from_mapping(
        DATABASE=os.environ.get("SOCCER_DATABASE", str(root / "soccer.db")),
        SECRET_KEY=os.environ.get("SOCCER_SECRET_KEY"),
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        SESSION_COOKIE_SECURE=os.environ.get("SOCCER_HTTPS") == "1",
        MAX_CONTENT_LENGTH=2 * 1024 * 1024,
        MAX_FORM_MEMORY_SIZE=1024 * 1024,
        MAX_FORM_PARTS=1500,
    )
    if config:
        app.config.update(config)
    if not app.config["SECRET_KEY"]:
        app.config["SECRET_KEY"] = local_secret(app.instance_path)

    database.init_app(app)
    CSRFProtect(app)
    app.register_blueprint(accounts.bp)
    app.register_blueprint(league.bp)
    app.register_blueprint(team_space.bp)

    @app.after_request
    def security_headers(response):
        if response.mimetype == "text/html":
            response.headers["Cache-Control"] = "no-store"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; object-src 'none'; base-uri 'none'; "
                "frame-ancestors 'none'; form-action 'self'"
            )
            response.headers["Referrer-Policy"] = "no-referrer"
            response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.errorhandler(400)
    @app.errorhandler(403)
    @app.errorhandler(404)
    @app.errorhandler(409)
    def error_page(error):
        return render_template("error.html", status=error.code, title=error.name), error.code

    return app
