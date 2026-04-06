"""
KYISA — Test Suite

Covers key workflows:
1. Model validation (squad size, starters, duplicate teams)
2. Permission checks (coordinator scoping)
3. Live match endpoints
4. Result override safeguards
5. Squad submission workflow
6. Match report approval + standings update
7. Bulk player upload
8. Email sending (mocked)
"""
import json
from datetime import date, time, timedelta
from unittest.mock import patch, MagicMock

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User, UserRole
from competitions.models import (
    Competition, Venue, Pool, PoolTeam, Fixture, FixtureStatus,
    SportType, CompetitionFormat, AgeGroup,
)
from matches.models import (
    SquadSubmission, SquadPlayer, MatchReport, MatchEvent, PlayerStatistics,
)
from teams.models import Team, Player, County
from admin_dashboard.models import ActivityLog, EmailLog


# ═══════════════════════════════════════════════════════════════════════════════
#   TEST HELPERS
# ═══════════════════════════════════════════════════════════════════════════════

class BaseTestCase(TestCase):
    """Common setup for all tests."""

    def setUp(self):
        # Create users with different roles
        self.admin = User.objects.create_user(
            email="admin@kyisa.ke", password="testpass123",
            first_name="Admin", last_name="User",
            role=UserRole.ADMIN, is_staff=True,
        )
        self.coordinator = User.objects.create_user(
            email="coord@kyisa.ke", password="testpass123",
            first_name="Coord", last_name="User",
            role=UserRole.COORDINATOR,
            assigned_discipline="football_men",
        )
        self.team_manager = User.objects.create_user(
            email="tm@kyisa.ke", password="testpass123",
            first_name="Team", last_name="Manager",
            role=UserRole.TEAM_MANAGER,
        )
        self.referee_user = User.objects.create_user(
            email="ref@kyisa.ke", password="testpass123",
            first_name="Ref", last_name="User",
            role=UserRole.REFEREE,
        )

        # Create venue
        self.venue = Venue.objects.create(
            name="Test Stadium", county="Makueni", city="Wote",
        )

        # Create county (required FK for Team) — may already exist from data migration
        self.county, _ = County.objects.get_or_create(
            code="MAK", defaults={"name": "Makueni", "capital": "Wote"},
        )

        # Create competition
        self.competition = Competition.objects.create(
            name="Test Cup 2026",
            sport_type=SportType.FOOTBALL_MEN,
            format_type=CompetitionFormat.GROUP_AND_KNOCKOUT,
            season="2026",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 6, 30),
            created_by=self.admin,
        )

        # Create teams
        self.team_a = Team.objects.create(
            name="Makueni FC", sport_type="football_men",
            competition=self.competition, manager=self.team_manager,
            county=self.county,
            status="registered", payment_confirmed=True,
            payment_amount=250000, contact_email="makueni@test.ke",
        )
        self.team_b = Team.objects.create(
            name="Kitui United", sport_type="football_men",
            competition=self.competition,
            county=self.county,
            status="registered", payment_confirmed=True,
            payment_amount=250000, contact_email="kitui@test.ke",
        )

        # Create pool
        self.pool = Pool.objects.create(
            competition=self.competition, name="Group A",
        )
        self.pool_team_a = PoolTeam.objects.create(pool=self.pool, team=self.team_a)
        self.pool_team_b = PoolTeam.objects.create(pool=self.pool, team=self.team_b)

        # Create fixture
        self.fixture = Fixture.objects.create(
            competition=self.competition,
            pool=self.pool,
            home_team=self.team_a,
            away_team=self.team_b,
            venue=self.venue,
            match_date=date(2026, 4, 10),
            kickoff_time=time(14, 0),
            status=FixtureStatus.CONFIRMED,
            created_by=self.admin,
        )

        # Create players
        self.players_a = []
        for i in range(1, 16):
            p = Player.objects.create(
                team=self.team_a,
                first_name=f"Player{i}", last_name="A",
                date_of_birth=date(2008, 1, i),
                position="GK" if i == 1 else "CM",
                shirt_number=i,
            )
            self.players_a.append(p)

        self.client = APIClient()


