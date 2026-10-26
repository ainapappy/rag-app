# Phase 02 : Embeddings et base vectorielle

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 et 01 terminées : `Settings`, `get_settings()`, exceptions, `ChatMessage`, `LLMClient`, `OpenAICompatibleLLM`, `FakeLLM`, `LLMFactory`, commande `chat_test`, tests verts.
- Ollama a le modèle `nomic-embed-text`.
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Transformer du texte en vecteurs, mesurer la similarité, et stocker/rechercher des vecteurs derrière une **interface `VectorStore`** avec deux implémentations interchangeables : `SimpleVectorStore` (NumPy + SQLite, sans dépendance lourde) et `ChromaVectorStore`.

## 4. Mini-cours Python pour développeur Laravel

- **Embedding** : un texte devient un vecteur de nombres ; deux textes proches par le sens ont des vecteurs proches. **Similarité cosinus** : mesure l'angle entre deux vecteurs (1 = identiques, 0 = sans rapport).
- **NumPy** : tableaux numériques vectorisés (`np.array`, `@` pour le produit matriciel). Ce que ferait une boucle `foreach` en PHP se fait en une opération sur tout le tableau, bien plus vite.
- **`sqlite3` (bibliothèque standard)** : ≈ PDO avec SQLite ; `with conn:` gère la transaction (commit/rollback automatique).
- **Sérialisation binaire** : `ndarray.tobytes()` / `np.frombuffer(...)` ≈ `pack()/unpack()` PHP, pour stocker un vecteur dans un BLOB.
- **Import paresseux** : importer `chromadb` dans le constructeur (pas en haut du fichier) pour que le projet fonctionne même si le paquet n'est pas installé.
- **Tests paramétrés** : `@pytest.mark.parametrize` ≈ `@dataProvider`.

## 5. Travail à réaliser

1. `rag_core/models.py` : ajouter les dataclasses `frozen` `Chunk(id, text, source, page, index, metadata)` avec `Chunk.make_id(source, page, index) -> str` (sha1 déterministe), et `SearchResult(chunk, score)`.
2. `rag_core/embeddings/base.py` : `EmbeddingProvider(ABC)` avec propriété abstraite `model_name`, `embed(texts) -> list[list[float]]`, `embed_query(text) -> list[float]`.
3. `rag_core/embeddings/openai_compatible.py` : `OpenAICompatibleEmbeddings(base_url, api_key, model, batch_size=32, client=None)` ; appelle `client.embeddings.create` par lots ; erreurs converties en `EmbeddingError` ; vérifie que le nombre de vecteurs égale le nombre de textes.
4. `rag_core/embeddings/fake.py` : `FakeEmbeddingProvider(dimension=64)` : vecteurs **déterministes** dérivés d'un hachage du texte (mêmes textes → mêmes vecteurs ; utile pour les tests). `model_name = "fake-embedding"`.
5. `rag_core/embeddings/similarity.py` : `cosine_similarity(a, b) -> float` et `cosine_similarity_matrix(query, matrix) -> np.ndarray` ; gérer les vecteurs nuls sans division par zéro.
6. `rag_core/embeddings/factory.py` : `EmbeddingFactory.create(settings)`.
7. `rag_core/vectorstore/base.py` : `VectorStore(ABC)` avec **exactement** les méthodes du contrat : `add`, `search`, `delete_by_source`, `count`, `list_sources`, `get_source_hash`, `iter_chunks`, `get_embedding_model`, `set_embedding_model`, `clear`. Documenter chaque méthode.
8. `rag_core/vectorstore/simple.py` : `SimpleVectorStore(path: Path)`.
   - Un fichier SQLite `index.sqlite3` dans `path` (créer le dossier si besoin).
   - Table `chunks(id TEXT PRIMARY KEY, source TEXT, page INTEGER NULL, chunk_index INTEGER, text TEXT, metadata TEXT, embedding BLOB)` et table `meta(key TEXT PRIMARY KEY, value TEXT)`.
   - `add` : upsert dans une transaction ; embeddings stockés en `float32`.
   - `search` : charge la matrice, normalise, produit scalaire, renvoie les `top_k` meilleurs (`np.argpartition` puis tri) en `SearchResult` triés par score décroissant.
   - `get_source_hash(source)` lit la clé `file_hash` dans `metadata` d'un chunk de cette source.
   - `get_embedding_model` / `set_embedding_model` via la table `meta`.
9. `rag_core/vectorstore/chroma.py` : `ChromaVectorStore(path, collection_name="rag")`.
   - Import de `chromadb` dans le constructeur ; si absent : `VectorStoreError("Installez requirements-chroma.txt")`.
   - Client persistant, collection en distance cosinus ; `score = 1 - distance`.
   - `page=None` stocké comme `-1` dans les métadonnées et reconverti à la lecture.
   - Implémenter toutes les méthodes de l'interface (l'itération sur les chunks se fait par pages).
10. `rag_core/vectorstore/factory.py` : `VectorStoreFactory.create(settings)` selon `vector_store`.
11. Commande `chatbot/management/commands/semantic_demo.py` : embed ~8 phrases en français (par ex. « Le chat dort sur le canapé », « Un félin se repose sur le sofa », « La voiture roule sur l'autoroute »...), affiche la matrice de similarité, puis permet `--query "..."` pour une recherche dans un store temporaire.
12. Compléter `container.py` ? **Non** : le conteneur arrive en phase 04.

## 6. Contraintes

- `rag_core/` n'importe pas Django.
- Les deux stores doivent respecter **strictement** la même interface et le même comportement observable.
- Ne pas charger tout l'index en mémoire dans `ChromaVectorStore`.
- Pas d'implémentation de chargement de fichiers ni de chunking ici.

## 7. Tests à écrire

- `tests/test_similarity.py` : vecteurs identiques = 1, orthogonaux = 0, vecteur nul sans erreur.
- `tests/test_embeddings.py` : `FakeEmbeddingProvider` déterministe ; `OpenAICompatibleEmbeddings` avec faux client (lots, erreur → `EmbeddingError`).
- `tests/test_vectorstore.py` : **suite de contrat paramétrée** exécutée sur `SimpleVectorStore` et, si `chromadb` est importable (`pytest.importorskip`), sur `ChromaVectorStore` : ajout, comptage, recherche triée, suppression par source, liste des sources, hash de source, modèle d'embedding, `clear`, `iter_chunks`, persistance (recréer l'objet sur le même dossier `tmp_path`).

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre.
- [ ] `python manage.py semantic_demo` montre « chat » proche de « félin » et loin de « voiture ».
- [ ] `VECTOR_STORE=simple` fonctionne sans `chromadb` installé.
- [ ] (Optionnel) après `pip install -r requirements-chroma.txt`, `VECTOR_STORE=chroma` passe les mêmes tests.
- [ ] Changer d'implémentation de store ne demande aucune modification hors configuration.

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **Mélanger deux modèles d'embedding** dans un même index : dimensions ou sens incompatibles (géré en phase 04).
- **Float64 vs float32** : rester cohérent entre écriture et lecture du BLOB.
- **API Chroma** : elle évolue ; si une méthode n'existe pas telle que décrite, consulter la documentation officielle de la version installée plutôt que d'inventer.
- **Score Chroma** : c'est une distance, pas une similarité.

## 11. Livrable de la phase

Une recherche sémantique fonctionnelle derrière l'interface `VectorStore`, avec un index `simple` sans dépendance lourde (et `chroma` en option), démontrée par `python manage.py semantic_demo`.
