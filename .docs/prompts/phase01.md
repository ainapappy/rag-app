# Phase 01 : Configuration typée et client LLM

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phase 00 terminée : venv actif, Django qui démarre, `rag_core/` avec sous-dossiers et `__init__.py`, `.env` et `.env.example`, `pytest` et `ruff` verts, Ollama avec `llama3.2:3b` et `nomic-embed-text`.
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Pouvoir interroger le LLM (local ou distant) depuis une commande `python manage.py chat_test "..."`, avec une configuration typée et un client LLM abstrait, testé sans réseau.

## 4. Mini-cours Python pour développeur Laravel

- **Annotations de type** (`def f(x: str) -> int`) : ressemblent aux types de paramètres/retour PHP 8 ; non vérifiées à l'exécution mais exploitées par l'éditeur et `ruff`.
- **`pydantic-settings` (`BaseSettings`)** : lit `.env` et valide les types, ≈ `config('...')` avec casting automatique. Les attributs sont typés (`int`, `bool`, `float`).
- **`abc.ABC` et `@abstractmethod`** : ≈ `interface` / classe abstraite PHP. Une classe qui n'implémente pas toutes les méthodes abstraites ne peut pas être instanciée.
- **Générateurs (`yield`) et `Iterator[str]`** : ≈ générateurs PHP. Parfait pour le streaming des tokens.
- **Exceptions** : `try/except` ≈ `try/catch` ; `raise LLMError(...) from exc` ≈ chaîner l'exception précédente.
- **`@lru_cache`** : mémorise le résultat d'une fonction, ≈ un singleton léger (`get_settings()`).

## 5. Travail à réaliser

1. `rag_core/exceptions.py` : `RagError(Exception)` et ses sous-classes du contrat (`ConfigError`, `LLMError`, `EmbeddingError`, `LoaderError`, `UnsupportedFileTypeError`, `VectorStoreError`, `EmbeddingModelMismatchError`). Docstring courte pour chacune.
2. `rag_core/settings.py` : classe `Settings(BaseSettings)` lisant `.env` avec **tous les champs** de la table du contrat qui concernent `rag_core` (LLM_*, EMBED_*, VECTOR_STORE*, CHUNK*, TOP_K, MIN_SCORE, HISTORY_WINDOW, STREAMING_ENABLED, etc.), types corrects, valeurs par défaut du contrat, validation (`chunk_overlap < chunk_size`, `0 <= min_score <= 1`, `vector_store in {"simple","chroma"}`). `extra="ignore"` pour ne pas échouer sur les variables `DJANGO_*`. Fonction `get_settings()` décorée par `@lru_cache`.
3. `rag_core/models.py` : `ChatMessage` (dataclass `frozen=True` : `role: str`, `content: str`) avec méthode `to_dict()`. Valider que `role` ∈ `{"system","user","assistant"}` dans `__post_init__`. (Les autres dataclasses viendront dans les phases suivantes.)
4. `rag_core/llm/base.py` : `LLMClient(ABC)` avec `chat(messages) -> str` et `stream(messages) -> Iterator[str]`.
5. `rag_core/llm/openai_compatible.py` : `OpenAICompatibleLLM(base_url, api_key, model, temperature=0.2, client=None)`. Utilise `openai.OpenAI`. Le paramètre `client` optionnel permet d'injecter un faux client en test. `chat` renvoie le texte ; `stream` produit les fragments `delta.content` non vides. Toute erreur du SDK (`openai.OpenAIError`, connexion refusée...) est convertie en `LLMError` avec un message clair en français (« Impossible de joindre le LLM à <url> : vérifiez qu'Ollama est lancé »). Ne jamais journaliser la clé API.
6. `rag_core/llm/fake.py` : `FakeLLM(responses: list[str] | None = None)` enregistrant les appels (`self.calls`) ; renvoie les réponses programmées dans l'ordre, sinon une réponse par défaut ; `stream` découpe la réponse en petits morceaux.
7. `rag_core/llm/factory.py` : `LLMFactory.create(settings: Settings) -> LLMClient`.
8. Commande `chatbot/management/commands/chat_test.py` : arguments `prompt`, `--stream`, `--system` ; construit le client via `LLMFactory.create(get_settings())` ; affiche la réponse (en streaming si demandé) ; en cas d'erreur `LLMError`, message lisible et code de sortie non nul.
9. Mettre à jour `CONVENTIONS.md` si une règle nouvelle apparaît (ex. comment mocker les clients externes).

## 6. Contraintes

- `rag_core/` n'importe pas Django.
- Aucune valeur en dur : modèle, URL et clé viennent de `Settings`.
- Pas de `print` dans `rag_core/` (utiliser `logging`) ; `print`/`self.stdout.write` autorisé uniquement dans les commandes.
- Ne pas encore implémenter les embeddings (phase 02).

## 7. Tests à écrire

- `tests/test_settings.py` : valeurs par défaut ; surcharge par variables d'environnement (`monkeypatch.setenv`) ; erreur si `chunk_overlap >= chunk_size` ; `get_settings()` renvoie la même instance.
- `tests/test_llm.py` : `FakeLLM` (réponses dans l'ordre, enregistrement des appels, stream) ; `OpenAICompatibleLLM` avec un faux client injecté (chat, stream, conversion d'erreur en `LLMError`) ; `LLMFactory` renvoie bien un `OpenAICompatibleLLM` configuré ; `ChatMessage` rejette un rôle invalide.
- Un test `@pytest.mark.integration` qui interroge réellement Ollama (ignoré par défaut).

## 8. Critères d'acceptation

- [ ] `pytest` vert (hors `integration`), `ruff check .` propre.
- [ ] `python manage.py chat_test "Dis bonjour en une phrase"` affiche une réponse d'Ollama.
- [ ] `python manage.py chat_test "Raconte une courte histoire" --stream` affiche le texte progressivement.
- [ ] Arrêter Ollama puis relancer la commande : message d'erreur clair, pas de trace Python brute.
- [ ] Changer `LLM_MODEL` dans `.env` change le modèle utilisé sans modifier le code.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **Oublier `base_url` avec `/v1`** pour Ollama : l'URL est `http://localhost:11434/v1`.
- **`stream=True`** : le dernier fragment peut avoir `content = None`, à ignorer.
- **Clé API vide** : le SDK `openai` exige une valeur non vide ; Ollama accepte n'importe quelle chaîne (`ollama`).
- **Tests qui appellent le vrai réseau** : toujours injecter un faux client.

## 11. Livrable de la phase

`python manage.py chat_test "Bonjour" --stream` qui répond via Ollama, avec une configuration typée et un client LLM interchangeable (interface `LLMClient`), le tout couvert par des tests sans réseau.