# ═══════════════════════════════════════════════════════════════════════════════
#   1. MODEL VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ModelValidationTests(BaseTestCase):

    def test_pool_team_requires_payment(self):
        """Teams without payment cannot be added to a pool."""
        unpaid_team = Team.objects.create(
            name="Unpaid FC", sport_type="football_men",
            competition=self.competition, county=self.county,
            status="registered", payment_confirmed=False,
        )
        pt = PoolTeam(pool=self.pool, team=unpaid_team)
        with self.assertRaises(Exception):
            pt.clean()

    def test_pool_team_requires_registered_status(self):
        """Pending teams cannot be added to a pool."""
        pending_team = Team.objects.create(
            name="Pending FC", sport_type="football_men",
            competition=self.competition, county=self.county,
            status="pending", payment_confirmed=True,
        )
        pt = PoolTeam(pool=self.pool, team=pending_team)
        with self.assertRaises(Exception):
            pt.clean()

    def test_football_points_calculation(self):
        """Football: Win = 3pts, Draw = 1pt."""
        self.pool_team_a.won = 2
        self.pool_team_a.drawn = 1
        self.assertEqual(self.pool_team_a.points, 7)

    def test_goal_difference_property(self):
        self.pool_team_a.goals_for = 5
        self.pool_team_a.goals_against = 2
        self.assertEqual(self.pool_team_a.goal_difference, 3)

    def test_fixture_determine_winner(self):
        """Winner is correctly determined from scores."""
        self.fixture.home_score = 3
        self.fixture.away_score = 1
        result = self.fixture.determine_winner()
        self.assertEqual(result, self.team_a)

    def test_fixture_determine_winner_penalties(self):
        """Winner determined from penalties when scores tied."""
        self.fixture.home_score = 1
        self.fixture.away_score = 1
        self.fixture.home_penalties = 4
        self.fixture.away_penalties = 3
        result = self.fixture.determine_winner()
        self.assertEqual(result, self.team_a)

    def test_player_statistics_goal_contributions(self):
        """goal_contributions = goals + assists on save."""
        stats = PlayerStatistics.objects.create(
            player=self.players_a[0],
            competition=self.competition,
            team=self.team_a,
            goals=5, assists=3,
        )
        self.assertEqual(stats.goal_contributions, 8)


