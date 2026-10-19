"""
KICOSCA Games — Models
========================
Kenya Inter-County Sports and Cultural Association (KICOSCA) player
registration and employment verification.

Completely separate from KYISA CountyPlayer — different eligibility rules:
  - KICOSCA: must be a current county government employee (verified via KRA)
  - KYISA: must be aged 18-23 (verified via IPRS)

County Sports Director adds players here via a dedicated KICOSCA portal
section — no overlap with the KYISA discipline/player flow.
"""
from django.db import models
from django.conf import settings
from django.utils import timezone
from accounts.models import KenyaCounty, kenya_phone_validator
from teams.models import CountyRegistration


# ── Sport choices (KICOSCA disciplines) ───────────────────────────────────────
class KicoscaSport(models.TextChoices):
    FOOTBALL_MEN    = "football_men",    "Football (Men)"
    FOOTBALL_WOMEN  = "football_women",  "Football (Women)"
    VOLLEYBALL_MEN  = "volleyball_men",  "Volleyball (Men)"
    VOLLEYBALL_WOMEN = "volleyball_women", "Volleyball (Women)"
    BASKETBALL_MEN  = "basketball_men",  "Basketball (Men)"
    BASKETBALL_WOMEN = "basketball_women", "Basketball (Women)"
    HANDBALL_MEN    = "handball_men",    "Handball (Men)"
    HANDBALL_WOMEN  = "handball_women",  "Handball (Women)"
    ATHLETICS       = "athletics",       "Athletics"
    SWIMMING        = "swimming",        "Swimming"
    RUGBY_SEVENS    = "rugby_sevens",    "Rugby Sevens (Men)"
    NETBALL         = "netball",         "Netball (Women)"


KICOSCA_SQUAD_LIMITS = {
    KicoscaSport.FOOTBALL_MEN:    24,
    KicoscaSport.FOOTBALL_WOMEN:  24,
    KicoscaSport.VOLLEYBALL_MEN:  14,
    KicoscaSport.VOLLEYBALL_WOMEN: 14,
    KicoscaSport.BASKETBALL_MEN:  12,
    KicoscaSport.BASKETBALL_WOMEN: 12,
    KicoscaSport.HANDBALL_MEN:    14,
    KicoscaSport.HANDBALL_WOMEN:  14,
    KicoscaSport.ATHLETICS:       30,
    KicoscaSport.SWIMMING:        20,
    KicoscaSport.RUGBY_SEVENS:    14,
    KicoscaSport.NETBALL:         14,
}


# ── Employment verification status ────────────────────────────────────────────
class EmploymentStatus(models.TextChoices):
    NOT_CHECKED = "not_checked", "Not Checked"
    VERIFIED    = "verified",    "Verified — County Employee"
    FAILED      = "failed",      "Failed — Not Found"
    MISMATCH    = "mismatch",    "Mismatch — Employer Differs"
    PENDING     = "pending",     "Pending Manual Review"


# ── KICOSCA Edition ───────────────────────────────────────────────────────────
class KicoscaEdition(models.Model):
    """
    A KICOSCA Games edition (e.g. KICOSCA 2026 Nakuru).
    Admin creates one edition; county directors register under it.
    """
    name         = models.CharField(max_length=200, unique=True,
                                    help_text="e.g. KICOSCA Games 2026 — Nakuru Edition")
    year         = models.PositiveIntegerField(help_text="Year of the games")
    host_county  = models.CharField(max_length=100, choices=KenyaCounty.choices)
    start_date   = models.DateField(null=True, blank=True)
    end_date     = models.DateField(null=True, blank=True)
    is_active    = models.BooleanField(default=True,
                                       help_text="County directors can only register under the active edition")
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-year']

    def __str__(self):
        return self.name

    @classmethod
    def get_active(cls):
        """Return the current active edition, or None."""
        return cls.objects.filter(is_active=True).first()


# ── KICOSCA County Entry ──────────────────────────────────────────────────────
class KicoscaCountyEntry(models.Model):
    """
    A county's entry into a KICOSCA edition.
    Linked to the existing CountyRegistration so the same county sports
    director account manages both KYISA and KICOSCA without a new login.
    """
    edition            = models.ForeignKey(KicoscaEdition, on_delete=models.CASCADE,
                                           related_name='county_entries')
    county_registration = models.ForeignKey(CountyRegistration, on_delete=models.CASCADE,
                                            related_name='kicosca_entries')

    class Meta:
        unique_together = ['edition', 'county_registration']
        ordering = ['county_registration__county']

    def __str__(self):
        return f"{self.county_registration.county} — {self.edition.name}"

    @property
    def county(self):
        return self.county_registration.county


# ── KICOSCA Discipline Entry ──────────────────────────────────────────────────
class KicoscaDiscipline(models.Model):
    """
    A specific sport/discipline entered by a county in a KICOSCA edition.
    """
    entry      = models.ForeignKey(KicoscaCountyEntry, on_delete=models.CASCADE,
                                   related_name='disciplines')
    sport      = models.CharField(max_length=30, choices=KicoscaSport.choices)

    class Meta:
        unique_together = ['entry', 'sport']
        ordering = ['sport']

    def __str__(self):
        return f"{self.entry.county} — {self.get_sport_display()}"

    @property
    def squad_limit(self):
        return KICOSCA_SQUAD_LIMITS.get(self.sport, 30)

    @property
    def player_count(self):
        return self.players.count()

    @property
    def can_add_player(self):
        return self.player_count < self.squad_limit


