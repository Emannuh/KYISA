"""
KYISA Teams — Models
"""
from django.db import models
from django.conf import settings
from competitions.models import SportType


# ══════════════════════════════════════════════════════════════════════════════
#  COUNTY MODEL
# ══════════════════════════════════════════════════════════════════════════════

class County(models.Model):
    """Kenyan counties with sports officer contact information."""
    name = models.CharField(max_length=100, unique=True, help_text="County name (e.g., Nairobi, Mombasa)")
    code = models.CharField(max_length=10, unique=True, help_text="County code (e.g., NAI, MSA)")
    capital = models.CharField(max_length=100, blank=True, help_text="County capital/headquarters")
    
    # Sports officer contact details
    sports_officer_name = models.CharField(max_length=200, blank=True, help_text="Sports officer full name")
    sports_officer_email = models.EmailField(blank=True, help_text="Sports officer email address")
    sports_officer_phone = models.CharField(max_length=20, blank=True, help_text="Sports officer phone number")
    
    # Alternative contact (backup)
    alt_contact_name = models.CharField(max_length=200, blank=True, help_text="Alternative contact name")
    alt_contact_email = models.EmailField(blank=True, help_text="Alternative contact email")
    alt_contact_phone = models.CharField(max_length=20, blank=True, help_text="Alternative contact phone")
    
    office_address = models.TextField(blank=True, help_text="County sports office address")
    is_active = models.BooleanField(default=True, help_text="County is active and participating")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name_plural = 'Counties'
    
    def __str__(self):
        return self.name
    
    @property
    def primary_contact_email(self):
        """Return sports officer email, fallback to alternative contact email."""
        return self.sports_officer_email or self.alt_contact_email
    
    @property
    def primary_contact_name(self):
        """Return sports officer name, fallback to alternative contact name."""
        return self.sports_officer_name or self.alt_contact_name


class TeamStatus(models.TextChoices):
    PENDING    = "pending",    "Pending Approval"
    REGISTERED = "registered", "Registered"
    SUSPENDED  = "suspended",  "Suspended"


