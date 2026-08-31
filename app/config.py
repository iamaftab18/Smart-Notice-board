import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
INSTANCE_DIR = BASE_DIR / "instance"


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")

    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{INSTANCE_DIR / 'notice_board.db'}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    ADMIN_NAME = os.environ.get("ADMIN_NAME", "College Admin")
    ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "admin@noticeboard.local")
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "Board@2026")

    BOARD_POLL_SECONDS = int(os.environ.get("BOARD_POLL_SECONDS", 10))
    BOARD_ROTATE_SECONDS = int(os.environ.get("BOARD_ROTATE_SECONDS", 12))

    SMTP_HOST = os.environ.get("SMTP_HOST", "")
    SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
    SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "1") == "1"
    SMTP_USERNAME = os.environ.get("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    MAIL_FROM = os.environ.get("MAIL_FROM", "")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    REMEMBER_COOKIE_DURATION = 60 * 60 * 12  # 12 hours
