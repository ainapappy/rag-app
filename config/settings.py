"""
Configuration Django du projet rag-app.

Toutes les valeurs configurables proviennent du `.env` via django-environ
(équivalent de `config()` dans Laravel). Aucune logique métier ici :
le cœur RAG vit dans `rag_core/` et n'importe jamais ce module.
"""

import logging
import re
from pathlib import Path

import environ

# BASE_DIR = racine du projet (contient manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# Initialise django-environ et charge le fichier .env s'il existe.
env = environ.Env()
environ.Env.read_env(BASE_DIR / ".env")


class SecretMaskingFilter(logging.Filter):
    """Masque les clés d'API / tokens dans les messages journalisés.

    Exemple : « X-API-Key: abc123 » devient « X-API-Key: *** ». Pour
    Authorization/Bearer, toute la fin de ligne est masquée (jetons à points).
    """

    _SIMPLE = re.compile(
        r"(?i)\b(x-api-key|api[_-]?key|token)(\s*[:=]\s*|\s+)(\S+)"
    )
    _HEADER_LINE = re.compile(
        r"(?im)\b(authorization|bearer)(\s*[:=]\s*|\s+).*$"
    )

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        masked = self._SIMPLE.sub(lambda m: f"{m.group(1)}{m.group(2)}***", message)
        masked = self._HEADER_LINE.sub(lambda m: f"{m.group(1)}{m.group(2)}***", masked)
        if masked != message:
            record.msg = masked
            record.args = None
        return True

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
    # WhiteNoise : sert les statiques compressés depuis l'application Python
    # (pratique quand on ne contrôle pas le serveur web, ex. mutualisé).
    "whitenoise.middleware.WhiteNoiseMiddleware",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                # Expose FRONTEND_DEV_URL aux templates (assets Vite).
                "chatbot.context_processors.frontend",
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

# Fichiers statiques de l'application (CSS/JS du chat, vendor).
STATICFILES_DIRS = [BASE_DIR / "static"]

# Compression à la collecte (collectstatic) ; WhiteNoise les sert.
# (Sans manifest : plus tolérant si collectstatic n'a pas encore tourné.)
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

MEDIA_ROOT = BASE_DIR / "data" / "media"

MEDIA_URL = "/media/"

# Dossiers de données : créés au démarrage s'ils manquent (hébergeur neuf).
for _data_dir in (MEDIA_ROOT, BASE_DIR / "data" / "index", BASE_DIR / "data" / "logs"):
    _data_dir.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Authentification (chat accessible uniquement connecté)
# ---------------------------------------------------------------------------

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "chat"

LOGOUT_REDIRECT_URL = "login"

# Type de champ auto par défaut pour les clés primaires.
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Options applicatives (lues aussi par chatbot/)
# ---------------------------------------------------------------------------

# Taille maximale d'un upload en Mo (contrat : MAX_UPLOAD_MB).
MAX_UPLOAD_MB = env.int("MAX_UPLOAD_MB", default=10)

# Indexer automatiquement un document juste après l'upload dans l'admin.
INDEX_ON_UPLOAD = env.bool("INDEX_ON_UPLOAD", default=True)

# URL du serveur Vite en développement front (ex. http://localhost:5173).
# Vide en production : les assets construits sont servis depuis static/.
FRONTEND_DEV_URL = env("FRONTEND_DEV_URL", default="")

# Limite de requêtes par fenêtre de 60 s (API par clé, chat par utilisateur,
# login par IP). Voir chatbot/ratelimit.py pour la limite multi-processus.
RATE_LIMIT_PER_MINUTE = env.int("RATE_LIMIT_PER_MINUTE", default=30)

# ---------------------------------------------------------------------------
# En-têtes de sécurité
# ---------------------------------------------------------------------------

# Toujours actives (sans risque même en local).
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True

# Uniquement en production (DEBUG=False) : HTTPS supposé en face.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = 3600  # modéré au départ ; monter ensuite à 31536000
    SECURE_REFERRER_POLICY = "same-origin"
    # ⚠️ SECURE_SSL_REDIRECT volontairement NON activé : dépend de la façon
    # dont PlanetHoster transmet HTTPS (proxy ?). Vérifier/poser
    # SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https") avec
    # l'hébergeur avant d'activer la redirection.

# ---------------------------------------------------------------------------
# Journalisation (console + fichier tournant, secrets masqués)
# ---------------------------------------------------------------------------

LOG_LEVEL = env("DJANGO_LOG_LEVEL", default="INFO")

LOG_DIR = BASE_DIR / "data" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Filtre : masque les clés d'API / tokens dans les messages journalisés.
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {
        "mask_secrets": {
            "()": "config.settings.SecretMaskingFilter",
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "filters": ["mask_secrets"],
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 5 * 1024 * 1024,  # 5 Mo par fichier
            "backupCount": 3,
            "encoding": "utf-8",
            "filters": ["mask_secrets"],
        },
    },
    # Les SDK httpx/openai sont très bavards en INFO : on les calme.
    "loggers": {
        "httpx": {"handlers": ["console", "file"], "level": "WARNING", "propagate": False},
        "httpx2": {"handlers": ["console", "file"], "level": "WARNING", "propagate": False},
        "openai": {"handlers": ["console", "file"], "level": "WARNING", "propagate": False},
    },
    "root": {
        "handlers": ["console", "file"],
        "level": LOG_LEVEL,
    },
}
