# rag-app

Application **RAG** (Retrieval-Augmented Generation) : déposez des documents,
posez vos questions en français, obtenez des réponses **uniquement à partir de
ces documents**, avec leurs sources. Cœur RAG en Python pur (`rag_core/`),
interface Django (`chatbot/`), LLM local **Ollama** en développement, **LLM
distant** (API compatible OpenAI) en production.

## Architecture

```
┌──────────────────────────  Django (couche fine)  ─────────────────────────┐
│  chatbot/  admin (documents)  chat web (SSE)  API JSON (django-ninja)     │
│  models: Document, Conversation, Message, ApiKey                          │
│  services: DocumentIndexingService, ChatService, ApiChatService           │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │ (interfaces ABC, injection par le Container)
┌──────────────────────────  rag_core (Python pur, zéro Django) ────────────┐
│ loaders (txt/md/pdf) → chunking (fixed/paragraph) → embeddings (OpenAI/Ollama)
│ → vectorstore (simple: NumPy+SQLite | chroma) → retrieval (vector | hybrid BM25+RRF)
│ → prompting (prompt strict, query rewriter) → pipeline (ingestion, RAG)
│ evaluation (Hit@k, MRR, refus, juge LLM) · settings (pydantic-settings)
└───────────────────────────────────────────────────────────────────────────┘
```

L'index par défaut (`simple`) ne dépend que de NumPy et SQLite ; Ollama n'est
requis qu'en local — en production, tout passe par une API distante.

## Prérequis

