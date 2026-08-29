from datetime import datetime

from flask import Blueprint, jsonify, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.models import PRIORITY_LEVELS, Notice

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("")
@login_required
def dashboard():
    notices = Notice.query.order_by(Notice.notice_date.desc(), Notice.created_at.desc()).all()
    return render_template("admin/dashboard.html", notices=notices, priorities=PRIORITY_LEVELS)


def _parse_notice_payload(data):
    """Validate incoming notice fields. Returns (fields_dict, error_message)."""
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    date_raw = (data.get("notice_date") or "").strip()
    priority = (data.get("priority") or "normal").strip().lower()

    if not title:
        return None, "Title is required."
    if len(title) > 200:
        return None, "Title must be 200 characters or fewer."
    if not description:
        return None, "Description is required."
    if not date_raw:
        return None, "Notice date is required."
    if priority not in PRIORITY_LEVELS:
        return None, "Invalid priority level."

    try:
        notice_date = datetime.strptime(date_raw, "%Y-%m-%d").date()
    except ValueError:
        return None, "Notice date must be a valid date."

    return {
        "title": title,
        "description": description,
        "notice_date": notice_date,
        "priority": priority,
    }, None


@admin_bp.route("/notices", methods=["POST"])
@login_required
def create_notice():
    fields, error = _parse_notice_payload(request.get_json(silent=True) or request.form)
    if error:
        return jsonify({"ok": False, "error": error}), 400

    notice = Notice(**fields, created_by=current_user, is_published=False)
    db.session.add(notice)
    db.session.commit()

    return jsonify({"ok": True, "notice": notice.to_dict()}), 201


@admin_bp.route("/notices/<int:notice_id>", methods=["GET"])
@login_required
def get_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        return jsonify({"ok": False, "error": "Notice not found."}), 404
    return jsonify({"ok": True, "notice": notice.to_dict()})


@admin_bp.route("/notices/<int:notice_id>", methods=["PUT"])
@login_required
def update_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        return jsonify({"ok": False, "error": "Notice not found."}), 404

    fields, error = _parse_notice_payload(request.get_json(silent=True) or request.form)
    if error:
        return jsonify({"ok": False, "error": error}), 400

    notice.title = fields["title"]
    notice.description = fields["description"]
    notice.notice_date = fields["notice_date"]
    notice.priority = fields["priority"]
    db.session.commit()

    return jsonify({"ok": True, "notice": notice.to_dict()})


@admin_bp.route("/notices/<int:notice_id>", methods=["DELETE"])
@login_required
def delete_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        return jsonify({"ok": False, "error": "Notice not found."}), 404

    db.session.delete(notice)
    db.session.commit()

    return jsonify({"ok": True})


@admin_bp.route("/notices/<int:notice_id>/publish", methods=["POST"])
@login_required
def publish_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        return jsonify({"ok": False, "error": "Notice not found."}), 404

    notice.is_published = True
    db.session.commit()
    return jsonify({"ok": True, "notice": notice.to_dict()})


@admin_bp.route("/notices/<int:notice_id>/unpublish", methods=["POST"])
@login_required
def unpublish_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        return jsonify({"ok": False, "error": "Notice not found."}), 404

    notice.is_published = False
    db.session.commit()
    return jsonify({"ok": True, "notice": notice.to_dict()})
