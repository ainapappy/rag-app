"""Endpoints JSON de l'interface Vue (phase 11).

Distincts de `chatbot/api.py` (API publique authentifiée par clé) : ici
l'utilisateur est connecté par la session Django et le CSRF est requis.
Vues fines : sérialisation → ORM/service → JsonResponse, aucune logique métier.
"""

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View

from chatbot.models import Conversation
from chatbot.services import ChatService


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


class ConversationListApiView(LoginRequiredMixin, View):
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


class ConversationDetailApiView(LoginRequiredMixin, View):
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