- Python **3.11+**, Git, [uv](https://docs.astral.sh/uv/) (optionnel mais rapide).
- Local : [Ollama](https://ollama.com) avec `llama3.2:3b` et `nomic-embed-text`
  (`ollama pull …`). Production : une API compatible OpenAI.
- Pour développer ou construire le front : **Node.js 20+** et npm (inutiles à
  l'exécution une fois les assets construits).

## Installation locale

```powershell
# 1. Cloner et entrer dans le projet
git clone <depot> rag-app ; cd rag-app

# 2. Créer le venv (≈ vendor/ isolé par projet)
uv venv .venv          # ou : python -m venv .venv

# 3. L'activer — PowerShell (.venv\Scripts\Activate.ps1 ; si bloqué :
#    Set-ExecutionPolicy -Scope CurrentUser RemoteSigned) — bash : source .venv/bin/activate

# 4. Installer (requirements.txt est déjà épinglé)
pip install -r requirements-dev.txt      # prod seule : requirements.txt

# 5. Configurer
Copy-Item .env.example .env              # macOS/Linux : cp .env.example .env

# 6. Base, super-utilisateur, documents d'exemple
python manage.py migrate
python manage.py createsuperuser
python manage.py ingest docs/

# 7. Construire le front (Vue 3 + Tailwind ; requis une fois)
cd frontend ; npm ci ; npm run build ; cd ..

# 8. Démarrer
python manage.py runserver               # http://127.0.0.1:8000
```

## Développement front

L'interface du chat vit dans [frontend/](frontend/) : **Vue 3 + TypeScript
strict**, **Reka UI** (composants headless accessibles) et **Tailwind CSS v4**,
empilés par Vite. Django rend la coquille HTML ; Vue monte sur `#chat-app`
(`chatbot/templates/chatbot/chat.html`). Les assets construits sortent dans
`static/chatbot/app/` (non commités) et sont résolus via le manifest Vite
(`chatbot/templatetags/vite.py`) — jamais de nom de fichier en dur.

```powershell
cd frontend
npm ci                      # ≈ composer install (versions du package-lock.json)
npm run dev                 # hot reload ; définir FRONTEND_DEV_URL=http://localhost:5173 dans .env
npm run build               # production (puis manage.py collectstatic)
npm run typecheck           # vue-tsc (≈ PHPStan du front)
npm run lint                # eslint + prettier
npm run test                # vitest (parseur SSE)
```

Structure : `src/api/` (fetch/CSRF, sans état) · `src/composables/` (état
réactif : `useChat`, `useConversations`) · `src/lib/sse.ts` (parseur SSE pur,
testé) · `src/types/` · `src/components/{chat,conversations,ui}/`. Les
endpoints JSON de session sont sous `chat/api/conversations/` ; le protocole
SSE (`sources` / `token` / `done` / `error`) est inchangé.

## Configuration (`.env`)

| Variable | Défaut | Rôle |
|---|---|---|
| `DJANGO_SECRET_KEY` | — | Clé secrète Django (générée localement) |
| `DJANGO_DEBUG` | `True` | `False` en production |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Hôtes autorisés |
| `DJANGO_CSRF_TRUSTED_ORIGINS` | (vide) | Origines `https://…` de confiance |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | Ollama / `ollama` / `llama3.2:3b` | Chat |
| `LLM_TEMPERATURE` | `0.2` | Température |
| `EMBED_BASE_URL` / `EMBED_API_KEY` / `EMBED_MODEL` | Ollama / `ollama` / `nomic-embed-text` | Embeddings |
| `EMBED_BATCH_SIZE` | `32` | Textes par appel d'embeddings |
| `VECTOR_STORE` / `VECTOR_STORE_PATH` | `simple` / `data/index` | Magasin vectoriel |
| `CHUNKER_STRATEGY` / `CHUNK_SIZE` / `CHUNK_OVERLAP` | `fixed` / 700 / 100 | Découpage |
| `TOP_K` / `MIN_SCORE` | 4 / 0.65¹ | Recherche |
| `HISTORY_WINDOW` / `STREAMING_ENABLED` | 6 / `True` | Chat |
| `RETRIEVER` | `vector` | `vector` ou `hybrid` (BM25 + RRF) |
| `INDEX_ON_UPLOAD` / `MAX_UPLOAD_MB` | `True` / 10 | Admin/uploads |
| `RATE_LIMIT_PER_MINUTE` | 30 | API, chat, login |
| `DJANGO_LOG_LEVEL` | `INFO` | Journaux |

¹ Ajusté localement pour nomic-embed-text après mesure (voir
[docs/EVALUATION.md](docs/EVALUATION.md)).

## Utilisation

- **Admin documents** : `/admin/` — upload `.txt`/`.md`/`.pdf` (indexation
  automatique), statut, actions Indexer / Réindexer / Retirer de l'index.
- **Chat web** : `/chat/` — conversations persistantes, questions de suivi
  reformulées, réponses en streaming avec sources dépliables.
- **API JSON** : `/api/` — clé via `python manage.py create_api_key <nom>`
  (affichée une seule fois) ; docs OpenAPI sur `/api/docs` ; exemples dans la
  section « Utiliser l'API » plus bas.

```powershell
# Commandes principales
python manage.py ingest docs/ --list    # indexation idempotente
python manage.py ask "…question…" --stream
python manage.py chunk_preview docs/guide_rag.md
python manage.py semantic_demo --query "un félin sommeille"
python manage.py eval_rag               # qualité : Hit@k, MRR, refus
python manage.py backup_data            # archive data/ + base SQLite
```

## Utiliser l'API

```powershell
python manage.py create_api_key integration      # clé affichée UNE FOIS
curl -H "X-API-Key: <cle>" -H "Content-Type: application/json" `
     -X POST http://127.0.0.1:8000/api/chat `
     -d '{"question":"Combien de jours de conges payes par an ?"}'
curl -H "X-API-Key: <cle>" http://127.0.0.1:8000/api/documents
```

Codes : 401 clé invalide · 422 validation · 429 `Retry-After` · 502 erreur
métier RAG (`{"detail": "…"}`) · `GET /health/` public · `?deep=1` staff.

## Tests et qualité

```powershell
pytest                          # 220+ tests, sans réseau ni Ollama
pytest -m integration           # tests réels (Ollama requis)
ruff check .                    # lint (max 100 colonnes)
python manage.py check --deploy # audit production (avec DJANGO_DEBUG=False)
python manage.py makemigrations --check
# Front (depuis frontend/) : npm run typecheck, lint, test
```

## Évaluation

`python manage.py eval_rag [--retriever hybrid] [--sweep] [--with-llm --judge]`
mesure Hit@k, MRR, taux de bons refus et compare les réglages. Bilan :
[docs/EVALUATION.md](docs/EVALUATION.md).

## Déploiement

Procédure complète, checklist, plan B VPS (gunicorn + nginx) et dépannage :
[docs/DEPLOYMENT.md](docs/DEPLOYMENT.md). Point d'entrée WSGI :
`passenger_wsgi.py`. Santé : `/health/`.

## Sécurité

- Clés d'API stockées **hachées** (sha256, comparaison temps constant) ;
  clé en clair affichée une seule fois.
- Secrets jamais dans Git ni les logs (filtre de masquage sur `X-API-Key`,
  `Authorization`, …).
- Rate limiting (API, chat, login), validation d'uploads (extension, taille,
  octets magiques PDF, nom nettoyé), en-têtes de sécurité ; HSTS/cookies
  sécurisés actifs quand `DEBUG=False`.
- Les 3 avertissements restants de `check --deploy` (SSL redirect, HSTS
  subdomains/preload) sont volontairement différés : ils supposent un HTTPS
  validé sur le domaine final.

## Limites connues

- Indexation dans la requête admin (pas de tâche d'arrière-plan) : un gros
  PDF peut être lent.
- Rate limit par processus avec le cache local : prévoir un cache partagé en
  multi-processus (`chatbot/ratelimit.py`).
- OCR non supporté (PDF scannés refusés) ; extraction PDF imparfaite possible.
- Échantillon d'évaluation réduit (15 questions) : chiffres indicatifs.

## Pistes d'évolution

- Tâches d'arrière-plan (`django-q2`) pour l'indexation.
- PostgreSQL + pgvector à la place de l'index `simple`.
- Re-ranking des résultats, OCR pour les PDF scannés, cache sémantique.
