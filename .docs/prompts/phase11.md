# Phase 11 (évolution « 10+ ») : Frontend Vue.js + Reka UI + Tailwind

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings/commentaires en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. Les phases 00 à 10 sont terminées (chatbot web en streaming, API JSON sécurisée, évaluation, production). L'interface actuelle du chat est en templates Django + HTMX + un `chat.js` écrit à la main (`static/chatbot/chat.js`).

Cette phase est une **évolution** : elle remplace le front du chatbot par une SPA légère **Vue 3 + TypeScript**, montée **dans les templates Django** (Django reste le serveur de pages et d'API ; pas de backend Node). Composants d'interface : **Reka UI** (composants headless accessibles). Style : **Tailwind CSS v4**.

Ce front sert de **pièce de portfolio** : la structure, la typage et la qualité de code doivent être exemplaires (organisation par responsabilité, api/ composables/ components/, composants petits et typés, lint propre).

Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 10 terminées : `pytest` vert, `ruff check .` propre, chat en streaming fonctionnel (`chat/`), API JSON avec clés (`/api/...`), WhiteNoise en production.
- `chatbot/templates/chatbot/` : `base.html`, `chat.html`, `partials/_message.html`, `partials/_sources.html` ; `static/chatbot/chat.css` et `chat.js` ; HTMX dans `static/vendor/`.
- Node.js ≥ 20 et npm ≥ 10 disponibles sur la machine de développement (`node --version`).
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Refondre **uniquement l'interface du chatbot web** (`/chat/...`) en **Vue 3 (TypeScript) + Reka UI + Tailwind**, sans toucher au cœur RAG, aux services, aux modèles ni à l'admin Django :

- Django continue de rendre les pages (coquille HTML) et l'authentification par session ;
- Vue gère toute l'interactivité : liste des conversations, fil de messages, streaming SSE, sources dépliables, suppression avec confirmation ;
- le protocole SSE existant (`sources` / `token` / `done` / `error`) est **conservé tel quel** ;
- le mode `STREAMING_ENABLED=False` continue de fonctionner ;
- HTMX et le JavaScript artisanal sont retirés.

## 4. Mini-cours pour développeur Laravel

- **Vite** : le même outil que Laravel utilise par défaut pour le front (`npm run dev` / `npm run build`). Ici configuré à la main (pas de `laravel-vite-plugin`), avec `@vitejs/plugin-vue` et `vue-tsc` pour compiler et vérifier les types des composants `.vue`.
- **Composant monofichier `.vue`** : ≈ un composant Blade + son Alpine + son CSS regroupés en un seul fichier (`<template>`, `<script setup lang="ts">`, `<style scoped>`).
- **`<script setup>`** : sucre syntaxique de la Composition API (≈ injections dans un contrôleur : ce qui est déclaré en haut est disponible dans le template).
- **`ref` / `computed`** : ≈ des propriétés réactives d'un composant Livewire : quand la valeur change, le DOM se met à jour tout seul.
- **TypeScript** : ≈ PHPDoc, mais vérifié à la compilation ; `tsc`/`vue-tsc` joue le rôle de PHPStan côté front.
- **Reka UI** (ex-Radix Vue) : composants **headless** (≈ Radix/Shadcn, Headless UI) : ils fournissent comportement et accessibilité (Dialog, DropdownMenu, Collapsible...), on fournit le style avec Tailwind.
- **Tailwind CSS** : utilitaires CSS dans les classes ; la v4 se branche directement sur Vite (`@tailwindcss/vite`), configuration par CSS (`@import "tailwindcss"`), plus de `tailwind.config.js` obligatoire.
- **`package.json`** : ≈ `composer.json` pour le front ; versions épinglées, `package-lock.json` commité (≈ `composer.lock`) ; ESLint + Prettier ≈ Pint + un formateur.
- **Props / événements** : `props` = données descendantes (≈ variables passées à une vue Blade), `emit` = événements montants.
- **Composable** : fonction réutilisable (`useChat`) ≈ un service ou trait Laravel, mais côté client ; l'objet de l'api (`api/`) est à l'ajax ce qu'un repository est à Eloquent.

## 5. Travail à réaliser

1. **Squelette front `frontend/`** à la racine, structuré par responsabilité (pièce de portfolio : chaque dossier a une raison d'être claire) :

   ```
   frontend/
   ├── index.html                  # point d'entrée Vite uniquement (jamais servi par Django)
   ├── package.json                # versions épinglées, scripts dev/build/typecheck/lint/test
   ├── package-lock.json           # commité (≈ composer.lock)
   ├── vite.config.ts              # plugins vue + tailwind, outDir, manifest, alias @
   ├── tsconfig.json               # strict: true
   ├── eslint.config.js            # eslint + eslint-plugin-vue + typescript-eslint
   ├── .prettierrc.json
   └── src/
       ├── main.ts                 # crée l'app Vue, monte sur #chat-app
       ├── assets/app.css          # @import "tailwindcss" + tokens (couleurs, police)
       ├── types/chat.ts           # Conversation, ChatMessage, Source, événements SSE typés
       ├── api/                    # accès HTTP : fetch, CSRF, erreurs — aucun état réactif ici
       │   ├── client.ts           # wrapper fetch (JSON, X-CSRFToken, gestion d'erreurs typée)
       │   └── conversations.ts    # liste / create / detail / delete, send (flux SSE)
       ├── lib/
       │   └── sse.ts              # parseur SSE pur (texte → événements), sans dépendance au DOM
       ├── composables/            # état réactif et orchestration — aucune logique HTTP bas niveau
       │   ├── useConversations.ts # liste, conversation courante, création/suppression
       │   └── useChat.ts          # envoi, streaming, isStreaming, erreur, mode non-streamé
       └── components/
           ├── chat/
           │   ├── MessageList.vue
           │   ├── MessageBubble.vue     # bulles user/assistant, texte échappé (jamais v-html)
           │   ├── SourcesPanel.vue      # Reka UI Collapsible : sources, score, page
           │   └── Composer.vue          # saisie + envoi, désactivé pendant la génération
           ├── conversations/
           │   ├── ConversationList.vue
           │   ├── ConversationMenu.vue  # Reka UI DropdownMenu (supprimer...)
           │   └── ConfirmDeleteDialog.vue  # Reka UI Dialog
           └── ui/                       # fins wrappers Reka UI réutilisables (BaseDialog, ...)
   ```

   - dépendances : `vue` 3.x, `reka-ui`, `tailwindcss` 4.x + `@tailwindcss/vite` ; dev : `vite`, `@vitejs/plugin-vue`, `typescript`, `vue-tsc`, `eslint`, `eslint-plugin-vue`, `typescript-eslint`, `prettier`, `vitest` ;
   - `vite.config.ts` : `build.outDir = "../static/chatbot/app/"`, `build.manifest = true`, `server.origin` pour le dev, alias `@` → `src/` ;
   - **`lib/sse.ts` est pur et testé** (vitest, `npm run test`) : c'est lui qui rend le code présentable et maintenable, à l'image de ce que fait `pytest` côté Python.
2. **Intégration Django/Vite** :
   - nouvelle variable `.env` **`FRONTEND_DEV_URL`** (défaut vide) : si définie (ex. `http://localhost:5173`), `base.html` charge les assets depuis le serveur Vite (hot reload) ; sinon elle charge les fichiers construits dans `static/chatbot/app/` via le **manifest Vite**, lu par `chatbot/templatetags/vite.py` (jamais de nom de fichier en dur, le hash change à chaque build) ;
   - l'ajouter à `.env.example` et au tableau du contrat (`prompts/README.md`) ;
   - `.gitignore` : `node_modules/` et `static/chatbot/app/` (assets construits non commités, comme `public/build` en Laravel).
3. **Endpoints JSON pour l'interface** (session + CSRF, distincts de l'API à clés de la phase 08) dans `chatbot/` :
   - `GET chat/api/conversations/` : liste des conversations de l'utilisateur ;
   - `POST chat/api/conversations/` : création (`{"title": ...}` optionnel) ;
   - `GET chat/api/conversations/<pk>/` : détail + messages (sources incluses) ;
   - `DELETE chat/api/conversations/<pk>/` : suppression ;
   - vues **fines** (JSON, jamais de fragment HTML) qui délèguent à `ChatService`/ORM ; filtrage par `request.user`, conversation d'autrui → 404 ; CSRF requis ;
   - `POST chat/<int:pk>/send/` reste la source unique du streaming SSE ; en mode `STREAMING_ENABLED=False`, renvoyer désormais **un JSON** (`{"role": ..., "content": ..., "sources": [...]}`) au lieu du fragment HTML (mettre à jour les tests concernés).
4. **Qualité front (niveau portfolio)** :
   - `npm run typecheck` (`vue-tsc --noEmit`) et `npm run lint` sans erreur ; formatage Prettier cohérent ;
   - composants **petits et à responsabilité unique** ; props et émissions **typés** (`defineProps<{...}>`, `defineEmits`) ;
   - aucune logique HTTP dans les composants : ils appellent les composables, les composables appellent l'api ;
   - accessibilité : les composants Reka UI gèrent focus/clavier ; un seul `h1`, labels sur les champs, focus visible ;
   - style 100 % Tailwind : sobre, responsive, mode sombre via `prefers-color-scheme`.
5. **Nettoyage** : supprimer `static/chatbot/chat.css`, `chat.js`, les partiels `partials/_message.html` et `partials/_sources.html`, et **HTMX** (`static/vendor/htmx.min.js` et son inclusion) ; `base.html` garde l'auth Django et la coquille ; la page de connexion `registration/login.html` peut être re-stylée avec le CSS Tailwind construit (un simple `<form>` Django suffit, pas de Vue).
6. **Tests** :
   - front : tests vitest du **parseur SSE uniquement** (`lib/sse.ts`, événements `sources`/`token`/`done`/`error` bien découpés, flux coupé en plein milieu d'un événement) — pas de sur-ingénierie au-delà ;
   - Django : tous les tests existants restent verts (adapter ceux qui lisaient le fragment HTML du mode non-streamé) ; nouveaux tests des endpoints JSON (voir §7).
7. **Docs** :
   - `README.md` : section « Développement front » (`npm install`, `npm run dev` avec `FRONTEND_DEV_URL`, scripts `typecheck`/`lint`/`test`, `npm run build` avant `collectstatic`) + une ou deux **captures d'écran** de l'interface (pièce de portfolio) ;
   - `docs/DEPLOYMENT.md` : ajouter `npm ci && npm run build` dans la procédure (Node requis sur la machine de build ; possible en local puis envoi de `static/chatbot/app/`) ;
   - `prompts/README.md` : mettre à jour le contrat (stack front, arborescence `frontend/`, routes JSON, variable `FRONTEND_DEV_URL`).

## 6. Contraintes

- **Django reste la seule source de vérité** : pas de backend Node, pas d'auth JWT, la session Django et le CSRF restent les mécanismes.
- Le protocole SSE de `ChatService.stream` ne change pas : côté serveur, seul l'habillage change.
- Le contenu du LLM n'est **jamais** inséré en HTML brut (`v-html` interdit).
- Pas de logique métier côté client au-delà de l'affichage ; pas de Pinia ni de routeur Vue (un seul écran : les composables suffisent, c'est le bon niveau d'abstraction) ; TypeScript strict activé.
- Ne pas toucher à `rag_core/`, aux modèles, aux services, à l'admin ni à l'API à clés de la phase 08.
- L'application doit fonctionner **sans Node** une fois les assets construits : si `static/chatbot/app/` est absent, lever une erreur claire (message dans le template ou log), pas une page blanche silencieuse.

## 7. Tests à écrire

- `frontend/src/lib/sse.test.ts` (vitest) : découpage correct des événements SSE, y compris un chunk coupé au milieu d'un événement, et la gestion de `error`.
- `tests/test_chat_api_views.py` : liste/création/détail/suppression JSON, connecté ; CSRF requis ; la conversation d'un autre utilisateur → 404 ; format JSON attendu (ids, messages, sources).
- Adapter `tests/test_chat_views.py` : `send/` en mode non-streamé renvoie du JSON (et plus du HTML) ; le mode streaming reste inchangé.
- Vérifier que la suite Python passe toujours **sans** Ollama, Internet ni Node, et que `npm run typecheck`, `npm run lint` et `npm run test` passent.

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre, `makemigrations --check` propre ; `npm run typecheck`, `npm run lint`, `npm run test` verts.
- [ ] Sur `/chat/`, l'interface Vue s'affiche (Tailwind visible), la liste des conversations se charge en JSON, l'envoi d'une question streame **progressivement** avec les sources dépliables.
- [ ] Supprimer une conversation demande une confirmation (Dialog) et fonctionne.
- [ ] Avec `STREAMING_ENABLED=False`, le chat fonctionne (réponse affichée d'un bloc).
- [ ] `npm run build` puis `collectstatic` : l'application fonctionne avec `DEBUG=False` (assets servis par WhiteNoise, sans serveur Node).
- [ ] Une question « et pour les congés maladie ? » après une question sur les congés est toujours correctement reformulée (rien n'a changé côté pipeline).
- [ ] Un second utilisateur ne voit pas mes conversations (endpoints JSON compris).
- [ ] Plus aucune trace de HTMX ni de `chat.js` dans le dépôt.
- [ ] Le front est présentable en portfolio : structure par responsabilité, typage strict, lint propre, captures d'écran dans le README.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion front nouvelle (analogie Laravel : Vite, SFC, headless UI, TypeScript).
3. Implémenter par petites étapes : squelette Vite → intégration template → endpoints JSON → api/ et composables → composants Vue (un par un, en testant `npm run dev`) → nettoyage HTMX.
4. Lancer `pytest`, `ruff check .`, `npm run typecheck` et `npm run lint` régulièrement ; corriger tout échec avant de continuer.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel, étapes de build.
6. Proposer un message de commit (Conventional Commits, ex. `feat: Vue 3 + Reka UI + Tailwind frontend for the chatbot`).

## 10. Pièges fréquents

- **CSRF avec `fetch`** : envoyer `X-CSRFToken` (cookie `csrftoken` ou `{% csrf_token %}` dans la coquille) ; sinon 403 sur les POST/DELETE.
- **Nom de fichier construit en dur** (`app-abc123.js`) : il change à chaque build → toujours passer par le manifest Vite.
- **Oubli de `npm run build` avant `collectstatic`** : page sans JS/CSS en production ; documenter l'ordre (build → collectstatic).
- **`v-html` avec du texte du LLM** : XSS ; les moustaches `{{ }}` échappent par défaut, s'en tenir là.
- **Chunks SSE coupés** : un `chunk` réseau peut terminer au milieu d'un événement — d'où un parseur avec buffer (le cas est testé dans `sse.test.ts`).
- **Streaming bufferisé** : mêmes en-têtes que la phase 07 (`X-Accel-Buffering: no`, `Cache-Control: no-cache`), le front n'y change rien.
- **Vite dev server et origine** : sans `server.origin`, les assets du mode dev pointent vers le mauvais hôte et Django les bloque.
- **Reka UI non stylé** : les composants headless n'apportent aucun style — tout l'habillage Tailwind est à écrire.
- **`tsconfig` trop permissif** : sans `strict: true`, le typage ne sert à rien ; le garder strict dès le départ plutôt que de rattraper ensuite.

## 11. Livrable de la phase

L'interface du chatbot refondue en **Vue 3 + TypeScript + Reka UI + Tailwind**, servie par des templates Django, avec le streaming SSE intact, le mode non-streamé conservé, des endpoints JSON de session, HTMX retiré, une base front structurée et typée (typecheck/lint/tests verts) et une procédure de build documentée dans le README et `docs/DEPLOYMENT.md`.
