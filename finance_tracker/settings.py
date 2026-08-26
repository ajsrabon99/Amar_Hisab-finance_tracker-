"""Django settings for Amar Hishab — personal finance tracker."""

from pathlib import Path
import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


# ============================================================
# SECURITY
# ============================================================

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-change-this-before-production",
)

DEBUG = os.getenv("DEBUG", "True").lower() == "true"


ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "").split(",")
    if host.strip()
]


# Local development
if DEBUG and not ALLOWED_HOSTS:
    ALLOWED_HOSTS = [
        "localhost",
        "127.0.0.1",
    ]


# ============================================================
# APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # django-allauth
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",

    # Amar Hishab
    "tracker",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",

    # django-allauth
    "allauth.account.middleware.AccountMiddleware",
]


# ============================================================
# URL / TEMPLATE CONFIGURATION
# ============================================================

ROOT_URLCONF = "finance_tracker.urls"


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [
            BASE_DIR / "tracker" / "templates",
        ],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


WSGI_APPLICATION = "finance_tracker.wsgi.application"


# ============================================================
# DATABASE
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Dhaka"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES
# ============================================================

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ============================================================
# DJANGO SITES
# ============================================================

SITE_ID = 1

ACCOUNT_DEFAULT_HTTP_PROTOCOL = "https"

SITE_DOMAIN = os.getenv(
    "SITE_DOMAIN",
    "127.0.0.1:8000",
)


# ============================================================
# AUTHENTICATION
# ============================================================

LOGIN_REDIRECT_URL = "/"

LOGOUT_REDIRECT_URL = "/accounts/login/"


AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]


# ============================================================
# DJANGO-ALLAUTH — REGULAR ACCOUNT
# ============================================================

# Login using email
ACCOUNT_LOGIN_METHODS = {"email"}


# Regular email/password signup fields
ACCOUNT_SIGNUP_FIELDS = [
    "email*",
    "password1*",
    "password2*",
]


# ------------------------------------------------------------
# EMAIL VERIFICATION
# ------------------------------------------------------------
#
# This applies to the regular email/password account flow.
#
# Your custom tracker/views.py signup flow also has its own
# 5-digit verification system.
#

ACCOUNT_EMAIL_VERIFICATION = "mandatory"

ACCOUNT_EMAIL_VERIFICATION_BY_CODE_ENABLED = True

ACCOUNT_EMAIL_VERIFICATION_BY_CODE_FORMAT = {
    "numeric": True,
    "dashed": False,
    "length": 5,
}

ACCOUNT_EMAIL_VERIFICATION_BY_CODE_MAX_ATTEMPTS = 3

ACCOUNT_EMAIL_VERIFICATION_BY_CODE_TIMEOUT = 600

ACCOUNT_EMAIL_VERIFICATION_SUPPORTS_RESEND = True


# ============================================================
# PASSWORD RESET — OTP / CODE
# ============================================================

ACCOUNT_PASSWORD_RESET_BY_CODE_ENABLED = True

ACCOUNT_PASSWORD_RESET_BY_CODE_FORMAT = {
    "numeric": True,
    "dashed": False,
    "length": 5,
}


# ============================================================
# GOOGLE SOCIAL LOGIN
# ============================================================

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "key": "",
        },

        "SCOPE": [
            "profile",
            "email",
        ],

        "AUTH_PARAMS": {
            "access_type": "online",
        },

        # Google provides the authenticated identity.
        # Do not send the user through your regular
        # email/password verification flow.
        "VERIFIED_EMAIL": True,
    }
}


# Google login button uses POST.
SOCIALACCOUNT_LOGIN_ON_GET = False


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = "smtp.gmail.com"

EMAIL_PORT = 587

EMAIL_USE_TLS = True

EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER")

EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")


DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    EMAIL_HOST_USER,
)


# ============================================================
# PRODUCTION SECURITY
# ============================================================

if not DEBUG:

    CSRF_TRUSTED_ORIGINS = [
        origin.strip()
        for origin in os.getenv(
            "CSRF_TRUSTED_ORIGINS",
            "",
        ).split(",")
        if origin.strip()
    ]

    SECURE_PROXY_SSL_HEADER = (
        "HTTP_X_FORWARDED_PROTO",
        "https",
    )


# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
        },
    },

    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "ERROR",
        },

        "allauth": {
            "handlers": ["console"],
            "level": "DEBUG",
        },
    },
}