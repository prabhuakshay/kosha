"""Django settings for Kosha.

Every deployment-specific value is read from the environment, falling back to a
``.env`` file in the project root. See ``.env.example`` for the full list.

Defaults are secure: with only ``SECRET_KEY``, ``ALLOWED_HOSTS``,
``DATABASE_URL`` and the R2 ``S3_*`` values set, the app runs in production
mode. Set ``DEBUG=true`` for local development.
"""

from pathlib import Path

import environ
from django.utils.csp import CSP

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
# Real environment variables take precedence over values in .env.
environ.Env.read_env(BASE_DIR / ".env")


# -----------------------------------------------------------------------------
# Core
# -----------------------------------------------------------------------------

DEBUG = env.bool("DEBUG", default=False)
SECRET_KEY = env.str("SECRET_KEY")
ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "[::1]"] if DEBUG else []
)
CSRF_TRUSTED_ORIGINS = env.list("CSRF_TRUSTED_ORIGINS", default=[])

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
# Project setting, not Django's: a non-default path deters admin login bots.
ADMIN_URL = env.str("ADMIN_URL", default="admin/")


# -----------------------------------------------------------------------------
# Applications
# -----------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.core",
    "apps.users",
]

MIDDLEWARE = [
    "apps.core.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise must sit directly after SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.template.context_processors.csp",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# -----------------------------------------------------------------------------
# Database and cache
# -----------------------------------------------------------------------------

DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("CONN_MAX_AGE", default=60)
# Persistent connections can be dropped by the server; check before reuse.
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True

CACHES = {"default": env.cache("CACHE_URL", default="locmemcache://")}


# -----------------------------------------------------------------------------
# Authentication
# -----------------------------------------------------------------------------

AUTH_USER_MODEL = "users.User"

validators = "django.contrib.auth.password_validation"
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": f"{validators}.UserAttributeSimilarityValidator",
        # The defaults check first_name/last_name, which this user model lacks.
        "OPTIONS": {"user_attributes": ("email", "name")},
    },
    {"NAME": f"{validators}.MinimumLengthValidator"},
    {"NAME": f"{validators}.CommonPasswordValidator"},
    {"NAME": f"{validators}.NumericPasswordValidator"},
]


# -----------------------------------------------------------------------------
# Security
# -----------------------------------------------------------------------------

# Project setting, not Django's: one switch for every HTTPS-only behaviour, so
# a plain-HTTP LAN deploy can turn them all off together.
SECURE_HTTPS = env.bool("SECURE_HTTPS", default=not DEBUG)
SECURE_SSL_REDIRECT = SECURE_HTTPS
SESSION_COOKIE_SECURE = SECURE_HTTPS
CSRF_COOKIE_SECURE = SECURE_HTTPS
SECURE_HSTS_SECONDS = env.int(
    "SECURE_HSTS_SECONDS", default=60 * 60 * 24 * 365 if SECURE_HTTPS else 0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=False
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=False)
# Only safe behind a proxy that always sets or strips X-Forwarded-Proto,
# otherwise clients can spoof HTTPS.
if env.bool("SECURE_PROXY_SSL_HEADER", default=False):
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# Templates must add {{ csp_nonce }} to inline <script> and <style> tags.
SECURE_CSP = {
    "default-src": [CSP.SELF],
    "script-src": [CSP.SELF, CSP.NONCE],
    "style-src": [CSP.SELF, CSP.NONCE],
    "img-src": [CSP.SELF, "data:"],
    "object-src": [CSP.NONE],
    "base-uri": [CSP.SELF],
    "form-action": [CSP.SELF],
    "frame-ancestors": [CSP.NONE],
}


# -----------------------------------------------------------------------------
# Internationalization
# -----------------------------------------------------------------------------

LANGUAGE_CODE = env.str("LANGUAGE_CODE", default="en-us")
TIME_ZONE = env.str("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True


# -----------------------------------------------------------------------------
# Static and media files
# -----------------------------------------------------------------------------

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
# Relative paths resolve against the project root; absolute paths are kept.
STATIC_ROOT = BASE_DIR / env.str("STATIC_ROOT", default="staticfiles")
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / env.str("MEDIA_ROOT", default="media")

# See docs/adr/0001-media-in-a-private-r2-bucket.md.
if DEBUG and not env.str("S3_BUCKET_NAME", default=""):
    media_storage = {"BACKEND": "django.core.files.storage.FileSystemStorage"}
else:
    media_storage = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env.str("S3_BUCKET_NAME"),
            "endpoint_url": env.str("S3_ENDPOINT_URL"),
            "access_key": env.str("S3_ACCESS_KEY_ID"),
            "secret_key": env.str("S3_SECRET_ACCESS_KEY"),
            # R2 rejects ACLs.
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": env.int("S3_QUERYSTRING_EXPIRE", default=300),
            "file_overwrite": False,
            "signature_version": "s3v4",
        },
    }

STORAGES = {
    "default": media_storage,
    # Hashed filenames let browsers cache static files forever.
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"
    },
}


# -----------------------------------------------------------------------------
# Email
# -----------------------------------------------------------------------------

ADMINS = env.list("ADMINS", default=[])
MANAGERS = ADMINS
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL", default="webmaster@localhost")
SERVER_EMAIL = env.str("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = env.str("EMAIL_SUBJECT_PREFIX", default="[Kosha] ")

# MAILERS replaces the EMAIL_* settings as of Django 6.1. django-environ's
# EMAIL_URL only produces the old settings, so options are read individually.
# Development defaults target a local Mailpit (SMTP on port 1025, no TLS).
email_use_ssl = env.bool("EMAIL_USE_SSL", default=False)
MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.smtp.EmailBackend",
        "OPTIONS": {
            "host": env.str("EMAIL_HOST", default="localhost"),
            "port": env.int("EMAIL_PORT", default=1025 if DEBUG else 587),
            "username": env.str("EMAIL_HOST_USER", default=""),
            "password": env.str("EMAIL_HOST_PASSWORD", default=""),
            "use_tls": env.bool(
                "EMAIL_USE_TLS", default=not DEBUG and not email_use_ssl
            ),
            "use_ssl": email_use_ssl,
            "timeout": env.int("EMAIL_TIMEOUT", default=10),
        },
    },
}


# -----------------------------------------------------------------------------
# Logging
# -----------------------------------------------------------------------------

LOG_LEVEL = env.str("LOG_LEVEL", default="INFO")
LOGGING = {
    "version": 1,
    # Keep Django's other default loggers, such as runserver's request log.
    "disable_existing_loggers": False,
    "formatters": {
        "default": {"format": "{asctime} {levelname} {name} {message}", "style": "{"},
    },
    "filters": {
        "require_debug_false": {"()": "django.utils.log.RequireDebugFalse"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "default"},
        "mail_admins": {
            "class": "django.utils.log.AdminEmailHandler",
            "level": "ERROR",
            "filters": ["require_debug_false"],
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        # Replaces Django's default, which has its own console handler and would
        # print every record twice; output reaches the console via root instead.
        "django": {"handlers": ["mail_admins"], "level": LOG_LEVEL},
    },
}
