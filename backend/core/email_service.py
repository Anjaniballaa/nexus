import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings
import structlog

logger = structlog.get_logger()


def send_report_email(to_email: str, user_name: str, source_name: str, html_body: str, analysis_id: str) -> bool:
    """
    Send HTML analysis report email.
    Returns True on success, False on any failure.
    Never sends to placeholder emails created for GitHub users with no public email.
    """
    # Guard: never send to placeholder emails
    if not to_email or "@github.noemail" in to_email:
        logger.info(
            "email_skipped_no_real_address",
            to=to_email,
            analysis_id=analysis_id,
        )
        return False

    if not settings.GMAIL_USER or not settings.GMAIL_PASSWORD:
        logger.warning("gmail_not_configured")
        return False

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[NEXUS] Analysis complete: {source_name}"
        msg["From"]    = settings.GMAIL_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.GMAIL_USER, settings.GMAIL_PASSWORD)
            server.sendmail(settings.GMAIL_USER, to_email, msg.as_string())

        logger.info("email_sent", to=to_email, analysis_id=analysis_id)
        return True

    except Exception as e:
        logger.error("email_failed", error=str(e), to=to_email, analysis_id=analysis_id)
        return False