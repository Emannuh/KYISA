"""
KYISA — System-Wide Email Notifications

All email triggers defined in the spec:
1. Account Created (welcome email)
2. Player Registered
3. Fixture Created/Updated
4. Squad Submitted
5. Squad Rejected
6. Match Report Submitted
7. Match Report Returned
"""
import logging
from django.conf import settings
from kyisa_cms.email_utils import (
    _send, _base_html, _info_box, _action_button,
    _get_coordinators_for_discipline, _get_team_manager_email, _get_referee_email,
)

logger = logging.getLogger(__name__)

SITE_URL = getattr(settings, "SITE_URL", "https://kyisa.ke")


# ═══════════════════════════════════════════════════════════════════════════════
#  1. ACCOUNT CREATED
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  2. PLAYER REGISTERED
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  3. FIXTURE CREATED / UPDATED
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  4. SQUAD SUBMITTED
# ═══════════════════════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════════════════════
#  5. SQUAD REJECTED
# ═══════════════════════════════════════════════════════════════════════════════

def notify_squad_rejected(submission):
    """Notify team manager when their squad is rejected."""
    fixture = submission.fixture
    team = submission.team
    email = _get_team_manager_email(team)
    if not email:
        return

    body = f"""
    <p>Your squad list has been <strong style="color:#dc3545;">rejected</strong> and needs revision.</p>
    {_info_box([
        ("Team", team.name),
        ("Match", f"{fixture.home_team.name} vs {fixture.away_team.name}"),
        ("Match Date", fixture.match_date.strftime("%d %B %Y")),
        ("Rejection Reason", submission.rejection_reason or "No reason provided"),
    ])}
    <p>Please revise and resubmit your squad list before the deadline.</p>
    {_action_button(f"{SITE_URL}/portal/team-manager/squads/", "Resubmit Squad")}
    """
    html = _base_html("Squad Rejected — Resubmission Required", body)
    _send(
        subject=f"Squad Rejected — {team.name} for {fixture.home_team.name} vs {fixture.away_team.name}",
        html_body=html,
        recipients=[email],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  6. MATCH REPORT SUBMITTED
# ═══════════════════════════════════════════════════════════════════════════════

def notify_match_report_submitted(report):
    """Notify coordinator when a referee submits a match report."""
    fixture = report.fixture
    discipline = fixture.competition.sport_type
    recipients = _get_coordinators_for_discipline(discipline)

    body = f"""
    <p>A match report has been submitted and requires your review.</p>
    {_info_box([
        ("Match", f"{fixture.home_team.name} vs {fixture.away_team.name}"),
        ("Competition", fixture.competition.name),
        ("Date", fixture.match_date.strftime("%d %B %Y")),
        ("Final Score", f"{report.home_score} — {report.away_score}"),
        ("Referee", report.referee.user.get_full_name() if report.referee and report.referee.user else "Unknown"),
        ("Yellow Cards", f"Home: {report.home_yellow_cards} | Away: {report.away_yellow_cards}"),
        ("Red Cards", f"Home: {report.home_red_cards} | Away: {report.away_red_cards}"),
    ])}
    {_action_button(f"{SITE_URL}/portal/coordinator/match-reports/", "Review Match Report")}
    """
    html = _base_html("Match Report Submitted — Review Required", body)
    _send(
        subject=f"Match Report Submitted — {fixture.home_team.name} {report.home_score}-{report.away_score} {fixture.away_team.name}",
        html_body=html,
        recipients=recipients,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  7. MATCH REPORT RETURNED
# ═══════════════════════════════════════════════════════════════════════════════

def notify_match_report_returned(report):
    """Notify referee when their match report is returned for revision."""
    referee_email = _get_referee_email(report.referee)
    if not referee_email:
        return

    fixture = report.fixture
    body = f"""
    <p>Your match report has been <strong style="color:#dc3545;">returned for revision</strong>.</p>
    {_info_box([
        ("Match", f"{fixture.home_team.name} vs {fixture.away_team.name}"),
        ("Competition", fixture.competition.name),
        ("Date", fixture.match_date.strftime("%d %B %Y")),
        ("Reviewer Notes", report.reviewer_notes or "No notes provided"),
    ])}
    <p>Please review the notes above, correct the report, and resubmit.</p>
    {_action_button(f"{SITE_URL}/portal/referee/match-reports/", "Edit Match Report")}
    """
    html = _base_html("Match Report Returned — Revision Required", body)
    _send(
        subject=f"Match Report Returned — {fixture.home_team.name} vs {fixture.away_team.name}",
        html_body=html,
        recipients=[referee_email],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  RESULT OVERRIDE NOTIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

def notify_result_override(fixture, override_reason, changed_by):
    """Notify team managers when a result is overridden by coordinator."""
    recipients = []
    for team in [fixture.home_team, fixture.away_team]:
        email = _get_team_manager_email(team)
        if email:
            recipients.append(email)

    body = f"""
    <p>The result of a match involving your team has been <strong>officially overridden</strong>.</p>
    {_info_box([
        ("Match", f"{fixture.home_team.name} vs {fixture.away_team.name}"),
        ("Competition", fixture.competition.name),
        ("New Score", f"{fixture.home_score} — {fixture.away_score}"),
        ("Override Reason", override_reason),
        ("Changed By", changed_by.get_full_name() if changed_by else "Administrator"),
    ])}
    <p>If you have concerns regarding this change, please contact KYISA administration
    or file an appeal through the portal.</p>
    """
    html = _base_html("Match Result Override", body)
    _send(
        subject=f"Result Override — {fixture.home_team.name} vs {fixture.away_team.name}",
        html_body=html,
        recipients=recipients,
    )
