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
    """Wrap email content in the branded KYISA template — logo header, title bar, body, footer."""
    year = timezone.now().year
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="color-scheme" content="light">
<meta name="supported-color-schemes" content="light">
<!--[if mso]><noscript><xml><o:OfficeDocumentSettings><o:PixelsPerInch>96</o:PixelsPerInch></o:OfficeDocumentSettings></xml></noscript><![endif]-->
</head>
<body style="margin:0;padding:0;background:#f0f2f5;font-family:'Segoe UI',Roboto,Arial,Helvetica,sans-serif;-webkit-font-smoothing:antialiased;">

<!-- Outer wrapper -->
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f0f2f5;">
<tr><td align="center" style="padding:32px 16px;">

<!-- Email card -->
<table role="presentation" width="600" cellpadding="0" cellspacing="0"
       style="max-width:600px;width:100%;border-radius:16px;overflow:hidden;background:#ffffff;box-shadow:0 4px 24px rgba(0,0,0,.08);">

  <!-- ═══ LOGO HEADER ═══ -->
  <tr>
    <td style="background:linear-gradient(135deg,#003311 0%,#004D1A 50%,#006B23 100%);padding:28px 32px;text-align:center;">
      <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto;">
        <tr>
          <td style="vertical-align:middle;padding-right:14px;">
            <img src="https://kyisa.org/static/img/kyisa_logo_official.jpg"
                 alt="KYISA" width="52" height="52"
                 style="width:52px;height:52px;border-radius:50%;border:2px solid rgba(255,255,255,.25);display:block;">
          </td>
          <td style="vertical-align:middle;text-align:left;">
            <p style="margin:0;font-size:18px;font-weight:800;color:#ffffff;letter-spacing:1.5px;line-height:1.2;">KYISA</p>
            <p style="margin:2px 0 0;font-size:10px;font-weight:500;color:rgba(255,255,255,.65);letter-spacing:2px;text-transform:uppercase;">Kenya Youth Intercounty Sports Association</p>
          </td>
        </tr>
      </table>
    </td>
  </tr>

  <!-- ═══ TITLE BAR ═══ -->
  <tr>
    <td style="background:#002208;padding:14px 32px;">
      <h2 style="margin:0;font-size:15px;font-weight:700;color:#ffffff;letter-spacing:.5px;">{title}</h2>
    </td>
  </tr>

  <!-- ═══ GREEN ACCENT LINE ═══ -->
  <tr>
    <td style="height:3px;background:linear-gradient(90deg,#4CAF50,#81C784,#4CAF50);font-size:0;line-height:0;">&nbsp;</td>
  </tr>

  <!-- ═══ BODY CONTENT ═══ -->
  <tr>
    <td style="padding:32px 32px 28px;color:#333333;font-size:14px;line-height:1.7;">
      {body_content}
    </td>
  </tr>

  <!-- ═══ DIVIDER ═══ -->
  <tr>
    <td style="padding:0 32px;">
      <div style="height:1px;background:linear-gradient(90deg,transparent,#e0e0e0,transparent);"></div>
    </td>
  </tr>

  <!-- ═══ FOOTER ═══ -->
  <tr>
    <td style="padding:24px 32px;text-align:center;">
      <p style="margin:0;font-size:12px;font-weight:600;color:#555;letter-spacing:.5px;">Kenya Youth Intercounty Sports Association</p>
      <p style="margin:6px 0 0;font-size:11px;color:#999;">
        <a href="mailto:admin@kyisa.org" style="color:#4CAF50;text-decoration:none;">admin@kyisa.org</a>
        &nbsp;&bull;&nbsp;
        <a href="https://kyisa.org" style="color:#4CAF50;text-decoration:none;">www.kyisa.org</a>
      </p>
      <p style="margin:12px 0 0;font-size:10px;color:#bbb;">&copy; {year} KYISA. All rights reserved.</p>
      <p style="margin:4px 0 0;font-size:9px;color:#ccc;">This is an automated message. Please do not reply directly.</p>
    </td>
  </tr>

</table>
<!-- /Email card -->

</td></tr>
</table>
<!-- /Outer wrapper -->

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
          <td style="padding:10px 14px;border-bottom:1px solid #e8eef3;font-weight:700;color:#333;width:38%;vertical-align:top;font-size:13px;">{label}</td>
          <td style="padding:10px 14px;border-bottom:1px solid #e8eef3;color:#555;font-size:13px;">{value}</td>
        </tr>"""
    return f"""<div style="background:#f4f9f4;border-left:4px solid #4CAF50;border-radius:8px;margin:20px 0;overflow:hidden;">
    <table style="width:100%; border-collapse:collapse;">{rows}</table>
    </div>"""


def _action_button(url, label, color="#004D1A"):
    """Build a CTA button for emails."""
    return f"""<div style="text-align:center;margin:28px 0;">
    <a href="{url}" style="display:inline-block;padding:14px 36px;background:{color};color:#ffffff;
       text-decoration:none;border-radius:8px;font-weight:700;font-size:14px;letter-spacing:.5px;
       box-shadow:0 2px 8px rgba(0,77,26,.25);">{label}</a>
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
