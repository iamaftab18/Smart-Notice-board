from flask import Blueprint, current_app, jsonify, redirect, render_template, url_for
from sqlalchemy import case

from app.models import Notice

board_bp = Blueprint("board", __name__)

_PRIORITY_RANK = case(
    (Notice.priority == "urgent", 3),
    (Notice.priority == "important", 2),
    else_=1,
)


@board_bp.route("/")
def index():
    return redirect(url_for("board.notice_board"))


@board_bp.route("/notice_board")
def notice_board():
    return render_template(
        "board/notice_board.html",
        poll_seconds=current_app.config["BOARD_POLL_SECONDS"],
        rotate_seconds=current_app.config["BOARD_ROTATE_SECONDS"],
    )


@board_bp.route("/api/notices/board")
def board_data():
    notices = (
        Notice.query.filter_by(is_published=True)
        .order_by(_PRIORITY_RANK.desc(), Notice.notice_date.desc(), Notice.updated_at.desc())
        .all()
    )
    return jsonify({"notices": [n.to_dict() for n in notices]})
