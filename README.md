# rag-app

Application RAG (documents + mini chatbot) en **Django**, avec un LLM local
(**Ollama**) en développement et un **LLM distant configurable** (API compatible
OpenAI) en production. Le cœur RAG est en Python pur dans `rag_core/` ; Django
est une couche mince dans `chatbot/`.

## Installation locale (Windows PowerShell)

```powershell
# 1. Cloner le dépôt et se placer dedans
cd rag-app

# 2. Créer le venv (≈ vendor/ isolé par projet)
uv venv .venv
# ou : python -m venv .venv

# 3. Activer le venv (si bloqué : Set-ExecutionPolicy -Scope CurrentUser RemoteSigned)
.venv\Scripts\Activate.ps1

# 4. Installer les dépendances
pip install -r requirements-dev.txt
# Chroma (optionnel, lourd — l'index « simple » est le défaut) :
# pip install -r requirements-chroma.txt

# 5. Copier la config locale et adapter si besoin
Copy-Item .env.example .env

# 6. Préparer la base et lancer
python manage.py migrate
python manage.py runserver   # http://127.0.0.1:8000
```

## Prérequis

- Python 3.11+, Git, [uv](https://docs.astral.sh/uv/) (optionnel mais recommandé).
- [Ollama](https://ollama.com) avec les modèles :
  ```powershell
  ollama pull llama3.2:3b
  ollama pull nomic-embed-text
  ```

## Développement

- Tests : `pytest` (aucun réseau requis).
- Lint : `ruff check .`
- Conventions du projet : voir [CONVENTIONS.md](CONVENTIONS.md).

## Utilisation en ligne de commande

```powershell
# 1. Indexer des documents (idempotent : les fichiers inchangés sont sautés)
python manage.py ingest docs/
python manage.py ingest docs/ --list     # voir les sources indexées
python manage.py ingest docs/ --reset    # reconstruire (obligatoire si EMBED_MODEL change)

# 2. Poser une question (réponse uniquement à partir des documents, sources citées)
python manage.py ask "Combien de jours de congés par an ?"
python manage.py ask "..." --stream            # réponse progressive
python manage.py ask "..." --show-context      # voir les chunks retrouvés
python manage.py ask "..." --top-k 6 --min-score 0.2   # expérimentation

# 3. Débug du découpage et de la sémantique
python manage.py chunk_preview docs/guide_rag.md --strategy paragraph
python manage.py semantic_demo --query "un félin sommeille"
```

## Gérer les documents depuis l'admin

```powershell
# 1. Créer un super-utilisateur (une seule fois)
python manage.py createsuperuser

# 2. Lancer le serveur et ouvrir http://127.0.0.1:8000/admin/
python manage.py runserver
```

Dans **Documents** : « Ajouter » pour téléverser un `.txt`, `.md` ou `.pdf`
(indexation automatique après l'upload si `INDEX_ON_UPLOAD=True`), statut et
nombre de chunks dans la liste, actions **Indexer / Retirer de l'index /
Réindexer** sur la sélection. La suppression retire aussi les chunks de
l'index et le fichier du disque.

## Utiliser le chatbot

1. Lancer `python manage.py runserver` et ouvrir http://127.0.0.1:8000/ .
2. Se connecter (compte créé via `createsuperuser` ou un `User` de test).
3. Cliquer « + Nouvelle conversation », poser une question : la réponse
   s'affiche progressivement (si `STREAMING_ENABLED=True`) avec ses sources
   dépliables sous le message.
4. Les questions de suivi sont reformulées automatiquement (ex. « et pour les
   congés maladie ? » après une question sur les congés) — visible dans les
   logs Django.
5. L'historique persiste (SQLite) ; chaque utilisateur ne voit que ses
   conversations.

Note streaming : en WSGI, un worker reste occupé pendant la génération —
désactivez `STREAMING_ENABLED` en production si nécessaire.

## Utiliser l'API

```powershell
# 1. Créer une clé d'API (affichée UNE SEULE FOIS)
python manage.py create_api_key integration
# → conservez la valeur affichée dans $env:API_KEY

# 2. Poser une question
curl -H "X-API-Key: %API_KEY%" -H "Content-Type: application/json" `
     -X POST http://127.0.0.1:8000/api/chat `
     -d '{"question":"Combien de jours de congés par an ?"}'

# 3. Lister / téléverser / supprimer des documents
curl -H "X-API-Key: %API_KEY%" http://127.0.0.1:8000/api/documents
curl -X POST -H "X-API-Key: %API_KEY%" -F "title=Guide" -F "file=@docs/guide_rag.md" `
     http://127.0.0.1:8000/api/documents

# 4. Documentation OpenAPI interactive (sans authentification)
start http://127.0.0.1:8000/api/docs
```

Codes : 401 (clé absente/invalide), 422 (validation), 429 (`Retry-After`,
limite `RATE_LIMIT_PER_MINUTE`), 502 (erreur métier RAG, message stable
`{"detail": "..."}`). `GET /api/health` est public.

Limites connues : avec le cache local (`LocMemCache`), les compteurs de
rate-limit sont par processus — en production, configurer un cache partagé
(voir `chatbot/ratelimit.py`). Les en-têtes HSTS/cookies sécurisés ne sont
actifs qu'avec `DEBUG=False` ; la redirection HTTPS (`SECURE_SSL_REDIRECT`)
et `SECURE_PROXY_SSL_HEADER` sont à valider avec PlanetHoster avant
activation (voir `config/settings.py`). Les 3 avertissements restants de
`check --deploy` (SECURE_SSL_REDIRECT, HSTS subdomains/preload) sont
volontairement différés : ils supposent un HTTPS opérationnel et vérifié
sur le domaine final, sous-domaines compris.

## Évaluer la qualité

```powershell
python manage.py eval_rag                     # Hit@k, MRR, taux de bons refus
python manage.py eval_rag --retriever hybrid  # comparer le BM25 + RRF
python manage.py eval_rag --sweep             # grille chunk/overlap/top_k (index temporaire)
python manage.py eval_rag --with-llm --judge  # rappel mots-clés + fidélité (indicatif)
```

Le jeu de questions vit dans `eval/questions.json` (15 questions, dont 3 hors
corpus). Bilan complet et réglages retenus : [docs/EVALUATION.md](docs/EVALUATION.md).

## Journaux

`data/logs/app.log` (rotation 5 Mo × 3) en plus de la console ; un filtre
masque les clés d'API / tokens (`X-API-Key:`, `Authorization:`, …).
