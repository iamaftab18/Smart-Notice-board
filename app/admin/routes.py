import threading
from datetime import datetime

from flask import Blueprint, current_app, jsonify, render_template, request
from flask_login import current_user, login_required

from app.extensions import db
from app.mailer import send_notice_alert
from app.models import PRIORITY_LEVELS, Notice, Student
from app.tts import is_available as tts_is_available
from app.tts import speak as tts_speak

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

    notice_data = notice.to_dict()
    recipients = [s.email for s in Student.query.all()]
    app_obj = current_app._get_current_object()
    threading.Thread(target=_send_alerts_in_background, args=(app_obj, notice_data, recipients), daemon=True).start()

    return jsonify({"ok": True, "notice": notice_data})


def _send_alerts_in_background(app_obj, notice_data, recipients):
    with app_obj.app_context():
        send_notice_alert(app_obj, notice_data, recipients)


@admin_bp.route("/notices/<int:notice_id>/unpublish", methods=["POST"])
@login_required
def unpublish_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        return jsonify({"ok": False, "error": "Notice not found."}), 404

    notice.is_published = False
    db.session.commit()
    return jsonify({"ok": True, "notice": notice.to_dict()})


@admin_bp.route("/notices/<int:notice_id>/announce", methods=["POST"])
@login_required
def announce_notice(notice_id):
    notice = db.session.get(Notice, notice_id)
    if not notice:
        return jsonify({"ok": False, "error": "Notice not found."}), 404

    if not tts_is_available():
        return jsonify({
            "ok": False,
            "error": "Text-to-speech is not installed on this device. Run: sudo apt install espeak-ng",
        }), 500

    text = (
        f"{notice.title}. "
        f"Date: {notice.notice_date.strftime('%d %B %Y')}. "
        f"{notice.description}"
    )
    app_obj = current_app._get_current_object()
    threading.Thread(target=_speak_in_background, args=(app_obj, text), daemon=True).start()

    return jsonify({"ok": True})


def _speak_in_background(app_obj, text):
    ok, error = tts_speak(text)
    if not ok:
        with app_obj.app_context():
            app_obj.logger.warning("Announce failed: %s", error)


# ---------- Students ----------


@admin_bp.route("/students")
@login_required
def students_page():
    students = Student.query.order_by(Student.name.asc()).all()
    return render_template("admin/students.html", students=students)


def _parse_student_payload(data):
    name = (data.get("name") or "").strip()
    enrollment_no = (data.get("enrollment_no") or "").strip()
    email = (data.get("email") or "").strip().lower()

    if not name:
        return None, "Name is required."
    if not enrollment_no:
        return None, "Enrollment number is required."
    if not email or "@" not in email:
        return None, "Enter a valid email address."

    return {"name": name, "enrollment_no": enrollment_no, "email": email}, None


@admin_bp.route("/students", methods=["POST"])
@login_required
def create_student():
    fields, error = _parse_student_payload(request.get_json(silent=True) or request.form)
    if error:
        return jsonify({"ok": False, "error": error}), 400

    if Student.query.filter_by(enrollment_no=fields["enrollment_no"]).first():
        return jsonify({"ok": False, "error": "A student with this enrollment number already exists."}), 400

    student = Student(**fields)
    db.session.add(student)
    db.session.commit()

    return jsonify({"ok": True, "student": student.to_dict()}), 201


@admin_bp.route("/students/<int:student_id>", methods=["DELETE"])
@login_required
def delete_student(student_id):
    student = db.session.get(Student, student_id)
    if not student:
        return jsonify({"ok": False, "error": "Student not found."}), 404

    db.session.delete(student)
    db.session.commit()

    return jsonify({"ok": True})
