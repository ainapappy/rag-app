# Phase 09 : Qualité et évaluation du RAG

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 08 terminées : RAG complet, chatbot web, API sécurisée, tests verts.
- Les documents d'exemple de `docs/` (`vanille_madagascar.md`, `politique_conges.txt`, `guide_rag.md`) sont indexés.
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

**Mesurer** la qualité du RAG au lieu de la deviner : jeu de questions de référence, métriques simples, comparaison avant/après réglages (taille de chunk, `top_k`, seuil), et option de **recherche hybride** (BM25 + vectorielle).

## 4. Mini-cours Python pour développeur Laravel

- **JSON et fichiers de données** : `json.load` ≈ `json_decode(file_get_contents())`.
- **Métriques de recherche** : *Hit@k* (le bon document est-il dans les k premiers ?), *MRR* (rang moyen inversé du premier bon résultat). Aucune bibliothèque nécessaire : quelques lignes de Python.
- **Normalisation de texte** : `unicodedata.normalize("NFD", s)` pour retirer les accents (≈ `Str::ascii`) afin de comparer des mots-clés.
- **`argparse` dans une commande Django** : `parser.add_argument(...)` ≈ signature `{--option=}` d'une commande Artisan.
- **Produit cartésien** : `itertools.product` pour tester des combinaisons de paramètres (« sweep »).
- **BM25** : algorithme de recherche lexicale (mots exacts) qui complète la recherche sémantique ; la fusion **RRF** (*Reciprocal Rank Fusion*) combine deux classements.

## 5. Travail à réaliser

