"""
KYISA Competition Management System — Django Settings
"""

import environ
from pathlib import Path
from datetime import timedelta

# ── PATHS ──────────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent

# ── ENVIRONMENT ────────────────────────────────────────────────────────────────
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / ".env")

# ── SECURITY ───────────────────────────────────────────────────────────────────
SECRET_KEY = env("SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG      = env("DEBUG", default=True)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["*"])

# Keep explicit local hosts available for Docker/local access even when
# ALLOWED_HOSTS is provided via environment variables.
for _host in ("localhost", "127.0.0.1", "[::1]"):
    if _host not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_host)

# ── APPS ───────────────────────────────────────────────────────────────────────
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",

    # Third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "crispy_forms",
    "crispy_bootstrap5",

    # KYISA Apps
    "accounts",
    "competitions",
    "referees.apps.RefereesConfig",
    "teams",
    "matches",
    "admin_dashboard",
    "appeals",
    "news_media",
]

# ── MIDDLEWARE ─────────────────────────────────────────────────────────────────
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "accounts.middleware.ForcePasswordChangeMiddleware",
    "admin_dashboard.activity_middleware.ActivityLoggingMiddleware",
]

ROOT_URLCONF   = "kyisa_cms.urls"
WSGI_APPLICATION = "kyisa_cms.wsgi.application"

# ── TEMPLATES ─────────────────────────────────────────────────────────────────
TEMPLATES = [{
    "BACKEND": "django.template.backends.django.DjangoTemplates",
    "DIRS": [BASE_DIR / "templates"],
    "APP_DIRS": True,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.debug",
        "django.template.context_processors.request",
        "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages",
    ]},
}]

# ── DATABASE ───────────────────────────────────────────────────────────────────
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
    )
}

# ── AUTH ───────────────────────────────────────────────────────────────────────
AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
]

LOGIN_URL = "web_login"
LOGIN_REDIRECT_URL = "dashboard"

# ── REST FRAMEWORK ─────────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ── JWT ────────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME":  timedelta(hours=8),
    "REFRESH_TOKEN_LIFETIME":  timedelta(days=7),
    "ROTATE_REFRESH_TOKENS":   True,
    "BLACKLIST_AFTER_ROTATION": True,
    "TOKEN_OBTAIN_SERIALIZER": "accounts.serializers.KYISATokenObtainSerializer",
}

# ── SESSION — Auto-logout after 10 minutes of inactivity ──────────────────────
SESSION_COOKIE_AGE = 600             # 10 minutes in seconds
SESSION_SAVE_EVERY_REQUEST = True    # Reset expiry on every request (activity)
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# ── CORS ───────────────────────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[
    "http://localhost:3000",
    "http://localhost:5173",
    "http://127.0.0.1:3000",
])
CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])
for _origin in ("http://localhost:8080", "http://127.0.0.1:8080"):
    if _origin not in CSRF_TRUSTED_ORIGINS:
        CSRF_TRUSTED_ORIGINS.append(_origin)

# ── SPECTACULAR (API DOCS) ─────────────────────────────────────────────────────
SPECTACULAR_SETTINGS = {
    "TITLE": "KYISA Competition Management System API",
    "DESCRIPTION": "Enterprise-grade football competition management for Kenya Youth Intercounty Sports Association",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth",         "description": "Authentication & user management"},
        {"name": "competitions", "description": "Competition management"},
        {"name": "fixtures",     "description": "Fixture scheduling"},
        {"name": "pools",        "description": "Group/pool management"},
        {"name": "venues",       "description": "Venue management"},
        {"name": "referees",     "description": "Referee management"},
        {"name": "teams",        "description": "Team management"},
        {"name": "players",      "description": "Player management"},
        {"name": "squads",       "description": "Squad submission & approval"},
        {"name": "matches",      "description": "Match reports & results"},
    ],
}

# ── STATIC & MEDIA ─────────────────────────────────────────────────────────────
STATIC_URL  = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

# ── CLOUD MEDIA STORAGE (production) ──────────────────────────────────────────
# Set STORAGE_BACKEND to "s3", "azure", or "gcs" to enable cloud storage.
# Leave empty or unset for local file storage (development).
STORAGE_BACKEND = env("STORAGE_BACKEND", default="")

