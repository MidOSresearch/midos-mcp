"""
VECTOR STORE - MidOS Knowledge Memory (LanceDB + Gemini + Hybrid Search)
=========================================================================
Semantic + keyword search over the MidOS knowledge base.
Uses gemini-embedding-001 (3072-d) + BM25 FTS with RRF fusion.
"""
import time
import json
import lancedb
import structlog
from pathlib import Path
from typing import List, Dict, Optional, Any

# Use hive_commons config
from .config import (
    LANCE_DB_URI, L1_MEMORY,
    get_api_key, ensure_env
)

ensure_env()

log = structlog.get_logger("hive_commons.vector_store")

# Table for Cloud Embeddings (3072 dims from Gemini gemini-embedding-001)
TABLE_NAME = "knowledge_chunks_cloud"

# Embedding cache: avoids re-embedding identical text within a session
# In-memory only by default (3072-d vectors are too large for JSON persistence)
_embedding_cache: Dict[str, List[float]] = {}

# Ensure directory exists
L1_MEMORY.mkdir(parents=True, exist_ok=True)

def _cache_key(text: str) -> str:
    """SHA256 hash of text for embedding cache lookup."""
    import hashlib
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# Configure Gemini (new SDK)
_genai_client = None

def _get_genai():
    """Lazy load google.genai Client."""
    global _genai_client
    if _genai_client is None:
        from google import genai
        key = get_api_key("GEMINI")
        if key:
            _genai_client = genai.Client(api_key=key)
        else:
            log.error("no_gemini_key", message="Memory will be disabled")
    return _genai_client


def get_embedding(text: str) -> Optional[List[float]]:
    """Get embedding from Google Gemini (gemini-embedding-001, 3072-d)."""
    client = _get_genai()
    if not client:
        return None

    try:
        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text,
        )
        return response.embeddings[0].values
    except Exception as e:
        log.error("embedding_failed", error=str(e))
        # Retry once
        try:
            time.sleep(1)
            response = client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=text,
            )
            return response.embeddings[0].values
        except Exception as e:
            log.warning("embed_content_failed", error=str(e))
            return None


def get_embeddings_batch(texts: List[str], batch_size: int = 50,
                         max_workers: int = 4) -> List[Optional[List[float]]]:
    """Batch-embed multiple texts with concurrent API calls + local cache.

    Flow:
      1. Check cache for each text (SHA256 hash → stored vector)
      2. Collect uncached texts into batches
      3. Embed uncached batches concurrently via ThreadPoolExecutor
      4. Store new embeddings in cache, persist to disk

    Performance stack:
      - Original: ~1200ms/text (1 API call each)
      - Batch only: ~35ms/text (50 per call)
      - Batch + concurrent: ~19ms/text (4 workers)
      - With cache hit: ~0ms/text (no API call)

    Returns list of embeddings (same order as input). None for failed items.
    """
    # Phase 1: Check in-memory cache
    results: List[Optional[List[float]]] = [None] * len(texts)
    uncached: List[tuple] = []  # (original_idx, text)
    cache_hits = 0

    for i, text in enumerate(texts):
        key = _cache_key(text)
        if key in _embedding_cache:
            results[i] = _embedding_cache[key]
            cache_hits += 1
        else:
            uncached.append((i, text))

    if cache_hits > 0:
        log.info("embedding_cache_hits", hits=cache_hits, total=len(texts))

    if not uncached:
        return results

    # Phase 2: Embed uncached texts
    client = _get_genai()
    if not client:
        return results

    uncached_texts = [text for _, text in uncached]

    # Split into batches
    batches = []
    for i in range(0, len(uncached_texts), batch_size):
        batches.append((i, uncached_texts[i:i + batch_size]))

    def _embed_batch(batch_info):
        """Embed a single batch with retry. Returns (start_idx, embeddings)."""
        start_idx, batch = batch_info
        try:
            response = client.models.embed_content(
                model="models/gemini-embedding-001",
                contents=batch,
            )
            return (start_idx, [emb.values for emb in response.embeddings])
        except Exception as e:
            log.warning("batch_embed_failed", batch_start=start_idx,
                        batch_size=len(batch), error=str(e))
            try:
                time.sleep(2)
                response = client.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=batch,
                )
                return (start_idx, [emb.values for emb in response.embeddings])
            except Exception as e2:
                log.error("batch_embed_retry_failed", batch_start=start_idx,
                          error=str(e2))
                return (start_idx, [None] * len(batch))

    # Concurrent execution
    from concurrent.futures import ThreadPoolExecutor
    uncached_results: List[Optional[List[float]]] = [None] * len(uncached_texts)

    effective_workers = min(max_workers, len(batches))
    with ThreadPoolExecutor(max_workers=effective_workers) as executor:
        for start_idx, embeddings in executor.map(_embed_batch, batches):
            for j, emb in enumerate(embeddings):
                uncached_results[start_idx + j] = emb

    # Phase 3: Populate cache + results
    new_cached = 0
    for (orig_idx, text), emb in zip(uncached, uncached_results):
        results[orig_idx] = emb
        if emb is not None:
            _embedding_cache[_cache_key(text)] = emb
            new_cached += 1

    if new_cached > 0:
        log.info("embedding_cache_updated", new_entries=new_cached,
                 total_cache=len(_embedding_cache))

    return results


