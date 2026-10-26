# Phase 10 : Déploiement et livraison

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI), hébergée sur **PlanetHoster**. Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 09 terminées : RAG, admin, chatbot web, API sécurisée, évaluation, tests verts, `docs/EVALUATION.md`.
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Préparer et documenter la **mise en production**, puis livrer un projet propre de bout en bout : configuration de production, fichier d'entrée WSGI, fichiers statiques, endpoint de santé, procédure de déploiement, sauvegardes, README final et revue complète.

## 4. Mini-cours Python pour développeur Laravel

- **WSGI** : interface standard entre serveur web et application Python (≈ `public/index.php` qui démarre Laravel). `application` (dans `config/wsgi.py`) est l'objet appelé par le serveur. Passenger, gunicorn et uWSGI savent le charger.
- **`collectstatic`** : ≈ `npm run build` + publication des assets : copie tous les fichiers statiques dans `STATIC_ROOT`. **WhiteNoise** les sert directement depuis l'application Python (pratique quand on ne contrôle pas Nginx).
- **Variables d'environnement en production** : jamais de `.env` versionné ; définies dans le panneau de l'hébergeur ou dans un `.env` hors dépôt.
- **`DEBUG=False`** : désactive les pages d'erreur détaillées (≈ `APP_DEBUG=false`) ; exige `ALLOWED_HOSTS` correct.
- **`manage.py check --deploy`** : ≈ audit de configuration de production.
- **Environnement virtuel serveur** : même principe qu'en local, créé par l'hébergeur ou à la main.

## 5. Travail à réaliser

