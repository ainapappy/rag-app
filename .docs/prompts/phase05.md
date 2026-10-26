# Phase 05 : RAG complet en ligne de commande

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 04 terminées : config, LLM, embeddings, `VectorStore`, loaders, chunkers, `IngestionPipeline`, `Container`, commandes `chat_test`, `semantic_demo`, `chunk_preview`, `ingest`, fixtures `conftest.py`, tests verts.
- L'index contient les documents de `docs/` (`python manage.py ingest docs/ --list`).
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Répondre à une question **uniquement à partir des documents**, en citant les sources (fichier, page), avec un comportement honnête quand l'information est absente (« je ne sais pas » sans appeler le LLM).

## 4. Mini-cours Python pour développeur Laravel

- **f-strings** : `f"Source {i}: {chunk.source}"` ≈ interpolation de chaînes PHP `"{$x}"`.
- **Chaînes multilignes** : `"""..."""` ≈ heredoc PHP.
- **`Sequence` / `tuple`** : le paramètre `history=()` évite l'argument mutable par défaut (piège classique : `history=[]` serait partagé entre appels, contrairement à PHP).
- **Dataclass avec itérateur** : `StreamedAnswer` transporte les sources **et** un générateur de tokens (non « frozen » car contient un itérateur).
- **Tri et déduplication** : `sorted(..., key=lambda r: r.score, reverse=True)` ≈ `usort`, et dictionnaire pour dédupliquer par clé.
- **Constantes de module** : `NO_ANSWER_MESSAGE = "..."` ≈ `const` de classe.

## 5. Travail à réaliser

1. `rag_core/models.py` : ajouter `Source(source, page, score, excerpt)`, `Answer(text, sources, found)` (frozen) et `StreamedAnswer(sources, found, tokens)` (dataclass non frozen).
2. `rag_core/retrieval/retriever.py` : `Retriever(embeddings, store, top_k, min_score)` avec `retrieve(query: str) -> list[SearchResult]` : embed la requête (`embed_query`), cherche `top_k`, **filtre** les scores `< min_score`, trie par score décroissant.
3. `rag_core/prompting/prompt_builder.py` : `PromptBuilder` avec `build(question, results, history=()) -> list[ChatMessage]` :
   - Message `system` en français : répondre **uniquement** avec le contexte fourni ; si l'information n'y figure pas, répondre exactement qu'elle est introuvable dans les documents ; citer les sources avec `[1]`, `[2]`... ; ne pas inventer ; répondre dans la langue de la question.
   - Contexte formaté : `[1] (fichier.pdf, page 3)\n<texte du chunk>` pour chaque résultat.
   - Historique (messages précédents) inséré avant la question finale.
   - Un contrôle de **taille maximale du contexte** (caractères) configurable en constante, en tronquant les chunks les moins bien classés.
4. `rag_core/pipeline/rag.py` :
   - Constante `NO_ANSWER_MESSAGE = "Je n'ai pas trouvé cette information dans les documents."`
   - `RagPipeline(retriever, prompt_builder, llm, rewriter=None)`.
   - `ask(question, history=()) -> Answer` : retrieve → si aucun résultat : `Answer(NO_ANSWER_MESSAGE, [], found=False)` **sans appeler le LLM** → sinon construit le prompt, appelle `llm.chat`, construit les `Source` (dédupliquées par `(source, page)`, meilleur score conservé, `excerpt` tronqué à ~200 caractères).
   - `ask_stream(question, history=()) -> StreamedAnswer` : même logique mais `tokens` est un itérateur issu de `llm.stream` ; si rien n'est trouvé, `tokens` produit directement `NO_ANSWER_MESSAGE`.
   - Le paramètre `rewriter` est accepté (peut être `None`) mais **non utilisé** avant la phase 07 ; documenter ce point.
5. `Container` : ajouter les propriétés `retriever`, `prompt_builder`, `rag_pipeline`.
6. Commande `ask` : `python manage.py ask "question" [--stream] [--top-k N] [--min-score X] [--show-context]` ; affiche la réponse, puis les sources (fichier, page, score) ; avec `--show-context`, affiche aussi les chunks retrouvés. Les options `--top-k` et `--min-score` surchargent la config pour l'expérimentation.
7. Mettre à jour `README.md` racine : section « Utilisation en ligne de commande » (`ingest` puis `ask`).

## 6. Contraintes

- Le RAG ne dépend que d'**interfaces** (`LLMClient`, `EmbeddingProvider` via `Retriever`, `VectorStore`).
- Pas d'historique de conversation persistant ici (phase 07) : l'historique est seulement un paramètre.
- Aucune logique de prompt dans la commande Django.
- Température basse (déjà configurée) : ne pas la modifier ici.

## 7. Tests à écrire

- `tests/test_retriever.py` : filtre par `min_score`, tri, `top_k` respecté.
- `tests/test_prompt_builder.py` : le message système interdit de sortir du contexte ; contexte numéroté ; historique placé avant la question ; troncature du contexte.
- `tests/test_rag_pipeline.py` (`FakeLLM`, `FakeEmbeddingProvider`, store temporaire) :
  - question avec contexte pertinent → `found=True`, sources présentes, LLM appelé une fois ;
  - **aucun résultat → `found=False`, `NO_ANSWER_MESSAGE`, le LLM n'est jamais appelé** (`fake_llm.calls == []`) ;
  - déduplication des sources par `(source, page)` ;
  - `ask_stream` : sources immédiatement disponibles, tokens consommables, texte reconstitué identique à `ask`.
- Test `@pytest.mark.integration` : question réelle sur `docs/politique_conges.txt` avec Ollama.

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre.
- [ ] `python manage.py ask "Combien de jours de congés par an ?"` répond correctement avec la source `politique_conges.txt`.
- [ ] `python manage.py ask "Quelle est la capitale de l'Australie ?"` répond que l'information est introuvable (aucun appel au LLM, vérifiable avec `--show-context` ou les logs).
- [ ] `--stream` affiche la réponse progressivement.
- [ ] Les sources affichées correspondent aux documents réellement utilisés.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **Seuil `MIN_SCORE` mal réglé** : trop haut → « introuvable » partout ; trop bas → le LLM reçoit du bruit. Il dépend du modèle d'embedding ; on l'ajustera en phase 09.
- **Contexte trop long** : dépasser la fenêtre du petit modèle local dégrade les réponses.
- **Argument mutable par défaut** (`history=[]`) : utiliser un tuple.
- **Citations inventées** : le LLM peut citer `[5]` alors qu'il n'y a que 4 sources ; les sources affichées viennent du retriever, pas du texte généré.

## 11. Livrable de la phase

`python manage.py ask "ma question"` qui répond uniquement à partir des documents, cite ses sources, refuse proprement quand l'information est absente, et fonctionne aussi en streaming.
