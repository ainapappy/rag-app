# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Projet

Application RAG (documents + mini chatbot) : **Django** comme couche mince, cœur RAG en **Python pur**. LLM local **Ollama** en développement (API compatible OpenAI), LLM distant configurable en production. Le développeur est PHP/Laravel confirmé, débutant en Python : expliquer les notions nouvelles par analogie Laravel. Répondre en français ; code en anglais, docstrings/commentaires en français.

## Contrat d'architecture (source de vérité)

- `.docs/prompts/README.md` : contrat complet — noms de classes, interfaces (`LLMClient`, `EmbeddingProvider`, `VectorStore`), signatures exactes, variables d'environnement. **À lire avant toute phase et respecter les noms à l'identique.**
- `.docs/prompts/phase00.md` à `phase11.md` : phases à exécuter **dans l'ordre, une par une**. Ne jamais sauter une phase ; vérifier ses critères d'acceptation avant de passer à la suivante. (`phase11.md` = évolution « 10+ », exécutable après phase10 uniquement.)
- `CONVENTIONS.md` : règles de style, POO, tests, Git.

## Commandes

```powershell
# Venv : soit l'activer (.venv\Scripts\Activate.ps1), soit préfixer par .venv\Scripts\
.venv\Scripts\python.exe -m pytest                 # tous les tests (sans réseau ni Ollama)
.venv\Scripts\python.exe -m pytest tests/test_smoke.py::test_language_code_is_french   # un seul test
.venv\Scripts\python.exe -m pytest -m integration  # tests réels (Ollama requis)
.venv\Scripts\python.exe -m ruff check .           # lint (max 100 colonnes, règles E,F,I,UP,B)
.venv\Scripts\python.exe -m ruff check . --fix     # corrections auto
.venv\Scripts\python.exe manage.py runserver       # http://127.0.0.1:8000
.venv\Scripts\python.exe manage.py migrate
```

Dépendances épinglées dans `requirements*.txt` (Django **5.2 LTS**, pas une version plus récente). `requirements-chroma.txt` est optionnel et lourd — ne pas l'installer par défaut.

## Architecture

Deux mondes strictement séparés :

- **`rag_core/`** — cœur RAG en Python pur. **Interdiction d'y importer Django.** Structure imposée par le contrat : `settings.py` (pydantic-settings, `get_settings()`), `exceptions.py` (hiérarchie sous `RagError`), `models.py` (dataclasses `frozen=True`), `container.py` (DI), et packages `llm/`, `embeddings/`, `vectorstore/`, `loaders/`, `chunking/`, `retrieval/`, `evaluation/`, `prompting/`, `pipeline/`. Chaque package suit le motif : `base.py` (ABC ≈ interface PHP), implémentations concrètes, `factory.py` (création depuis `Settings`).
- **`chatbot/`** — app Django, couche fine : modèles ORM, vues sans logique métier, services (`DocumentIndexingService`, `ChatService`) qui délèguent au `Container` de `rag_core`.
- **`frontend/`** — front Vue 3 + TypeScript strict + Reka UI + Tailwind v4 (phase 11), build Vite vers `static/chatbot/app/` (non commité). Django rend la coquille HTML ; Vue monte sur `#chat-app` ; pas de logique métier côté client, pas de `v-html`.

Configuration : `.env` lu par django-environ dans `config/settings.py` (côté Django) et par pydantic-settings dans `rag_core/settings.py` (côté métier). Aucune valeur en dur dans le code. Toutes les variables du contrat sont dans `.env.example`.

Données : `data/media/` (uploads), `data/index/` (index vectoriel), `db.sqlite3` — tout ignoré par Git, comme `.env`.

## Règles non négociables

- Tests unitaires **sans réseau ni Ollama** : utiliser `FakeLLM` / `FakeEmbeddingProvider` ; marquer `@pytest.mark.integration` les tests réels.
- POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen=True`, exceptions métier.
- Aucun secret dans Git : `.env` ignoré, `.env.example` sans vraies clés.
- Commits en Conventional Commits (`feat:`, `fix:`, `docs:`, ...). **Commit à la fin de chaque phase**, avec l'identité Git du dépôt (l'utilisateur a délégué les commits).
- Ne jamais laisser le projet cassé : corriger tout échec de test/lint avant de continuer.