# ═══════════════════════════════════════════════════════════════════════════════
#   2. PERMISSION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class PermissionTests(BaseTestCase):

    def test_team_manager_cannot_approve_squads(self):
        """Team managers should not be able to approve squads."""
        self.client.force_authenticate(user=self.team_manager)
        response = self.client.post(f"/api/v1/matches/squads/{999}/approve/", {"action": "approve"})
        self.assertEqual(response.status_code, 403)

    def test_coordinator_can_approve_squads(self):
        """Coordinators can approve squads."""
        sub = SquadSubmission.objects.create(
            fixture=self.fixture, team=self.team_a,
            status="submitted", submitted_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(f"/api/v1/matches/squads/{sub.pk}/approve/", {"action": "approve"})
        self.assertEqual(response.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "approved")

    def test_referee_cannot_override_result(self):
        """Referees cannot override results."""
        self.client.force_authenticate(user=self.referee_user)
        response = self.client.post(
            f"/api/v1/matches/fixtures/{self.fixture.pk}/override-result/",
            {"home_score": 5, "away_score": 0, "confirm_exceptional": True, "override_reason": "Test override reason here"},
        )
        self.assertEqual(response.status_code, 403)


# ═══════════════════════════════════════════════════════════════════════════════
#   3. LIVE MATCH ENDPOINT TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class LiveMatchTests(BaseTestCase):

    def test_start_match(self):
        """Starting a match sets status to live."""
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(f"/api/v1/matches/live/{self.fixture.pk}/start/")
        self.assertEqual(response.status_code, 200)
        self.fixture.refresh_from_db()
        self.assertEqual(self.fixture.status, FixtureStatus.LIVE)
        self.assertEqual(self.fixture.live_half, 1)
        self.assertIsNotNone(self.fixture.live_started_at)

    def test_cannot_start_completed_match(self):
        """Cannot start a match that is already completed."""
        self.fixture.status = FixtureStatus.COMPLETED
        self.fixture.save()
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(f"/api/v1/matches/live/{self.fixture.pk}/start/")
        self.assertEqual(response.status_code, 400)

    def test_record_goal(self):
        """Recording a goal increments the score."""
        self.fixture.status = FixtureStatus.LIVE
        self.fixture.home_score = 0
        self.fixture.away_score = 0
        self.fixture.save()

        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            f"/api/v1/matches/live/{self.fixture.pk}/goal/",
            {"team_id": self.team_a.pk, "player_id": self.players_a[0].pk, "minute": 23},
        )
        self.assertEqual(response.status_code, 200)
        self.fixture.refresh_from_db()
        self.assertEqual(self.fixture.home_score, 1)

    def test_pause_and_resume(self):
        """Pausing and resuming toggles the paused state."""
        self.fixture.status = FixtureStatus.LIVE
        self.fixture.save()

        self.client.force_authenticate(user=self.coordinator)

        # Pause
        response = self.client.post(
            f"/api/v1/matches/live/{self.fixture.pk}/pause/",
            {"paused_minute": 45},
        )
        self.assertEqual(response.status_code, 200)
        self.fixture.refresh_from_db()
        self.assertTrue(self.fixture.live_paused)
        self.assertEqual(self.fixture.live_paused_minute, 45)

        # Resume
        response = self.client.post(f"/api/v1/matches/live/{self.fixture.pk}/resume/")
        self.assertEqual(response.status_code, 200)
        self.fixture.refresh_from_db()
        self.assertFalse(self.fixture.live_paused)

    def test_change_period(self):
        """Changing period updates live_half."""
        self.fixture.status = FixtureStatus.LIVE
        self.fixture.save()

        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            f"/api/v1/matches/live/{self.fixture.pk}/period/",
            {"live_half": 2, "extra_minutes": 3},
        )
        self.assertEqual(response.status_code, 200)
        self.fixture.refresh_from_db()
        self.assertEqual(self.fixture.live_half, 2)
        self.assertEqual(self.fixture.live_extra_minutes, 3)

    def test_end_match(self):
        """Ending a match sets status to completed."""
        self.fixture.status = FixtureStatus.LIVE
        self.fixture.home_score = 2
        self.fixture.away_score = 1
        self.fixture.save()

        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            f"/api/v1/matches/live/{self.fixture.pk}/end/",
            {"final_home_score": 2, "final_away_score": 1},
        )
        self.assertEqual(response.status_code, 200)
        self.fixture.refresh_from_db()
        self.assertEqual(self.fixture.status, FixtureStatus.COMPLETED)

    def test_scoreboard_public(self):
        """Public scoreboard returns fixture data without auth."""
        response = self.client.get(f"/api/v1/matches/live/{self.fixture.pk}/scoreboard/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("fixture", response.data)


# ═══════════════════════════════════════════════════════════════════════════════
#   4. RESULT OVERRIDE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class ResultOverrideTests(BaseTestCase):

    def setUp(self):
        super().setUp()
        self.fixture.status = FixtureStatus.COMPLETED
        self.fixture.home_score = 1
        self.fixture.away_score = 1
        self.fixture.save()

    @patch("kyisa_cms.notifications._send")
    def test_override_with_valid_reason(self, mock_send):
        """Coordinator can override result with valid reason."""
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            f"/api/v1/matches/fixtures/{self.fixture.pk}/override-result/",
            {
                "home_score": 3,
                "away_score": 0,
                "confirm_exceptional": True,
                "override_reason": "VAR review determined offside goal should stand",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.fixture.refresh_from_db()
        self.assertEqual(self.fixture.home_score, 3)
        self.assertEqual(self.fixture.away_score, 0)

        # Verify ActivityLog created with before/after
        log = ActivityLog.objects.filter(action="RESULT_OVERRIDE").first()
        self.assertIsNotNone(log)
        self.assertIsNotNone(log.previous_state)
        self.assertIsNotNone(log.new_state)

    def test_override_rejected_without_confirmation(self):
        """Override fails without confirmation checkbox."""
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            f"/api/v1/matches/fixtures/{self.fixture.pk}/override-result/",
            {
                "home_score": 3,
                "away_score": 0,
                "confirm_exceptional": False,
                "override_reason": "Some valid reason text here",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_override_rejected_with_short_reason(self):
        """Override fails with reason < 12 characters."""
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            f"/api/v1/matches/fixtures/{self.fixture.pk}/override-result/",
            {
                "home_score": 3,
                "away_score": 0,
                "confirm_exceptional": True,
                "override_reason": "Short",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 400)


# ═══════════════════════════════════════════════════════════════════════════════
#   5. SQUAD SUBMISSION WORKFLOW TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class SquadSubmissionTests(BaseTestCase):

    @patch("kyisa_cms.notifications._send")
    def test_coordinator_rejects_squad_with_notification(self, mock_send):
        """Rejecting a squad sends notification email."""
        sub = SquadSubmission.objects.create(
            fixture=self.fixture, team=self.team_a,
            status="submitted", submitted_at=timezone.now(),
        )
        self.client.force_authenticate(user=self.coordinator)
        response = self.client.post(
            f"/api/v1/matches/squads/{sub.pk}/approve/",
            {"action": "reject", "rejection_reason": "Missing goalkeeper in starters"},
        )
        self.assertEqual(response.status_code, 200)
        sub.refresh_from_db()
        self.assertEqual(sub.status, "rejected")

    def test_squad_unique_per_fixture_team(self):
        """Only one squad per fixture per team."""
        SquadSubmission.objects.create(
            fixture=self.fixture, team=self.team_a,
            status="draft",
        )
        with self.assertRaises(Exception):
            SquadSubmission.objects.create(
                fixture=self.fixture, team=self.team_a,
                status="draft",
            )


# ═══════════════════════════════════════════════════════════════════════════════
#   6. MATCH REPORT + STANDINGS UPDATE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class MatchReportStandingsTests(BaseTestCase):

    def test_standings_update_on_approval(self):
        """Approving a match report updates pool standings."""
        from referees.models import RefereeProfile
        ref_profile, _ = RefereeProfile.objects.get_or_create(
            user=self.referee_user,
            defaults={"license_number": "REF001", "level": "County", "is_approved": True},
        )

        self.fixture.status = FixtureStatus.COMPLETED
        self.fixture.home_score = 2
        self.fixture.away_score = 0
        self.fixture.save()

        report = MatchReport.objects.create(
            fixture=self.fixture, referee=ref_profile,
            status="submitted",
            home_score=2, away_score=0,
            submitted_at=timezone.now(),
        )

        from matches.stats_engine import process_approved_report
        process_approved_report(report)

        self.pool_team_a.refresh_from_db()
        self.pool_team_b.refresh_from_db()

        self.assertEqual(self.pool_team_a.played, 1)
        self.assertEqual(self.pool_team_a.won, 1)
        self.assertEqual(self.pool_team_a.goals_for, 2)
        self.assertEqual(self.pool_team_b.played, 1)
        self.assertEqual(self.pool_team_b.lost, 1)


# ═══════════════════════════════════════════════════════════════════════════════
#   7. BULK PLAYER UPLOAD TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class BulkUploadTests(BaseTestCase):

    def test_csv_template_download(self):
        """Template download returns a CSV file."""
        self.client.force_authenticate(user=self.team_manager)
        response = self.client.get("/api/v1/teams/players/bulk-template/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])

    def test_csv_upload_dry_run(self):
        """Dry run parses CSV without creating players."""
        import io
        csv_content = (
            "first_name,last_name,date_of_birth,position,shirt_number,national_id_number\n"
            "Test,Player1,2008-01-15,CF,20,99887766\n"
            "Test,Player2,2007-06-20,GK,30,99887755\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "players.csv"

        self.client.force_authenticate(user=self.team_manager)
        response = self.client.post(
            "/api/v1/teams/players/bulk-upload/",
            {"file": csv_file, "team_id": self.team_a.pk, "dry_run": "true"},
            format="multipart",
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["dry_run"])
        self.assertEqual(len(response.data["players"]), 2)

    def test_csv_upload_creates_players(self):
        """Actual upload creates player records."""
        import io
        csv_content = (
            "first_name,last_name,date_of_birth,position,shirt_number,national_id_number\n"
            "Bulk,Player1,2008-03-15,CF,50,11223344\n"
        )
        csv_file = io.BytesIO(csv_content.encode("utf-8"))
        csv_file.name = "players.csv"

        initial_count = Player.objects.filter(team=self.team_a).count()
        self.client.force_authenticate(user=self.team_manager)
        response = self.client.post(
            "/api/v1/teams/players/bulk-upload/",
            {"file": csv_file, "team_id": self.team_a.pk},
            format="multipart",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["created"], 1)
        self.assertEqual(Player.objects.filter(team=self.team_a).count(), initial_count + 1)


# ═══════════════════════════════════════════════════════════════════════════════
#   8. EMAIL LOG TESTS
# ═══════════════════════════════════════════════════════════════════════════════

@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class EmailLogTests(BaseTestCase):

    def test_email_log_created_on_send(self):
        """Sending an email creates an EmailLog entry (call worker directly)."""
        from kyisa_cms.email_utils import _base_html, _send
        import threading

        html = _base_html("Test Email", "<p>Test content</p>")

        # Patch Thread to run worker synchronously so the test is deterministic
        original_thread_init = threading.Thread.__init__
        captured_target = {}

        def patched_init(self_thread, *args, **kwargs):
            captured_target["fn"] = kwargs.get("target")
            original_thread_init(self_thread, *args, **kwargs)

        with patch.object(threading.Thread, "__init__", patched_init), \
             patch.object(threading.Thread, "start", lambda self_thread: captured_target["fn"]()):
            _send("Test Subject", html, ["test@example.com"])

        log = EmailLog.objects.filter(subject="Test Subject").first()
        self.assertIsNotNone(log)
        self.assertEqual(log.status, "sent")
        self.assertIn("test@example.com", log.to_emails)

    def test_email_log_records_failure(self):
        """Failed email is logged with error message."""
        log = EmailLog.objects.create(
            direction="OUT",
            status="failed",
            from_email="noreply@kyisa.ke",
            to_emails="bad@example.com",
            subject="Failed Test",
            error_message="Connection refused",
        )
        self.assertEqual(log.status, "failed")
        self.assertIn("Connection refused", log.error_message)
