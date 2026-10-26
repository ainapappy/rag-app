<div align="center">

# 🤖 rag-app

### Un chatbot RAG complet, en français, propulsé par Vue 3 & TypeScript

*[Déposez vos documents · Posez vos questions · Obtenez des réponses sourcées, en streaming](#-fonctionnalités)*

![Vue.js](https://img.shields.io/badge/Vue.js-3-4FC08D?logo=vuedotjs&logoColor=white&style=for-the-badge)
![TypeScript](https://img.shields.io/badge/TypeScript-strict-3178C6?logo=typescript&logoColor=white&style=for-the-badge)
![Vite](https://img.shields.io/badge/Vite-6-646CFF?logo=vite&logoColor=white&style=for-the-badge)
![Tailwind CSS](https://img.shields.io/badge/Tailwind-v4-06B6D4?logo=tailwindcss&logoColor=white&style=for-the-badge)
![Django](https://img.shields.io/badge/Django-5.2_LTS-092E20?logo=django&logoColor=white&style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?logo=python&logoColor=white&style=for-the-badge)
![Ollama](https://img.shields.io/badge/LLM-Ollama-111111?style=for-the-badge)

**🌐 Découvrez mes autres projets sur [ainatrix.com](https://ainatrix.com)**

![GitHub](https://img.shields.io/badge/GitHub-ainapappy%2Frag--app-181717?logo=github&logoColor=white&style=for-the-badge)
[![ainatrix.com](https://img.shields.io/badge/Portfolio-ainatrix.com-8A2BE2?logo=googlechrome&logoColor=white&style=for-the-badge)](https://ainatrix.com)

![Tests](https://img.shields.io/badge/tests-220%2B-brightgreen)
![Coverage](https://img.shields.io/badge/pytest%20%2B%20vitest-sans%20r%C3%A9seau-blue)
![License](https://img.shields.io/badge/lint-ruff%20%2B%20eslint-ff69b4)

</div>

---

> **rag-app** est une application **RAG** (Retrieval-Augmented Generation) complète :
> importez des documents (`.txt`, `.md`, `.pdf`), discutez avec, et recevez des réponses
> **uniquement fondées sur ces documents** — avec leurs sources, en streaming temps réel.
>
> Un cœur métier en **Python pur, testable sans réseau** (`rag_core/`), une couche API
> **Django** volontairement mince, et une interface **Vue 3 + TypeScript strict** qui
> fait toute l'expérience utilisateur.

---

## ✨ Fonctionnalités

| | |
|---|---|
| 💬 **Chat en streaming (SSE)** | Réponses token par token via Server-Sent Events, avec un parseur SSE **pur TypeScript et testé** (Vitest) |
| 📎 **Sources dépliables** | Chaque réponse cite ses extraits de documents — pas d'hallucination sans traçabilité |
| 🧠 **Questions de suivi** | Les relances sont **reformulées** automatiquement avec l'historique de la conversation |
| 🔄 **Conversations persistantes** | Historique complet côté serveur, liste de conversations réactive côté client |
| 📄 **Indexation multi-formats** | Upload `.txt` / `.md` / `.pdf` depuis l'admin, indexation automatique idempotente |
| 🔍 **Retrieval vectoriel ou hybride** | Similarité cosinus (NumPy + SQLite) **ou** BM25 + fusion RRF — au choix via config |
| 🔑 **API JSON sécurisée** | django-ninja + OpenAPI auto-documentée, clés hachées (sha256), rate limiting |
| 🧪 **Qualité outillée** | 220+ tests pytest sans réseau, vue-tsc, ESLint flat config, Prettier, Ruff |

## 🎨 L'interface : Vue 3 + TypeScript strict

Le front vit dans [`frontend/`](frontend/) — c'est une **vraie application Vue**,
pas une surcouche décorative :

```
frontend/src/
├── components/{chat,conversations,ui,auth}/   # composants SFC organisés par domaine
├── composables/       # état réactif : useChat, useConversations, useAuth
├── api/               # couche fetch typée (CSRF, auth, conversations) — sans état
├── lib/sse.ts         # parseur SSE pur, testé avec Vitest
└── types/             # types partagés front/back
```

- **Vue 3.5 `<script setup>`** + Composition API, état mutualisé dans des **composables réutilisables**
- **TypeScript `strict`**, vérifié en CI avec `vue-tsc --noEmit` — le PHPStan du front
- **Reka UI** : composants headless accessibles (focus trap, ARIA, clavier)
- **Tailwind CSS v4** via plugin Vite, build de production optimisé
- **Vitest** sur la logique critique (protocole SSE), ESLint 9 + Prettier
- Intégration Django propre : Vue monte sur `#chat-app`, les assets construits sont
  résolus via le **manifest Vite** — jamais de nom de fichier en dur
- **Zéro `v-html`, zéro logique métier côté client** : la sécurité et le RAG restent serveur

```powershell
cd frontend
npm run dev          # hot reload (proxy Vite → Django :8000)
npm run typecheck    # vue-tsc --noEmit
npm run test         # vitest
npm run build        # bundle production → static/chatbot/app/
```

## 🏗 Architecture

Deux mondes strictement séparés, liés par **injection de dépendances** et des
**interfaces ABC** (≈ contrats d'interface PHP) :

```
┌──────────────────────────  Django (couche fine)  ─────────────────────────┐
│  chatbot/  admin (documents)  chat web (SSE)  API JSON (django-ninja)     │
└───────────────────────────────────┬───────────────────────────────────────┘
                                    │  interfaces ABC + Container (DI)
┌──────────────────────────  rag_core (Python pur, zéro Django) ────────────┐
│ loaders → chunking → embeddings → vectorstore → retrieval → prompting     │
│ → pipeline · evaluation (Hit@k, MRR, refus, juge LLM)                     │
└───────────────────────────────────────────────────────────────────────────┘
```

Chaque brique (`llm/`, `embeddings/`, `vectorstore/`, `retrieval/`…) suit le même
motif : `base.py` (ABC), implémentations concrètes, `factory.py`. Résultat :
**Ollama en local, API compatible OpenAI en production — un simple changement de `.env`.**

L'index par défaut ne dépend que de **NumPy + SQLite** : aucun service externe requis.

## 🚀 Démarrage rapide

```bash
git clone https://github.com/ainapappy/rag-app.git rag-app && cd rag-app

# Backend
python -m venv .venv && .venv\Scripts\Activate.ps1   # source .venv/bin/activate sur Linux/macOS
pip install -r requirements-dev.txt
cp .env.example .env                                  # Copy-Item sous Windows

python manage.py migrate
python manage.py createsuperuser
python manage.py ingest docs/                         # indexe les documents d'exemple

# Front (une seule fois)
cd frontend && npm ci && npm run build && cd ..

# Lancer 🎉
python manage.py runserver                            # http://127.0.0.1:8000
```

Prérequis : Python 3.11+, Node 20+ (build du front), et
[Ollama](https://ollama.com) avec `llama3.2:3b` + `nomic-embed-text` en local.
👉 Procédure détaillée et configuration complète : [`docs/README.md`](docs/README.md).

## 🖥 Utilisation

| URL | Quoi |
|---|---|
| `/chat/` | Le chat Vue 3 : conversations, streaming, sources dépliables |
| `/admin/` | Upload et gestion des documents (indexation automatique) |
| `/api/docs` | Documentation OpenAPI interactive de l'API JSON |
| `/health/` | Health-check public |

```bash
# CLI incluse
python manage.py ask "…question…" --stream   # poser une question depuis le terminal
python manage.py eval_rag                    # qualité : Hit@k, MRR, taux de bons refus
```

## 🧪 Tests & qualité

```bash
pytest                        # 220+ tests, sans réseau ni Ollama (fakes injectés)
pytest -m integration         # tests réels contre Ollama
ruff check .                  # lint Python
cd frontend
npm run typecheck && npm run lint && npm run test
```

Le cœur `rag_core/` est **entièrement testable hors ligne** grâce à l'injection
de `FakeLLM` / `FakeEmbeddingProvider` — l'IA n'est jamais nécessaire pour tester.

## 🔐 Sécurité

- Clés d'API **hachées** (sha256, comparaison à temps constant), affichées une seule fois
- Rate limiting (API, chat, login) et validation d'uploads (extension, taille, octets magiques PDF)
- Secrets jamais dans Git ni les logs (filtre de masquage) ; HSTS + cookies sécurisés en production

## 🗺 Pistes d'évolution

- [ ] Indexation en tâche de fond (django-q2)
- [ ] PostgreSQL + pgvector en remplacement de l'index `simple`
- [ ] Re-ranking des résultats & OCR pour les PDF scannés

## 📚 Documentation

| Document | Contenu |
|---|---|
| [`docs/README.md`](docs/README.md) | Guide technique complet : installation, configuration `.env`, API, déploiement |
| [`docs/EVALUATION.md`](docs/EVALUATION.md) | Méthodologie et résultats d'évaluation du retrieval (Hit@k, MRR) |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | Checklist production, gunicorn + nginx, dépannage |

---

<div align="center">

**Construit par [Aina Papy](https://github.com/ainapappy)**

🌐 Portfolio : **[ainatrix.com](https://ainatrix.com)** · 💻 Code : [github.com/ainapappy](https://github.com/ainapappy)

</div>
