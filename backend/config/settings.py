"""
Settings come from the environment, so the same image runs the hosted instance,
a self-hosted server and an offline box. See deploy/.env.example.
"""

import os
from pathlib import Path

import dj_database_url


def env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def env_bool(name: str, default: bool = False) -> bool:
    return env(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_list(name: str, default: str = "") -> list[str]:
    return [v.strip() for v in env(name, default).split(",") if v.strip()]


BASE_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BASE_DIR.parent

DEBUG = env_bool("DEBUG")
SECRET_KEY = env("SECRET_KEY", "dev-insecure-change-me" if DEBUG else "")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set")

# Where people reach the instance, e.g. https://risa-dash.kobolabs.dev or http://risa.kobo.local
PUBLIC_URL = env("PUBLIC_URL", "http://localhost:8000").rstrip("/")
ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "*")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS", PUBLIC_URL)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    "procrastinate.contrib.django",
    "risa",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

DATABASES = {
    "default": dj_database_url.parse(
        env("DATABASE_URL", "postgis://risa:risa@localhost:5432/risa"),
        engine="django.contrib.gis.db.backends.postgis",
        conn_max_age=60,
    )
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LANGUAGE_CODE = "en-gb"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---- static: Django admin plus the built frontend (served as the SPA) -----------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
FRONTEND_DIST = Path(env("FRONTEND_DIST", str(REPO_DIR / "frontend" / "dist")))
WHITENOISE_ROOT = FRONTEND_DIST if FRONTEND_DIST.exists() else None
STORAGES = {
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# ---- file storage: s3 (DO Spaces, MinIO, ...) or filesystem -----------------------
STORAGE = env("STORAGE", "filesystem")
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))
MEDIA_URL = "/media/"
if STORAGE == "s3":
    STORAGES["default"] = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "bucket_name": env("S3_BUCKET"),
            "endpoint_url": env("S3_ENDPOINT_URL") or None,
            "region_name": env("S3_REGION") or None,
            "access_key": env("S3_ACCESS_KEY_ID"),
            "secret_key": env("S3_SECRET_ACCESS_KEY"),
            "location": env("S3_PREFIX", ""),
            "default_acl": "private",
            "file_overwrite": True,
            "querystring_auth": True,
            "querystring_expire": 6 * 3600,
        },
    }
    # Imagery (COGs) is public-read under an unguessable key so the browser and QGIS
    # can range-read it straight from the bucket/CDN. Everything else is presigned.
    MEDIA_PUBLIC_URL = env("MEDIA_PUBLIC_URL", "").rstrip("/")
else:
    STORAGES["default"] = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(MEDIA_ROOT), "base_url": MEDIA_URL},
    }
    MEDIA_PUBLIC_URL = ""

# Request bodies: upload chunks are 8 MB
UPLOAD_CHUNK_SIZE = 8 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = UPLOAD_CHUNK_SIZE + 1024 * 1024
MAX_UPLOAD_SIZE = int(env("MAX_UPLOAD_SIZE", str(8 * 1024**3)))

# ---- access ---------------------------------------------------------------------
# Creating a response needs this key when set (the hosted instance sets it).
CREATE_KEY = env("CREATE_KEY")
# false: viewing needs the response's edit key too (for instances that want nothing public)
READ_ONLY_PUBLIC = env_bool("READ_ONLY_PUBLIC", True)
# Encrypts Kobo tokens at rest. Defaults to a key derived from SECRET_KEY.
TOKEN_KEY = env("TOKEN_KEY")

# ---- Kobo -------------------------------------------------------------------------
# Servers this instance may connect to. An http:// server is accepted only when listed
# exactly (e.g. http://kf.kobo.local on a box); the token is only sent to that server.
ALLOWED_SERVERS = env_list("ALLOWED_SERVERS", "https://kf.kobotoolbox.org,https://eu.kobotoolbox.org")
KOBO_SYNC_MINUTES = int(env("KOBO_SYNC_MINUTES", "10"))

# ---- maps -------------------------------------------------------------------------
# false on an offline box: hides basemaps that need the internet
ONLINE_BASEMAPS = env_bool("ONLINE_BASEMAPS", True)
# Local PMTiles basemaps loaded with `manage.py pack load`, under MEDIA_ROOT/basemaps
GLYPHS_URL = env("GLYPHS_URL", "https://tiles.openfreemap.org/fonts/{fontstack}/{range}.pbf")

# ---- print ------------------------------------------------------------------------
# The worker opens the print route here. Inside compose: http://web:8000
PRINT_BASE_URL = env("PRINT_BASE_URL", PUBLIC_URL).rstrip("/")

SYMBOLOGY_FILE = Path(env("SYMBOLOGY_FILE", str(REPO_DIR / "symbology" / "risa.json")))

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
}
