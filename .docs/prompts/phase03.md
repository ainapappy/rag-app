# Phase 03 : Chargement et découpage (chunking)

## 0. Rôle de l'agent

Tu es un agent de code senior et un mentor Python. Le développeur est un dev **PHP/Laravel confirmé, débutant en Python** : explique chaque notion nouvelle avec une analogie Laravel. Réponds en français. Code en anglais, docstrings en français.

## 1. Contexte du projet

Projet `rag-app` : application RAG en **Django**, testée en local avec **Ollama**, déployée avec un **LLM distant configurable** (API compatible OpenAI). Cœur RAG en **Python pur** dans `rag_core/`, Django en couche mince dans `chatbot/`. POO : interfaces `ABC`, injection par constructeur, dataclasses `frozen`, exceptions métier. Lis `CONVENTIONS.md` et le contrat d'architecture dans `prompts/README.md` ; respecte les noms à l'identique.

## 2. État attendu du dépôt avant cette phase

- Phases 00 à 02 terminées : `Settings`, exceptions, `ChatMessage`, `Chunk`, `SearchResult`, LLM, embeddings, `VectorStore` (simple et chroma), commandes `chat_test` et `semantic_demo`, tests verts.
- Le dossier `docs/` existe (vide ou presque).
- Vérifie ces points ; s'il en manque, arrête-toi et signale-le.

## 3. Objectif de la phase

Charger des fichiers `.txt`, `.md`, `.pdf` en objets `Document`, puis les découper en `Chunk` avec métadonnées (fichier, page, index), via deux stratégies interchangeables.

## 4. Mini-cours Python pour développeur Laravel

- **`pathlib.Path`** : ≈ `SplFileInfo` en plus pratique (`path.suffix`, `path.name`, `path.read_text()`, `path.rglob("*.pdf")`).
- **Gestion des fichiers** : `with open(...) as f:` ferme le fichier automatiquement (≈ `try/finally` + `fclose`). Toujours préciser `encoding="utf-8"`.
- **Compréhensions de liste** : `[c for c in chunks if c.text.strip()]` ≈ `array_filter` + `array_map` en une ligne.
- **Expressions régulières (`re`)** : ≈ `preg_*` ; `re.split(r"\n\s*\n", text)` découpe sur les lignes vides.
- **Attributs de classe** : `supported_extensions = (".txt",)` ≈ `const` / propriété statique d'une classe PHP.
- **Fabrique** : `LoaderFactory.for_path(path)` choisit la bonne classe selon l'extension, comme une factory Laravel.

## 5. Travail à réaliser

1. `rag_core/models.py` : ajouter `Document` (dataclass frozen : `source: str`, `content: str`, `page: int | None = None`, `metadata: dict = field(default_factory=dict)`). `source` est le **nom du fichier** (ex. `guide.pdf`).
2. `rag_core/loaders/base.py` : `DocumentLoader(ABC)` avec attribut de classe `supported_extensions: tuple[str, ...]` et méthode abstraite `load(path: Path, source: str | None = None) -> list[Document]`.
3. `rag_core/loaders/txt.py` : `TxtLoader` (UTF-8, repli sur `latin-1` si échec de décodage, avec un avertissement dans les logs). Un `Document`, `page=None`.
4. `rag_core/loaders/markdown.py` : `MarkdownLoader` (même logique ; conserver le texte brut, ajouter le premier titre `#` dans `metadata["title"]` s'il existe).
5. `rag_core/loaders/pdf.py` : `PdfLoader` avec `pypdf` ; **un `Document` par page** (`page` commence à 1) ; ignorer les pages vides ; si aucun texte n'est extrait (PDF scanné), lever `LoaderError` avec un message expliquant que l'OCR n'est pas supporté ; fichier corrompu → `LoaderError`.
6. `rag_core/loaders/factory.py` : `LoaderFactory` avec `supported_extensions()` (liste agrégée), `supports(path) -> bool`, `for_path(path) -> DocumentLoader` (lève `UnsupportedFileTypeError` sinon).
7. `rag_core/chunking/base.py` : `Chunker(ABC)` avec `split(document: Document) -> list[Chunk]`.
8. `rag_core/chunking/fixed_size.py` : `FixedSizeChunker(chunk_size=700, overlap=100)` ; valider `0 <= overlap < chunk_size` ; fenêtre glissante qui **recule la coupure jusqu'à une fin de phrase ou un espace** proche de la limite pour ne pas couper un mot ; ignorer les chunks vides ; garantir que la boucle progresse toujours (pas de boucle infinie).
9. `rag_core/chunking/paragraph.py` : `ParagraphChunker(max_size=700)` ; découpe sur lignes vides, **fusionne** les petits paragraphes jusqu'à `max_size`, et délègue les paragraphes trop longs à un `FixedSizeChunker`.
10. Pour les deux chunkers : `Chunk.index` commence à 0 par document ; `Chunk.id = Chunk.make_id(source, page, index)` ; `Chunk.metadata` contient au minimum `{"chunk_chars": len(text)}` et reprend les métadonnées du document.
11. `rag_core/chunking/factory.py` : `ChunkerFactory.create(settings)` selon `chunker_strategy`.
12. Commande `chunk_preview` : `python manage.py chunk_preview <chemin> [--strategy fixed|paragraph] [--size N] [--overlap N]` qui charge un fichier, le découpe et affiche : nombre de chunks, longueur min/moyenne/max, et les 3 premiers chunks.
13. **Documents d'exemple dans `docs/`** (rédigés par toi, en français, contenant des **faits précis et vérifiables** qui serviront aux tests et à l'évaluation de la phase 09) :
    - `docs/vanille_madagascar.md` : ~600 mots sur la culture de la vanille (régions, récolte, séchage, chiffres inventés mais cohérents).
    - `docs/politique_conges.txt` : politique de congés fictive d'une entreprise (jours annuels, préavis, report, congé maladie, avec des chiffres précis).
    - `docs/guide_rag.md` : ~500 mots expliquant ce qu'est un RAG.
    - Demander ensuite au développeur de **déposer au moins un vrai PDF** de son choix dans `docs/` (il n'est pas versionné s'il est confidentiel : ajouter `docs/*.pdf` à `.gitignore` si pertinent).
