"""Vues du chatbot : classes fines qui délèguent à `ChatService`.

Aucune logique RAG ici : validation → service → réponse.
Toutes les requêtes filtrent par `user` : une conversation d'autrui → 404.
"""

from django.contrib.auth import views as auth_views
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import (
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseForbidden,
    JsonResponse,
    StreamingHttpResponse,
)
from django.shortcuts import get_object_or_404, render
from django.views import View

from chatbot.api_views import ApiLoginRequiredMixin
from chatbot.models import Conversation
from chatbot.ratelimit import default_limiter
from chatbot.services import ChatService, ping_llm
from rag_core.exceptions import RagError
from rag_core.settings import get_settings


class ChatView(LoginRequiredMixin, View):
    """Liste des conversations + conversation courante (la plus récente)."""

    def get(self, request):
        conversations = request.user.conversations.all()
        current = conversations.first()
        return render(
            request,
            "chatbot/chat.html",
            self._context(request, conversations, current),
        )

    @staticmethod
    def _context(request, conversations, current) -> dict:
        settings = get_settings()
        return {
            "conversations": conversations,
            "current": current,
            "messages": current.messages.all() if current else [],
            "streaming_enabled": settings.streaming_enabled,
        }


class ConversationDetailView(ChatView):
    """Coquille HTML d'une conversation précise (deep-link, filtrée par utilisateur)."""

    def get(self, request, pk):
        conversations = request.user.conversations.all()
        current = get_object_or_404(Conversation, pk=pk, user=request.user)
        return render(
            request, "chatbot/chat.html", self._context(request, conversations, current)
        )


class SendView(ApiLoginRequiredMixin, View):
    """Envoie une question : SSE si STREAMING_ENABLED, sinon un JSON unique."""

    def post(self, request, pk):
        conversation = get_object_or_404(Conversation, pk=pk, user=request.user)
        question = (request.POST.get("question") or "").strip()
        if not question:
            return HttpResponseBadRequest("Question vide.")
        # Frein anti-abus, par utilisateur (voir chatbot/ratelimit.py pour
        # la limite multi-processus du cache local).
        result = default_limiter().hit(f"chat-send:{request.user.pk}")
        if not result.allowed:
            return HttpResponse(
                "Trop de requêtes, réessayez dans quelques instants.",
                status=429,
                headers={"Retry-After": str(result.retry_after)},
            )
        service = ChatService()
        if get_settings().streaming_enabled:
            response = StreamingHttpResponse(
                service.stream(conversation, question), content_type="text/event-stream"
            )
            response["Cache-Control"] = "no-cache"
            response["X-Accel-Buffering"] = "no"  # pas de tampon côté proxy
            return response
        message = service.ask(conversation, question)
        return JsonResponse(
            {
                "role": message.role,
                "content": message.content,
                "sources": message.sources,
            }
        )


class HealthView(View):
    """Sonde de santé : `/health/` (public), `?deep=1` réservé au staff."""

    def get(self, request):
        if request.GET.get("deep") == "1" and not request.user.is_staff:
            return HttpResponseForbidden("Le check approfondi est réservé au staff.")

        payload: dict = {"status": "ok", "db": True}
        try:
            from rag_core.container import get_container

            store = get_container().store
            payload["index_chunks"] = store.count()
            payload["embedding_model"] = store.get_embedding_model()
        except RagError:
            payload["status"] = "degraded"
            payload["index_chunks"] = None
            payload["embedding_model"] = None

        if request.GET.get("deep") == "1":
            try:
                payload["llm"] = ping_llm()
            except RagError as exc:
                payload["llm"] = str(exc)
                payload["status"] = "degraded"
        return JsonResponse(payload)


class RateLimitedLoginView(auth_views.LoginView):
    """Login freiné par IP contre la force brute (429 + Retry-After)."""

    def post(self, request, *args, **kwargs):
        ip = request.META.get("REMOTE_ADDR", "unknown")
        result = default_limiter().hit(f"login:{ip}")
        if not result.allowed:
            return HttpResponse(
                "Trop de tentatives de connexion. Réessayez plus tard.",
                status=429,
                headers={"Retry-After": str(result.retry_after)},
            )
        return super().post(request, *args, **kwargs)


login_view = RateLimitedLoginView.as_view(template_name="registration/login.html")
logout_view = auth_views.LogoutView.as_view()
