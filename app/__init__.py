import click
from flask import Flask

from app.config import Config, INSTANCE_DIR
from app.extensions import csrf, db, login_manager


def create_app(config_class=Config):
    INSTANCE_DIR.mkdir(parents=True, exist_ok=True)

    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_class)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    from app.models import Admin

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(Admin, int(user_id))

    from app.auth.routes import auth_bp
    from app.admin.routes import admin_bp
    from app.board.routes import board_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(board_bp)

    with app.app_context():
        db.create_all()
        _seed_default_admin(app)

    register_cli(app)

    return app


def _seed_default_admin(app):
    from app.models import Admin

    if Admin.query.first() is not None:
        return

    admin = Admin(name=app.config["ADMIN_NAME"], email=app.config["ADMIN_EMAIL"].strip().lower())
    admin.set_password(app.config["ADMIN_PASSWORD"])
    db.session.add(admin)
    db.session.commit()


def register_cli(app):
    @app.cli.command("seed-admin")
    @click.option("--name", default=None, help="Admin display name")
    @click.option("--email", default=None, help="Admin login email")
    @click.option("--password", default=None, help="Admin login password")
    def seed_admin(name, email, password):
        """Create or update the single admin account from config/env or flags."""
        from app.models import Admin

        name = name or app.config["ADMIN_NAME"]
        email = (email or app.config["ADMIN_EMAIL"]).strip().lower()
        password = password or app.config["ADMIN_PASSWORD"]

        if not email or not password:
            click.echo("An email and password are required.")
            return

        admin = Admin.query.filter_by(email=email).first()
        if admin:
            admin.name = name
            admin.set_password(password)
            click.echo(f"Updated existing admin: {email}")
        else:
            admin = Admin(name=name, email=email)
            admin.set_password(password)
            db.session.add(admin)
            click.echo(f"Created new admin: {email}")

        db.session.commit()
