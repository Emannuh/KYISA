"""
KYISA Teams — Models
"""
from django.db import models
from django.conf import settings
from competitions.models import SportType


class TeamStatus(models.TextChoices):
    PENDING    = "pending",    "Pending Approval"
    REGISTERED = "registered", "Registered"
    SUSPENDED  = "suspended",  "Suspended"


class Team(models.Model):
    name        = models.CharField(max_length=200, unique=True)
    county      = models.CharField(max_length=100)
    sport_type  = models.CharField(
        max_length=30, choices=SportType.choices, default=SportType.SOCCER,
        help_text="Sport this team competes in"
    )
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
    county_logo = models.ImageField(upload_to="county_logos/", null=True, blank=True, help_text="County government logo")
    home_colour = models.CharField(max_length=50, blank=True, help_text="Primary kit colour")
    away_colour = models.CharField(max_length=50, blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)
    contact_email = models.EmailField(blank=True)

    # ── Payment tracking ───────────────────────────────────────────────────────
    payment_confirmed    = models.BooleanField(default=False, help_text="Payment verified by treasurer")
    payment_reference    = models.CharField(max_length=100, blank=True, help_text="M-Pesa or receipt reference")
    payment_amount       = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Amount paid (KSh)")
    payment_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="payment_confirmations",
    )
    payment_confirmed_at = models.DateTimeField(null=True, blank=True)

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


class VerificationStatus(models.TextChoices):
    PENDING  = "pending",  "Pending Verification"
    VERIFIED = "verified", "Verified"
    REJECTED = "rejected", "Rejected"


class RejectionReason(models.TextChoices):
    FAKE_ID         = "fake_id",         "Fake / Invalid ID"
    FAKE_BIRTH_CERT = "fake_birth_cert", "Fake / Invalid Birth Certificate"
    PHOTO_MISMATCH  = "photo_mismatch",  "Photo Does Not Match"
    AGE_OUTSIDE     = "age_outside",     "Outside Age Bracket (18-23)"
    INCOMPLETE_DOCS = "incomplete_docs", "Incomplete Documents"
    OTHER           = "other",           "Other"


# Age bracket constants
PLAYER_MIN_AGE = 18
PLAYER_MAX_AGE = 23


class Player(models.Model):
    team           = models.ForeignKey(Team, on_delete=models.CASCADE, related_name="players")
    first_name     = models.CharField(max_length=100)
    last_name      = models.CharField(max_length=100)
    date_of_birth  = models.DateField()
    position       = models.CharField(max_length=10, choices=Position.choices)
    shirt_number       = models.PositiveIntegerField()
    national_id_number = models.CharField(max_length=20, blank=True, default="",
                                          help_text="National ID number")
    birth_cert_number  = models.CharField(max_length=30, blank=True, default="",
                                          help_text="Birth Certificate number")

    # ── Document uploads for verification ─────────────────────────────────
    photo          = models.ImageField(upload_to="players/photos/", null=True, blank=True,
                                       help_text="Passport-size photo")
    id_document    = models.ImageField(upload_to="players/ids/", null=True, blank=True,
                                       help_text="Copy of National ID")
    birth_certificate = models.ImageField(upload_to="players/birth_certs/", null=True, blank=True,
                                          help_text="Copy of Birth Certificate")

    # ── Verification workflow ─────────────────────────────────────────────
    verification_status = models.CharField(
        max_length=20, choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
    )
    rejection_reason = models.CharField(
        max_length=30, choices=RejectionReason.choices,
        blank=True, default="",
    )
    rejection_notes  = models.TextField(blank=True, default="",
                                        help_text="Additional notes on rejection")
    verified_by      = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="verified_players",
    )
    verified_at      = models.DateTimeField(null=True, blank=True)

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

    @property
    def is_age_eligible(self):
        """True if the player falls within the 18–23 age bracket."""
        return PLAYER_MIN_AGE <= self.age <= PLAYER_MAX_AGE

    @property
    def documents_uploaded(self):
        """True if all three required documents are present."""
        return bool(self.photo and self.id_document and self.birth_certificate)

    def auto_check_age(self):
        """
        Automatically lock out players outside the 18-23 bracket.
        Called on save. Sets status to ineligible and rejection reason.
        """
        if not self.is_age_eligible:
            self.verification_status = VerificationStatus.REJECTED
            self.rejection_reason = RejectionReason.AGE_OUTSIDE
            self.rejection_notes = (
                f"Player is {self.age} years old. "
                f"Must be between {PLAYER_MIN_AGE} and {PLAYER_MAX_AGE}."
            )
            self.status = PlayerStatus.INELIGIBLE
            return False
        return True

    def save(self, *args, **kwargs):
        # Auto-reject players outside the age bracket on every save
        self.auto_check_age()
        super().save(*args, **kwargs)
