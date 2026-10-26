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
