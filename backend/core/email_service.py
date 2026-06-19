"""NEXUS — Email Service (Gmail SMTP via port 587 TLS)
Port 465 (SSL) is blocked by Render free tier.
Port 587 (TLS/STARTTLS) may work — trying this first.
If this also fails with Network unreachable, switch to Resend.
"""
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
    if not to_email or "@github.noemail" in to_email:
        logger.warning("email_skipped_placeholder_address", to=to_email, analysis_id=analysis_id)
        return False

    if not settings.GMAIL_USER or not settings.GMAIL_PASSWORD:
        logger.warning("gmail_not_configured", analysis_id=analysis_id)
        return False

    logger.info(
        "email_attempting_send",
        to=to_email,
        source=source_name,
        analysis_id=analysis_id,
        gmail_user=settings.GMAIL_USER,
        port=587,
    )

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"[NEXUS] Analysis complete: {source_name}"
        msg["From"]    = settings.GMAIL_USER
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        # Port 587 with STARTTLS — different from port 465 SSL
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(settings.GMAIL_USER, settings.GMAIL_PASSWORD)
            server.sendmail(settings.GMAIL_USER, to_email, msg.as_string())

        logger.info("email_sent_successfully", to=to_email, analysis_id=analysis_id)
        return True

    except smtplib.SMTPAuthenticationError as e:
        logger.error(
            "email_failed_auth",
            error=str(e),
            analysis_id=analysis_id,
            hint="Use Gmail App Password not account password",
        )
        return False

    except OSError as e:
        logger.error(
            "email_failed_network",
            error=str(e),
            analysis_id=analysis_id,
            hint="Port 587 also blocked by Render — switch to Resend",
        )
        return False

    except Exception as e:
        logger.error("email_failed_unexpected", error=str(e), analysis_id=analysis_id)
        return False