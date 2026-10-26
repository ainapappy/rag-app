"""Context processors du chatbot (variables globales des templates)."""

from django.conf import settings


def frontend(request) -> dict:
    """Expose `frontend_dev_url` : URL du serveur Vite en dev front, sinon vide."""
    return {"frontend_dev_url": settings.FRONTEND_DEV_URL}
