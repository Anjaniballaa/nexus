import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from core.config import settings
import structlog

logger = structlog.get_logger()


def send_report_email(
    to_email: str,
    user_name: str,
    source_name: str,
    html_body: str,
    analysis_id: str,
) -> bool:
    """
    Send HTML analysis report email.
    Returns True on success, False on any failure.
    Logs the exact reason for every skip/failure so you can diagnose in Render logs.
    """

    # Guard 1: never send to placeholder emails
    if not to_email:
        logger.warning("email_skipped_no_email", analysis_id=analysis_id)
        return False

    if "@github.noemail" in to_email:
        logger.warning(
            "email_skipped_placeholder_address",
            to=to_email,
            analysis_id=analysis_id,
            hint="User has no real email — log out and sign in with Google to fix",
        )
        return False

    # Guard 2: SMTP credentials must be configured
    if not settings.GMAIL_USER:
        logger.warning(
            "email_skipped_no_gmail_user",
            analysis_id=analysis_id,
            hint="Set GMAIL_USER env var in Render backend environment",
        )
        return False

    if not settings.GMAIL_PASSWORD:
        logger.warning(
            "email_skipped_no_gmail_password",
            analysis_id=analysis_id,
            hint="Set GMAIL_PASSWORD env var (use Gmail App Password, not account password)",
        )
        return False

    # Guard 3: html body must not be empty
    if not html_body or len(html_body) < 50:
        logger.warning(
            "email_skipped_empty_body",
            analysis_id=analysis_id,
            body_len=len(html_body) if html_body else 0,
        )
        return False

    logger.info(
        "email_attempting_send",
        to=to_email,
        source=source_name,
        analysis_id=analysis_id,
        gmail_user=settings.GMAIL_USER,
    )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[NEXUS] Analysis complete: {source_name}"
        msg["From"]    = settings.GMAIL_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(settings.GMAIL_USER, settings.GMAIL_PASSWORD)
            server.sendmail(settings.GMAIL_USER, to_email, msg.as_string())

        logger.info(
            "email_sent_successfully",
            to=to_email,
            analysis_id=analysis_id,
        )
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "email_failed_auth",
            error=str(e),
            analysis_id=analysis_id,
            hint="Gmail rejected login — use an App Password from myaccount.google.com/security, not your account password",
        )
        return False

    except smtplib.SMTPException as e:
        logger.error(
            "email_failed_smtp",
            error=str(e),
            analysis_id=analysis_id,
        )
        return False

    except Exception as e:
        logger.error(
            "email_failed_unexpected",
            error=str(e),
            analysis_id=analysis_id,
        )
        return False