# Phase 08 : API JSON et sécurité

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 07 terminées : chatbot web fonctionnel, `ChatService`, `DocumentIndexingService`, modèles `Document`, `Conversation`, `Message`, admin, tests verts.
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Exposer une **API JSON** (`django-ninja`) protégée par **clé d'API**, et renforcer la sécurité de l'application : validation des uploads, limitation de débit, gestion propre des erreurs, en-têtes de sécurité, journalisation fichier.

## 4. Mini-cours Python pour développeur Laravel

- **django-ninja** : ≈ routes API Laravel + API Resources + FormRequest en un seul outil ; les **schémas** (`Schema`) valident l'entrée et formatent la sortie, et génèrent la doc OpenAPI automatiquement (`/api/docs`).
- **Authentification par en-tête** : classe d'auth (`APIKeyHeader`) ≈ middleware `auth:api` personnalisé.
- **`secrets.token_urlsafe(32)`** ≈ `Str::random(40)` cryptographiquement sûr ; ne stocker que le **hash** de la clé (`hashlib.sha256`) comme on hache un mot de passe/token, et comparer avec `hmac.compare_digest`.
- **Cache Django** : ≈ `Cache::` Laravel ; `cache.add/incr` pour compter les requêtes par fenêtre.
- **Middleware** : ≈ middleware Laravel ; classe avec `__init__(get_response)` et `__call__(request)`.
- **Gestionnaires d'exceptions** : `@api.exception_handler(...)` ≈ `Handler::render` de Laravel.

## 5. Travail à réaliser

1. Dépendance : ajouter `django-ninja` à `requirements.txt` (version installée, épinglée).
2. `chatbot/models.py` : `ApiKey(name, prefix, key_hash, is_active, created_at, last_used_at)` ; méthodes de classe `ApiKey.generate(name) -> tuple[ApiKey, str]` (renvoie la clé **en clair une seule fois**) et `ApiKey.authenticate(raw_key) -> ApiKey | None` (compare les hashes en temps constant, met à jour `last_used_at`). Migrations.
3. Commande `create_api_key <name>` : crée une clé, l'affiche **une seule fois** avec un avertissement.
4. `chatbot/api.py` :
   - `ApiKeyAuth(APIKeyHeader)` sur l'en-tête `X-API-Key`.
   - `NinjaAPI(title="RAG API", version="1.0", auth=ApiKeyAuth())`, monté sur `/api/`.
   - Schémas : `ChatRequest(question: str [1..2000 caractères], history: list[HistoryItem] = [])`, `ChatResponse(answer, found, sources: list[SourceOut])`, `DocumentOut(id, title, original_name, status, chunks_count, indexed_at)`.
   - Endpoints : `POST /api/chat` (appelle `container.rag_pipeline.ask` via un petit service, **sans** persistance de conversation), `GET /api/documents`, `POST /api/documents` (upload multipart + indexation via `DocumentIndexingService`), `DELETE /api/documents/{id}`, `GET /api/health` (sans auth : état simple de l'app).
   - Gestionnaires d'exceptions : `RagError` → 502 (ou 400 pour erreurs de validation métier) avec un message JSON stable `{"detail": "..."}` ; aucune trace interne exposée.
5. `chatbot/validators.py` : classe `UploadValidator(max_mb, loader_factory)` avec `validate(uploaded_file)` : extension supportée, taille maximale, **vérification des octets magiques** pour les PDF (`%PDF-`), nom de fichier nettoyé (pas de chemin, longueur limitée). Utilisée par l'admin **et** l'API. Erreurs → `django.core.exceptions.ValidationError` (admin) / 422 (API).
6. `chatbot/ratelimit.py` : classe `RateLimiter(cache, limit, window_seconds=60)` avec `hit(identifier) -> RateLimitResult(allowed, remaining, retry_after)` (fenêtre fixe basée sur le cache Django) ; utilisée pour : `POST /api/chat` (par clé), `chat_send` (par utilisateur), connexion (par IP, pour freiner la force brute). Retour **429** avec en-tête `Retry-After`. Documenter la limite : avec `LocMemCache`, le compteur est **par processus** ; en production multi-processus, prévoir un cache partagé (fichier ou base) — documenter l'option `CACHES` choisie.
7. Sécurité Django dans `config/settings.py` : `SECURE_CONTENT_TYPE_NOSNIFF`, `X_FRAME_OPTIONS = "DENY"`, `SESSION_COOKIE_HTTPONLY`, et, **uniquement quand `DEBUG=False`** : `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_HSTS_SECONDS` (valeur modérée au départ), `SECURE_REFERRER_POLICY`. Ne pas activer `SECURE_SSL_REDIRECT` sans savoir comment l'hébergeur transmet HTTPS ; documenter le point (`SECURE_PROXY_SSL_HEADER` à vérifier avec l'hébergeur).
8. Journalisation : handler `RotatingFileHandler` vers `data/logs/app.log` (taille limitée, quelques sauvegardes) en plus de la console ; **filtre** qui masque les clés d'API et tokens éventuels dans les messages.
9. Mettre à jour `README.md` racine : « Utiliser l'API » avec un exemple `curl` (création de clé, appel `/api/chat`).

## 6. Contraintes

- Aucune clé en clair en base ni dans les logs ; comparaison en temps constant.
- L'API **n'expose pas** les chemins disque ni les erreurs internes.
- Même `UploadValidator` pour l'admin et l'API (pas de duplication).
- Les vues et endpoints restent fins : la logique reste dans les services.

## 7. Tests à écrire

- `tests/test_api_key.py` : génération (préfixe, hash ≠ clé), authentification valide/invalide/désactivée, `last_used_at` mis à jour.
- `tests/test_api.py` : sans clé → 401 ; mauvaise clé → 401 ; `POST /api/chat` valide avec container factice → 200 et structure attendue ; question vide ou trop longue → 422 ; liste/upload/suppression de documents ; upload d'un faux PDF (mauvais octets magiques) → refusé ; erreur `RagError` → 502 sans fuite d'information.
- `tests/test_ratelimit.py` : N requêtes autorisées puis 429 avec `Retry-After` ; la fenêtre se réinitialise (simuler le temps) ; compteurs séparés par identifiant.
- `tests/test_upload_validator.py` : extension, taille, magic bytes, nom de fichier malveillant (`../../x.pdf`).
- Test du filtre de logs : une clé d'API dans un message est masquée.

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre, `makemigrations --check` propre.
- [ ] `python manage.py create_api_key test` affiche une clé ; `curl -H "X-API-Key: ..." -X POST http://127.0.0.1:8000/api/chat -d '{"question":"..."}' -H "Content-Type: application/json"` renvoie une réponse sourcée.
- [ ] Sans clé : 401. Au-delà de la limite : 429.
- [ ] `/api/docs` affiche la documentation OpenAPI.
- [ ] `python manage.py check --deploy` (avec `DEBUG=False` simulé) ne signale plus d'avertissement critique, ou chaque avertissement restant est expliqué dans le README.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **Stocker la clé d'API en clair** : stocker uniquement son hash.
- **Rate limit contourné** en multi-processus avec `LocMemCache` : le dire clairement.
- **HSTS/SSL redirect activés trop tôt** : peut rendre le site inaccessible si HTTPS n'est pas correctement configuré.
- **Fuite d'informations** dans les messages d'erreur de l'API.
- **Validation par extension seule** : vérifier aussi le contenu (magic bytes).

## 11. Livrable de la phase

Une API JSON documentée et authentifiée par clé, des uploads validés, une limitation de débit, des en-têtes de sécurité et des logs maîtrisés, le tout couvert par des tests.
