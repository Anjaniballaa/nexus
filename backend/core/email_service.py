"""NEXUS — Email Service (Resend)
Uses Resend API over HTTPS — works on Render free tier.
Gmail SMTP (port 465) is blocked by Render on free plans.
"""
import resend
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
    # Guard: never send to placeholder emails
    if not to_email or "@github.noemail" in to_email:
        logger.warning(
            "email_skipped_placeholder_address",
            to=to_email,
            analysis_id=analysis_id,
        )
        return False

    if not settings.RESEND_API_KEY:
        logger.warning(
            "resend_not_configured",
            analysis_id=analysis_id,
            hint="Set RESEND_API_KEY in Render backend environment variables",
        )
        return False

    logger.info(
        "email_attempting_send",
        to=to_email,
        source=source_name,
        analysis_id=analysis_id,
    )

    try:
        resend.api_key = settings.RESEND_API_KEY
        resend.Emails.send({
            "from": settings.EMAIL_FROM,
            "to": [to_email],
            "subject": f"[NEXUS] Analysis complete: {source_name}",
            "html": html_body,
        })
        logger.info("email_sent_successfully", to=to_email, analysis_id=analysis_id)
        return True
    except Exception as e:
        logger.error("email_failed", error=str(e), analysis_id=analysis_id)
        return False