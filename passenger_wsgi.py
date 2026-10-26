"""Point d'entrée WSGI pour les hébergeurs type Passenger (≈ public/index.php).

Chaque ligne sert à charger l'application Django quand le serveur de
l'hébergeur importe ce fichier.
"""

import os
import sys

# 1. Ajouter la racine du projet au chemin Python : permet d'importer
#    `config` et `chatbot` quel que soit le dossier de travail du serveur.
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

# 2. Indiquer quel module de settings charger (config/settings.py).
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# 3. Créer l'objet WSGI `application` : c'est LUI que Passenger/gunicorn/uWSGI
#    appellent pour chaque requête HTTP.
from django.core.wsgi import get_wsgi_application  # noqa: E402  (après sys.path, volontaire)

application = get_wsgi_application()
