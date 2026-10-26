# Phase 07 : Chatbot web (historique, reformulation, streaming)

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 06 terminées : `rag_core/` complet (`RagPipeline.ask` et `ask_stream`), modèle `Document`, admin avec indexation, `DocumentIndexingService`, tests verts, un super-utilisateur existe.
- Au moins un document est indexé.
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Un **mini chatbot web** : connexion, liste de conversations, historique persistant, questions de suivi reformulées automatiquement, réponses en **streaming**, sources dépliables sous chaque réponse.

## 4. Mini-cours Python pour développeur Laravel

- **Vues basées sur les classes** (`View`, `TemplateView`) : ≈ contrôleurs Laravel ; `urls.py` ≈ `routes/web.php` (les `name=` = noms de routes).
- **Templates Django** : ≈ Blade. `{% extends %}`, `{% block %}`, `{% include %}`, `{{ variable }}` (échappé automatiquement, comme `{{ }}` Blade), `{% csrf_token %}`, `{% url 'nom' %}`.
- **Authentification** : `LoginRequiredMixin` ≈ middleware `auth` ; `LoginView`/`LogoutView` fournis ; `request.user`.
- **Autorisation par filtrage** : `Conversation.objects.filter(user=request.user)` ≈ policies/scopes ; `get_object_or_404` pour refuser l'accès aux conversations d'autrui.
- **`StreamingHttpResponse`** : ≈ `response()->stream()` Laravel ; accepte un générateur. Le format SSE est du texte `event: ...\ndata: ...\n\n`.
- **JSONField** : colonne JSON pour stocker les sources (≈ cast `array`/`json` Eloquent).
- **Client de test Django** : ≈ `$this->actingAs($user)->post(...)`.

## 5. Travail à réaliser

1. `chatbot/models.py` : `Conversation(user FK, title, created_at)` avec `Meta.ordering = ["-created_at"]` ; `Message(conversation FK related_name="messages", role [user|assistant], content, sources JSONField(default=list), created_at)` ordonné par `created_at`. Migrations.
2. `rag_core/prompting/query_rewriter.py` : `QueryRewriter(llm)` avec `rewrite(question, history) -> str` : si l'historique est vide, renvoie la question telle quelle (aucun appel LLM) ; sinon demande au LLM de **reformuler la question en question autonome** (français, une phrase, sans réponse) et renvoie le résultat nettoyé ; en cas d'erreur LLM, repli sur la question originale (log `warning`).
3. `RagPipeline` : utiliser le `rewriter` s'il est fourni (la recherche utilise la question reformulée ; le prompt final garde la question originale + l'historique). `Container` : fournir `rewriter` et le brancher dans `rag_pipeline`.
4. `chatbot/services.py` : classe `ChatService(container=None)` :
   - `history(conversation) -> list[ChatMessage]` : les `HISTORY_WINDOW` derniers messages.
   - `ask(conversation, question) -> Message` : enregistre la question, appelle `ask`, enregistre la réponse (avec `sources` sérialisées) et la renvoie.
   - `stream(conversation, question) -> Iterator[str]` : enregistre la question, produit des **événements SSE** (chaînes déjà formatées) : `event: sources` (JSON des sources), plusieurs `event: token` (JSON `{"t": "..."}`), puis `event: done` (JSON avec l'id du message) ; **enregistre le message assistant à la fin** (bloc `finally` pour ne pas perdre le texte partiel si le client coupe). Erreurs `RagError` → événement `event: error` avec message lisible.
   - Titre automatique de la conversation à partir de la première question (60 caractères max).
5. Vues (classes, `LoginRequiredMixin`) et routes (`chatbot/urls.py`, incluses dans `config/urls.py`) :
   - `chat/` (`name="chat"`) : liste des conversations + conversation courante ;
   - `chat/new/` (POST, `chat_new`) ; `chat/<int:pk>/` (`chat_detail`) ; `chat/<int:pk>/delete/` (POST, `chat_delete`) ;
   - `chat/<int:pk>/send/` (POST, `chat_send`) : si `STREAMING_ENABLED`, renvoie `StreamingHttpResponse(content_type="text/event-stream")` ; sinon renvoie le fragment HTML du message (réponse non streamée) ;
   - connexion/déconnexion (`LoginView`, `LogoutView`) avec un template `registration/login.html` ; `LOGIN_REDIRECT_URL = "chat"`.
   - Toutes les requêtes filtrent par `user` ; une conversation d'autrui → 404.
6. Templates (`chatbot/templates/chatbot/` + `templates/registration/`) : `base.html`, `chat.html`, `partials/_message.html`, `partials/_sources.html`. Interface sobre et responsive (CSS simple, sans framework lourd), zone de messages, champ de saisie, bouton « Nouvelle conversation », sources sous chaque réponse dans un `<details>`.
7. Statique : `static/chatbot/chat.css` et `static/chatbot/chat.js` :
   - `chat.js` envoie la question avec `fetch` (POST + en-tête CSRF), lit le flux avec `ReadableStream`, analyse les événements SSE, ajoute les tokens au fur et à mesure, affiche les sources à l'événement `sources`, gère `error`, désactive le champ pendant la génération.
   - **HTMX** : pour les actions simples (création/suppression de conversation, chargement de la liste). Placer le fichier `htmx.min.js` d'une version stable précise dans `static/vendor/` (téléchargé depuis la source officielle ; sinon indiquer au développeur où le placer). Ne pas charger de script depuis un CDN sans version figée.
   - Échapper tout texte injecté dans le DOM (`textContent`, pas `innerHTML` pour du contenu venant du LLM).
8. `config/settings.py` : `STATICFILES_DIRS`, `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`.
9. Mettre à jour le `README.md` racine : « Utiliser le chatbot ».

## 6. Contraintes

- Les vues sont **fines** : elles valident, appellent `ChatService`, renvoient la réponse. Aucune logique RAG dans les vues.
- Pas d'accès anonyme au chat.
- Le contenu généré par le LLM n'est **jamais** inséré comme HTML brut.
- Streaming en WSGI : documenter qu'un worker reste occupé pendant la génération (d'où `STREAMING_ENABLED`).
- Ne pas encore créer l'API JSON (phase 08).

