# Phase 00 : Environnement et squelette du projet

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Le code (classes, fonctions, variables) est en anglais ; les docstrings et commentaires utiles sont en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG (documents + mini chatbot) en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI), hébergée sur PlanetHoster. Le cœur RAG est en **Python pur** dans `rag_core/`, Django est une couche mince dans `chatbot/`. Principes de POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Le contrat d'architecture complet est dans `prompts/README.md` : lis-le avant de coder et respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Dossier `rag-app/` contenant uniquement `prompts/` (README.md et phase00 à phase10).
- Aucun autre fichier. Si le dossier contient déjà du code, signale-le et demande confirmation avant de continuer.

## 3. Objectif de la phase

Avoir un environnement Python isolé, Ollama opérationnel avec les deux modèles, un projet Django qui démarre, la structure de dossiers du contrat, la config par `.env`, et un premier test `pytest` qui passe.

## 4. Mini-cours Python pour développeur Laravel

- **Environnement virtuel (`venv`) et `uv`** : équivalent du dossier `vendor/` isolé par projet. On « active » le venv dans le terminal pour que `python` et `pip` pointent vers lui. `uv` est un gestionnaire rapide (comme Composer) ; `pip` + `requirements.txt` suffit.
- **`requirements.txt` / `pyproject.toml`** : `requirements.txt` ≈ `composer.lock` simplifié (liste des paquets) ; `pyproject.toml` ≈ `composer.json` + config des outils.
- **Modules et packages** : un dossier avec un fichier `__init__.py` est un package (≈ namespace PSR-4). `from rag_core.settings import Settings` ≈ `use App\Rag\Settings;`.
- **`manage.py`** : ≈ `artisan` (`runserver`, `migrate`, `createsuperuser`, `test`...).
- **`pytest`** : ≈ PHPUnit/Pest. Les fonctions `test_xxx()` sont découvertes automatiquement ; `assert` remplace les `assertSame`.
- **Indentation** : en Python l'indentation (4 espaces) remplace les accolades.

## 5. Travail à réaliser

1. **Vérifier / installer les prérequis** et donner les commandes pour Windows (PowerShell), macOS, Linux :
   - Python 3.11+ (`python --version`), Git.
   - `uv` (optionnel, recommandé ; suivre la doc officielle d'installation).
   - **Ollama** (ollama.com), puis `ollama pull llama3.2:3b` et `ollama pull nomic-embed-text`, vérifier avec `ollama list` et `curl http://localhost:11434/v1/models`.
2. `git init`, créer `.gitignore` (Python, `.venv/`, `.env`, `db.sqlite3`, `data/`, `staticfiles/`, `.pytest_cache/`, `.ruff_cache/`, `__pycache__/`).
3. Créer le venv `.venv` et expliquer l'activation (PowerShell : `.venv\Scripts\Activate.ps1`, avec la remarque sur `ExecutionPolicy` ; macOS/Linux : `source .venv/bin/activate`).
4. Créer les fichiers de dépendances :
   - `requirements.txt` : `django` (version **5.2 LTS**), `django-environ`, `openai`, `pydantic-settings`, `numpy`, `pypdf`.
   - `requirements-chroma.txt` : `chromadb` (optionnel, lourd ; l'index `simple` est le défaut).
   - `requirements-dev.txt` : `-r requirements.txt`, `pytest`, `pytest-django`, `ruff`, `reportlab` (pour fabriquer des PDF de test).
   - Installer, puis **épingler les versions réellement installées** (`pip freeze` filtré ou `uv pip compile`) dans `requirements.txt` pour la reproductibilité. Ne pas inventer de numéros de version : utiliser ceux installés.
5. Créer le projet Django : `django-admin startproject config .` puis `python manage.py startapp chatbot`.
6. Créer l'arborescence `rag_core/` du contrat (`llm/`, `embeddings/`, `vectorstore/`, `loaders/`, `chunking/`, `retrieval/`, `prompting/`, `pipeline/`), chaque dossier avec son `__init__.py` ; créer aussi `tests/`, `docs/`, `data/` (avec `.gitkeep` si utile), `eval/`.
7. Configurer `config/settings.py` avec **django-environ** : lecture du `.env` ; `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` depuis l'environnement ; `LANGUAGE_CODE = "fr"`, `TIME_ZONE = "Indian/Antananarivo"` ; `MEDIA_ROOT = BASE_DIR / "data" / "media"`, `MEDIA_URL = "/media/"` ; `STATIC_ROOT = BASE_DIR / "staticfiles"` ; enregistrer l'app `chatbot`. Base SQLite par défaut.
8. Créer `.env.example` avec **toutes** les variables du contrat (section « Variables d'environnement » de `prompts/README.md`) et un `.env` local copié depuis l'exemple (avec une vraie `DJANGO_SECRET_KEY` générée).
9. Créer `pyproject.toml` : configuration `ruff` (longueur de ligne 100, règles `E,F,I,UP,B`), configuration `pytest` (`DJANGO_SETTINGS_MODULE = config.settings`, `testpaths = ["tests"]`, marqueur `integration`).
10. Créer `CONVENTIONS.md` : règles du projet (POO, noms, interfaces, injection, exceptions, tests sans réseau, style, messages de commit Conventional Commits, structure des dossiers, comment lancer tests et lint).
11. Écrire `tests/test_smoke.py` : (a) `import rag_core` fonctionne ; (b) `django.conf.settings.LANGUAGE_CODE == "fr"` ; (c) `config.settings` se charge sans erreur.
12. Lancer `python manage.py migrate`, `python manage.py check`, `python manage.py runserver` (vérifier la page d'accueil Django, puis arrêter).
13. Créer un `README.md` racine minimal (installation locale en 6 étapes) à compléter en phase10.

## 6. Contraintes

- Ne pas encore écrire de logique RAG : uniquement le squelette.
- Aucun secret dans Git (`.env` ignoré, `.env.example` sans vraies clés).
- `rag_core/` ne doit jamais importer Django.
- Ne pas installer `chromadb` par défaut.

## 7. Tests à écrire

- `tests/test_smoke.py` comme décrit en 5.11.

## 8. Critères d'acceptation

- [ ] `ollama list` montre `llama3.2:3b` et `nomic-embed-text`.
- [ ] `pytest` : tous les tests passent.
- [ ] `ruff check .` : aucune erreur.
- [ ] `python manage.py check` : « no issues ».
- [ ] `python manage.py runserver` affiche la page Django sur http://127.0.0.1:8000.
- [ ] `.env` est ignoré par Git (`git status` ne le liste pas).
- [ ] `CONVENTIONS.md` et `.env.example` existent et sont complets.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les vérifications régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés, commandes pour tester à la main.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **Venv non activé** : `pip install` installe globalement. Vérifier `which python` / `where python`.
- **PowerShell bloque l'activation** : `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.
- **`python` vs `python3`** selon l'OS.
- **Ollama non démarré** : le lancer (application ou `ollama serve`) avant `curl`.
- **Oublier `__init__.py`** : les imports échouent.

## 11. Livrable de la phase

Un projet Django qui démarre (`python manage.py runserver`), une suite de tests verte (`pytest`), Ollama prêt avec les deux modèles, et le squelette `rag_core/` conforme au contrat.