# ── KICOSCA Player ────────────────────────────────────────────────────────────
class KicoscaPlayer(models.Model):
    """
    A county government employee registered as a KICOSCA Games participant.

    Eligibility: must be a current employee of the county government
    they are representing, verified via KRA PAYE records.

    Completely separate from CountyPlayer (KYISA) — different model,
    different eligibility, different verification workflow.
    """
    discipline = models.ForeignKey(KicoscaDiscipline, on_delete=models.CASCADE,
                                   related_name='players')

    # ── Personal details ──────────────────────────────────────────────────
    first_name         = models.CharField(max_length=100)
    last_name          = models.CharField(max_length=100)
    date_of_birth      = models.DateField()
    national_id_number = models.CharField(max_length=20,
                                          help_text="Kenya National ID number")
    kra_pin            = models.CharField(max_length=11, blank=True, default="",
                                          help_text="KRA PIN (e.g. A001234567B)")
    phone              = models.CharField(max_length=13, validators=[kenya_phone_validator])
    department         = models.CharField(max_length=200, blank=True, default="",
                                          help_text="County department/office")
    employee_number    = models.CharField(max_length=50, blank=True, default="",
                                          help_text="Employee/payroll number")
    position_title     = models.CharField(max_length=100, blank=True, default="",
                                          help_text="Job title / designation")
    jersey_number      = models.PositiveIntegerField(null=True, blank=True)
    sport_position     = models.CharField(max_length=50, blank=True, default="",
                                          help_text="Playing position (e.g. GK, ST)")

    # ── Documents ─────────────────────────────────────────────────────────
    photo            = models.ImageField(upload_to="kicosca/photos/", null=True, blank=True)
    id_document      = models.ImageField(upload_to="kicosca/ids/",    null=True, blank=True)
    payslip          = models.FileField(upload_to="kicosca/payslips/", null=True, blank=True,
                                        help_text="Latest payslip (PDF or image) — proof of county employment")
    appointment_letter = models.FileField(upload_to="kicosca/letters/", null=True, blank=True,
                                          help_text="Appointment letter from county government (optional)")
    iprs_photo       = models.ImageField(upload_to="kicosca/iprs_photos/", null=True, blank=True,
                                         help_text="Passport photo from IPRS lookup (auto-populated)")

    # ── IPRS Identity Verification (Prembly) ─────────────────────────────
    prembly_status        = models.CharField(max_length=20,
                                             choices=EmploymentStatus.choices,
                                             default=EmploymentStatus.NOT_CHECKED)
    prembly_verified_name = models.CharField(max_length=200, blank=True, default="")
    prembly_reference     = models.CharField(max_length=255, blank=True, default="")
    prembly_checked_at    = models.DateTimeField(null=True, blank=True)

    # ── KRA Employment Verification (GavaConnect) ─────────────────────────
    kra_employment_status   = models.CharField(max_length=20,
                                               choices=EmploymentStatus.choices,
                                               default=EmploymentStatus.NOT_CHECKED)
    kra_employer_name       = models.CharField(max_length=300, blank=True, default="",
                                               help_text="Employer name returned by KRA")
    kra_employer_pin        = models.CharField(max_length=20, blank=True, default="",
                                               help_text="Employer KRA PIN from PAYE records")
    kra_verification_ref    = models.CharField(max_length=255, blank=True, default="")
    kra_checked_at          = models.DateTimeField(null=True, blank=True)
    kra_raw_response        = models.JSONField(default=dict, blank=True,
                                               help_text="Raw GavaConnect API response for audit")

    # ── Overall verification status ───────────────────────────────────────
    verification_status = models.CharField(
        max_length=20,
        choices=[
            ('pending',   'Pending Verification'),
            ('verified',  'Verified — Eligible'),
            ('rejected',  'Rejected — Ineligible'),
            ('resubmit',  'Requires Resubmission'),
        ],
        default='pending',
    )
    rejection_reason    = models.TextField(blank=True, default="")
    verified_by         = models.ForeignKey(settings.AUTH_USER_MODEL,
                                            on_delete=models.SET_NULL,
                                            null=True, blank=True,
                                            related_name='kicosca_verified_players')
    verified_at         = models.DateTimeField(null=True, blank=True)

    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['last_name', 'first_name']
        # Allow same person in different disciplines
        unique_together = ['discipline', 'national_id_number']

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.discipline})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def age(self):
        today = timezone.now().date()
        dob   = self.date_of_birth
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    @property
    def is_verified(self):
        return self.verification_status == 'verified'

    @property
    def identity_verified(self):
        return self.prembly_status == 'verified'

    @property
    def employment_verified(self):
        return self.kra_employment_status == 'verified'
