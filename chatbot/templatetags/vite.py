"""Templatetags Vite : résout les assets du front via le manifest de build.

Le manifest (`.vite/manifest.json`) fait correspondre le point d'entrée
(`src/main.ts`) aux noms de fichiers construits, qui contiennent un hash
changeant : jamais de nom de fichier en dur dans les templates.
"""

import json
import logging
from pathlib import Path

from django import template
from django.conf import settings

register = template.Library()

logger = logging.getLogger(__name__)

# Le build Vite sort dans static/chatbot/app/ (voir frontend/vite.config.ts).
_MANIFEST_PATH = Path(settings.BASE_DIR) / "static" / "chatbot" / "app" / ".vite" / "manifest.json"


@register.simple_tag
def vite_js(entry: str) -> str:
    """URL du fichier JS construit pour `entry` ("" si le front n'est pas construit)."""
    chunk = _load_manifest().get(entry)
    if chunk is None:
        return ""
    return f"{settings.STATIC_URL}chatbot/app/{chunk['file']}"


@register.simple_tag
def vite_css(entry: str) -> str:
    """URL de la feuille de style de `entry` ("" en l'absence de CSS extrait)."""
    chunk = _load_manifest().get(entry)
    if chunk is None:
        return ""
    css_files = [f for f in chunk.get("css", []) if f.endswith(".css")]
    return f"{settings.STATIC_URL}chatbot/app/{css_files[0]}" if css_files else ""


def _load_manifest() -> dict:
    """Lit le manifest Vite ; en cas d'absence, journalise et renvoie un dict vide.

    On ne lève pas d'exception : le template affiche un bandeau clair à la
    place de l'interface plutôt qu'une page blanche silencieuse (ou un 500).
    """
    try:
        return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning(
            "Manifest Vite introuvable (%s) : lancez « npm install && npm run build » "
            "dans frontend/, puis collectstatic.",
            _MANIFEST_PATH,
        )
        return {}
