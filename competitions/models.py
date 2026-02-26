"""
KYISA Competitions — Core Models
"""
from django.db import models
from django.conf import settings
from django.utils import timezone


class CompetitionStatus(models.TextChoices):
    REGISTRATION = "registration", "Registration Open"
    UPCOMING     = "upcoming",     "Upcoming"
    ACTIVE       = "active",       "Active / Ongoing"
    COMPLETED    = "completed",    "Completed"
    CANCELLED    = "cancelled",    "Cancelled"


class AgeGroup(models.TextChoices):
    U13 = "U13", "Under 13"
    U15 = "U15", "Under 15"
    U17 = "U17", "Under 17"
    U20 = "U20", "Under 20"
    U23 = "U23", "Under 23"
    OPEN = "Open", "Open Age"


class Competition(models.Model):
    name        = models.CharField(max_length=200, unique=True)
    season      = models.CharField(max_length=10, default="2025")
    age_group   = models.CharField(max_length=10, choices=AgeGroup.choices, default=AgeGroup.U17)
    status      = models.CharField(max_length=20, choices=CompetitionStatus.choices, default=CompetitionStatus.REGISTRATION)
    description = models.TextField(blank=True)
    start_date  = models.DateField()
    end_date    = models.DateField()
    max_teams   = models.PositiveIntegerField(default=16)
    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="competitions_created"
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date"]
        verbose_name = "Competition"
        verbose_name_plural = "Competitions"

    def __str__(self):
        return f"{self.name} ({self.season})"


class Venue(models.Model):
    name       = models.CharField(max_length=200)
    county     = models.CharField(max_length=100)
    city       = models.CharField(max_length=100)
    address    = models.TextField(blank=True)
    capacity   = models.PositiveIntegerField(default=0)
    surface    = models.CharField(max_length=100, default="Natural Grass")
    facilities = models.TextField(blank=True, help_text="List facilities available")
    photo      = models.ImageField(upload_to="venues/", null=True, blank=True)
    is_active  = models.BooleanField(default=True)
    latitude   = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude  = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    class Meta:
        ordering = ["county", "name"]

    def __str__(self):
        return f"{self.name}, {self.county}"


class Pool(models.Model):
    """A group/pool within a competition (e.g., Group A, Group B)."""
    competition = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="pools")
    name        = models.CharField(max_length=50, help_text="e.g., Group A, Group B, Pool 1")
    notes       = models.TextField(blank=True)

    class Meta:
        unique_together = ["competition", "name"]
        ordering = ["competition", "name"]

    def __str__(self):
        return f"{self.competition.name} — {self.name}"


class PoolTeam(models.Model):
    """Team assignment to a pool with standing data."""
    pool       = models.ForeignKey(Pool, on_delete=models.CASCADE, related_name="pool_teams")
    team       = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="pool_memberships")
    played     = models.PositiveIntegerField(default=0)
    won        = models.PositiveIntegerField(default=0)
    drawn      = models.PositiveIntegerField(default=0)
    lost       = models.PositiveIntegerField(default=0)
    goals_for  = models.PositiveIntegerField(default=0)
    goals_against = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ["pool", "team"]
        ordering = ["-won", "-goals_for"]

    @property
    def points(self):
        return (self.won * 3) + self.drawn

    @property
    def goal_difference(self):
        return self.goals_for - self.goals_against

    def __str__(self):
        return f"{self.team.name} in {self.pool}"


class FixtureStatus(models.TextChoices):
    PENDING       = "pending",    "Pending"
    CONFIRMED     = "confirmed",  "Confirmed"
    LIVE          = "live",       "Live"
    COMPLETED     = "completed",  "Completed"
    POSTPONED     = "postponed",  "Postponed"
    CANCELLED     = "cancelled",  "Cancelled"


class Fixture(models.Model):
    """A scheduled match between two teams."""
    competition    = models.ForeignKey(Competition, on_delete=models.CASCADE, related_name="fixtures")
    pool           = models.ForeignKey(Pool, on_delete=models.SET_NULL, null=True, blank=True, related_name="fixtures")
    home_team      = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="home_fixtures")
    away_team      = models.ForeignKey("teams.Team", on_delete=models.CASCADE, related_name="away_fixtures")
    venue          = models.ForeignKey(Venue, on_delete=models.SET_NULL, null=True, blank=True)
    match_date     = models.DateField()
    kickoff_time   = models.TimeField()
    status         = models.CharField(max_length=20, choices=FixtureStatus.choices, default=FixtureStatus.PENDING)
    round_number   = models.PositiveIntegerField(null=True, blank=True)

    # Results (filled after match)
    home_score     = models.PositiveIntegerField(null=True, blank=True)
    away_score     = models.PositiveIntegerField(null=True, blank=True)
    is_walkover    = models.BooleanField(default=False)
    walkover_team  = models.ForeignKey(
        "teams.Team", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="walkovers_won"
    )

    created_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="fixtures_created"
    )
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["match_date", "kickoff_time"]

    def __str__(self):
        return f"{self.home_team} vs {self.away_team} — {self.match_date}"

    @property
    def kickoff_datetime(self):
        from datetime import datetime
        return datetime.combine(self.match_date, self.kickoff_time)

    @property
    def squad_deadline(self):
        """Squad must be submitted SQUAD_SUBMISSION_HOURS_BEFORE_KICKOFF hours before KO."""
        from django.conf import settings as conf
        hours = getattr(conf, "SQUAD_SUBMISSION_HOURS_BEFORE_KICKOFF", 4)
        from datetime import timedelta
        import pytz
        nairobi = pytz.timezone("Africa/Nairobi")
        ko = nairobi.localize(self.kickoff_datetime)
        return ko - timedelta(hours=hours)
