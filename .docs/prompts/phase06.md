# Phase 06 : Django, modèles, admin et upload de documents

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 05 terminées : tout `rag_core/` fonctionnel, `Container` avec `rag_pipeline`, commandes `ingest` et `ask`, tests verts.
- `python manage.py ask "..."` répond avec des sources.
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Gérer les documents depuis **l'admin Django** : upload, liste, statut d'indexation, actions « Indexer » / « Retirer de l'index », suppression propre (fichier + index). Le tout via une couche **service** qui appelle `rag_core`.

## 4. Mini-cours Python pour développeur Laravel

- **Modèles Django** : ≈ Eloquent. `models.CharField`, `FileField`, `ForeignKey` ; `Meta` pour l'ordre et les contraintes. **Migrations** : `makemigrations` (génère) puis `migrate` (applique), comme `php artisan make:migration` + `migrate` mais générées automatiquement depuis le modèle.
- **`TextChoices`** : ≈ enum PHP 8.1 pour le statut du document.
- **Admin Django** : ≈ Filament/Nova, fourni d'office. `ModelAdmin` avec `list_display`, `list_filter`, `actions`, `readonly_fields`.
- **Signals vs services** : les signals Django ≈ Observers Eloquent. On les **évite** ici : un service explicite (`DocumentIndexingService`) est plus lisible et testable.
- **Tests Django avec pytest-django** : `@pytest.mark.django_db` ≈ `RefreshDatabase` ; la fixture `tmp_path` et `settings` pour surcharger `MEDIA_ROOT`.
- **`FileField` et `upload_to`** : ≈ `Storage::putFile`.

## 5. Travail à réaliser

1. `chatbot/models.py` : modèle `Document` :
   - `title: CharField`, `file: FileField(upload_to="documents/")`, `original_name: CharField(unique=True, editable=False)` (renseigné automatiquement depuis le nom du fichier à l'enregistrement), `status` (`TextChoices` : `pending`, `indexing`, `indexed`, `error`, défaut `pending`), `chunks_count: PositiveIntegerField(default=0)`, `error_message: TextField(blank=True)`, `created_at`, `indexed_at` (nullable).
   - `__str__` renvoie le titre. `Meta.ordering = ["-created_at"]`.
2. `chatbot/validators.py` : fonction/classe de validation d'upload minimale pour cette phase : extension supportée via `LoaderFactory().supports(...)`, taille maximale `MAX_UPLOAD_MB` (à lire dans `django.conf.settings`, valeur par défaut du contrat). (Le durcissement complet viendra en phase 08.)
3. `config/settings.py` : exposer `MAX_UPLOAD_MB` depuis l'environnement ; s'assurer que `data/media` est utilisé comme `MEDIA_ROOT`.
4. `chatbot/services.py` : classe `DocumentIndexingService(container=None)` (si `None`, utiliser `get_container()`) :
   - `index(document) -> None` : passe en `indexing`, appelle `container.ingestion_pipeline.ingest_file(Path(document.file.path), source=document.original_name, force=True)`, puis met à jour `status="indexed"`, `chunks_count`, `indexed_at`, vide `error_message` ; en cas d'exception `RagError`, `status="error"` et `error_message` renseigné (pas de plantage de l'admin).
   - `remove_from_index(document) -> None` : appelle `remove_source`, repasse en `pending`, `chunks_count=0`.
5. `chatbot/admin.py` : `DocumentAdmin` :
   - `list_display` : titre, nom d'origine, statut (avec couleur ou icône simple), nombre de chunks, dates ; `list_filter` sur le statut ; `search_fields`.
   - Champs en lecture seule : `original_name`, `status`, `chunks_count`, `error_message`, `indexed_at`.
   - Actions : **« Indexer les documents sélectionnés »**, **« Retirer de l'index »**, **« Réindexer »** ; messages Django (`self.message_user`) résumant succès/échecs.
   - **Option : indexer automatiquement après l'upload** (`save_model`), contrôlable par une constante/booléen de config `INDEX_ON_UPLOAD = True` ; en cas d'échec, le document est enregistré avec le statut `error`.
   - Suppression : surcharger `delete_model` **et** `delete_queryset` (la suppression en masse contourne `Model.delete()`) pour retirer les chunks de l'index et supprimer le fichier physique.
6. Migrations : `python manage.py makemigrations chatbot && python manage.py migrate`.
7. Créer un super-utilisateur local (`python manage.py createsuperuser`) et documenter la procédure.
8. `tests/conftest.py` : fixture `indexing_service` avec un `Container` factice ; fixture qui force `MEDIA_ROOT` sur `tmp_path`.
9. Mettre à jour le `README.md` racine : « Gérer les documents depuis l'admin ».

## 6. Contraintes

- **Aucune logique d'indexation dans `admin.py`** : il délègue à `DocumentIndexingService`.
- Les erreurs métier sont affichées à l'utilisateur de l'admin, jamais de trace brute.
- Ne pas créer encore les vues de chat ni les modèles `Conversation`/`Message`.
- Les tests n'utilisent ni Ollama ni le vrai `MEDIA_ROOT`.

## 7. Tests à écrire

- `tests/test_document_model.py` (`django_db`) : `original_name` renseigné automatiquement ; unicité du nom d'origine ; statut par défaut.
- `tests/test_indexing_service.py` : indexation réussie (statut, `chunks_count`, `indexed_at`) ; erreur de pipeline → statut `error` avec message ; `remove_from_index` ; relance après erreur.
- `tests/test_admin.py` : action « Indexer » via le client Django (super-utilisateur) ; suppression d'un document supprime le fichier et les chunks ; upload d'un fichier non supporté refusé ; fichier trop gros refusé.

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre, `python manage.py makemigrations --check` ne détecte rien.
- [ ] Dans `/admin/`, je peux uploader un PDF ; il passe à `indexed` avec un nombre de chunks.
- [ ] `python manage.py ask "..."` répond ensuite à partir de ce document.
- [ ] Supprimer le document dans l'admin le retire aussi de l'index (`ingest --list`).
- [ ] Un fichier `.exe` ou trop volumineux est refusé avec un message clair.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **`delete_queryset`** : la suppression en masse de l'admin ne déclenche pas `Model.delete()`.
- **Indexation dans la requête web** : un gros PDF peut être lent ; acceptable ici (usage admin), à documenter comme limite (tâche d'arrière-plan = amélioration future).
- **Chemin du fichier** : utiliser `document.file.path` (chemin disque), pas `document.file.url`.
- **Nom de fichier en doublon** : l'unicité de `original_name` évite d'écraser un autre document dans l'index.

## 11. Livrable de la phase

Un back-office Django où l'on dépose des documents, les indexe d'un clic, voit leur statut, et les supprime proprement (fichier + index), le tout via un service testé.
