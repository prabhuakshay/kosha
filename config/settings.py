"""Django settings for Kosha.

Every deployment-specific value is read from the environment, falling back to a
``.env`` file in the project root. See ``.env.example`` for the full list.

Defaults are secure: with only ``SECRET_KEY``, ``ALLOWED_HOSTS``,
``DATABASE_URL``, ``WEBAUTHN_ORIGINS`` (or an HTTPS ``CSRF_TRUSTED_ORIGINS``)
and the R2 ``S3_*`` values set, the app runs in production mode. Set
``DEBUG=true`` for local development.
"""

from datetime import timedelta
from pathlib import Path
from urllib.parse import urlsplit

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
    "django_otp",
    "django_otp.plugins.otp_totp",
    "django_otp.plugins.otp_static",
    "django_otp_webauthn",
    "axes",
    "apps.core",
    "apps.masters",
    "apps.signin",
    "apps.users",
]

MIDDLEWARE = [
    "apps.core.middleware.HealthCheckMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # WhiteNoise must sit directly after SecurityMiddleware.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "apps.core.middleware.NoStoreMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # Every view needs sign-in unless it opts out with @login_not_required.
    "django.contrib.auth.middleware.LoginRequiredMiddleware",
    "django_otp.middleware.OTPMiddleware",
    # A password alone reaches only the code step, or setting up a Way to sign in.
    "apps.signin.middleware.WayToSignInMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "django.middleware.csp.ContentSecurityPolicyMiddleware",
    # Last, so the paused page it swaps in still gets the CSP header.
    "axes.middleware.AxesMiddleware",
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
                "apps.core.context_processors.section",
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
AUTHENTICATION_BACKENDS = [
    # First, so a paused address is refused before any password is checked.
    "axes.backends.AxesStandaloneBackend",
    "django.contrib.auth.backends.ModelBackend",
    "django_otp_webauthn.backends.WebAuthnBackend",
]
LOGIN_URL = "sign_in"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "sign_in"

# A sign-in lasts 30 days from the last visit, so the installed app rarely
# asks again.
SESSION_COOKIE_AGE = 60 * 60 * 24 * 30
SESSION_SAVE_EVERY_REQUEST = True

OTP_TOTP_ISSUER = "Kosha"

# Passkeys work only from these origins, over HTTPS except on localhost. They
# default to the public URL CSRF already trusts, so it needn't be set twice;
# wildcards can't be Passkey origins.
webauthn_origins = [
    o for o in CSRF_TRUSTED_ORIGINS if o.startswith("https://") and "*" not in o
] or (["http://localhost:8000"] if DEBUG else [])
OTP_WEBAUTHN_ALLOWED_ORIGINS = (
    env.list("WEBAUTHN_ORIGINS", default=webauthn_origins)
    if webauthn_origins
    else env.list("WEBAUTHN_ORIGINS")
)
# Passkeys are bound to this domain; changing it orphans every one registered.
OTP_WEBAUTHN_RP_ID = (
    env.str("WEBAUTHN_RP_ID", default="")
    or urlsplit(OTP_WEBAUTHN_ALLOWED_ORIGINS[0]).hostname
)
OTP_WEBAUTHN_RP_NAME = "Kosha"

# A Pause: 5 wrong passwords or codes from an address pause it for an hour.
# By address only, so a stranger guessing can never pause the Owner elsewhere.
AXES_LOCKOUT_PARAMETERS = ["ip_address"]
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = timedelta(hours=1)
# Off, or a right password would wipe the count of wrong Authenticator codes.
AXES_RESET_ON_SUCCESS = False
# Tries refused during a Pause don't restart its hour.
AXES_RESET_COOL_OFF_ON_FAILURE_DURING_LOCKOUT = False
AXES_CLIENT_IP_CALLABLE = "apps.signin.client.address"
AXES_LOCKOUT_CALLABLE = "apps.signin.pause.paused_page"
# The Security log records sign-ins already.
AXES_DISABLE_ACCESS_LOG = True

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
# Project setting, not Django's. Behind a proxy every request comes from the
# proxy, so the client's address is the one the proxy adds to X-Forwarded-For.
# Without such a proxy, clients could choose their own address and escape a
# Pause.
USE_X_FORWARDED_FOR = env.bool("USE_X_FORWARDED_FOR", default=False)

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
