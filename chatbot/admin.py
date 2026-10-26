"""Admin Django des documents : upload, indexation, suppression propre.

Aucune logique d'indexation ici : l'admin délègue à `DocumentIndexingService`.
"""

from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html

from chatbot.models import Document
from chatbot.services import DocumentIndexingService
from chatbot.validators import UploadValidator

_STATUS_COLORS = {
    Document.Status.PENDING: "#888",
    Document.Status.INDEXING: "#b8860b",
    Document.Status.INDEXED: "#1a7f37",
    Document.Status.ERROR: "#c62828",
}


class DocumentForm(forms.ModelForm):
    """Formulaire d'upload : valide extension et taille avant sauvegarde."""

    class Meta:
        model = Document
        fields = ("title", "file")

    def clean_file(self) -> object:
        uploaded = self.cleaned_data["file"]
        UploadValidator().validate(uploaded)
        return uploaded


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    """Back-office des documents (≈ Filament : fourni, juste configuré)."""

    form = DocumentForm
    list_display = ("title", "original_name", "status_badge", "chunks_count",
                    "created_at", "indexed_at")
    list_filter = ("status",)
    search_fields = ("title", "original_name")
    readonly_fields = ("original_name", "status", "chunks_count", "error_message",
                       "indexed_at", "created_at")
    actions = ("action_index_documents", "action_remove_from_index", "action_reindex")

    def status_badge(self, obj: Document) -> str:
        """Statut coloré dans la liste."""
        color = _STATUS_COLORS.get(obj.status, "#888")
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_status_display(),
        )

    status_badge.short_description = "statut"

    # -- Enregistrement ------------------------------------------------------

    def save_model(self, request, obj: Document, form, change: bool) -> None:
        """Après l'upload : indexation automatique si INDEX_ON_UPLOAD est actif.

        Limite documentée : l'indexation se fait dans la requête web ; un gros
        PDF peut être lent. Une tâche d'arrière-plan est une amélioration future.
        """
        super().save_model(request, obj, form, change)
        if not change and self._index_on_upload():
            DocumentIndexingService().index(obj)
            if obj.status == Document.Status.ERROR:
                self.message_user(
                    request,
                    f"Document enregistré mais indexation échouée : {obj.error_message}",
                    level=messages.ERROR,
                )
            else:
                self.message_user(
                    request,
                    f"Document indexé ({obj.chunks_count} chunks).",
                    level=messages.SUCCESS,
                )

    @staticmethod
    def _index_on_upload() -> bool:
        from django.conf import settings as django_settings

        return getattr(django_settings, "INDEX_ON_UPLOAD", True)

    # -- Actions -----------------------------------------------------------------

    @admin.action(description="Indexer les documents sélectionnés")
    def action_index_documents(self, request, queryset) -> None:
        """Indexe les documents en attente ou en erreur."""
        targets = queryset.exclude(status=Document.Status.INDEXED)
        skipped = queryset.count() - targets.count()
        self._run_indexing(request, targets, verb="indexés")
        if skipped:
            self.message_user(
                request, f"{skipped} document(s) déjà indexé(s) ignoré(s).",
                level=messages.INFO,
            )

    @admin.action(description="Réindexer (forcer)")
    def action_reindex(self, request, queryset) -> None:
        """Réindexe tous les documents sélectionnés, même déjà indexés."""
        self._run_indexing(request, queryset, verb="réindexés")

    @admin.action(description="Retirer de l'index")
    def action_remove_from_index(self, request, queryset) -> None:
        """Retire les chunks de l'index sans supprimer les documents."""
        service = DocumentIndexingService()
        for document in queryset:
            service.remove_from_index(document)
        self.message_user(
            request, f"{queryset.count()} document(s) retiré(s) de l'index.",
            level=messages.SUCCESS,
        )

    def _run_indexing(self, request, queryset, verb: str) -> None:
        if not queryset.exists():
            self.message_user(request, "Aucun document à traiter.", level=messages.INFO)
            return
        service = DocumentIndexingService()
        for document in queryset:
            service.index(document)
        ok = queryset.filter(status=Document.Status.INDEXED).count()
        failed = queryset.exclude(status=Document.Status.INDEXED).count()
        if ok:
            self.message_user(request, f"{ok} document(s) {verb} avec succès.",
                              level=messages.SUCCESS)
        if failed:
            details = "; ".join(
                f"{doc.title} : {doc.error_message}" for doc in queryset.exclude(
                    status=Document.Status.INDEXED
                )
            )
            self.message_user(request, f"{failed} échec(s) : {details}", level=messages.ERROR)

    # -- Suppression --------------------------------------------------------------

    def delete_model(self, request, obj: Document) -> None:
        """Suppression unitaire : retire l'index et le fichier physique."""
        DocumentIndexingService().remove_from_index(obj)
        obj.file.delete(save=False)  # supprime le fichier sur le disque
        super().delete_model(request, obj)

    def delete_queryset(self, request, queryset) -> None:
        """Suppression en masse : Model.delete() n'est PAS appelé par l'admin."""
        for obj in queryset:
            self.delete_model(request, obj)