1. `eval/questions.json` : **12 à 15 questions** rédigées **à partir du contenu réel** des documents de `docs/` (les relire d'abord). Schéma de chaque entrée :
   ```
   {"id": "q01", "question": "...", "expected_source": "politique_conges.txt",
    "expected_page": null, "expected_keywords": ["25 jours"], "should_answer": true}
   ```
   Inclure **au moins 3 questions sans réponse possible** (`should_answer: false`, `expected_source: null`) et quelques questions de reformulation (synonymes, fautes légères).
2. `rag_core/evaluation/` (package Python pur) :
   - `models.py` : dataclasses `EvalCase`, `CaseResult`, `EvalReport` (métriques agrégées + détail par question).
   - `dataset.py` : `EvalDataset.load(path) -> list[EvalCase]` avec validation du schéma (erreur claire si champ manquant).
   - `metrics.py` : fonctions pures `hit_at_k`, `reciprocal_rank`, `keyword_recall` (insensible à la casse et aux accents), `no_answer_correct`.
   - `evaluator.py` : classe `RagEvaluator(retriever, pipeline=None, judge=None)` : pour chaque cas, mesure la **récupération** (la source attendue est-elle dans le top-k ? à quel rang ? page correcte si précisée ?) ; pour `should_answer: false`, vérifie qu'**aucun** résultat ne dépasse le seuil (ou que `found=False`) ; **si un pipeline est fourni** (option `--with-llm`), mesure aussi `keyword_recall` sur la réponse générée.
   - `judge.py` (optionnel, activé par `--judge`) : `FaithfulnessJudge(llm)` demande au LLM si la réponse est **entièrement soutenue par le contexte** (réponse `OUI`/`NON` analysée strictement) ; documenter que c'est une **mesure indicative** (le juge est lui-même un LLM).
3. **Recherche hybride** (optionnelle mais à implémenter) :
   - `rag_core/retrieval/bm25.py` : `Bm25Index` écrit à la main (≈ 50 lignes : tokenisation simple en minuscules sans accents, k1=1.5, b=0.75), construit à partir de `store.iter_chunks()`.
   - `rag_core/retrieval/hybrid.py` : `HybridRetriever(embeddings, store, bm25, top_k, min_score)` avec `retrieve(query)` : fusion **RRF** des classements vectoriel et BM25 ; le filtre `min_score` s'applique au score vectoriel d'origine.
   - Configuration : `RETRIEVER=vector|hybrid` (nouvelle variable du `.env.example`, ajoutée à `Settings`) ; le `Container` choisit l'implémentation. `HybridRetriever` doit respecter la **même interface publique** que `Retriever`.
4. Commande `python manage.py eval_rag` : options `--file eval/questions.json`, `--top-k`, `--min-score`, `--retriever vector|hybrid`, `--with-llm`, `--judge`, `--output eval/reports/<horodatage>.json`, et **`--sweep`**.
   - `--sweep` : teste une grille (par ex. `chunk_size ∈ {400, 700, 1000}`, `overlap ∈ {50, 100}`, `top_k ∈ {3, 4, 6}`) en **réindexant dans un dossier temporaire** (jamais l'index de production) avec le `IngestionPipeline`, puis affiche un tableau comparatif trié par MRR.
   - Sortie console lisible : tableau par question (✔/✘, rang, source trouvée) + métriques globales (Hit@k, MRR, taux de bons refus, `keyword_recall` si LLM).
5. **Rapport avant/après** : exécuter une première évaluation avec les valeurs par défaut, noter les résultats, appliquer des réglages (taille de chunk, `top_k`, `MIN_SCORE`, retriever hybride), réévaluer, et consigner le tout dans `docs/EVALUATION.md` (tableau avant/après, réglages retenus, limites). Mettre à jour les valeurs par défaut de `.env.example` et de `Settings` **uniquement si l'amélioration est mesurée**.
6. Mettre à jour `README.md` racine : « Évaluer la qualité ».

## 6. Contraintes

- Le paquet `evaluation` ne dépend pas de Django ; la commande `eval_rag` ne fait que l'orchestration et l'affichage.
- L'évaluation de la récupération doit fonctionner **sans LLM** (embeddings seuls). Le LLM n'est sollicité qu'avec `--with-llm` / `--judge`.
- Ne jamais modifier l'index réel pendant un `--sweep`.
- Ne pas prétendre que les chiffres du jeu de test sont représentatifs : l'échantillon est petit, le dire dans `docs/EVALUATION.md`.

## 7. Tests à écrire

- `tests/test_eval_metrics.py` : `hit_at_k`, `reciprocal_rank`, `keyword_recall` (accents, casse), cas limites (liste vide).
- `tests/test_eval_dataset.py` : chargement valide ; champ manquant → erreur claire.
- `tests/test_evaluator.py` (embeddings factices, store temporaire) : cas qui doit répondre, cas sans réponse, agrégation des métriques.
- `tests/test_bm25.py` : un mot exact rare remonte en tête ; accents ignorés ; index vide.
- `tests/test_hybrid_retriever.py` : la fusion RRF améliore le rang d'un chunk bien classé par les deux méthodes ; même interface que `Retriever`.
- Test de la commande `eval_rag` avec `call_command` (sans LLM).

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre.
- [ ] `python manage.py eval_rag` affiche Hit@k, MRR et le taux de bons refus sur le vrai index.
- [ ] `python manage.py eval_rag --retriever hybrid` fonctionne et se compare à `vector`.
- [ ] `python manage.py eval_rag --sweep` produit un tableau comparatif sans toucher à `data/index/`.
- [ ] `docs/EVALUATION.md` contient un tableau avant/après et les réglages retenus.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **Évaluer sur ce qu'on a utilisé pour régler** : avec 15 questions, le risque de sur-ajustement est réel ; garder quelques questions « non vues ».
- **Seuil `MIN_SCORE`** : sa bonne valeur dépend du modèle d'embedding ; la mesurer, ne pas la supposer.
- **Questions trop faciles** (copiées mot pour mot) : inclure des reformulations.
- **Juge LLM trop indulgent** : à utiliser comme indicateur, pas comme vérité.

## 11. Livrable de la phase

Un outil de mesure (`python manage.py eval_rag`) et un rapport avant/après qui justifient les réglages par défaut du RAG, avec une recherche hybride disponible par configuration.
