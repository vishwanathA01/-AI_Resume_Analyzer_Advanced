import os
from pathlib import Path
import click
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

load_dotenv()
db = SQLAlchemy()

def create_app():
    app = Flask(__name__, static_folder="static", template_folder="templates")
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-change-me")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///resume_ai.sqlite3"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["MAX_CONTENT_LENGTH"] = int(os.getenv("MAX_UPLOAD_MB", "5")) * 1024 * 1024
    app.config["UPLOAD_FOLDER"] = os.getenv("UPLOAD_DIR", "uploads")
    app.config["SEMANTIC_MATCHING"] = os.getenv("SEMANTIC_MATCHING", "false").lower() == "true"

    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
    CORS(app)

    db.init_app(app)

    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    from app.routes.workspace import workspace_bp
    from app.routes.resources import resources_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(workspace_bp)
    app.register_blueprint(resources_bp)

    from app import models  # noqa: F401

    with app.app_context():
        db.create_all()

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.password_option(confirmation_prompt=True)
    def create_admin(name, email, password):
        from app.models import User

        name = name.strip()
        email = email.strip().lower()
        if not name or "@" not in email:
            raise click.ClickException("A name and valid email address are required.")
        if len(password) < 8:
            raise click.ClickException("The administrator password must be at least 8 characters.")
        if User.query.filter_by(email=email).first():
            raise click.ClickException("An account with that email already exists.")

        user = User(name=name, email=email, role="admin")
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"Administrator account created for {email}.")

    return app
