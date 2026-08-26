"""
Django settings for Amar Hishab — personal finance tracker.
Google-only authentication.
"""

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
#
# Google-only authentication.
# Normal users do not create passwords.
#
# Django admin can still use its own password authentication.
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

    # Required for Django admin
    "django.contrib.auth.backends.ModelBackend",

    # django-allauth
    "allauth.account.auth_backends.AuthenticationBackend",
]


# ============================================================
# DJANGO-ALLAUTH
# GOOGLE ONLY
# ============================================================

# ------------------------------------------------------------
# IMPORTANT
# ------------------------------------------------------------
#
# Amar Hishab uses Google authentication only.
#
# No:
#   - Email/password login
#   - Email/password signup
#   - Email verification
#   - Password reset
#
# Users must authenticate through Google.
# ------------------------------------------------------------

SOCIALACCOUNT_ONLY = True


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

        # Allow verified Google email authentication
        "EMAIL_AUTHENTICATION": True,

        "VERIFIED_EMAIL": True,
    }
}


# Don't automatically start OAuth on GET.
# Your template button will POST to Google login.
SOCIALACCOUNT_LOGIN_ON_GET = False


# ============================================================
# SOCIAL ACCOUNT SIGNUP
# ============================================================

# Allow new users to create accounts using Google.
SOCIALACCOUNT_AUTO_SIGNUP = True


# Google already verifies the user's email.
ACCOUNT_EMAIL_VERIFICATION = 'none'

# ============================================================
# EMAIL
# ============================================================
#
# Amar Hishab no longer sends verification emails.
#
# Keep SMTP configuration only if another part of your project
# needs email later.
# ============================================================

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

EMAIL_HOST = os.getenv(
    "EMAIL_HOST",
    "smtp.resend.com",
)

EMAIL_PORT = int(
    os.getenv("EMAIL_PORT", "587")
)

EMAIL_USE_TLS = (
    os.getenv("EMAIL_USE_TLS", "True").lower() == "true"
)

EMAIL_HOST_USER = os.getenv(
    "EMAIL_HOST_USER",
    "resend",
)

EMAIL_HOST_PASSWORD = os.getenv(
    "EMAIL_HOST_PASSWORD"
)

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "onboarding@resend.dev",
)

SERVER_EMAIL = DEFAULT_FROM_EMAIL


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


MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"