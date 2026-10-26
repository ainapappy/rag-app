"""
Configuration Django du projet rag-app.

Toutes les valeurs configurables proviennent du `.env` via django-environ
(équivalent de `config()` dans Laravel). Aucune logique métier ici :
le cœur RAG vit dans `rag_core/` et n'importe jamais ce module.
"""

from pathlib import Path

import environ

# BASE_DIR = racine du projet (contient manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialise django-environ et charge le fichier .env s'il existe.
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Sécurité / Django de base
# ---------------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env.bool("DJANGO_DEBUG", default=True)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Application métier (couche fine par-dessus rag_core).
    "chatbot",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# Base de données (SQLite par défaut)
# ---------------------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# ---------------------------------------------------------------------------
# Règles de validation des mots de passe
# ---------------------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalisation
# ---------------------------------------------------------------------------

LANGUAGE_CODE = "fr"

TIME_ZONE = "Indian/Antananarivo"

USE_I18N = True

USE_TZ = True

# ---------------------------------------------------------------------------
# Fichiers statiques et médias
# ---------------------------------------------------------------------------

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_ROOT = BASE_DIR / "data" / "media"

MEDIA_URL = "/media/"

# Type de champ auto par défaut pour les clés primaires.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Journalisation
# ---------------------------------------------------------------------------

LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {
        "console": {"class": "logging.StreamHandler"},
    },
    # Les SDK httpx/openai sont très bavards en INFO : on les calme.
    "loggers": {
        "httpx": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "httpx2": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "openai": {"handlers": ["console"], "level": "WARNING", "propagate": False},
    },
    "root": {
        "handlers": ["console"],
        "level": LOG_LEVEL,
    },
}
