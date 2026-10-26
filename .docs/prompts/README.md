# Prompts du projet `rag-app` (Django + Ollama + RAG)

Ce dossier contient **12 prompts** (`phase00.md` à `phase11.md`). Exécutés **dans l'ordre**, un par un, par un agent de code (Claude Code, Cursor...), ils produisent une application RAG complète, testée et déployable.

## Mode d'emploi

1. Créer un dossier vide `rag-app/`, y copier ce dossier `prompts/`, puis l'ouvrir avec l'agent.
2. Dire à l'agent : **« Exécute `prompts/phase00.md` »**.
3. Quand l'agent a terminé, **vérifier les critères d'acceptation** (section 8 de la phase), faire le commit proposé, puis passer à la phase suivante.
4. Ne jamais sauter une phase. Si une phase échoue, la corriger avant de continuer.
5. Chaque phase est autonome : elle rappelle le contexte et vérifie l'état du dépôt avant de commencer.

## Correspondance indicative sur 7 jours

| Jour | Phases | Résultat |
|---|---|---|
| 1 | phase00 + phase01 | Environnement prêt, LLM local interrogé par une commande |
| 2 | phase02 | Embeddings et recherche sémantique |
| 3 | phase03 + phase04 | Documents chargés, découpés, indexés |
| 4 | phase05 | RAG complet en ligne de commande, avec sources |
| 5 | phase06 + phase07 | Admin Django et chatbot web en streaming |
| 6 | phase08 + phase09 | API sécurisée, évaluation et réglages |
| 7 | phase10 | Déploiement et livraison |
| + | phase11 (évolution) | Front du chatbot en Vue 3 + Reka UI + Tailwind |

## Contrat d'architecture (à respecter à l'identique dans toutes les phases)

### Variables d'environnement (`.env`)

| Variable | Défaut local | Rôle |
|---|---|---|
| `DJANGO_SECRET_KEY` | (générée) | Clé secrète Django |
| `DJANGO_DEBUG` | `True` | `False` en production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hôtes autorisés |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | (vide) | Origines `https://...` en production |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | API compatible OpenAI |
| `LLM_API_KEY` | `ollama` | Clé API |
| `LLM_MODEL` | `llama3.2:3b` | Modèle de chat |
| `LLM_TEMPERATURE` | `0.2` | Température |
| `EMBED_BASE_URL` | `http://localhost:11434/v1` | API d'embeddings |
| `EMBED_API_KEY` | `ollama` | Clé API embeddings |
| `EMBED_MODEL` | `nomic-embed-text` | Modèle d'embeddings |
| `EMBED_BATCH_SIZE` | `32` | Taille des lots d'embeddings |
| `VECTOR_STORE` | `simple` | `simple` ou `chroma` |
| `VECTOR_STORE_PATH` | `data/index` | Dossier de l'index |
| `CHUNKER_STRATEGY` | `fixed` | `fixed` ou `paragraph` |
| `CHUNK_SIZE` | `700` | Taille d'un chunk (caractères) |
| `CHUNK_OVERLAP` | `100` | Chevauchement (caractères) |
| `TOP_K` | `4` | Nombre de chunks retrouvés |
| `MIN_SCORE` | `0.35` | Score de similarité minimal |
| `HISTORY_WINDOW` | `6` | Nombre de messages d'historique gardés |
| `STREAMING_ENABLED` | `True` | Streaming des réponses |
| `MAX_UPLOAD_MB` | `10` | Taille maximale d'un upload |
| `RATE_LIMIT_PER_MINUTE` | `30` | Limite de requêtes par minute |
| `RETRIEVER` | `vector` | `vector` ou `hybrid` (BM25 + vectoriel, phase 09) |
| `INDEX_ON_UPLOAD` | `True` | Indexer automatiquement après l'upload dans l'admin |
| `DJANGO_LOG_LEVEL` | `INFO` | Niveau de journalisation |
| `FRONTEND_DEV_URL` | (vide) | URL du serveur Vite en développement front (phase 11) |

### Package `rag_core/` (Python pur, aucun import de Django)

```
rag_core/
├── settings.py        Settings (pydantic-settings), get_settings()
├── exceptions.py      RagError > ConfigError, LLMError, EmbeddingError, LoaderError,
│                      UnsupportedFileTypeError(LoaderError), VectorStoreError,
│                      EmbeddingModelMismatchError(VectorStoreError)
├── models.py          dataclasses frozen : ChatMessage(role, content), Document(source, content, page, metadata),
│                      Chunk(id, text, source, page, index, metadata) + Chunk.make_id(source, page, index),
│                      SearchResult(chunk, score), Source(source, page, score, excerpt),
│                      Answer(text, sources, found), StreamedAnswer(sources, found, tokens)
├── container.py       Container(settings, *, llm=None, embeddings=None, store=None), get_container()
├── llm/               base.LLMClient(chat, stream) · openai_compatible.OpenAICompatibleLLM
│                      · fake.FakeLLM · factory.LLMFactory.create(settings)
├── embeddings/        base.EmbeddingProvider(model_name, embed, embed_query) · openai_compatible.OpenAICompatibleEmbeddings
│                      · fake.FakeEmbeddingProvider · factory.EmbeddingFactory.create(settings)
│                      · similarity.cosine_similarity / cosine_similarity_matrix
├── vectorstore/       base.VectorStore · simple.SimpleVectorStore · chroma.ChromaVectorStore
│                      · factory.VectorStoreFactory.create(settings)
├── loaders/           base.DocumentLoader · txt.TxtLoader · markdown.MarkdownLoader · pdf.PdfLoader
│                      · factory.LoaderFactory (for_path, supports, supported_extensions)
├── chunking/          base.Chunker · fixed_size.FixedSizeChunker · paragraph.ParagraphChunker
│                      · factory.ChunkerFactory.create(settings)
├── retrieval/         retriever.Retriever(embeddings, store, top_k, min_score) · bm25.Bm25Index · hybrid.HybridRetriever (phase09)
├── evaluation/        models · dataset.EvalDataset · metrics · evaluator.RagEvaluator · judge.FaithfulnessJudge (phase09)
├── prompting/         prompt_builder.PromptBuilder · query_rewriter.QueryRewriter
└── pipeline/          ingestion.IngestionPipeline + IngestionReport · rag.RagPipeline
```