14. Mettre à jour `CONVENTIONS.md` (règle : un chunk garde toujours `source`, `page`, `index`).

## 6. Contraintes

- Ne pas encore embedder ni stocker : cette phase s'arrête aux `Chunk`.
- Pas de dépendance nouvelle sauf `reportlab` (dev) pour fabriquer des PDF de test.
- Les fichiers de `docs/` créés par toi sont fictifs : ne pas présenter leur contenu comme réel.

## 7. Tests à écrire

- `tests/test_loaders.py` : chargement `.txt`, `.md` (titre extrait), repli d'encodage ; PDF généré avec `reportlab` dans `tmp_path` (plusieurs pages → plusieurs `Document` avec les bons numéros) ; PDF vide ou corrompu → `LoaderError` ; extension inconnue → `UnsupportedFileTypeError` ; `LoaderFactory.supports`.
- `tests/test_chunking.py` : taille maximale respectée ; chevauchement présent ; aucun chunk vide ; indices consécutifs ; ids déterministes et uniques ; texte plus court que `chunk_size` → un seul chunk ; `ParagraphChunker` fusionne les petits paragraphes et découpe les longs ; paramètres invalides → `ConfigError` ou `ValueError` (choisir et documenter).

## 8. Critères d'acceptation

- [ ] `pytest` vert, `ruff check .` propre.
- [ ] `python manage.py chunk_preview docs/politique_conges.txt` affiche des statistiques et des chunks cohérents.
- [ ] `python manage.py chunk_preview docs/<ton_pdf>.pdf --strategy paragraph` fonctionne et affiche les numéros de page.
- [ ] Aucun chunk ne dépasse `chunk_size` (hors cas explicitement documenté).

## 9. Méthode de travail de l'agent

1. Lire l'état du dépôt et annoncer le plan en quelques lignes.
2. Expliquer brièvement chaque notion Python nouvelle (analogie Laravel).
3. Implémenter par petites étapes en lançant les tests régulièrement.
4. Corriger tout échec avant de continuer : ne jamais laisser le projet cassé.
5. Terminer par un récapitulatif : fichiers créés/modifiés, commandes de test manuel.
6. Proposer un message de commit (Conventional Commits) et mettre à jour README/CONVENTIONS si nécessaire.

## 10. Pièges fréquents

- **Boucle infinie** dans la fenêtre glissante si le pas devient 0 ou négatif.
- **Texte PDF mal extrait** (mots collés, colonnes mélangées) : normaliser les espaces, ne pas promettre une extraction parfaite.
- **Encodage Windows** : ouvrir les fichiers avec `encoding="utf-8"` explicitement.
- **Coupure au milieu d'un mot** : reculer jusqu'à un séparateur.

## 11. Livrable de la phase

`python manage.py chunk_preview <fichier>` qui découpe proprement `.txt`, `.md` et `.pdf` en chunks avec métadonnées, plus trois documents d'exemple dans `docs/`.
