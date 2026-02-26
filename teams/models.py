"""
KYISA Teams — Models
"""
from django.db import models
from django.conf import settings


class TeamStatus(models.TextChoices):
    PENDING    = "pending",    "Pending Approval"
    REGISTERED = "registered", "Registered"
    SUSPENDED  = "suspended",  "Suspended"


class Team(models.Model):
    name        = models.CharField(max_length=200, unique=True)
    county      = models.CharField(max_length=100)
    competition = models.ForeignKey(
        "competitions.Competition", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="teams"
    )
    manager     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="managed_teams"
    )
    status      = models.CharField(max_length=20, choices=TeamStatus.choices, default=TeamStatus.PENDING)
    badge       = models.ImageField(upload_to="team_badges/", null=True, blank=True)
    home_colour = models.CharField(max_length=50, blank=True, help_text="Primary kit colour")
    away_colour = models.CharField(max_length=50, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at    = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["county", "name"]

    def __str__(self):
        return self.name


class Position(models.TextChoices):
    GK  = "GK",  "Goalkeeper"
    CB  = "CB",  "Centre Back"
    LB  = "LB",  "Left Back"
    RB  = "RB",  "Right Back"
    CDM = "CDM", "Defensive Mid"
    CM  = "CM",  "Centre Mid"
    AM  = "AM",  "Attacking Mid"
    LW  = "LW",  "Left Wing"
    RW  = "RW",  "Right Wing"
    CF  = "CF",  "Centre Forward"
    ST  = "ST",  "Striker"


class PlayerStatus(models.TextChoices):
    ELIGIBLE   = "eligible",   "Eligible"
    INELIGIBLE = "ineligible", "Ineligible"
    SUSPENDED  = "suspended",  "Suspended"
    INJURED    = "injured",    "Injured"


class Player(models.Model):
    team           = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")
    first_name     = models.CharField(max_length=100)
    last_name      = models.CharField(max_length=100)
    date_of_birth  = models.DateField()
    position       = models.CharField(max_length=10, choices=Position.choices)
    shirt_number   = models.PositiveIntegerField()
    id_number      = models.CharField(max_length=20, help_text="Birth cert / National ID")
    photo          = models.ImageField(upload_to="players/", null=True, blank=True)
    status         = models.CharField(max_length=20, choices=PlayerStatus.choices, default=PlayerStatus.ELIGIBLE)
    registered_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["team", "shirt_number"]
        ordering        = ["team", "shirt_number"]

    def __str__(self):
        return f"#{self.shirt_number} {self.first_name} {self.last_name} ({self.team})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        from django.utils import timezone
        today = timezone.now().date()
        dob   = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
