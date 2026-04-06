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

def notify_account_created(user, temporary_password=None):
    """Send welcome email with login credentials to a newly created user."""
    body = f"""
    <p>Dear <strong>{user.get_full_name()}</strong>,</p>
    <p>Welcome to the Kenya Youth Intercounty Sports Association (KYISA) system.
    Your account has been created with the following details:</p>
    {_info_box([
        ("Email", user.email),
        ("Role", user.get_role_display() if hasattr(user, 'get_role_display') else user.role),
        ("Temporary Password", f"<code>{temporary_password}</code>" if temporary_password else "<em>Set by administrator</em>"),
    ])}
    <p>Please log in and change your password immediately.</p>
    {_action_button(f"{SITE_URL}/portal/login/", "Log In to KYISA")}
    <p style="color:#888; font-size:12px;">If you did not expect this email, please contact KYISA administration.</p>
    """
    html = _base_html(f"Welcome to KYISA — {user.get_role_display() if hasattr(user, 'get_role_display') else user.role}", body)
    _send(
        subject=f"Welcome to KYISA — {user.get_role_display() if hasattr(user, 'get_role_display') else user.role}",
        html_body=html,
        recipients=[user.email],
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  2. PLAYER REGISTERED
# ═══════════════════════════════════════════════════════════════════════════════

def notify_player_registered(player, team):
    """Notify verification officer and subcounty officer about new player."""
    from accounts.models import User, UserRole
    recipients = list(
        User.objects.filter(
            is_active=True,
            role=UserRole.VERIFICATION_OFFICER,
        ).values_list("email", flat=True)
    )
    # Add county sports director if one exists for the team's county
    county_directors = list(
        User.objects.filter(
            is_active=True,
            role=UserRole.COUNTY_SPORTS_DIRECTOR,
        ).values_list("email", flat=True)
    )
    recipients.extend(county_directors)

    body = f"""
    <p>A new player has been registered and requires document verification.</p>
    {_info_box([
        ("Player", player.get_full_name()),
        ("Team", team.name),
        ("Sport", team.get_sport_type_display() if hasattr(team, 'get_sport_type_display') else team.sport_type),
        ("ID Number", player.national_id_number or "Not provided"),
        ("Documents", "Uploaded" if player.documents_uploaded else "Pending upload"),
    ])}
    <p>Please review the player's documents in the verification portal.</p>
    {_action_button(f"{SITE_URL}/portal/verification/players/", "Review Player Documents")}
    """
    html = _base_html("New Player Registered — Verification Required", body)
    _send(
        subject=f"Player Registered — {player.get_full_name()} ({team.name})",
        html_body=html,
        recipients=recipients,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  3. FIXTURE CREATED / UPDATED
# ═══════════════════════════════════════════════════════════════════════════════

def notify_fixture_created(fixture):
    """Notify both team managers when a fixture is created or rescheduled."""
    recipients = []
    for team in [fixture.home_team, fixture.away_team]:
        email = _get_team_manager_email(team)
        if email:
            recipients.append(email)

    venue_name = fixture.venue.name if fixture.venue else "TBC"
    body = f"""
    <p>A fixture has been scheduled for your team.</p>
    {_info_box([
        ("Competition", fixture.competition.name),
        ("Match", f"{fixture.home_team.name} vs {fixture.away_team.name}"),
        ("Date", fixture.match_date.strftime("%d %B %Y")),
        ("Kick-off", fixture.kickoff_time.strftime("%H:%M") if fixture.kickoff_time else "TBC"),
        ("Venue", venue_name),
        ("Pool/Round", fixture.pool.name if fixture.pool else fixture.get_knockout_round_display() if fixture.knockout_round else "—"),
    ])}
    <p>Please ensure your squad list is submitted at least <strong>4 hours before kick-off</strong>.</p>
    {_action_button(f"{SITE_URL}/portal/team-manager/fixtures/", "View Fixtures")}
    """
    html = _base_html("Fixture Scheduled", body)
    _send(
        subject=f"Fixture — {fixture.home_team.name} vs {fixture.away_team.name} on {fixture.match_date.strftime('%d %b %Y')}",
        html_body=html,
        recipients=recipients,
    )


def notify_fixture_updated(fixture, changes_description=""):
    """Notify team managers when a fixture is rescheduled or updated."""
    recipients = []
    for team in [fixture.home_team, fixture.away_team]:
        email = _get_team_manager_email(team)
        if email:
            recipients.append(email)

    venue_name = fixture.venue.name if fixture.venue else "TBC"
    body = f"""
    <p>A fixture involving your team has been <strong>updated</strong>.</p>
    {f"<p><strong>Changes:</strong> {changes_description}</p>" if changes_description else ""}
    {_info_box([
        ("Competition", fixture.competition.name),
        ("Match", f"{fixture.home_team.name} vs {fixture.away_team.name}"),
        ("New Date", fixture.match_date.strftime("%d %B %Y")),
        ("Kick-off", fixture.kickoff_time.strftime("%H:%M") if fixture.kickoff_time else "TBC"),
        ("Venue", venue_name),
    ])}
    <p>Please review and ensure your squad list is up to date.</p>
    {_action_button(f"{SITE_URL}/portal/team-manager/fixtures/", "View Fixtures")}
    """
    html = _base_html("Fixture Updated", body)
    _send(
        subject=f"Fixture Updated — {fixture.home_team.name} vs {fixture.away_team.name} on {fixture.match_date.strftime('%d %b %Y')}",
        html_body=html,
        recipients=recipients,
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  4. SQUAD SUBMITTED
# ═══════════════════════════════════════════════════════════════════════════════

def notify_squad_submitted(submission):
    """Notify coordinator when a team manager submits a squad."""
    fixture = submission.fixture
    team = submission.team
    discipline = fixture.competition.sport_type
    recipients = _get_coordinators_for_discipline(discipline)

    starters = submission.squad_players.filter(is_starter=True).count()
    subs = submission.squad_players.filter(is_starter=False).count()
    total = starters + subs

    deadline_str = ""
    try:
        deadline = fixture.squad_deadline
        deadline_str = deadline.strftime("%d %B %Y, %H:%M")
    except Exception:
        deadline_str = "N/A"

    body = f"""
    <p>A squad list has been submitted and requires your review.</p>
    {_info_box([
        ("Team", team.name),
        ("Match", f"{fixture.home_team.name} vs {fixture.away_team.name}"),
        ("Competition", fixture.competition.name),
        ("Match Date", fixture.match_date.strftime("%d %B %Y")),
        ("Kick-off", fixture.kickoff_time.strftime("%H:%M") if fixture.kickoff_time else "TBC"),
        ("Squad Size", f"{total} players ({starters} starters, {subs} subs)"),
        ("Formation", submission.formation or "—"),
        ("Kit", submission.get_kit_choice_display()),
    ])}
    <div style="background:#fff3cd; border:1px solid #ffeaa7; padding:12px; border-radius:4px; margin:12px 0;">
        <strong>⏰ Approval Reminder:</strong> Must be approved by 2 hours before kick-off.
    </div>
    {_action_button(f"{SITE_URL}/portal/coordinator/squads/", "Review Squad")}
    """
    html = _base_html("Squad Submitted — Review Required", body)
    _send(
        subject=f"Squad Submitted — {team.name} for {fixture.home_team.name} vs {fixture.away_team.name}",
        html_body=html,
        recipients=recipients,
    )


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