## 7. Tests à écrire

- `tests/test_query_rewriter.py` : historique vide → pas d'appel LLM ; reformulation avec `FakeLLM` ; repli en cas d'erreur.
- `tests/test_chat_service.py` : `ask` enregistre 2 messages ; fenêtre d'historique respectée ; `stream` produit `sources`, `token`, `done` dans l'ordre et enregistre la réponse ; titre automatique ; erreur LLM → événement `error`.
- `tests/test_chat_views.py` (client Django, container factice injecté) : redirection vers la connexion si anonyme ; création et affichage d'une conversation ; **un utilisateur ne peut pas lire/supprimer la conversation d'un autre** (404) ; envoi d'un message en mode streaming (contenu `text/event-stream`, événements attendus) ; mode sans streaming ; CSRF requis.

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre, `makemigrations --check` propre.
- [ ] Je me connecte sur `/chat/`, crée une conversation, pose une question : la réponse s'affiche **progressivement** avec ses sources.
- [ ] La question « et pour les congés maladie ? » après une question sur les congés est correctement reformulée (visible dans les logs).
- [ ] Recharger la page conserve l'historique.
- [ ] Avec `STREAMING_ENABLED=False`, le chat fonctionne sans streaming.
- [ ] Un second utilisateur ne voit pas mes conversations.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **`EventSource` ne fait que du GET** : d'où `fetch` + `ReadableStream` pour un POST avec CSRF.
- **Mise en tampon du streaming** : certains proxys/serveurs bufferisent ; envoyer l'en-tête `X-Accel-Buffering: no` et `Cache-Control: no-cache`.
- **Perte du message partiel** si le client ferme la connexion : enregistrer dans un `finally`.
- **XSS** : ne jamais utiliser `innerHTML` avec du texte du LLM.
- **Historique trop long** : toujours appliquer la fenêtre `HISTORY_WINDOW`.

## 11. Livrable de la phase

Un chatbot web fonctionnel en local : connexion, conversations persistantes, questions de suivi comprises, réponses en streaming avec sources dépliables, et isolation des conversations par utilisateur.
