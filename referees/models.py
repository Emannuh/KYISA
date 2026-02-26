"""
KYISA Referees — Models
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


class RefereeLevel(models.TextChoices):
    FIFA     = "FIFA",     "FIFA Referee"
    CAF      = "CAF",      "CAF Referee"
    NATIONAL = "National", "FKF National"
    COUNTY   = "County",   "County Level"


class RefereeProfile(models.Model):
    """
    Extended profile for users with role=REFEREE.
    Created when a referee registers; activated when Referee Manager approves.
    """
    user         = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="referee_profile"
    )
    license_number = models.CharField(max_length=50, unique=True, blank=True)
    level          = models.CharField(max_length=20, choices=RefereeLevel.choices, default=RefereeLevel.COUNTY)
    county         = models.CharField(max_length=100)
    is_approved    = models.BooleanField(default=False)
    approved_by    = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="referees_approved"
    )
    approved_at    = models.DateTimeField(null=True, blank=True)
    id_number      = models.CharField(max_length=20, blank=True, help_text="National ID / Passport")
    bio            = models.TextField(blank=True)
    years_experience = models.PositiveIntegerField(default=0)

    # Aggregated stats (updated after each match)
    total_matches  = models.PositiveIntegerField(default=0)
    avg_rating     = models.DecimalField(max_digits=3, decimal_places=1, default=0.0)

    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Referee Profile"
        ordering     = ["user__last_name"]

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.level})"


class RefereeCertification(models.Model):
    """Certifications, licenses and badges held by a referee."""
    referee     = models.ForeignKey(RefereeProfile, on_delete=models.CASCADE, related_name="certifications")
    title       = models.CharField(max_length=200)
    issued_by   = models.CharField(max_length=200)
    issued_date = models.DateField()
    expiry_date = models.DateField(null=True, blank=True)
    certificate = models.FileField(upload_to="referee_certs/", null=True, blank=True)

    def __str__(self):
        return f"{self.title} — {self.referee}"


class AppointmentRole(models.TextChoices):
    CENTRE  = "centre",  "Centre Referee"
    AR1     = "ar1",     "Assistant Referee 1"
    AR2     = "ar2",     "Assistant Referee 2"
    FOURTH  = "fourth",  "4th Official"


class AppointmentStatus(models.TextChoices):
    PENDING   = "pending",   "Pending Confirmation"
    CONFIRMED = "confirmed", "Confirmed"
    DECLINED  = "declined",  "Declined"
    REPLACED  = "replaced",  "Replaced"


class RefereeAppointment(models.Model):
    """Referee Manager assigns a referee to a fixture."""
    fixture   = models.ForeignKey(
        "competitions.Fixture", on_delete=models.CASCADE,
        related_name="referee_appointments"
    )
    referee   = models.ForeignKey(
        RefereeProfile, on_delete=models.CASCADE,
        related_name="appointments"
    )
    role      = models.CharField(max_length=20, choices=AppointmentRole.choices, default=AppointmentRole.CENTRE)
    status    = models.CharField(max_length=20, choices=AppointmentStatus.choices, default=AppointmentStatus.PENDING)
    appointed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        related_name="appointments_made"
    )
    appointed_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    notes        = models.TextField(blank=True)

    class Meta:
        unique_together = ["fixture", "referee", "role"]
        ordering        = ["-appointed_at"]

    def __str__(self):
        return f"{self.referee} → {self.fixture} ({self.role})"


class AvailabilityStatus(models.TextChoices):
    AVAILABLE   = "available",   "Available"
    UNAVAILABLE = "unavailable", "Unavailable"


class RefereeAvailability(models.Model):
    """Referee declares availability for a specific date."""
    referee = models.ForeignKey(RefereeProfile, on_delete=models.CASCADE, related_name="availability")
    date    = models.DateField()
    status  = models.CharField(max_length=20, choices=AvailabilityStatus.choices)
    notes   = models.CharField(max_length=200, blank=True)

    class Meta:
        unique_together = ["referee", "date"]
        ordering        = ["date"]

    def __str__(self):
        return f"{self.referee.user.get_full_name()} — {self.date} ({self.status})"


class RefereeReview(models.Model):
    """Referee Manager rates a referee after a match."""
    referee      = models.ForeignKey(RefereeProfile, on_delete=models.CASCADE, related_name="reviews")
    fixture      = models.ForeignKey(
        "competitions.Fixture", on_delete=models.CASCADE,
        related_name="referee_reviews"
    )
    reviewer     = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
        related_name="referee_reviews_given"
    )
    overall_score     = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    positioning       = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    decision_making   = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    fitness           = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    communication     = models.PositiveIntegerField(validators=[MinValueValidator(1), MaxValueValidator(10)])
    notes             = models.TextField(blank=True)
    reviewed_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ["referee", "fixture"]
        ordering = ["-reviewed_at"]

    def __str__(self):
        return f"Review: {self.referee} @ {self.fixture}"
