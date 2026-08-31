import smtplib
import ssl
from email.message import EmailMessage


def send_notice_alert(app, notice_data, recipients):
    """Email a published notice to a list of student addresses.

    Runs best-effort: any failure is logged and swallowed so a broken SMTP
    config never blocks publishing a notice.
    """
    recipients = [email for email in recipients if email]
    if not recipients:
        return

    host = app.config.get("SMTP_HOST")
    if not host:
        app.logger.info("SMTP_HOST not configured; skipping notice email alerts.")
        return

    port = app.config["SMTP_PORT"]
    username = app.config.get("SMTP_USERNAME")
    password = app.config.get("SMTP_PASSWORD")
    mail_from = app.config.get("MAIL_FROM") or username or "notice-board@localhost"

    subject = f"[Notice Board] {notice_data['title']}"
    body = (
        f"{notice_data['title']}\n"
        f"Date: {notice_data['notice_date_display']}\n\n"
        f"{notice_data['description']}"
    )

    try:
        with smtplib.SMTP(host, port, timeout=10) as server:
            if app.config.get("SMTP_USE_TLS"):
                server.starttls(context=ssl.create_default_context())
            if username and password:
                server.login(username, password)
            for email in recipients:
                message = EmailMessage()
                message["Subject"] = subject
                message["From"] = mail_from
                message["To"] = email
                message.set_content(body)
                server.send_message(message)
    except Exception:
        app.logger.exception("Failed to send notice email alerts.")
