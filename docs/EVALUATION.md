# Rapport d'évaluation du RAG

> ⚠️ **Lecture prudente** : le jeu de test ne compte que 15 questions sur 3
> documents fictifs. L'échantillon est **petit et non représentatif** ; les
> chiffres ci-dessous valident surtout que le pipeline fonctionne et permettent
> de comparer des variantes, pas de garantir la qualité en production.

## Jeu de test

`eval/questions.json` — 15 questions rédigées à partir du contenu réel de
`docs/` : 12 avec réponse attendue (dont 3 reformulations ou fautes légères :
« C'est quoi exactement un RAG ? », « Sur combien d'hectares… ») et 3 hors
corpus (`should_answer: false`) pour mesurer les refus.

## Résultats mesurés (2026-10-26, Ollama / nomic-embed-text, index : 19 chunks)

| Réglages | Hit@k | MRR | Bons refus |
|---|---|---|---|
| **Avant** — vector, chunk 700/100, top_k 4, min_score 0.65 (défauts) | **100 %** | **1.000** | **33 %** |
| hybrid (RRF vector + BM25), mêmes autres réglages | 100 % | 1.000 | 0 % |
| vector, min_score 0.72 | 75 % | 0.750 | 67 % |
| vector, min_score 0.78 | 8 % | 0.083 | 100 % |
| Sweep 18 combinaisons (chunk 400/700/1000 × overlap 50/100 × top_k 3/4/6) | 100 % partout | 1.000 partout | 33 % partout |

## Conclusions et réglages retenus

- **Les défauts du contrat sont conservés** (chunk 700, overlap 100, top_k 4,
  min_score 0.65, retriever `vector`) : aucune variante ne les améliore de
  façon mesurée, et la règle du projet est de ne changer les défauts que sur
  une amélioration mesurée.
- **MIN_SCORE 0.65 est le meilleur compromis** pour nomic-embed-text : à
  0.72 on gagne un refus mais on perd une vraie question (Hit 75 %) ; à 0.78
  presque tout est refusé. La plage utile est étroite — la re-mesurer si le
  modèle d'embeddings change.
- **L'hybride (RRF) est disponible par configuration** (`RETRIEVER=hybrid`)
  mais ne se justifie pas ici : sur des documents courts, le BM25 ramène
  toujours du lexical et casse le taux de bons refus (0 %). À réévaluer avec
  un corpus contenant des noms propres ou codes exacts.
- Le sweep sature partout (Hit 100 %) : le corpus est trop facile pour
  départager les tailles de chunk. Aucun changement de `CHUNK_SIZE`/`OVERLAP`
  ne se justifie sur ces données.

## Limites connues

1. **Sur-ajustement** : les questions ont été rédigées en relisant les
   documents, comme les réglages ont été choisis en les mesurant — le risque
   de sur-ajustement est réel. Garder quelques questions « non vues » et
   renouveler le jeu avant toute conclusion ferme.
2. **Refus imparfaits** : avec un seuil sémantique seul, 2 questions hors
   corpus sur 3 laissent passer du contexte (le LLM reste toutefois invité à
   répondre « introuvable » si le contexte ne contient pas la réponse — le
   test LLM de phase 05 montre qu'il le fait souvent).
3. **Juge LLM** (`--judge`) : mesure indicative — le juge est lui-même un
   LLM, potentiellement indulgent ; ne pas s'en servir comme vérité.
4. **Échantillon** : 15 questions / 3 documents ≈ 20 chunks. Des métriques à
   100 % signifient « pipeline correct sur ce mini-corpus », rien de plus.

## Reproduire

```powershell
python manage.py ingest docs/                  # index de référence
python manage.py eval_rag                      # baseline (vector)
python manage.py eval_rag --retriever hybrid   # comparaison hybride
python manage.py eval_rag --min-score 0.72     # sensibilité au seuil
python manage.py eval_rag --sweep              # grille chunk/overlap/top_k
python manage.py eval_rag --with-llm --judge   # rappel mots-clés + fidélité
```
