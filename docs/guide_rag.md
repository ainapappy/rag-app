# Comprendre le RAG en 500 mots

## Le problème

Les grands modèles de langage (LLM) ont deux limites connues : leurs
connaissances s'arrêtent à la date de leur entraînement, et ils ignorent tout
des documents internes d'une organisation. Surtout, quand on leur pose une
question hors de leur domaine, ils ont tendance à « halluciner » : inventer
une réponse plausible mais fausse, avec un assurance parfaite.

## La solution : RAG

RAG signifie *Retrieval-Augmented Generation*, soit « génération augmentée
par recherche ». L'idée est simple : avant de répondre, le système va
**rechercher** les passages pertinents dans une base documentaire, puis les
**donner au modèle** comme contexte, avec la question. Le modèle ne répond
plus de mémoire : il répond à partir des documents fournis. On peut même lui
demander de citer ses sources.

Un pipeline RAG comporte deux temps : l'**ingestion** (préparer les
documents) et la **recherche-réponse** (répondre aux questions).

## Le temps d'ingestion

L'ingestion transforme des fichiers bruts (PDF, texte, markdown) en unités
exploitables :

1. **Chargement** : extraire le texte des fichiers, page par page.
2. **Découpage** (*chunking*) : couper le texte en fragments de quelques
   centaines de caractères, avec un léger chevauchement pour ne pas perdre
   les phrases à cheval sur deux fragments.
3. **Vectorisation** (*embeddings*) : convertir chaque fragment en un vecteur
   de nombres qui capture son sens. Deux textes de sens proche ont des
   vecteurs proches.
4. **Indexation** : stocker les vecteurs dans une base vectorielle capable de
   retrouver rapidement les plus proches d'un vecteur de requête.

## Le temps de question-réponse

Quand l'utilisateur pose une question, le système :

1. vectorise la question avec le même modèle d'embeddings ;
2. retrouve les `top_k` fragments les plus proches (recherche sémantique) ;
3. construit un prompt contenant la question et les fragments retenus ;
4. envoie le tout au LLM, qui rédige la réponse finale ;
5. renvoie la réponse accompagnée des sources (fichier et page).

## Pourquoi cela fonctionne

Le LLM n'a plus besoin de « savoir » : il n'a plus qu'à « lire » des passages
courts et pertinents. Les hallucinations diminuent fortement, les documents
restent à jour (il suffit de ré-indexer), et chaque réponse est traçable.

## Les points de vigilance

- **La qualité du découpage** : des fragments trop courts perdent le contexte,
  des fragments trop longs diluent l'information.
- **Le seuil de pertinence** : si aucun fragment ne dépasse un score minimal,
  mieux vaut répondre « je ne sais pas » que d'inventer.
- **La fraîcheur de l'index** : un document modifié doit être ré-indexé, sinon
  les réponses s'appuient sur une version obsolète.
- **Le coût et la latence** : chaque question déclenche une recherche
  vectorielle puis un appel au LLM ; en local avec Ollama, tout reste gratuit
  et privé, au prix d'un matériel suffisant.

## En résumé

RAG = recherche sémantique + génération encadrée. C'est le pont entre les
documents d'une organisation et la capacité de rédaction d'un LLM, sans
réentraîner le modèle et sans lui faire confiance aveuglément.