### Interface `VectorStore` (méthodes exactes)

`add(chunks, embeddings) -> None` · `search(query_embedding, top_k) -> list[SearchResult]` · `delete_by_source(source) -> int` · `count() -> int` · `list_sources() -> list[str]` · `get_source_hash(source) -> str | None` · `iter_chunks() -> Iterator[Chunk]` · `get_embedding_model() -> str | None` · `set_embedding_model(name) -> None` · `clear() -> None`

### Interface `LLMClient`

`chat(messages: list[ChatMessage]) -> str` · `stream(messages: list[ChatMessage]) -> Iterator[str]`

### Interface `EmbeddingProvider`

`model_name` (propriété) · `embed(texts: list[str]) -> list[list[float]]` · `embed_query(text: str) -> list[float]`

### Pipelines

- `IngestionPipeline(loader_factory, chunker, embeddings, store, batch_size)` : `ingest_file(path, source=None, force=False) -> IngestionReport`, `ingest_directory(path, force=False) -> list[IngestionReport]`, `remove_source(source) -> int`
- `RagPipeline(retriever, prompt_builder, llm, rewriter=None)` : `ask(question, history=()) -> Answer`, `ask_stream(question, history=()) -> StreamedAnswer`
- Message fixe quand rien n'est trouvé : constante `NO_ANSWER_MESSAGE` dans `rag_core/pipeline/rag.py`.

### Application Django `chatbot/`

- Modèles : `Document(title, file, original_name [unique], status [pending|indexing|indexed|error], chunks_count, error_message, created_at, indexed_at)`, `Conversation(user, title, created_at)`, `Message(conversation, role, content, sources [JSON], created_at)`, `ApiKey(name, prefix, key_hash, is_active, created_at, last_used_at)`
- Services (`chatbot/services.py`) : `DocumentIndexingService(container=None)` avec `index(document)`, `remove_from_index(document)` ; `ChatService(container=None)` avec `ask(conversation, question)`, `stream(conversation, question)`
- Autres classes : `UploadValidator` (`chatbot/validators.py`), `RateLimiter` (`chatbot/ratelimit.py`), `ApiKeyAuth` (`chatbot/api.py`)
- Commandes de gestion : `chat_test`, `semantic_demo`, `chunk_preview`, `ingest`, `ask`, `create_api_key`, `eval_rag`, `backup_data`
- Routes : `/admin/`, `/chat/...` + `chat/api/conversations/...` (JSON de session, phase 11), `/api/...` (docs sur `/api/docs`), `/health/`
- Données : `data/media/` (uploads), `data/index/` (index vectoriel), `db.sqlite3`

### Frontend `frontend/` (Vue 3 + Reka UI + Tailwind, phase 11)

- Vue 3 + **TypeScript strict**, Vite, Reka UI (headless), Tailwind CSS v4 ; ESLint + Prettier + vitest (parseur SSE).
- Django rend la coquille HTML et l'auth par session ; Vue monte sur `#chat-app` ; assets construits dans `static/chatbot/app/` (non commités), résolus via le **manifest Vite** (`chatbot/templatetags/vite.py`) ; dev hot-reload via `FRONTEND_DEV_URL`.
- Structure : `src/api/` (HTTP/CSRF, sans état) · `src/composables/` (état réactif, `useChat`, `useConversations`) · `src/lib/sse.ts` (parseur SSE pur, testé) · `src/types/` · `src/components/{chat,conversations,ui}/`.
- Protocole SSE inchangé : `event: sources | token | done | error`. Interdits : `v-html`, logique métier côté client, backend Node.

### Règles transversales

- POO : interfaces `ABC`, injection par le constructeur, dataclasses `frozen=True`, exceptions métier, aucune logique métier dans les vues.
- Les tests passent **sans Ollama ni Internet** (faux LLM / faux embeddings). Tests réels marqués `@pytest.mark.integration`.
- Code en anglais, docstrings en français, annotations de type partout, `ruff` propre.
- Aucune valeur de config en dur : tout passe par `Settings`.

## Équivalences Laravel / Django / Python

| Laravel | Ici |
|---|---|
| `php artisan` | `python manage.py` |
| Composer, `composer.json` | `uv` ou `pip`, `requirements.txt`, `pyproject.toml` |
| `.env`, `config()` | `.env`, `Settings` (pydantic-settings) |
| Eloquent, migrations | ORM Django, `makemigrations` / `migrate` |
| Blade | Templates Django |
| Contrôleurs, FormRequest | Vues (classes), `Form` / schémas ninja |
| Middleware | Middleware Django |
| Policies / Gates | Permissions Django, filtrage par utilisateur |
| Queue | `django-q2` (optionnel) |
| Service Container | `Container` + factories |
| DTO | `@dataclass(frozen=True)` |
| Interface PHP | `abc.ABC` |
| PHPUnit | `pytest` |
| Pint / PHPStan | `ruff` / annotations de type |
