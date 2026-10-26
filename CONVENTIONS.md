# Conventions du projet `rag-app`

## Architecture

- **`rag_core/`** : cœur RAG en **Python pur**. Interdiction absolue d'y importer Django.
  - **`chatbot/`** : application Django, couche fine (modèles, vues, services). Toute la
    logique métier vit dans `rag_core/` ; les vues ne contiennent aucune logique.
- Structure de `rag_core/` conforme au contrat : `settings.py`, `exceptions.py`,
  `models.py`, `container.py` + packages `llm/`, `embeddings/`, `vectorstore/`,
  `loaders/`, `chunking/`, `retrieval/`, `evaluation/`, `prompting/`, `pipeline/`.

## POO

- **Interfaces** : classes de base abstraites `abc.ABC` (≈ `interface` PHP), avec
  méthodes abstraites `@abstractmethod`. Une interface par dossier (`base.py`).
- **Injection de dépendances** : par le constructeur, jamais d'import direct d'une
  implémentation concrète dans le métier ; les factories créent les objets à partir
  des `Settings`.
- **DTO / valeurs** : `@dataclass(frozen=True)` (≈ DTO immutable).
- **Exceptions métier** : hiérarchie sous `RagError` dans `rag_core/exceptions.py`.
- **Configuration** : aucune valeur en dur dans le code — tout passe par
  `Settings` (pydantic-settings) ou le `.env` Django.

## Nommage et style

- Code (classes, fonctions, variables) en **anglais** ; docstrings et commentaires
  utiles en **français**.
- `snake_case` pour fonctions/variables/modules, `PascalCase` pour classes,
  `UPPER_SNAKE_CASE` pour les constantes.
- Annotations de type partout (`def chat(self, messages: list[ChatMessage]) -> str:`).
- Indentation 4 espaces ; longueur de ligne max 100.
- Docstrings en français sur chaque classe/module public.

## Tests

- **Aucun test unitaire ne touche le réseau ni Ollama** : faux LLM
  (`FakeLLM`) et faux embeddings (`FakeEmbeddingProvider`).
- Pour les clients externes (SDK `openai`...), injecter un double par le
  paramètre `client=` du constructeur — c'est le point d'injection prévu ;
  ne jamais laisser un test ouvrir une vraie connexion.
- Les tests réels (Ollama, API distante) sont marqués `@pytest.mark.integration`
  et **exclus par défaut** (`addopts` dans `pyproject.toml`) ; les lancer
  explicitement avec `pytest -m integration`.
- Un fichier de test par module, dans `tests/`, nommé `test_<module>.py`.

## Journalisation et affichage

- Pas de `print` dans `rag_core/` : utiliser le module `logging`.
- `print` / `self.stdout.write` autorisés uniquement dans les commandes Django.
- Ne jamais journaliser une clé API.

## Git

- **Conventional Commits** : `feat:`, `fix:`, `docs:`, `refactor:`, `test:`,
  `chore:`... (ex. `feat: squelette Django et rag_core`).
- Jamais de secret dans Git : `.env` ignoré, `.env.example` sans vraies clés.

## Commandes usuelles

```powershell
# Activer le venv (PowerShell)
.venv\Scripts\Activate.ps1   # si bloqué : Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# Lancer les tests
.venv\Scripts\python.exe -m pytest

# Linter
.venv\Scripts\python.exe -m ruff check .

# Serveur de développement
.venv\Scripts\python.exe manage.py runserver

# Migrations
.venv\Scripts\python.exe manage.py migrate
```

## Données et documents

- Un chunk garde toujours `source`, `page` et `index` (traçabilité vers le
  document d'origine ; `page` vaut None pour les fichiers sans pagination).
- Les paramètres invalides de constructeur lèvent `ValueError` ; `ConfigError`
  est réservé à la couche Settings / factories.
- `docs/` contient les documents d'exemple ; les PDF locaux ne sont pas
  versionnés (`.gitignore`).

## Données

- `data/media/` : documents uploadés.
- `data/index/` : index vectoriel.
- `db.sqlite3` : base locale (ignorée par Git).