1. **Configuration de production** dans `config/settings.py` (pilotée par l'environnement) :
   - `DEBUG` faux par défaut hors développement ; `ALLOWED_HOSTS` et `CSRF_TRUSTED_ORIGINS` depuis `.env` ;
   - **WhiteNoise** (ajouter `whitenoise` aux dépendances ; middleware juste après `SecurityMiddleware`) ; stockage statique compressé/manifest ;
   - `STATIC_ROOT = BASE_DIR / "staticfiles"` ; chemins de données (`data/media`, `data/index`, `data/logs`) configurables et créés au démarrage s'ils n'existent pas ;
   - vérifier que `python manage.py check --deploy` ne signale rien de critique.
2. **`passenger_wsgi.py`** à la racine : ajoute le dossier du projet à `sys.path`, définit `DJANGO_SETTINGS_MODULE`, et expose `application = get_wsgi_application()` (importé depuis `config.wsgi`). Commenter chaque ligne en français.
3. **Endpoint de santé** `GET /health/` (vue fine, sans authentification) : JSON `{"status": "ok", "db": true, "index_chunks": N, "embedding_model": "..."}` ; ne **jamais** exposer de secret ni de chemin ; option `?deep=1` réservée aux utilisateurs staff pour tester la joignabilité du LLM (appel court avec timeout).
4. **Commandes d'exploitation** :
   - `python manage.py backup_data [--output chemin]` : archive `.tar.gz` ou `.zip` de `data/media`, `data/index` et de la base SQLite (copie cohérente via l'API de sauvegarde `sqlite3`), avec horodatage ; ne contient pas `.env`.
   - Réutiliser `ingest --reset` pour reconstruire l'index.
5. **Documentation `docs/DEPLOYMENT.md`** (français, claire et honnête) :
   - **Questions à poser / vérifier auprès de PlanetHoster avant tout** (ne rien affirmer sur leur offre sans source) : version de Python disponible, prise en charge d'applications Python/WSGI (Passenger ou équivalent) sur l'offre, accès SSH, mémoire et temps CPU/processus autorisés, possibilité d'installer `numpy` et `pypdf` (compilation/roues), version de SQLite, accès sortant HTTPS vers l'API du LLM, dossiers inscriptibles et persistants, durée maximale d'une requête, gestion des variables d'environnement, tâches planifiées.
   - **Procédure générique de déploiement WSGI** : récupérer le code (Git ou FTP), créer/utiliser l'environnement virtuel, `pip install -r requirements.txt`, définir les variables d'environnement, `migrate`, `createsuperuser`, `collectstatic`, redémarrer l'application (méthode dépendante de l'hébergeur : à vérifier dans leur documentation), tester `/health/`.
   - **Choix de l'index vectoriel** : `VECTOR_STORE=simple` recommandé en mutualisé ; `chroma` seulement si l'hébergeur le permet.
   - **Embeddings et LLM en production** : API distante (`LLM_*`, `EMBED_*`) ; rappel : **même modèle d'embedding** partout, sinon `ingest --reset`.
   - **Streaming sous WSGI** : un worker occupé par génération ; `STREAMING_ENABLED=False` si l'hébergeur limite les processus ou bufferise les réponses.
   - **Plan B : VPS** : exemple de service `systemd` pour `gunicorn` et un bloc `nginx` minimal (avec `proxy_buffering off` pour le streaming) ; présenté comme alternative, pas comme prérequis.
   - **Checklist de mise en production** (secrets, `DEBUG`, hôtes, HTTPS, sauvegardes, clé d'API, comptes admin, logs, limite de débit).
   - **Dépannage** : erreur 500 (consulter les logs), fichiers statiques absents (`collectstatic`), erreurs d'import, permissions de dossiers, timeouts, mémoire insuffisante.
6. **Revue de bout en bout** (à exécuter et à consigner dans le récapitulatif) :
   - repartir d'un dossier propre : clone, venv, `pip install -r requirements-dev.txt`, `.env` depuis `.env.example`, `migrate`, `createsuperuser`, `ingest docs/`, `runserver` ;
   - `pytest` (tout vert), `ruff check .`, `python manage.py check --deploy`, `makemigrations --check` ;
   - parcours manuel : connexion, upload d'un PDF dans l'admin, question dans le chat avec streaming et sources, appel API avec clé, `eval_rag` ;
   - relire `CONVENTIONS.md`, corriger les incohérences ou code mort, vérifier qu'il n'y a **aucun TODO**, aucun secret, aucun `print` dans `rag_core/`.
7. **README.md final** : présentation, schéma d'architecture (ASCII ou Mermaid), prérequis, installation locale pas à pas (Windows/macOS/Linux), configuration (tableau des variables), utilisation (admin, chat, API, commandes), tests et qualité, évaluation, déploiement (renvoi vers `docs/DEPLOYMENT.md`), sécurité, limites connues, pistes d'évolution (tâches d'arrière-plan avec `django-q2`, PostgreSQL + pgvector, re-ranking, OCR).
8. **Figer les dépendances** : `requirements.txt` à jour (versions installées), `requirements-chroma.txt` optionnel, `requirements-dev.txt`.
9. Vérifier que `.env`, `data/`, `db.sqlite3`, `staticfiles/` et les PDF privés ne sont pas versionnés ; proposer un **tag** `v1.0.0`.

## 6. Contraintes

- Ne pas inventer les fonctionnalités ou menus du panneau PlanetHoster : renvoyer à leur documentation/support pour les étapes propres à l'hébergeur.
- Aucun secret dans le dépôt, la documentation ou les logs.
- Pas de nouvelle fonctionnalité métier : cette phase est une phase de finition et de livraison.
- Pas de sur-ingénierie (pas de Docker obligatoire, pas de Celery).

## 7. Tests à écrire

- `tests/test_health.py` : `/health/` renvoie 200 et la structure attendue ; n'expose ni chemin ni secret ; `?deep=1` interdit aux non-staff.
- `tests/test_backup.py` : la commande `backup_data` produit une archive contenant l'index, les médias et la base, mais pas `.env`.
- `tests/test_settings_production.py` : avec `DEBUG=False`, les cookies sécurisés sont activés ; `ALLOWED_HOSTS` est pris dans l'environnement.
- Vérifier que toute la suite passe toujours **sans** Ollama ni Internet.

## 8. Critères d'acceptation

- [ ] `pytest`, `ruff check .`, `python manage.py check --deploy`, `makemigrations --check` : tous OK.
- [ ] Installation depuis zéro en suivant **uniquement** le `README.md` : l'application fonctionne.
- [ ] `/health/` répond correctement ; `collectstatic` réussit ; l'application démarre avec `DEBUG=False`.
- [ ] `docs/DEPLOYMENT.md` contient la procédure, la checklist, le dépannage et la liste des points à vérifier auprès de l'hébergeur.
- [ ] `python manage.py backup_data` produit une archive exploitable.
- [ ] Aucun TODO, secret ou `print` parasite dans le code livré.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, résultats de la revue de bout en bout, **liste des points restant à vérifier auprès de PlanetHoster**.
6. Proposer un message de commit (Conventional Commits) et le tag `v1.0.0`.

## 10. Pièges fréquents

- **`ALLOWED_HOSTS` vide avec `DEBUG=False`** : erreur 400 sur toutes les pages.
- **Statiques manquants** : oublier `collectstatic` ou mal configurer WhiteNoise.
- **Dossiers non inscriptibles** pour `data/` : l'index et les uploads échouent.
- **Dépendances qui nécessitent une compilation** sur l'hébergeur : prévoir une alternative (versions précompilées, autre offre).
- **Modèle d'embedding différent entre local et production** : index inutilisable tant qu'on ne réindexe pas.
- **Streaming bufferisé** par un proxy : la réponse arrive d'un bloc ; désactiver le streaming si besoin.

## 11. Livrable de la phase

Un projet **complet, testé, documenté et prêt à déployer** : `README.md`, `docs/DEPLOYMENT.md`, `passenger_wsgi.py`, `/health/`, commande de sauvegarde, dépendances figées, et une revue de bout en bout réussie.
