"""
KYISA Matches — Models (Squad Submissions, Match Reports, Results)
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator


class SquadStatus(models.TextChoices):
    DRAFT     = "draft",     "Draft"
    SUBMITTED = "submitted", "Submitted"
    APPROVED  = "approved",  "Approved by Referee"
    REJECTED  = "rejected",  "Rejected — Needs Changes"


class SquadSubmission(models.Model):
    """
    Team Manager submits squad; Referee approves it before kick-off.
    Must be submitted at least 4 hours before kick-off (enforced in serializer).
    """
    fixture     = models.ForeignKey(
        "competitions.Fixture", on_delete=models.CASCADE,
        related_name="squads"
    )
    team        = models.ForeignKey(
        "teams.Team", on_delete=models.CASCADE,
        related_name="squad_submissions"
    )
    status      = models.CharField(max_length=20, choices=SquadStatus.choices, default=SquadStatus.DRAFT)
    submitted_at = models.DateTimeField(null=True, blank=True)
    reviewed_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="squads_reviewed"
    )
    reviewed_at  = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)

    class Meta:
        unique_together = ["fixture", "team"]
        verbose_name = "Squad Submission"

    def __str__(self):
        return f"{self.team} squad for {self.fixture}"


class SquadPlayer(models.Model):
    """Individual player entry in a squad submission."""
    submission   = models.ForeignKey(SquadSubmission, on_delete=models.CASCADE, related_name="squad_players")
    player       = models.ForeignKey("teams.Player", on_delete=models.CASCADE)
    is_starter   = models.BooleanField(default=True)
    shirt_number = models.PositiveIntegerField()  # May differ from regular number

    class Meta:
        unique_together = ["submission", "player"]
        ordering        = ["-is_starter", "shirt_number"]

    def __str__(self):
        role = "Starter" if self.is_starter else "Sub"
        return f"#{self.shirt_number} {self.player.get_full_name()} ({role})"


class MatchReportStatus(models.TextChoices):
    DRAFT    = "draft",    "Draft"
    SUBMITTED = "submitted", "Submitted"
    APPROVED = "approved", "Approved"
    RETURNED = "returned", "Returned for Revision"


class MatchReport(models.Model):
    """
    Referee submits match report after the game.
    Referee Manager reviews and approves.
    """
    fixture      = models.OneToOneField(
        "competitions.Fixture", on_delete=models.CASCADE,
        related_name="match_report"
    )
    referee      = models.ForeignKey(
        "referees.RefereeProfile", on_delete=models.SET_NULL, null=True,
        related_name="match_reports"
    )
    status       = models.CharField(max_length=20, choices=MatchReportStatus.choices, default=MatchReportStatus.DRAFT)

    # Final Score
    home_score   = models.PositiveIntegerField()
    away_score   = models.PositiveIntegerField()

    # Disciplinary
    home_yellow_cards = models.PositiveIntegerField(default=0)
    away_yellow_cards = models.PositiveIntegerField(default=0)
    home_red_cards    = models.PositiveIntegerField(default=0)
    away_red_cards    = models.PositiveIntegerField(default=0)

    # Report details
    match_duration  = models.PositiveIntegerField(default=90, help_text="Actual minutes played")
    added_time_ht   = models.PositiveIntegerField(default=0, help_text="Added time 1st half (mins)")
    added_time_ft   = models.PositiveIntegerField(default=0, help_text="Added time 2nd half (mins)")
    pitch_condition = models.CharField(max_length=20, choices=[
        ("excellent","Excellent"),("good","Good"),("fair","Fair"),("poor","Poor")
    ], default="good")
    weather         = models.CharField(max_length=100, blank=True)
    attendance      = models.PositiveIntegerField(null=True, blank=True)

    referee_notes   = models.TextField(blank=True, help_text="Incidents, injuries, misconduct details")
    is_abandoned    = models.BooleanField(default=False)
    abandonment_reason = models.TextField(blank=True)

    # Review
    reviewed_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="match_reports_reviewed"
    )
    reviewed_at   = models.DateTimeField(null=True, blank=True)
    reviewer_notes = models.TextField(blank=True)

    submitted_at  = models.DateTimeField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Match Report"
        ordering     = ["-submitted_at"]

    def __str__(self):
        return f"Report: {self.fixture}"


class MatchEvent(models.Model):
    """Goals, assists, cards, substitutions recorded in the match report."""
    EVENT_TYPES = [
        ("goal",    "Goal"),
        ("assist",  "Assist"),
        ("yellow",  "Yellow Card"),
        ("red",     "Red Card"),
        ("second_yellow", "Second Yellow (Red)"),
        ("sub_on",  "Substitution On"),
        ("sub_off", "Substitution Off"),
        ("injury",  "Injury"),
        ("penalty", "Penalty Goal"),
        ("penalty_miss", "Penalty Missed"),
        ("og",      "Own Goal"),
    ]
    report     = models.ForeignKey(MatchReport, on_delete=models.CASCADE, related_name="events")
    team       = models.ForeignKey("teams.Team", on_delete=models.CASCADE)
    player     = models.ForeignKey("teams.Player", on_delete=models.SET_NULL, null=True, blank=True)
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    minute     = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(130)])
    notes      = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["minute"]

    def __str__(self):
        return f"{self.event_type} @ {self.minute}' — {self.player}"


# ═══════════════════════════════════════════════════════════════════════════════
#   PLAYER STATISTICS (aggregated from match events)
# ═══════════════════════════════════════════════════════════════════════════════

class PlayerStatistics(models.Model):
    """
    Aggregated player statistics for a specific competition.
    Auto-updated when a match report is approved by the Competition Manager.
    """
    player       = models.ForeignKey("teams.Player", on_delete=models.CASCADE, related_name="statistics")
    competition  = models.ForeignKey("competitions.Competition", on_delete=models.CASCADE, related_name="player_statistics")
    team         = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="player_statistics")

    # Appearance stats
    matches_played   = models.PositiveIntegerField(default=0)
    matches_started  = models.PositiveIntegerField(default=0)
    matches_sub      = models.PositiveIntegerField(default=0, help_text="Appearances as substitute")
    minutes_played   = models.PositiveIntegerField(default=0)

    # Offensive stats
    goals            = models.PositiveIntegerField(default=0)
    assists          = models.PositiveIntegerField(default=0)
    penalties_scored = models.PositiveIntegerField(default=0)
    penalties_missed = models.PositiveIntegerField(default=0)
    own_goals        = models.PositiveIntegerField(default=0)

    # Disciplinary
    yellow_cards     = models.PositiveIntegerField(default=0)
    red_cards        = models.PositiveIntegerField(default=0)

    # Goalkeeper stats
    clean_sheets     = models.PositiveIntegerField(default=0, help_text="Matches where team conceded 0 goals (GK only)")
    goals_conceded   = models.PositiveIntegerField(default=0, help_text="Goals conceded while playing (GK only)")

    # Auto-calculated
    goal_contributions = models.PositiveIntegerField(default=0, help_text="Goals + Assists")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ["player", "competition"]
        ordering = ["-goals", "-assists", "-matches_played"]
        verbose_name = "Player Statistics"
        verbose_name_plural = "Player Statistics"

    def __str__(self):
        return f"{self.player.get_full_name()} — {self.competition.name} (G:{self.goals} A:{self.assists})"

    def save(self, *args, **kwargs):
        self.goal_contributions = self.goals + self.assists
        super().save(*args, **kwargs)
