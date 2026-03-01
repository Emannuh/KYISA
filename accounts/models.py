"""
KYISA Accounts — Custom User Model with Role-Based Access
"""
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UserRole(models.TextChoices):
    COMPETITION_MANAGER = "competition_manager", "Competition Manager"
    REFEREE_MANAGER     = "referee_manager",     "Referees Manager"
    REFEREE             = "referee",             "Referee"
    TEAM_MANAGER        = "team_manager",        "Team Manager"
    TREASURER           = "treasurer",           "Treasurer"
    JURY_CHAIR          = "jury_chair",          "Chair of the Jury"
    ADMIN               = "admin",               "System Admin"


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user  = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff",     True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role",         UserRole.ADMIN)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Central KYISA user — single table, role differentiates access.
    """
    email       = models.EmailField(unique=True)
    first_name  = models.CharField(max_length=100)
    last_name   = models.CharField(max_length=100)
    phone       = models.CharField(max_length=20, blank=True)
    role        = models.CharField(max_length=30, choices=UserRole.choices, default=UserRole.TEAM_MANAGER)
    county      = models.CharField(max_length=100, blank=True, help_text="Kenyan county")
    profile_photo = models.ImageField(upload_to="profiles/", null=True, blank=True)
    is_active   = models.BooleanField(default=True)
    is_staff    = models.BooleanField(default=False)
    is_suspended = models.BooleanField(default=False, help_text="Admin-suspended account")
    must_change_password = models.BooleanField(
        default=False,
        help_text="When True the user must set a new password on next login.",
    )
    date_joined = models.DateTimeField(default=timezone.now)
    last_login  = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD  = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    class Meta:
        verbose_name      = "User"
        verbose_name_plural = "Users"
        ordering = ["last_name", "first_name"]

    def __str__(self):
        return f"{self.get_full_name()} ({self.get_role_display()})"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    # ── Role helpers ──────────────────────────────────────────────────────────
    @property
    def is_competition_manager(self): return self.role == UserRole.COMPETITION_MANAGER
    @property
    def is_referee_manager(self): return self.role == UserRole.REFEREE_MANAGER
    @property
    def is_referee(self): return self.role == UserRole.REFEREE
    @property
    def is_team_manager(self): return self.role == UserRole.TEAM_MANAGER
    @property
    def is_treasurer(self): return self.role == UserRole.TREASURER
    @property
    def is_jury_chair(self): return self.role == UserRole.JURY_CHAIR
    @property
    def is_admin(self): return self.role == UserRole.ADMIN or self.is_superuser


class KenyaCounty(models.TextChoices):
    NAIROBI   = "Nairobi",   "Nairobi"
    MOMBASA   = "Mombasa",   "Mombasa"
    KISUMU    = "Kisumu",    "Kisumu"
    NAKURU    = "Nakuru",    "Nakuru"
    ELDORET   = "Eldoret",   "Uasin Gishu (Eldoret)"
    MERU      = "Meru",      "Meru"
    THIKA     = "Thika",     "Kiambu (Thika)"
    NYERI     = "Nyeri",     "Nyeri"
    KISII     = "Kisii",     "Kisii"
    KAKAMEGA  = "Kakamega",  "Kakamega"
    MACHAKOS  = "Machakos",  "Machakos"
    GARISSA   = "Garissa",   "Garissa"
    EMBU      = "Embu",      "Embu"
    KITALE    = "Kitale",    "Trans-Nzoia (Kitale)"
    BUNGOMA   = "Bungoma",   "Bungoma"
    MIGORI    = "Migori",    "Migori"
    SIAYA     = "Siaya",     "Siaya"
    LAMU      = "Lamu",      "Lamu"
    MALINDI   = "Malindi",   "Kilifi (Malindi)"
    VIHIGA    = "Vihiga",    "Vihiga"
