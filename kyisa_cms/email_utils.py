"""
KYISA — Core Email Utilities

Background-threaded email delivery with:
- Branded HTML templates
- Retry logic (3 attempts, exponential backoff)
- EmailLog audit trail
- Never blocks web requests
"""
import logging
import threading
import time
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════════
#   BRANDED HTML TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════════

def _base_html(title, body_content):
    """Wrap email content in the branded KYISA two-column template."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"></head>
<body style="margin:0; padding:0; background:#f4f6f9; font-family: Arial, Helvetica, sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f9;">
<tr><td align="center" style="padding: 24px 0;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0"
       style="max-width:640px; width:100%; border:1px solid #e0e0e0; border-radius:8px; overflow:hidden; background:#fff;">
  <!-- Logo Bar -->
  <tr>
    <td style="background: linear-gradient(135deg, #004D1A 0%, #006B23 100%); color:#fff; padding:20px 30px; text-align:center;">
      <h1 style="margin:0; font-size:20px; letter-spacing:1px;">KENYA YOUTH INTERCOUNTY SPORTS ASSOCIATION</h1>
      <p style="margin:4px 0 0; font-size:12px; opacity:0.8;">KYISA &bull; 11th Edition</p>
    </td>
  </tr>
  <!-- Title Bar -->
  <tr>
    <td style="background:#003311; color:#fff; padding:14px 30px;">
      <h2 style="margin:0; font-size:16px; font-weight:600;">{title}</h2>
    </td>
  </tr>
  <!-- Body -->
  <tr>
    <td style="padding:28px 30px; color:#333; font-size:14px; line-height:1.6;">
      {body_content}
    </td>
  </tr>
  <!-- Footer -->
  <tr>
    <td style="background:#f8f9fa; padding:20px 30px; border-top:1px solid #e0e0e0; text-align:center; font-size:11px; color:#888;">
      <p style="margin:0;">Kenya Youth Inter-Secondary School Association (KYISA)</p>
      <p style="margin:4px 0 0;">Email: admin@kyisa.org &bull; Website: www.kyisa.org</p>
      <p style="margin:4px 0 0;">&copy; {timezone.now().year} KYISA. All rights reserved.</p>
      <p style="margin:8px 0 0; font-size:10px; color:#aaa;">
        This is an automated message. Please do not reply directly to this email.
      </p>
    </td>
  </tr>
</table>
</td></tr>
</table>
</body>
</html>"""


def _info_box(items):
    """
    Build an info box block from a list of (label, value) tuples.
    Example: [("Match", "Group A"), ("Date", "5 April 2025, 14:00")]
    """
    rows = ""
    for label, value in items:
        rows += f"""<tr>
          <td style="padding:6px 0; border-bottom:1px solid #e8eef3; font-weight:bold; color:#555; width:40%; vertical-align:top;">{label}</td>
          <td style="padding:6px 0; border-bottom:1px solid #e8eef3; color:#333;">{value}</td>
        </tr>"""
    return f"""<div style="background:#eef6ff; border-left:4px solid #2196F3; padding:16px; border-radius:4px; margin:16px 0;">
    <table style="width:100%; border-collapse:collapse;">{rows}</table>
    </div>"""


def _action_button(url, label, color="#004D1A"):
    """Build a CTA button for emails."""
    return f"""<div style="text-align:center; margin:24px 0;">
    <a href="{url}" style="display:inline-block; padding:12px 28px; background:{color}; color:#fff;
       text-decoration:none; border-radius:6px; font-weight:bold; font-size:14px;">{label}</a>
    </div>"""


# ═══════════════════════════════════════════════════════════════════════════════
#   CORE SEND FUNCTION (BACKGROUND THREADED)
# ═══════════════════════════════════════════════════════════════════════════════

def _send(subject, html_body, recipients, fail_silently=True, sent_by=None, cc=None, bcc=None):
    """
    Send an HTML email on a background daemon thread.
    - Filters empty/None recipients
    - Retries 3 times with exponential backoff (5s, 10s)
    - Logs to EmailLog model
    - Never blocks the calling thread
    """
    recipients = [e for e in (recipients or []) if e]
    if not recipients:
        logger.warning("No valid recipients for email: %s", subject)
        return

    def _worker():
        from admin_dashboard.models import EmailLog

        plain_body = strip_tags(html_body)
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "KYISA Administration <admin@kyisa.org>")
        max_retries = 3
        last_error = ""

        for attempt in range(1, max_retries + 1):
            try:
                msg = EmailMultiAlternatives(
                    subject=subject,
                    body=plain_body,
                    from_email=from_email,
                    to=recipients,
                    cc=cc or [],
                    bcc=bcc or [],
                )
                msg.attach_alternative(html_body, "text/html")
                msg.send(fail_silently=False)

                # Log success
                EmailLog.objects.create(
                    direction="OUT",
                    status="sent",
                    from_email=from_email,
                    to_emails=", ".join(recipients),
                    cc_emails=", ".join(cc or []),
                    bcc_emails=", ".join(bcc or []),
                    subject=subject,
                    body_text=plain_body[:5000],
                    body_html=html_body[:10000],
                    sent_by=sent_by,
                    message_id=getattr(msg, "extra_headers", {}).get("Message-ID", ""),
                )
                logger.info("Email sent: '%s' to %s (attempt %d)", subject, recipients, attempt)
                return

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Email attempt %d/%d failed for '%s': %s",
                    attempt, max_retries, subject, exc,
                )
                if attempt < max_retries:
                    time.sleep(5 * attempt)  # 5s, 10s backoff

        # All retries failed — log failure
        try:
            EmailLog.objects.create(
                direction="OUT",
                status="failed",
                from_email=from_email,
                to_emails=", ".join(recipients),
                cc_emails=", ".join(cc or []),
                bcc_emails=", ".join(bcc or []),
                subject=subject,
                body_text=plain_body[:5000],
                body_html=html_body[:10000],
                sent_by=sent_by,
                error_message=last_error[:2000],
            )
        except Exception:
            pass
        logger.error("Email permanently failed after %d attempts: '%s' — %s", max_retries, subject, last_error)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()


# ═══════════════════════════════════════════════════════════════════════════════
#   HELPER: GET RECIPIENTS BY ROLE
# ═══════════════════════════════════════════════════════════════════════════════

def _get_coordinators_for_discipline(discipline):
    """Return email list of coordinators assigned to a discipline."""
    from accounts.models import User, UserRole
    emails = list(
        User.objects.filter(
            is_active=True,
            assigned_discipline=discipline,
            role__in=[
                UserRole.COORDINATOR,
                UserRole.SOCCER_COORDINATOR,
                UserRole.HANDBALL_COORDINATOR,
                UserRole.BASKETBALL_COORDINATOR,
                UserRole.VOLLEYBALL_COORDINATOR,
            ],
        ).values_list("email", flat=True)
    )
    return [e for e in emails if e]


def _get_team_manager_email(team):
    """Return the team manager's email."""
    if team.manager and team.manager.email:
        return team.manager.email
    return team.contact_email or None


def _get_referee_email(referee_profile):
    """Return the referee user's email."""
    if referee_profile and referee_profile.user:
        return referee_profile.user.email
    return None
