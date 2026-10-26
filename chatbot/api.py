"""API JSON (django-ninja) protégée par clé d'API.

Endpoints montés sur /api/ ; documentation OpenAPI sur /api/docs.
Les endpoints restent fins : la logique vit dans les services.
"""

from dataclasses import asdict
from datetime import datetime

from django.core.exceptions import ValidationError
from django.http import HttpRequest
from ninja import File, Form, NinjaAPI, Schema, Status, UploadedFile
from ninja.security import APIKeyHeader
from pydantic import Field

from chatbot.models import ApiKey, Document
from chatbot.ratelimit import default_limiter
from chatbot.services import ApiChatService, DocumentIndexingService
from chatbot.validators import UploadValidator
from rag_core.exceptions import RagError
from rag_core.models import ChatMessage


class ApiKeyAuth(APIKeyHeader):
    """Authentification par en-tête X-API-Key (≈ middleware auth:api)."""

    param_name = "X-API-Key"

    def authenticate(self, request: HttpRequest, key: str | None) -> str | None:
        if not key:  # en-tête absent → None → 401 par ninja
            return None
        api_key = ApiKey.authenticate(key)
        if api_key is None:
            from ninja.errors import HttpError

            raise HttpError(401, "Clé d'API absente, invalide ou désactivée.")
        request.api_key = api_key
        return key


# ---------------------------------------------------------------------------
# Schémas (≈ API Resources + FormRequest)
# ---------------------------------------------------------------------------


class HistoryItem(Schema):
    role: str = Field(pattern="^(user|assistant|system)$")
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(Schema):
    question: str = Field(min_length=1, max_length=2000)
    history: list[HistoryItem] = []


class SourceOut(Schema):
    source: str
    page: int | None
    score: float
    excerpt: str


class ChatResponse(Schema):
    answer: str
    found: bool
    sources: list[SourceOut]


class DocumentOut(Schema):
    id: int
    title: str
    original_name: str
    status: str
    chunks_count: int
    indexed_at: datetime | None



# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------

api = NinjaAPI(title="RAG API", version="1.0", auth=ApiKeyAuth())


class RateLimited(Exception):
    """Lève une 429 avec en-tête Retry-After (gérée par le handler ci-dessous)."""

    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after


def _check_rate_limit(request: HttpRequest) -> None:
    """Applique la limite par clé d'API ; lève `RateLimited` si dépassée."""
    result = default_limiter().hit(f"api-chat:{request.api_key.pk}")
    if not result.allowed:
        raise RateLimited(result.retry_after)


@api.post("/chat", response=ChatResponse)
def chat(request, payload: ChatRequest):
    """Répond à une question à partir des documents (sans persistance)."""
    _check_rate_limit(request)
    history = tuple(
        ChatMessage(role=item.role, content=item.content) for item in payload.history
    )
    answer = ApiChatService().ask(payload.question, history=history)
    return {
        "answer": answer.text,
        "found": answer.found,
        "sources": [asdict(source) for source in answer.sources],
    }


@api.get("/documents", response=list[DocumentOut])
def list_documents(request):
    return Document.objects.all()


@api.post("/documents", response={201: DocumentOut})
def upload_document(
    request,
    title: str = Form(...),  # noqa: B008
    file: UploadedFile = File(...),  # noqa: B008
):
    """Téléverse un document et l'indexe immédiatement (via le service)."""
    if not 1 <= len(title) <= 200:
        from ninja.errors import HttpError

        raise HttpError(422, "Le titre doit contenir entre 1 et 200 caractères.")
    validator = UploadValidator()
    try:
        validator.validate(file)
        clean_name = validator.clean_name(file.name)
    except ValidationError as exc:
        from ninja.errors import HttpError

        raise HttpError(422, "; ".join(exc.messages)) from exc

    document = Document(title=title)
    document.file.save(clean_name, file, save=True)
    DocumentIndexingService().index(document)
    return Status(201, document)


@api.delete("/documents/{document_id}")
def delete_document(request, document_id: int):
    document = Document.objects.filter(pk=document_id).first()
    if document is None:
        from ninja.errors import HttpError

        raise HttpError(404, "Document introuvable.")
    service = DocumentIndexingService()
    service.purge(document)
    document.delete()
    return {"deleted": document_id}


@api.get("/health", auth=None)
def health(request):
    """État simple de l'application (sans authentification)."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# Gestionnaires d'exceptions : messages JSON stables, aucune trace interne
# ---------------------------------------------------------------------------


@api.exception_handler(RagError)
def rag_error_handler(request, exc: RagError):
    """Erreur métier RAG → 502 avec le message lisible (pas de trace interne)."""
    return api.create_response(request, {"detail": str(exc)}, status=502)


@api.exception_handler(RateLimited)
def rate_limited_handler(request, exc: RateLimited):
    """Quota dépassé → 429 avec Retry-After."""
    response = api.create_response(
        request, {"detail": "Limite de requêtes atteinte, réessayez plus tard."}, status=429
    )
    response["Retry-After"] = str(exc.retry_after)
    return response
