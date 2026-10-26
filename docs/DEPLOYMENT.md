# Déploiement de rag-app

Ce document décrit la mise en production de l'application (Django + cœur RAG
Python pur, LLM via API compatible OpenAI). Il ne présuppose **rien** sur
l'offre de l'hébergeur : les points propres à PlanetHoster sont listés comme
« à vérifier auprès de l'hébergeur », à confronter à leur documentation
officielle et à leur support.

---

## 1. Points à vérifier auprès de PlanetHoster AVANT tout

Ne rien supposer sur leur offre ; obtenir des réponses écrites à :

| Point | Pourquoi |
|---|---|
| Version(s) de Python disponibles (3.11+ requis) | Le code utilise `X | Y` (3.10+), `zip(strict=)` (3.10+) |
| Applications Python/WSGI supportées sur l'offre (Passenger ou équivalent) | C'est ce qui charge `passenger_wsgi.py` |
| Accès SSH | Indispensable pour venv, migrations, collectstatic |
| Mémoire RAM par processus et temps CPU autorisés | numpy + embeddings : viser ≥ 512 Mo |
| Installation de paquets avec roues précompilées (`numpy`, `pypdf`) | Éviter une compilation à la main sur le serveur |
| Version de SQLite disponible | Le cœur utilise la SQLite de Python (stdlib) |
| Accès sortant HTTPS vers l'API du LLM distant | Sinon aucun chat possible |
| Dossiers inscriptibles et **persistants** (entre redémarrages) | `data/` (uploads, index, logs, sauvegardes) |
| Durée maximale d'une requête | Le streaming RAG peut durer plusieurs secondes |
| Gestion des variables d'environnement | Pour `DJANGO_SECRET_KEY`, `LLM_*`, etc. sans `.env` versionné |
| Tâches planifiées (cron) | Pour les sauvegardes automatiques éventuelles |

## 2. Procédure générique de déploiement WSGI

```bash
# 1. Récupérer le code
git clone <depot> rag-app && cd rag-app

# 2. Environnement virtuel (créé par l'hébergeur ou à la main)
python3.11 -m venv ~/.virtualenvs/rag-app
source ~/.virtualenvs/rag-app/bin/activate

# 3. Dépendances (production uniquement — pas requirements-dev.txt)
pip install -r requirements.txt

# 4. Variables d'environnement : panneau de l'hébergeur OU .env HORS dépôt
#    Copier .env.example et renseigner TOUTES les valeurs (voir tableau README).

# 5. Initialisation
python manage.py migrate
python manage.py createsuperuser
python manage.py collectstatic --noinput

# 5 bis. Front : construire AVANT collectstatic (sinon pages sans JS/CSS).
#    Node 20+ requis sur la machine de build (ou construire en local puis
#    téléverser static/chatbot/app/, non versionné).
cd frontend && npm ci && npm run build && cd ..
python manage.py collectstatic --noinput

# 6. Lancer le serveur : méthode DE L'HÉBERGEUR (à vérifier dans leur doc).
#    Le point d'entrée est passenger_wsgi.py (objet `application`).

# 7. Indexer les documents
python manage.py ingest docs/

# 8. Vérifier
curl https://votre-domaine/health/
```

## 3. Choix techniques

### Index vectoriel

- **`VECTOR_STORE=simple` recommandé en mutualisé** : NumPy + SQLite, aucune
  dépendance système.
- `VECTOR_STORE=chroma` seulement si l'hébergeur autorise ses dépendances
  (paquet lourd,SQLite/roues natives) — tester avant de s'engager.

### LLM et embeddings en production