if STORAGE_BACKEND == "azure":
    AZURE_ACCOUNT_NAME  = env("AZURE_ACCOUNT_NAME")
    AZURE_ACCOUNT_KEY   = env("AZURE_ACCOUNT_KEY")
    AZURE_CONTAINER     = env("AZURE_CONTAINER", default="media")
    AZURE_CUSTOM_DOMAIN = env("AZURE_CUSTOM_DOMAIN", default=f"{AZURE_ACCOUNT_NAME}.blob.core.windows.net")
    MEDIA_URL = f"https://{AZURE_CUSTOM_DOMAIN}/{AZURE_CONTAINER}/"
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.azure_storage.AzureStorage",
            "OPTIONS": {
                "azure_container": AZURE_CONTAINER,
            },
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
elif STORAGE_BACKEND == "gcs":
    GS_BUCKET_NAME      = env("GS_BUCKET_NAME")
    GS_PROJECT_ID       = env("GS_PROJECT_ID", default="")
    GS_DEFAULT_ACL      = None
    MEDIA_URL = f"https://storage.googleapis.com/{GS_BUCKET_NAME}/media/"
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {"location": "media"},
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
elif STORAGE_BACKEND == "s3":
    AWS_ACCESS_KEY_ID       = env("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY   = env("AWS_SECRET_ACCESS_KEY")
    AWS_STORAGE_BUCKET_NAME = env("AWS_STORAGE_BUCKET_NAME")
    AWS_S3_REGION_NAME      = env("AWS_S3_REGION_NAME", default="af-south-1")
    AWS_S3_ENDPOINT_URL     = env("AWS_S3_ENDPOINT_URL", default=None)  # for DO Spaces / other S3-compatible
    AWS_S3_CUSTOM_DOMAIN    = env("AWS_S3_CUSTOM_DOMAIN", default=f"{AWS_STORAGE_BUCKET_NAME}.s3.amazonaws.com")
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "max-age=86400"}
    AWS_DEFAULT_ACL          = None
    AWS_QUERYSTRING_AUTH     = False
    if AWS_S3_ENDPOINT_URL:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    else:
        MEDIA_URL = f"https://{AWS_S3_CUSTOM_DOMAIN}/media/"
    STORAGES = {
        "default": {
            "BACKEND": "storages.backends.s3boto3.S3Boto3Storage",
            "OPTIONS": {"location": "media"},
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }
else:
    MEDIA_URL  = "/media/"
    MEDIA_ROOT = BASE_DIR / "media"
    STORAGES = {
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
        },
    }

# ── CACHE ──────────────────────────────────────────────────────────────────────
REDIS_URL = env("REDIS_URL", default="")
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        }
    }

# ── CELERY ─────────────────────────────────────────────────────────────────────
CELERY_BROKER_URL        = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_RESULT_BACKEND    = env("REDIS_URL", default="redis://127.0.0.1:6379/0")
CELERY_ACCEPT_CONTENT    = ["json"]
CELERY_TASK_SERIALIZER   = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE          = "Africa/Nairobi"

# ── EMAIL ──────────────────────────────────────────────────────────────────────
# Dev: console backend. Production: set EMAIL_BACKEND to django_ses.
EMAIL_BACKEND    = env("EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend")
EMAIL_HOST       = env("EMAIL_HOST", default="localhost")
EMAIL_PORT       = env.int("EMAIL_PORT", default=587)
EMAIL_USE_TLS    = True
EMAIL_HOST_USER  = env("EMAIL_HOST_USER",     default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="KYISA Administration <admin@kyisa.org>")

# ── AWS SES (used when EMAIL_BACKEND = django_ses.SESBackend) ─────────────────
AWS_SES_REGION_NAME      = env("AWS_SES_REGION_NAME", default="eu-west-1")
AWS_SES_REGION_ENDPOINT  = env("AWS_SES_REGION_ENDPOINT", default="email.eu-west-1.amazonaws.com")

# ── ADMINS (receive 500-error emails + system alerts) ─────────────────────────
ADMINS = [
    ("KYISA Admin", env("ADMIN_EMAIL", default="admin@kyisa.org")),
]
MANAGERS = ADMINS
SERVER_EMAIL = env("SERVER_EMAIL", default="server@kyisa.org")

# ── LOGGING (email admins on server errors) ───────────────────────────────────
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {module}:{lineno} — {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "mail_admins": {
            "level": "ERROR",
            "filters": ["require_debug_false"],
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "mail_admins"],
            "level": "INFO",
            "propagate": True,
        },
        "django.request": {
            "handlers": ["mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "kyisa_cms": {
            "handlers": ["console", "mail_admins"],
            "level": "WARNING",
            "propagate": False,
        },
    },
}