def store_wisdom_chunks_batch(items: List[Dict]) -> int:
    """Batch-store multiple chunks: batch embed + single LanceDB write.

    items: list of {"text": str, "source": str, "metadata": dict}
    Returns count of successfully stored chunks.

    ~50x faster than sequential store_wisdom_chunk() calls:
    - 1 API call per 50 texts (vs 1 per text)
    - 1 LanceDB write per batch (vs 1 per chunk)
    """
    if not items:
        return 0

    # Filter valid items
    valid = [(i, item) for i, item in enumerate(items) if item.get("text") and len(item["text"]) >= 10]
    if not valid:
        return 0

    texts = [item["text"] for _, item in valid]
    embeddings = get_embeddings_batch(texts)

    # Build chunk records only for successful embeddings
    chunks = []
    ts = time.time()
    for (_, item), vector in zip(valid, embeddings):
        if vector is None:
            continue
        chunks.append({
            "text": item["text"],
            "vector": vector,
            "source": item["source"],
            "timestamp": ts,
            "metadata": json.dumps(item.get("metadata") or {}),
        })

    if not chunks:
        return 0

    ok = get_store().add(chunks)
    if ok:
        log.info("batch_stored", count=len(chunks))
        return len(chunks)

    log.error("batch_store_failed", attempted=len(chunks))
    return 0


def expand_query(query: str) -> str:
    """Expand short queries with context for better embedding match.

    Short queries (< 30 chars) get expanded with domain synonyms
    to improve semantic similarity with stored chunks.
    No API calls — pure local text enrichment.
    """
    if len(query) > 60:
        return query  # Long queries are already descriptive

    q_lower = query.lower()

    # Domain-specific expansions: short term → richer context
    expansions = {
        "caching": "caching response cache semantic cache performance",
        "testing": "testing unit test integration test e2e playwright vitest",
        "deployment": "deployment deploy production CI/CD docker kubernetes",
        "security": "security authentication authorization OWASP vulnerability",
        "performance": "performance optimization speed latency throughput",
        "migration": "migration upgrade breaking changes version update",
        "api": "API REST GraphQL endpoint request response",
        "database": "database SQL ORM query schema migration",
        "auth": "authentication authorization JWT OAuth session tokens",
        "docker": "Docker container image compose kubernetes deployment",
        "react": "React hooks components state management JSX",
        "typescript": "TypeScript types generics interfaces type safety",
        "astro": "Astro framework SSG SSR content collections islands",
        "fastapi": "FastAPI Python web framework async Pydantic",
        "mcp": "MCP Model Context Protocol tools server integration",
        "rag": "RAG retrieval augmented generation vector embeddings search",
        "chunking": "chunking text splitting segmentation embedding retrieval",
        "monitoring": "monitoring logging metrics observability health check",
    }

    for term, expansion in expansions.items():
        if term in q_lower:
            return f"{query} — {expansion}"

    return query


def get_query_embedding(text: str) -> Optional[List[float]]:
    """Embedding for search queries (with automatic expansion)."""
    text = expand_query(text)

    client = _get_genai()
    if not client:
        return None

    try:
        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text,
        )
        return response.embeddings[0].values
    except Exception as e:
        log.error("query_embedding_failed", error=str(e))
        return None