class Team(models.Model):
    name        = models.CharField(max_length=200, unique=True)
    county      = models.ForeignKey(County, on_delete=models.CASCADE, related_name="teams", help_text="County this team represents")
    sport_type  = models.CharField(
        max_length=30, choices=SportType.choices, default=SportType.FOOTBALL_MEN,
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

    # ── Kit details (mandatory for registration) ───────────────────────────
    # Home kit
    home_outfield_colour = models.CharField(max_length=50, blank=True, help_text="Home outfield jersey colour")
    home_shorts_colour   = models.CharField(max_length=50, blank=True, help_text="Home shorts colour")
    home_socks_colour    = models.CharField(max_length=50, blank=True, help_text="Home socks colour")
    home_gk_colour       = models.CharField(max_length=50, blank=True, help_text="Home goalkeeper jersey colour")
    home_kit_image       = models.ImageField(upload_to="kits/home/", null=True, blank=True, help_text="Photo of home kit")

    # Away kit
    away_outfield_colour = models.CharField(max_length=50, blank=True, help_text="Away outfield jersey colour")
    away_shorts_colour   = models.CharField(max_length=50, blank=True, help_text="Away shorts colour")
    away_socks_colour    = models.CharField(max_length=50, blank=True, help_text="Away socks colour")
    away_gk_colour       = models.CharField(max_length=50, blank=True, help_text="Away goalkeeper jersey colour")
    away_kit_image       = models.ImageField(upload_to="kits/away/", null=True, blank=True, help_text="Photo of away kit")

    # Third kit (optional)
    third_outfield_colour = models.CharField(max_length=50, blank=True, help_text="Third outfield jersey colour")
    third_shorts_colour   = models.CharField(max_length=50, blank=True, help_text="Third shorts colour")
    third_socks_colour    = models.CharField(max_length=50, blank=True, help_text="Third socks colour")
    third_gk_colour       = models.CharField(max_length=50, blank=True, help_text="Third goalkeeper jersey colour")
    third_kit_image       = models.ImageField(upload_to="kits/third/", null=True, blank=True, help_text="Photo of third kit")

    # Legacy fields (kept for backward compat; prefer new kit fields above)
    home_colour = models.CharField(max_length=50, blank=True, help_text="Primary kit colour (legacy)")
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

    @property
    def home_kit_complete(self):
        """True if all mandatory home kit fields are filled."""
        return all([self.home_outfield_colour, self.home_shorts_colour,
                    self.home_socks_colour, self.home_gk_colour])

    @property
    def away_kit_complete(self):
        """True if all mandatory away kit fields are filled."""
        return all([self.away_outfield_colour, self.away_shorts_colour,
                    self.away_socks_colour, self.away_gk_colour])

    @property
    def kits_complete(self):
        """True if both home and away kit details are filled (required for approval)."""
        return self.home_kit_complete and self.away_kit_complete


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
    FIFA_CONNECT_FLAGGED = "fifa_connect_flagged", "Flagged by FIFA Connect (Higher League)"
    HUDUMA_FAILED   = "huduma_failed",   "Huduma Kenya Verification Failed"
    OTHER           = "other",           "Other"


class HudumaVerificationStatus(models.TextChoices):
    NOT_CHECKED = "not_checked", "Not Checked"
    PENDING     = "pending",     "Pending Verification"
    VERIFIED    = "verified",    "Verified"
    FAILED      = "failed",      "Failed"
    EXPIRED     = "expired",     "Expired"


class FIFAConnectStatus(models.TextChoices):
    NOT_CHECKED = "not_checked", "Not Checked"
    PENDING     = "pending",     "Pending Check"
    CLEAR       = "clear",       "Clear — No Higher League"
    FLAGGED     = "flagged",     "Flagged — Higher League Found"
    ERROR       = "error",       "API Error"


class HigherLeague(models.TextChoices):
    REGIONAL_LEAGUE      = "regional_league",      "Regional League"
    DIVISION_TWO         = "division_two",         "Division Two"
    DIVISION_ONE         = "division_one",         "Division One"
    NATIONAL_SUPER_LEAGUE = "national_super_league", "National Super League"
    FKF_PREMIER_LEAGUE   = "fkf_premier_league",   "Kenya FKF Premier League"


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

    # ── Huduma Kenya Verification (Age) ───────────────────────────────────
    huduma_status = models.CharField(
        max_length=20, choices=HudumaVerificationStatus.choices,
        default=HudumaVerificationStatus.NOT_CHECKED,
        help_text="Huduma Kenya age verification status",
    )
    huduma_verified_at  = models.DateTimeField(null=True, blank=True)
    huduma_verified_by  = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="huduma_verified_players",
    )
    huduma_reference    = models.CharField(max_length=100, blank=True, default="",
                                           help_text="Huduma Kenya verification reference")
    huduma_notes        = models.TextField(blank=True, default="",
                                           help_text="Notes from Huduma verification")

    # ── FIFA Connect Verification (Higher League Check) ───────────────────
    fifa_connect_id     = models.CharField(max_length=50, blank=True, default="",
                                           help_text="FIFA Connect Player ID")
    fifa_connect_status = models.CharField(
        max_length=20, choices=FIFAConnectStatus.choices,
        default=FIFAConnectStatus.NOT_CHECKED,
        help_text="FIFA Connect higher-league check status",
    )
    fifa_connect_leagues = models.JSONField(
        default=list, blank=True,
        help_text="List of higher-level leagues found in FIFA Connect",
    )
    fifa_connect_checked_at = models.DateTimeField(null=True, blank=True)
    fifa_connect_checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="fifa_connect_checked_players",
    )
    fifa_connect_notes = models.TextField(blank=True, default="",
                                          help_text="Notes from FIFA Connect check")

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

    @property
    def is_huduma_verified(self):
        """True if Huduma Kenya age verification has passed."""
        return self.huduma_status == HudumaVerificationStatus.VERIFIED

    @property
    def is_fifa_connect_clear(self):
        """True if FIFA Connect check found no higher-league registration."""
        return self.fifa_connect_status == FIFAConnectStatus.CLEAR

    @property
    def is_fully_cleared(self):
        """
        True ONLY if the player passes ALL verification steps:
        1. Document verification (admin verified)
        2. Huduma Kenya age verification
        3. FIFA Connect higher-league check is clear
        """
        return (
            self.verification_status == VerificationStatus.VERIFIED
            and self.is_huduma_verified
            and self.is_fifa_connect_clear
        )

    @property
    def clearance_summary(self):
        """Return a dict summarising each verification step."""
        return {
            'documents': {
                'status': self.verification_status,
                'display': self.get_verification_status_display(),
                'passed': self.verification_status == VerificationStatus.VERIFIED,
            },
            'huduma': {
                'status': self.huduma_status,
                'display': self.get_huduma_status_display(),
                'passed': self.is_huduma_verified,
            },
            'fifa_connect': {
                'status': self.fifa_connect_status,
                'display': self.get_fifa_connect_status_display(),
                'passed': self.is_fifa_connect_clear,
                'leagues_found': self.fifa_connect_leagues,
            },
            'fully_cleared': self.is_fully_cleared,
        }

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


# ══════════════════════════════════════════════════════════════════════════════
#  PLAYER VERIFICATION LOG — Audit Trail
# ══════════════════════════════════════════════════════════════════════════════

class VerificationStep(models.TextChoices):
    DOCUMENT   = "document",     "Document Verification"
    HUDUMA     = "huduma",       "Huduma Kenya (Age)"
    FIFA_CONNECT = "fifa_connect", "FIFA Connect (League Check)"
    CLEARANCE  = "clearance",    "Final Clearance"


class PlayerVerificationLog(models.Model):
    """Records every verification action for audit trail."""
    player      = models.ForeignKey(Player, on_delete=models.CASCADE, related_name="verification_logs")
    step        = models.CharField(max_length=20, choices=VerificationStep.choices)
    action      = models.CharField(max_length=50, help_text="e.g. 'verified', 'rejected', 'flagged', 'cleared'")
    result      = models.CharField(max_length=50, help_text="Outcome of the action")
    details     = models.JSONField(default=dict, blank=True, help_text="Detailed data from the verification")
    notes       = models.TextField(blank=True, default="")
    performed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="verification_actions",
    )
    performed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_at"]
        verbose_name = "Verification Log"
        verbose_name_plural = "Verification Logs"

    def __str__(self):
        return f"{self.player.get_full_name()} — {self.get_step_display()} — {self.action}"