- Renseigner `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, `EMBED_BASE_URL`,
  `EMBED_API_KEY`, `EMBED_MODEL` avec l'API distante choisie (compatible
  OpenAI).
- ⚠️ **Même modèle d'embeddings partout** : un index construit avec
  `nomic-embed-text` est inutilisable avec un autre modèle — le pipeline
  refusera (`EmbeddingModelMismatchError`) ; dans ce cas :
  `python manage.py ingest docs/ --reset`.

### Streaming

- Sous WSGI, **un worker reste occupé pendant toute la génération**. Si
  l'hébergeur limite les processus ou bufferise les réponses :
  `STREAMING_ENABLED=False` (le chat fonctionne sans streaming).

### WhiteNoise et fichiers statiques

- `collectstatic` copie et compresse les statiques dans `staticfiles/` ;
  WhiteNoise les sert depuis l'application. À relancer à chaque déploiement.

## 4. Plan B : VPS (gunicorn + nginx)

Présenté comme **alternative** (pas un prérequis), pour garder la maîtrise :

```ini
# /etc/systemd/system/rag-app.service
[Unit]
Description=rag-app (Django WSGI)
After=network.target

[Service]
User=ragapp
WorkingDirectory=/srv/rag-app
Environment=DJANGO_SETTINGS_MODULE=config.settings
EnvironmentFile=/srv/rag-app/.env   # hors dépôt, permissions 600
ExecStart=/srv/rag-app/.venv/bin/gunicorn --workers 2 --bind 127.0.0.1:8000 config.wsgi:application
Restart=always

[Install]
WantedBy=multi-user.target
```

```nginx
server {
    listen 443 ssl;
    server_name rag.exemple.com;
    # certificats TLS à configurer ici

    location /static/ { alias /srv/rag-app/staticfiles/; }
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;          # indispensable pour le streaming SSE
        proxy_read_timeout 120s;      # génération LLM potentiellement longue
    }
}
```

## 5. Checklist de mise en production

- [ ] `DJANGO_SECRET_KEY` unique, hors dépôt, permissions restrictives
- [ ] `DJANGO_DEBUG=False`
- [ ] `DJANGO_ALLOWED_HOSTS` = domaine réel (sinon 400 partout)
- [ ] `DJANGO_CSRF_TRUSTED_ORIGINS=https://votre-domaine`
- [ ] HTTPS actif ; `SECURE_PROXY_SSL_HEADER` validé avec l'hébergeur avant
      d'activer `SECURE_SSL_REDIRECT`
- [ ] `LLM_API_KEY` / `EMBED_API_KEY` de production (clés distinctes, quota)
- [ ] Une clé d'API créée : `python manage.py create_api_key <nom>`
- [ ] Compte admin créé, mot de passe fort
- [ ] `python manage.py migrate` appliqué
- [ ] `python manage.py collectstatic --noinput` exécuté
- [ ] `python manage.py ingest docs/` (ou corpus de production)
- [ ] `data/` inscriptible et persistant
- [ ] Sauvegardes testées : `python manage.py backup_data` (puis cron si dispo)
- [ ] `RATE_LIMIT_PER_MINUTE` ajusté ; cache partagé si multi-processus
- [ ] `python manage.py check --deploy` : avertissements restants compris et
      assumés (voir README §Sécurité)

## 6. Dépannage

| Symptôme | Cause probable / action |
|---|---|
| Erreur 500 | Consulter `data/logs/app.log` (rotation 5 Mo × 3) |
| Pages CSS/JS absentes | `collectstatic` oublié ou `STATIC_ROOT` non accessible |
| 400 sur toutes les pages | `ALLOWED_HOSTS` vide/incomplet avec `DEBUG=False` |
| `ModuleNotFoundError` au démarrage | venv non activé ou `sys.path` (voir `passenger_wsgi.py`) |
| Upload/indexation échoue | `data/` non inscriptible ou non persistant |
| Réponse qui met X secondes puis timeout | Limite de durée de requête de l'hébergeur ; désactiver le streaming, réduire `TOP_K`/`CHUNK_SIZE` |
| `MemoryError` / process tué | Mémoire insuffisante pour numpy/llm : réduire `EMBED_BATCH_SIZE`, changer d'offre |
| Chat « information introuvable » partout | Modèle d'embeddings changé sans `--reset`, ou `MIN_SCORE` trop haut pour le nouveau modèle |
| Le streaming arrive d'un bloc | Proxy bufferise : `X-Accel-Buffering: no` est déjà envoyé ; sinon `STREAMING_ENABLED=False` |
