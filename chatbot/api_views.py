"""Endpoints JSON de l'interface Vue (phase 11).

Distincts de `chatbot/api.py` (API publique authentifiée par clé) : ici
l'utilisateur est connecté par la session Django et le CSRF est requis.
Vues fines : sérialisation → ORM/service → JsonResponse, aucune logique métier.
"""

import json

from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login
from django.contrib.auth import logout as auth_logout
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View
from django.views.decorators.csrf import ensure_csrf_cookie

from chatbot.models import Conversation
from chatbot.ratelimit import default_limiter
from chatbot.services import ChatService


class ApiLoginRequiredMixin(View):
    """Pour les endpoints JSON : 401 au lieu d'une redirection HTML (302).

    Un `fetch` suit les redirections et récupérerait la page de connexion
    (HTML) avec un statut 200 : le front ne pourrait pas détecter la fin de
    session. Un 401 franc est déclenchable et interceptable.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": "Authentification requise."}, status=401)
        return super().dispatch(request, *args, **kwargs)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class MeApiView(View):
    """`GET chat/api/me/` : état de session pour le front Vue.

    Public (jamais de 401) : c'est le premier appel du front, il pose aussi
    le cookie CSRF pour les POST/DELETE ultérieurs.
    """

    def get(self, request):
        return JsonResponse(
            {
                "authenticated": request.user.is_authenticated,
                "username": request.user.username if request.user.is_authenticated else None,
            }
        )


class LoginApiView(View):
    """`POST accounts/api/login/` : connexion session en JSON.

    Même mécanisme que la page Django (`authenticate` + `login`) et le même
    frein anti-force-brute par IP.
    """

    def post(self, request):
        ip = request.META.get("REMOTE_ADDR", "unknown")
        result = default_limiter().hit(f"login:{ip}")
        if not result.allowed:
            return JsonResponse(
                {"error": "Trop de tentatives. Réessayez plus tard."},
                status=429,
            )
        try:
            payload = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            payload = {}
        username = str(payload.get("username") or "")
        password = str(payload.get("password") or "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({"error": "Identifiants invalides."}, status=400)
        auth_login(request, user)
        return JsonResponse({"authenticated": True, "username": user.username})


class LogoutApiView(View):
    """`POST accounts/api/logout/` : déconnexion session (CSRF requis)."""

    def post(self, request):
        auth_logout(request)
        return JsonResponse({"authenticated": False})


def _conversation_data(conversation: Conversation) -> dict:
    """Sérialise une conversation pour le front Vue."""
    return {
        "id": conversation.pk,
        "title": conversation.title or "",
        "created_at": conversation.created_at.isoformat(),
    }


def _message_data(message) -> dict:
    """Sérialise un message (sources incluses, format des dataclasses rag_core)."""
    return {
        "id": message.pk,
        "role": message.role,
        "content": message.content,
        "sources": message.sources,
        "created_at": message.created_at.isoformat(),
    }


class ConversationListApiView(ApiLoginRequiredMixin, View):
    """`GET` : liste des conversations de l'utilisateur ; `POST` : création."""

    def get(self, request):
        conversations = request.user.conversations.all()
        return JsonResponse(
            {"conversations": [_conversation_data(c) for c in conversations]}
        )

    def post(self, request):
        try:
            payload = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"error": "Corps JSON invalide."}, status=400)
        if not isinstance(payload, dict):
            return JsonResponse({"error": "Corps JSON invalide."}, status=400)
        title = str(payload.get("title") or "")[: ChatService.TITLE_MAX_CHARS]
        conversation = Conversation.objects.create(user=request.user, title=title)
        return JsonResponse(_conversation_data(conversation), status=201)


class ConversationDetailApiView(ApiLoginRequiredMixin, View):
    """`GET` : détail + messages ; `DELETE` : suppression (définitive)."""

    def get(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
        return JsonResponse(
            {
                "conversation": _conversation_data(conversation),
                "messages": [_message_data(m) for m in conversation.messages.all()],
            }
        )

    def delete(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
        conversation.delete()
        return HttpResponse(status=204)