# ── LOCALISATION ───────────────────────────────────────────────────────────────
LANGUAGE_CODE = "en-us"
TIME_ZONE     = "Africa/Nairobi"
USE_I18N      = True
USE_TZ        = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ── SQUAD RULES ────────────────────────────────────────────────────────────────
SQUAD_SUBMISSION_HOURS_BEFORE_KICKOFF = 2
SQUAD_MIN_STARTERS = 7      # Minimum starters required
SQUAD_MIN_PLAYERS  = 7      # Absolute minimum players (starters only if no subs)
SQUAD_MAX_PLAYERS  = 23
SQUAD_MAX_STARTERS = 11
SQUAD_MAX_SUBS     = 12

# ── CRISPY FORMS ───────────────────────────────────────────────────────────────
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# ── PLAYER VERIFICATION APIs ──────────────────────────────────────────────────
# FIFA Connect Integration (set API key in .env for production)
FIFA_CONNECT_API_URL = env("FIFA_CONNECT_API_URL", default="https://api.fifaconnect.ke/v1")
FIFA_CONNECT_API_KEY = env("FIFA_CONNECT_API_KEY", default="")
FIFA_CONNECT_ENABLED = env.bool("FIFA_CONNECT_ENABLED", default=True)
FIFA_CONNECT_TIMEOUT = env.int("FIFA_CONNECT_TIMEOUT", default=30)

# Smile Identity — IPRS / Enhanced KYC Verification
# Sign up at smileidentity.com → Dashboard → API Keys
# Use sandbox for testing (SMILE_ENVIRONMENT=sandbox)
SMILE_PARTNER_ID = env("SMILE_PARTNER_ID", default="")
SMILE_API_KEY    = env("SMILE_API_KEY", default="")
SMILE_ENVIRONMENT = env("SMILE_ENVIRONMENT", default="sandbox")  # 'sandbox' or 'production'
SMILE_TIMEOUT    = env.int("SMILE_TIMEOUT", default=30)

# ── M-PESA (DARAJA) INTEGRATION ──────────────────────────────────────────────
# Safaricom Daraja API — STK Push (Lipa Na M-Pesa Online)
# Register at developer.safaricom.co.ke → My Apps → Create App
MPESA_ENVIRONMENT    = env("MPESA_ENVIRONMENT", default="sandbox")  # 'sandbox' or 'production'
MPESA_CONSUMER_KEY   = env("MPESA_CONSUMER_KEY", default="")
MPESA_CONSUMER_SECRET = env("MPESA_CONSUMER_SECRET", default="")
MPESA_SHORTCODE      = env("MPESA_SHORTCODE", default="174379")       # Business shortcode (Paybill/Till)
MPESA_PASSKEY        = env("MPESA_PASSKEY", default="")               # Lipa Na M-Pesa Online passkey
MPESA_CALLBACK_URL   = env("MPESA_CALLBACK_URL", default="")          # Public URL for callbacks
MPESA_ACCOUNT_REF    = env("MPESA_ACCOUNT_REF", default="KYISA2026")  # Account reference on receipts

# ── KYISA BANK ACCOUNT DETAILS ────────────────────────────────────────────────
# Displayed on registration page for bank transfers
KYISA_BANK_NAME        = env("KYISA_BANK_NAME", default="Kenya Commercial Bank (KCB)")
KYISA_BANK_BRANCH      = env("KYISA_BANK_BRANCH", default="Meru Branch")
KYISA_BANK_ACCOUNT_NAME = env("KYISA_BANK_ACCOUNT_NAME", default="Kenya Youth Inter-County Sports Association")
KYISA_BANK_ACCOUNT_NO  = env("KYISA_BANK_ACCOUNT_NO", default="1234567890")
KYISA_BANK_SWIFT_CODE  = env("KYISA_BANK_SWIFT_CODE", default="")
KYISA_MPESA_PAYBILL    = env("KYISA_MPESA_PAYBILL", default="")       # Paybill number for manual payments
KYISA_MPESA_ACCOUNT_NO = env("KYISA_MPESA_ACCOUNT_NO", default="")    # Account number for Paybill
IPRS_ENABLED     = env.bool("IPRS_ENABLED", default=True)