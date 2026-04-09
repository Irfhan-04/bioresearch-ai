"""
Embedding Service — semantic search backbone (Component 2).

Architecture decisions documented here for interview-readiness:

1. MODEL CHOICE: sentence-transformers/all-MiniLM-L6-v2
   - 80MB download, runs fully local (zero API cost)
   - 384-dimensional embeddings (fast cosine similarity)
   - Strong performance on scientific text out-of-the-box
   - Trade-off: not fine-tuned on biotech literature
     → mitigated by domain context prefix injection (see below)

2. DOMAIN CONTEXT PREFIX INJECTION:
   At index time:  "Biotech research abstract: {title}. {abstract}"
   At query time:  "Biotech researcher query: {query}"

   Without prefix: embedding("safety") might cluster near "workplace safety"
   or "food safety". The prefix shifts embedding geometry toward scientific
   interpretation without fine-tuning. This is lightweight domain adaptation.

   Critical: the prefix MUST be applied consistently at both index and query
   time. A mismatch breaks semantic alignment — queries won't find indexed docs.

3. VECTOR STORE: ChromaDB PersistentClient (embedded in FastAPI process)
   - Zero cost, zero network latency, zero auth
   - Stores embeddings to ./chromadb_store on disk
   - Limitation: ephemeral on Render.com (resets on redeploy)
     Production fix: use Pinecone or a persistent volume mount
   - Collection name: "researchers"

4. abstract_relevance_score vs per-query semantic_similarity:
   - abstract_relevance_score: computed ONCE at enrichment time, stored on
     Researcher model. Uses a generic biotech query baseline:
     "biotech drug discovery toxicology organoids". This is Feature 12 in
     the ML scorer — a static signal about how "biotech-flavoured" the
     researcher's abstract is in general.
   - semantic_similarity: computed FRESH at every search query, returned
     in the API response per result. This is the per-query relevance —
     how closely "liver toxicity organoids" matches THIS researcher.
   These are two different numbers that serve different purposes.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# ── Lazy imports — heavy libraries loaded once at first use ──────────────────
_sentence_transformer = None
_chroma_client = None
_chroma_collection = None

CHROMA_PATH = os.environ.get("CHROMADB_PATH", "./chromadb_store")
COLLECTION_NAME = "researchers"

# Default biotech baseline query — used to compute abstract_relevance_score
# at enrichment time (Feature 12 for ML scorer). Covers all 5 research domains.
DEFAULT_BIOTECH_QUERY = (
    "biotech research drug discovery toxicology organoids liver safety"
)

# Domain context prefixes — applied at BOTH index and query time.
# Changing these prefixes after researchers are indexed breaks alignment.
# If you change them: clear ChromaDB and re-index all researchers.
ABSTRACT_PREFIX = "Biotech research abstract: "
QUERY_PREFIX = "Biotech researcher query: "


def _get_model():
    """Load sentence-transformer model once. Cached at module level."""
    global _sentence_transformer
    if _sentence_transformer is None:
        from sentence_transformers import SentenceTransformer  # noqa: PLC0415

        logger.info("Loading sentence-transformers model all-MiniLM-L6-v2 (~80MB on first run)...")
        _sentence_transformer = SentenceTransformer("all-MiniLM-L6-v2")
        logger.info("Model loaded successfully.")
    return _sentence_transformer


def _get_collection():
    """Get or create ChromaDB collection. Initialised once."""
    global _chroma_client, _chroma_collection
    if _chroma_collection is None:
        import chromadb  # noqa: PLC0415

        os.makedirs(CHROMA_PATH, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
        _chroma_collection = _chroma_client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},  # cosine distance for similarity
        )
        logger.info(
            "ChromaDB collection '%s' ready at '%s' (%d documents)",
            COLLECTION_NAME,
            CHROMA_PATH,
            _chroma_collection.count(),
        )
    return _chroma_collection


def _embed_text(text: str) -> List[float]:
    """Embed a single text string. Returns list[float] (384 dims)."""
    model = _get_model()
    embedding = model.encode(text, normalize_embeddings=True)
    return embedding.tolist()


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    """
    Cosine similarity between two L2-normalised vectors.
    Since we use normalize_embeddings=True, this simplifies to dot product.
    """
    a = np.array(vec_a)
    b = np.array(vec_b)
    return float(np.dot(a, b))


class EmbeddingService:
    """
    Manages semantic embedding, ChromaDB indexing, and similarity search
    for researcher profiles.

    All methods are async — CPU-bound embedding is offloaded via asyncio.to_thread()
    to avoid blocking the FastAPI event loop during inference.
    """

    async def index_researcher(
        self,
        researcher_id: str,
        user_id: str,
        title: Optional[str],
        abstract: Optional[str],
        research_area: str,
        name: Optional[str] = None,
    ) -> str:
        """
        Embed researcher abstract and upsert into ChromaDB.

        Called during enrichment after research_area is classified.
        Returns the ChromaDB document ID (same as researcher_id for traceability).

        Args:
            researcher_id:  UUID string — used as ChromaDB doc ID
            user_id:        Owner UUID string — used to isolate tenant queries
            title:          Publication or job title
            abstract:       Research abstract text
            research_area:  Output of research_area_classifier
            name:           Researcher name (stored in metadata)

        Returns:
            document_id (str) — always equals researcher_id
        """
        # Build domain-prefixed text for embedding
        content_parts = filter(None, [title, abstract])
        content = ". ".join(content_parts)
        prefixed = (
            f"{ABSTRACT_PREFIX}{content}"
            if content.strip()
            else ABSTRACT_PREFIX + "biotech researcher"
        )

        doc_id = str(researcher_id)

        def _upsert():
            collection = _get_collection()
            embedding = _embed_text(prefixed)
            collection.upsert(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[prefixed],
                metadatas=[
                    {
                        "researcher_id": doc_id,
                        "user_id": str(user_id),
                        "research_area": research_area,
                        "name": name or "",
                    }
                ],
            )
            return doc_id

        result = await asyncio.to_thread(_upsert)
        logger.debug("Indexed researcher %s (area=%s)", doc_id, research_area)
        return result

    async def compute_abstract_relevance(
        self,
        title: Optional[str],
        abstract: Optional[str],
    ) -> float:
        """
        Compute cosine similarity between researcher abstract and the default
        biotech baseline query. Returns float [0.0, 1.0].

        This is Feature 12 (abstract_relevance_score) for the ML scorer.
        It measures how "biotech-flavoured" this profile is in general —
        independent of any specific search query.

        Stored once on the Researcher model at enrichment time.
        Not recomputed at search time (that is semantic_similarity).
        """
        content_parts = filter(None, [title, abstract])
        content = ". ".join(content_parts)
        prefixed_abstract = (
            f"{ABSTRACT_PREFIX}{content}" if content.strip() else ABSTRACT_PREFIX
        )

        def _compute():
            abstract_vec = _embed_text(prefixed_abstract)
            query_vec = _embed_text(f"{QUERY_PREFIX}{DEFAULT_BIOTECH_QUERY}")
            return _cosine_similarity(abstract_vec, query_vec)

        score = await asyncio.to_thread(_compute)
        # Clamp to [0, 1] — cosine similarity with normalised embeddings is
        # theoretically in [-1, 1] but practically in [0, 1] for related texts
        return float(max(0.0, min(1.0, score)))

    async def semantic_search(
        self,
        query: str,
        user_id: str,
        n_results: int = 20,
        research_area_filter: Optional[str] = None,
    ) -> List[Tuple[str, float]]:
        """
        Semantic search over ChromaDB. Returns (researcher_id, similarity) pairs
        sorted by similarity descending.

        Args:
            query:                 Natural language search query
            user_id:               Owner UUID string for tenant isolation
            n_results:             Number of results to return
            research_area_filter:  If set, filter to this research area only

        Returns:
            List of (researcher_id, similarity_score) tuples
        """
        prefixed_query = f"{QUERY_PREFIX}{query}"

        def _search():
            collection = _get_collection()
            count = collection.count()
            if count == 0:
                logger.warning("ChromaDB collection is empty — no researchers indexed yet")
                return [], []

            where_filter = {"user_id": {"$eq": str(user_id)}}
            if research_area_filter and research_area_filter != "all":
                where_filter["research_area"] = {"$eq": research_area_filter}

            query_embedding = _embed_text(prefixed_query)

            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=min(n_results, count),
                where=where_filter,
                include=["distances", "metadatas"],
            )
            return results["ids"][0], results["distances"][0]

        ids, distances = await asyncio.to_thread(_search)

        # ChromaDB with cosine space returns distances — convert to similarity
        # distance = 1 - cosine_similarity → similarity = 1 - distance
        results = [(doc_id, float(1.0 - dist)) for doc_id, dist in zip(ids, distances)]
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    async def delete_researcher(self, researcher_id: str) -> None:
        """Remove a researcher from the ChromaDB index."""

        def _delete():
            collection = _get_collection()
            collection.delete(ids=[str(researcher_id)])

        await asyncio.to_thread(_delete)
        logger.debug("Deleted researcher %s from ChromaDB", researcher_id)

    def get_index_count(self) -> int:
        """Return number of researchers currently indexed in ChromaDB."""
        collection = _get_collection()
        return collection.count()


# ── Module-level singleton ───────────────────────────────────────────────────
_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


__all__ = ["EmbeddingService", "get_embedding_service"]
