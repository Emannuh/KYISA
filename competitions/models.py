"""
KYISA Competitions — Core Models
"""
from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils import timezone

COUNTY_REGISTRATION_FEE_CAP = 250_000  # KSh — maximum participation fee per county


class SportType(models.TextChoices):
    SOCCER             = "soccer",             "Soccer"
    VOLLEYBALL_MEN     = "volleyball_men",     "Volleyball (Men)"
    VOLLEYBALL_WOMEN   = "volleyball_women",   "Volleyball (Women)"
    BASKETBALL         = "basketball",         "Basketball"
    BASKETBALL_3X3     = "basketball_3x3",     "Basketball 3x3"
    HANDBALL           = "handball",           "Handball"
    BEACH_VOLLEYBALL   = "beach_volleyball",   "Beach Volleyball"
    BEACH_HANDBALL     = "beach_handball",     "Beach Handball"


EXHIBITION_SPORTS = {SportType.BEACH_VOLLEYBALL, SportType.BEACH_HANDBALL}


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
    sport_type  = models.CharField(
        max_length=30, choices=SportType.choices, default=SportType.SOCCER,
        help_text="Sport discipline for this competition"
    )
    is_exhibition = models.BooleanField(
        default=False,
        help_text="Mark as exhibition match (e.g. Beach Volleyball, Beach Handball)"
    )
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

    def save(self, *args, **kwargs):
        # Auto-mark beach sports as exhibition
        if self.sport_type in EXHIBITION_SPORTS:
            self.is_exhibition = True
        super().save(*args, **kwargs)


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

    def clean(self):
        from django.core.exceptions import ValidationError
        if self.team_id:
            if not self.team.payment_confirmed:
                raise ValidationError(
                    f"{self.team.name} cannot be pooled — payment has not been confirmed by the treasurer."
                )
            if self.team.status != "registered":
                raise ValidationError(
                    f"{self.team.name} is not approved. Only registered teams can be pooled."
                )

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

    def clean(self):
        from django.core.exceptions import ValidationError
        errors = {}
        for side, fk in [("home_team", self.home_team_id), ("away_team", self.away_team_id)]:
            if fk:
                team = getattr(self, side)
                if not team.payment_confirmed:
                    errors[side] = f"{team.name} cannot play — payment not confirmed by the treasurer."
                elif team.status != "registered":
                    errors[side] = f"{team.name} is not an approved team."
        if errors:
            raise ValidationError(errors)

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


# ─────────────────────────────────────────────────────────────────────────────
# County Registration & Participation Fee
# ─────────────────────────────────────────────────────────────────────────────

class PaymentStatus(models.TextChoices):
    PENDING  = "pending",  "Pending Payment"
    PAID     = "paid",     "Paid"
    WAIVED   = "waived",   "Waived"


class CountyRegistration(models.Model):
    """
    Tracks a county's registration for a competition.
    One record per county per competition — participation fee capped at KSh 250,000.
    """
    competition     = models.ForeignKey(
        Competition, on_delete=models.CASCADE, related_name="county_registrations"
    )
    county          = models.CharField(max_length=100)
    participation_fee = models.DecimalField(
        max_digits=10, decimal_places=2,
        default=COUNTY_REGISTRATION_FEE_CAP,
        help_text="Participation fee in KSh (max 250,000)"
    )
    payment_status  = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.PENDING
    )
    payment_reference = models.CharField(
        max_length=100, blank=True,
        help_text="M-Pesa or bank reference number"
    )
    payment_date    = models.DateField(null=True, blank=True)
    registered_by   = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="county_registrations_created"
    )
    registered_at   = models.DateTimeField(auto_now_add=True)
    notes           = models.TextField(blank=True)

    class Meta:
        unique_together = ["competition", "county"]
        ordering = ["competition", "county"]
        verbose_name = "County Registration"
        verbose_name_plural = "County Registrations"

    def clean(self):
        if self.participation_fee and self.participation_fee > COUNTY_REGISTRATION_FEE_CAP:
            raise ValidationError(
                f"Participation fee cannot exceed KSh {COUNTY_REGISTRATION_FEE_CAP:,}."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.county} — {self.competition.name} ({self.get_payment_status_display()})"

    @property
    def is_paid(self):
        return self.payment_status in (PaymentStatus.PAID, PaymentStatus.WAIVED)
