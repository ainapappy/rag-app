"""Modèles de l'application chatbot (≈ Eloquent, migrations auto-générées)."""

from pathlib import Path

from django.conf import settings
from django.db import models
from django.utils import timezone


class Document(models.Model):
    """Un document téléversé et son état d'indexation.

    La logique d'indexation ne vit pas ici : elle est déléguée à
    `DocumentIndexingService` (couche service), comme un action Laravel.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "En attente"
        INDEXING = "indexing", "Indexation en cours"
        INDEXED = "indexed", "Indexé"
        ERROR = "error", "Erreur"

    title = models.CharField("titre", max_length=200)
    file = models.FileField("fichier", upload_to="documents/")
    original_name = models.CharField(
        "nom d'origine", max_length=255, unique=True, editable=False
    )
    status = models.CharField(
        "statut", max_length=10, choices=Status.choices, default=Status.PENDING
    )
    chunks_count = models.PositiveIntegerField("chunks indexés", default=0)
    error_message = models.TextField("message d'erreur", blank=True, default="")
    created_at = models.DateTimeField("créé le", auto_now_add=True)
    indexed_at = models.DateTimeField("indexé le", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "document"

    def __str__(self) -> str:
        return self.title

    def save(self, *args, **kwargs) -> None:
        """Renseigne `original_name` depuis le fichier au premier enregistrement."""
        if not self.original_name and self.file:
            self.original_name = Path(self.file.name).name
        super().save(*args, **kwargs)


class Conversation(models.Model):
    """Une conversation de chat, propriété d'un utilisateur (≈ scope Eloquent)."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="conversations",
        verbose_name="utilisateur",
    )
    title = models.CharField("titre", max_length=200, blank=True, default="")
    created_at = models.DateTimeField("créée le", auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "conversation"

    def __str__(self) -> str:
        return self.title or f"Conversation #{self.pk}"


class Message(models.Model):
    """Un message de conversation : rôle (user|assistant), contenu, sources."""

    ROLE_CHOICES = [("user", "Utilisateur"), ("assistant", "Assistant")]

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages",
        verbose_name="conversation",
    )
    role = models.CharField("rôle", max_length=10, choices=ROLE_CHOICES)
    content = models.TextField("contenu")
    sources = models.JSONField("sources", default=list, blank=True)
    created_at = models.DateTimeField("créé le", auto_now_add=True)

    class Meta:
        # `id` en second critère : ordre stable quand deux messages partagent
        # la même seconde (auto_now_add a une précision d'une seconde).
        ordering = ["created_at", "id"]
        verbose_name = "message"

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:50]}"


class ApiKey(models.Model):
    """Clé d'API pour l'API JSON : seul le hash est stocké, jamais la clé.

    `generate()` renvoie la clé en clair UNE SEULE FOIS (comme un mot de
    passe initial) ; `authenticate()` compare en temps constant.
    """

    name = models.CharField("nom", max_length=100)
    prefix = models.CharField(
        "préfixe", max_length=8, db_index=True, help_text="8 premiers caractères."
    )
    key_hash = models.CharField("hash de la clé", max_length=64, unique=True)
    is_active = models.BooleanField("active", default=True)
    created_at = models.DateTimeField("créée le", auto_now_add=True)
    last_used_at = models.DateTimeField("dernière utilisation", null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "clé d'API"

    def __str__(self) -> str:
        return f"{self.name} ({self.prefix}…)"

    @classmethod
    def generate(cls, name: str) -> tuple["ApiKey", str]:
        """Crée une clé ; renvoie (ApiKey, clé en clair) — à afficher une fois."""
        import hashlib
        import secrets

        raw_key = secrets.token_urlsafe(32)
        api_key = cls.objects.create(
            name=name,
            prefix=raw_key[:8],
            key_hash=hashlib.sha256(raw_key.encode("utf-8")).hexdigest(),
        )
        return api_key, raw_key

    @classmethod
    def authenticate(cls, raw_key: str) -> "ApiKey | None":
        """Valide une clé : hash sha256 comparé en temps constant."""
        import hashlib
        import hmac

        digest = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        candidate = cls.objects.filter(is_active=True, prefix=raw_key[:8]).first()
        if candidate is not None and hmac.compare_digest(candidate.key_hash, digest):
            candidate.last_used_at = timezone.now()
            candidate.save(update_fields=["last_used_at"])
            return candidate
        return None
