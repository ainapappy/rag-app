"""Modèles de l'application chatbot (≈ Eloquent, migrations auto-générées)."""

from pathlib import Path

from django.conf import settings
from django.db import models


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
