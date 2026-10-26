# Phase 04 : Pipeline d'ingestion et conteneur de services

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 03 terminées : config, LLM, embeddings, `VectorStore` (simple/chroma), loaders, chunkers, `Document`/`Chunk`, commandes `chat_test`, `semantic_demo`, `chunk_preview`, documents d'exemple dans `docs/`, tests verts.
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Assembler les briques : **charger → découper → embedder par lots → stocker**, avec détection des fichiers inchangés, protection contre le mélange de modèles d'embedding, et un **conteneur de services** (équivalent du Service Container) qui construit les objets selon la config.

## 4. Mini-cours Python pour développeur Laravel

- **Composition root / conteneur** : une classe `Container` qui construit et met en cache les dépendances (≈ `AppServiceProvider` + `app()->singleton(...)`). Les classes métier ne font jamais `new` de leurs dépendances.
- **Propriétés paresseuses** : `@property` + attribut privé `_llm` créé au premier accès (≈ lazy singleton). `functools.cached_property` fait cela en une ligne.
- **Hachage de fichier** : `hashlib.sha256` par blocs de lecture ≈ `hash_file('sha256', $path)`.
- **Découpage en lots** : `for i in range(0, len(items), batch_size): batch = items[i:i+batch_size]` ≈ `array_chunk`.
- **`logging`** : `logger = logging.getLogger(__name__)` ≈ `Log::info()` ; niveaux `info`, `warning`, `error`.
- **Dataclass de résultat** : `IngestionReport` ≈ DTO de retour.

## 5. Travail à réaliser

1. `rag_core/pipeline/ingestion.py` :
   - `IngestionReport` (dataclass frozen : `source`, `chunks_count`, `skipped: bool`, `error: str | None`, `duration_seconds: float`).
   - `IngestionPipeline(loader_factory, chunker, embeddings, store, batch_size)`.
   - `ingest_file(path, source=None, force=False) -> IngestionReport` :
     1. `source` par défaut = nom du fichier.
     2. Calcule le sha256 du fichier ; si `store.get_source_hash(source)` est identique et `force=False` → rapport `skipped=True`.
     3. Vérifie le modèle d'embedding : si `store.get_embedding_model()` est `None` → `set_embedding_model(embeddings.model_name)` ; s'il diffère → lève `EmbeddingModelMismatchError` (message : réindexer avec `--reset`).
     4. Charge, découpe, ajoute `file_hash` aux métadonnées de chaque chunk.
     5. Supprime l'ancienne version de la source (`delete_by_source`), embed par lots, `store.add`.
     6. Une erreur sur un fichier est capturée dans le rapport (`error`) **dans `ingest_directory`**, mais **levée** dans `ingest_file`.
   - `ingest_directory(path, force=False) -> list[IngestionReport]` : parcourt récursivement les fichiers supportés (ignorer les autres avec un log), un rapport par fichier, sans interrompre le lot en cas d'erreur.
   - `remove_source(source) -> int`.
2. `rag_core/container.py` : `Container(settings, *, llm=None, embeddings=None, store=None)` avec propriétés paresseuses : `llm`, `embeddings`, `store`, `loader_factory`, `chunker`, `ingestion_pipeline`. Les paramètres nommés servent à **injecter des faux en test**. Fonction `get_container()` (cache) pour l'usage normal, et `reset_container()` pour les tests.
   - La propriété `rag_pipeline` sera ajoutée en phase 05.
3. Commande `ingest` : `python manage.py ingest <chemin> [--force] [--reset] [--list]`.
   - `--reset` : `store.clear()` puis réinitialise le modèle d'embedding.
   - `--list` : affiche les sources indexées et le nombre total de chunks, puis quitte.
   - Affiche un tableau lisible des rapports (source, chunks, statut, durée) et un résumé final ; code de sortie non nul si au moins une erreur.
4. `tests/conftest.py` : fixtures partagées `fake_llm`, `fake_embeddings`, `tmp_store` (`SimpleVectorStore` sur `tmp_path`), `container` (avec les faux injectés).
5. Journalisation : configurer `logging` dans `config/settings.py` (console, niveau configurable par `DJANGO_LOG_LEVEL`) ; aucun secret journalisé.
6. Mettre à jour `CONVENTIONS.md` : « Les classes ne construisent pas leurs dépendances ; seul le `Container` assemble ».

## 6. Contraintes

- `IngestionPipeline` ne connaît que des **interfaces** (`DocumentLoader` via `LoaderFactory`, `Chunker`, `EmbeddingProvider`, `VectorStore`).
- Pas de logique d'ingestion dans la commande Django : elle ne fait qu'appeler le pipeline et afficher.
- Ne pas encore écrire le retriever ni le RAG (phase 05).

## 7. Tests à écrire

- `tests/test_ingestion.py` (avec `FakeEmbeddingProvider` + `SimpleVectorStore` temporaire) :
  - ingestion d'un fichier → bon nombre de chunks, `store.count()` correct ;
  - ré-ingestion identique → `skipped=True` ; avec `force=True` → réindexé sans doublons ;
  - fichier modifié → ancien contenu remplacé ;
  - changement de modèle d'embedding → `EmbeddingModelMismatchError` ;
  - dossier contenant un fichier invalide → les autres sont indexés, l'erreur figure dans le rapport ;
  - traitement par lots (vérifier le nombre d'appels à `embed` avec un petit `batch_size`) ;
  - `remove_source`.
- `tests/test_container.py` : instanciation paresseuse, injection de faux, `reset_container()`.
- Tests de la commande `ingest` via `call_command` (sortie capturée).

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre.
- [ ] `python manage.py ingest docs/` indexe les documents d'exemple avec Ollama (embeddings réels).
- [ ] Relancer la même commande : tous les fichiers sont `skipped`.
- [ ] `python manage.py ingest --list` affiche les sources et le nombre de chunks.
- [ ] Changer `EMBED_MODEL` puis relancer `ingest docs/` : erreur claire proposant `--reset`.
- [ ] `python manage.py ingest docs/ --reset` reconstruit l'index.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **Index mélangé** : réindexer après changement de modèle d'embedding, sinon les scores n'ont aucun sens.
- **Doublons** : toujours supprimer l'ancienne version d'une source avant d'ajouter la nouvelle.
- **Lots trop gros** : certaines API d'embeddings limitent le nombre de textes par requête (d'où `EMBED_BATCH_SIZE`).
- **État global dans les tests** : réinitialiser le conteneur entre les tests.

## 11. Livrable de la phase

`python manage.py ingest docs/` qui indexe proprement un dossier (idempotent, protégé contre le mélange de modèles), avec un `Container` qui assemble toutes les dépendances.
