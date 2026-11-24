"""ChromaDB operations — store and retrieve past cases."""

import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

CHROMA_DIR = os.environ.get("CHROMA_DIR", "./knowledge/chroma_db")
COLLECTION_NAME = "past_cases"


def get_collection():
    """Get or create the ChromaDB collection."""
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        raise ImportError("chromadb not installed. Run: pip install chromadb")

    client = chromadb.PersistentClient(path=CHROMA_DIR)
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def store_chunks(chunks: list[dict]):
    """
    Store text chunks with embeddings into ChromaDB.
    Each chunk: {id, text, metadata}
    """
    if not chunks:
        return

    collection = get_collection()
    embedder = _get_embedder()

    ids = [c["id"] for c in chunks]
    texts = [c["text"] for c in chunks]
    metadatas = [c.get("metadata", {}) for c in chunks]

    # Embed in batches
    batch_size = 50
    all_embeddings = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = embedder.encode(batch).tolist()
        all_embeddings.extend(embeddings)

    # Upsert (add or update)
    collection.upsert(
        ids=ids,
        embeddings=all_embeddings,
        documents=texts,
        metadatas=metadatas,
    )
    logger.info(f"Stored {len(chunks)} chunks in ChromaDB")


def query_similar(text: str, n_results: int = 20, filters: Optional[dict] = None) -> list[dict]:
    """
    Query ChromaDB for similar chunks.
    Returns list of {text, metadata, distance} dicts.
    """
    collection = get_collection()
    embedder = _get_embedder()

    query_embedding = embedder.encode([text]).tolist()[0]

    kwargs = {
        "query_embeddings": [query_embedding],
        "n_results": min(n_results, collection.count()),
        "include": ["documents", "metadatas", "distances"],
    }
    if filters:
        kwargs["where"] = filters

    results = collection.query(**kwargs)

    output = []
    if results["documents"]:
        for doc, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            output.append({"text": doc, "metadata": meta, "distance": dist})
    return output


def list_cases() -> list[str]:
    """Return distinct case names in the knowledge base."""
    try:
        collection = get_collection()
        if collection.count() == 0:
            return []
        # Get all metadatas and extract unique case names
        results = collection.get(include=["metadatas"])
        cases = set()
        for meta in results.get("metadatas", []):
            if meta and meta.get("case_name"):
                cases.add(meta["case_name"])
        return sorted(cases)
    except Exception as e:
        logger.error(f"Failed to list cases: {e}")
        return []


def _get_embedder():
    """Load sentence-transformers embedder (cached)."""
    if not hasattr(_get_embedder, "_model"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            raise ImportError("sentence-transformers not installed. Run: pip install sentence-transformers")
        _get_embedder._model = SentenceTransformer("all-MiniLM-L6-v2")
    return _get_embedder._model