class VectorStore:
    """LanceDB-backed vector store with Gemini embeddings + hybrid search.

    Default search uses RRF fusion of vector (semantic) + FTS (BM25 keyword).
    Benchmark v3 showed +9.3% relevance vs vector-only on 9,753 vectors.
    """

    # Query result cache: hash(query+top_k) -> (timestamp, results)
    _query_cache: dict = {}
    _QUERY_CACHE_TTL = 60  # seconds
    _fts_ready: bool = False  # FTS index created flag

    # RRF constant (standard value, higher = more weight to lower ranks)
    RRF_K = 60

    def __init__(self, table_name: str = TABLE_NAME):
        self.uri = LANCE_DB_URI
        self.table_name = table_name
        self.db = lancedb.connect(str(self.uri))

    def _get_table(self):
        try:
            return self.db.open_table(self.table_name)
        except Exception as e:
            log.warning("open_table_failed", table=self.table_name, error=str(e))
            return None

    def _ensure_fts_index(self, tbl) -> bool:
        """Create FTS index on text column if not already done."""
        if self._fts_ready:
            return True
        try:
            tbl.search("test", query_type="fts").limit(1).to_list()
            self._fts_ready = True
            return True
        except Exception:
            try:
                tbl.create_fts_index("text", replace=True)
                self._fts_ready = True
                log.info("fts_index_created", table=self.table_name)
                return True
            except Exception as e:
                log.warning("fts_index_failed", error=str(e))
                return False

    @staticmethod
    def _rrf_fuse(ranked_lists: List[List[dict]], k: int = 60,
                  limit: int = 5) -> List[dict]:
        """Reciprocal Rank Fusion: merge multiple ranked result lists.

        score(doc) = sum(1 / (rank_i + k)) across all lists.
        Uses first 200 chars of text as doc identity.
        """
        doc_scores: Dict[str, tuple] = {}  # text_hash -> (score, doc)
        for ranked_list in ranked_lists:
            for rank, doc in enumerate(ranked_list):
                doc_id = doc["text"][:200]
                rrf_score = 1.0 / (rank + 1 + k)
                if doc_id in doc_scores:
                    doc_scores[doc_id] = (doc_scores[doc_id][0] + rrf_score, doc)
                else:
                    doc_scores[doc_id] = (rrf_score, doc)
        sorted_docs = sorted(doc_scores.values(), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in sorted_docs[:limit]]

    def add(self, items: List[Dict[str, Any]]) -> bool:
        """Add items to the vector store."""
        if not items:
            return False

        try:
            tbl = self._get_table()
            if tbl:
                tbl.add(items)
            else:
                self.db.create_table(self.table_name, data=items)
            return True
        except Exception as e:
            log.error("add_failed", error=str(e))
            return False

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """Hybrid search: vector + FTS + RRF fusion (with 60s cache).

        Pipeline:
          1. Vector search (semantic similarity via Gemini embeddings)
          2. FTS search (BM25 keyword matching)
          3. RRF fusion merges both ranked lists
          Falls back to vector-only if FTS unavailable.

        Benchmark: +9.3% relevance vs vector-only on 9,753 vectors.
        """
        try:
            # Check cache first
            cache_key = _cache_key(f"{query}:{top_k}")
            now = time.time()
            if cache_key in self._query_cache:
                cached_ts, cached_results = self._query_cache[cache_key]
                if now - cached_ts < self._QUERY_CACHE_TTL:
                    return cached_results

            tbl = self._get_table()
            if not tbl:
                return []

            # Retrieve more candidates for fusion (3x final)
            retrieve_k = min(top_k * 3, 30)

            # Vector search (semantic)
            query_vector = get_query_embedding(query)
            if not query_vector:
                log.warning("no_query_embedding")
                return []
            vec_results = tbl.search(query_vector).limit(retrieve_k).to_list()

            # FTS search (BM25 keyword matching)
            fts_results = []
            if self._ensure_fts_index(tbl):
                try:
                    fts_results = tbl.search(query, query_type="fts").limit(retrieve_k).to_list()
                except Exception as e:
                    log.debug("fts_search_failed", error=str(e))

            # Fuse results (or fallback to vector-only)
            if fts_results:
                merged = self._rrf_fuse(
                    [vec_results, fts_results],
                    k=self.RRF_K,
                    limit=top_k
                )
            else:
                merged = vec_results[:top_k]

            refined = []
            for rank, r in enumerate(merged):
                refined.append({
                    "text": r["text"],
                    "source": r.get("source", "unknown"),
                    "score": 1.0 / (rank + 1),  # RRF-based relevance
                    "timestamp": r.get("timestamp", 0),
                    "metadata": r.get("metadata", "{}")
                })

            # Store in cache
            self._query_cache[cache_key] = (now, refined)
            return refined
        except Exception as e:
            log.error("search_failed", error=str(e))
            return []

    def count(self) -> int:
        tbl = self._get_table()
        return len(tbl) if tbl else 0


# Singleton
_store: Optional[VectorStore] = None

def get_store() -> VectorStore:
    """Get singleton VectorStore instance."""
    global _store
    if _store is None:
        _store = VectorStore()
    return _store


def store_wisdom_chunk(text: str, source: str, metadata: Dict = None) -> bool:
    """Store a chunk of wisdom in the vector store."""
    if not text or len(text) < 10:
        return False

    try:
        vector = get_embedding(text)
        if not vector:
            return False

        chunk = {
            "text": text,
            "vector": vector,
            "source": source,
            "timestamp": time.time(),
            "metadata": json.dumps(metadata or {})
        }

        return get_store().add([chunk])
    except Exception as e:
        log.error("store_error", error=str(e))
        return False


def search_memory(query: str, top_k: int = 5) -> List[Dict]:
    """Search the memory for relevant chunks."""
    return get_store().search(query, top_k)


def get_memory_stats() -> Dict:
    """Get stats about the memory store."""
    return {
        "status": "online",
        "engine": "lancedb_hybrid (gemini-embedding-001 + BM25 RRF)",
        "table": TABLE_NAME,
        "total_chunks": get_store().count()
    }


if __name__ == "__main__":
    # Test
    stats = get_memory_stats()
    print(f"Memory stats: {stats}")
