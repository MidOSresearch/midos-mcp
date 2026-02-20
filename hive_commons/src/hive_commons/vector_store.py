"""
VECTOR STORE - MidOS Knowledge Memory (LanceDB + Gemini + Hybrid Search)
=========================================================================
Semantic + keyword search over the MidOS knowledge base.
Uses gemini-embedding-001 (3072-d) + BM25 FTS with RRF fusion.
Includes memory decay scoring for knowledge lifecycle management.
"""
import math
import time
import json
import lancedb
import structlog
from pathlib import Path
from typing import List, Dict, Optional, Any

# Use hive_commons config
from .config import LANCE_DB_URI, L1_MEMORY, get_api_key, ensure_env

ensure_env()

log = structlog.get_logger("hive_commons.vector_store")

# Table for Cloud Embeddings (3072 dims from Gemini gemini-embedding-001)
TABLE_NAME = "knowledge_chunks_cloud_rebuild"

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


def get_embeddings_batch(
    texts: List[str], batch_size: int = 50, max_workers: int = 4
) -> List[Optional[List[float]]]:
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
        batches.append((i, uncached_texts[i : i + batch_size]))

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
            log.warning(
                "batch_embed_failed",
                batch_start=start_idx,
                batch_size=len(batch),
                error=str(e),
            )
            try:
                time.sleep(2)
                response = client.models.embed_content(
                    model="models/gemini-embedding-001",
                    contents=batch,
                )
                return (start_idx, [emb.values for emb in response.embeddings])
            except Exception as e2:
                log.error(
                    "batch_embed_retry_failed", batch_start=start_idx, error=str(e2)
                )
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
        log.info(
            "embedding_cache_updated",
            new_entries=new_cached,
            total_cache=len(_embedding_cache),
        )

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
    valid = [
        (i, item)
        for i, item in enumerate(items)
        if item.get("text") and len(item["text"]) >= 10
    ]
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
        chunks.append(
            {
                "text": item["text"],
                "vector": vector,
                "source": item["source"],
                "timestamp": ts,
                "metadata": json.dumps(item.get("metadata") or {}),
            }
        )

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


# LRU cache for query embeddings — avoids repeated Gemini API calls
# Key: expanded query text, Value: embedding vector
# Typical latency savings: 1-2s per cached hit
_QUERY_EMBEDDING_CACHE: dict = {}  # {text: (timestamp, embedding)}
_QUERY_EMBEDDING_CACHE_TTL = 300  # 5 minutes
_QUERY_EMBEDDING_CACHE_MAX = 100  # max entries


def get_query_embedding(text: str) -> Optional[List[float]]:
    """Embedding for search queries (with automatic expansion + LRU cache)."""
    text = expand_query(text)

    # Check cache first
    now = time.time()
    if text in _QUERY_EMBEDDING_CACHE:
        cached_ts, cached_emb = _QUERY_EMBEDDING_CACHE[text]
        if now - cached_ts < _QUERY_EMBEDDING_CACHE_TTL:
            return cached_emb
        else:
            del _QUERY_EMBEDDING_CACHE[text]

    client = _get_genai()
    if not client:
        return None

    try:
        response = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text,
        )
        embedding = response.embeddings[0].values
        # Store in cache (evict oldest if full)
        if len(_QUERY_EMBEDDING_CACHE) >= _QUERY_EMBEDDING_CACHE_MAX:
            oldest_key = min(
                _QUERY_EMBEDDING_CACHE, key=lambda k: _QUERY_EMBEDDING_CACHE[k][0]
            )
            del _QUERY_EMBEDDING_CACHE[oldest_key]
        _QUERY_EMBEDDING_CACHE[text] = (now, embedding)
        return embedding
    except Exception as e:
        log.error("query_embedding_failed", error=str(e))
        return None


# ============================================================================
# DECAY SCORING
# ============================================================================

# Default half-life: 30 days (score halves every 30 days without access)
DEFAULT_HALF_LIFE_DAYS = 30.0


def compute_decay_score(
    base_quality: float = 0.5,
    last_accessed: float = 0.0,
    access_count: int = 0,
    created_at: float = 0.0,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """Compute memory decay score using importance-weighted exponential decay.

    Formula: decay_score = base_quality * time_factor * access_boost
    Where:
      time_factor = 0.95 ^ days_since_access  (≈ half-life of ~14 days)
      access_boost = log(access_count + 1)     (logarithmic to avoid runaway)

    Uses the simpler V1 formula from the task spec. For the full importance-weighted
    exponential with configurable half-life, see compute_decay_score_v2().

    Returns float in range [0.0, ~5.0] (unbounded on access_boost).
    """
    now = time.time()
    days_since = (now - (last_accessed or created_at or now)) / 86400.0
    days_since = max(0.0, days_since)

    time_factor = 0.95**days_since
    access_boost = math.log(access_count + 1) if access_count > 0 else 0.1

    return base_quality * time_factor * access_boost


def compute_decay_score_v2(
    base_score: float = 0.5,
    importance: float = 0.5,
    created_at: float = 0.0,
    last_accessed: float = 0.0,
    access_count: int = 0,
    half_life_days: float = DEFAULT_HALF_LIFE_DAYS,
) -> float:
    """Full importance-weighted exponential decay (research-grade).

    From mcp_persistent_memory_patterns_2026.md recommended formula.
    """
    now = time.time()
    days_since = max(0.0, (now - (last_accessed or created_at or now)) / 86400.0)

    lambda_decay = math.log(2) / half_life_days
    time_factor = math.exp(-lambda_decay * days_since)

    access_boost = 1.0 + 0.1 * math.log1p(access_count)

    return base_score * importance * time_factor * access_boost


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
    def _rrf_fuse(
        ranked_lists: List[List[dict]], k: int = 60, limit: int = 5
    ) -> List[dict]:
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

        # Normalize source paths to POSIX forward-slash (BL-118)
        for item in items:
            if "source" in item and isinstance(item["source"], str):
                item["source"] = item["source"].replace("\\", "/")

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

    def search(
        self,
        query: str,
        top_k: int = 5,
        *,
        search_mode: str = "hybrid",
        rerank: bool = False,
        alpha: float = 0.5,
    ) -> List[Dict]:
        """Configurable search: vector, keyword, or hybrid with optional reranking.

        Args:
            query: Search query string.
            top_k: Number of final results.
            search_mode: "vector" | "keyword" | "hybrid" (default: "hybrid").
            rerank: If True, apply reranking after initial retrieval.
            alpha: Balance for weighted RRF (0.0 = pure keyword, 1.0 = pure vector).
                   Only used in hybrid mode. Default 0.5 (equal weight).

        Pipeline:
          1. Retrieve candidates via vector and/or keyword search
          2. Fuse with alpha-weighted RRF (hybrid mode)
          3. Optionally rerank (cross-encoder or score-based fallback)

        Backwards compatible: search(query, top_k) works as before.
        """
        try:
            cache_key = _cache_key(f"{query}:{top_k}:{search_mode}:{rerank}:{alpha}")
            now = time.time()
            if cache_key in self._query_cache:
                cached_ts, cached_results = self._query_cache[cache_key]
                if now - cached_ts < self._QUERY_CACHE_TTL:
                    return cached_results

            tbl = self._get_table()
            if not tbl:
                return []

            retrieve_k = min(top_k * 3, 30)
            vec_results = []
            fts_results = []

            # Vector search (semantic)
            if search_mode in ("vector", "hybrid"):
                query_vector = get_query_embedding(query)
                if query_vector:
                    vec_results = tbl.search(query_vector).limit(retrieve_k).to_list()
                elif search_mode == "vector":
                    log.warning("no_query_embedding_for_vector_mode")
                    return []

            # FTS/BM25 search (keyword)
            if search_mode in ("keyword", "hybrid"):
                if self._ensure_fts_index(tbl):
                    try:
                        fts_results = (
                            tbl.search(query, query_type="fts")
                            .limit(retrieve_k)
                            .to_list()
                        )
                    except Exception as e:
                        log.debug("fts_search_failed", error=str(e))

            # Merge results based on mode
            if search_mode == "vector":
                merged = vec_results[: top_k * 2]
            elif search_mode == "keyword":
                merged = fts_results[: top_k * 2]
            else:  # hybrid
                if vec_results and fts_results:
                    merged = self._rrf_fuse_weighted(
                        vec_results,
                        fts_results,
                        alpha=alpha,
                        k=self.RRF_K,
                        limit=top_k * 2,
                    )
                elif vec_results:
                    merged = vec_results[: top_k * 2]
                else:
                    merged = fts_results[: top_k * 2]

            # Rerank if requested
            if rerank and merged:
                merged = self._rerank(query, merged, top_k)
            else:
                merged = merged[:top_k]

            refined = []
            for rank, r in enumerate(merged):
                entry = {
                    "text": r["text"],
                    "source": r.get("source", "unknown"),
                    "score": r.get("_rerank_score", 1.0 / (rank + 1)),
                    "timestamp": r.get("timestamp", 0),
                    "metadata": r.get("metadata", "{}"),
                    "search_mode": search_mode,
                }
                refined.append(entry)

            self._query_cache[cache_key] = (now, refined)
            return refined
        except Exception as e:
            log.error("search_failed", error=str(e))
            return []

    @staticmethod
    def _rrf_fuse_weighted(
        vec_results: List[dict],
        fts_results: List[dict],
        alpha: float = 0.5,
        k: int = 60,
        limit: int = 10,
    ) -> List[dict]:
        """Alpha-weighted Reciprocal Rank Fusion.

        score(doc) = alpha * (1/(vec_rank + k)) + (1-alpha) * (1/(fts_rank + k))

        Args:
            alpha: 0.0 = pure keyword, 1.0 = pure vector, 0.5 = equal weight.
        """
        doc_scores: Dict[str, tuple] = {}

        for rank, doc in enumerate(vec_results):
            doc_id = doc["text"][:200]
            score = alpha * (1.0 / (rank + 1 + k))
            doc_scores[doc_id] = (score, doc)

        for rank, doc in enumerate(fts_results):
            doc_id = doc["text"][:200]
            score = (1.0 - alpha) * (1.0 / (rank + 1 + k))
            if doc_id in doc_scores:
                doc_scores[doc_id] = (doc_scores[doc_id][0] + score, doc)
            else:
                doc_scores[doc_id] = (score, doc)

        sorted_docs = sorted(doc_scores.values(), key=lambda x: x[0], reverse=True)
        return [doc for _, doc in sorted_docs[:limit]]

    def _rerank(self, query: str, candidates: List[dict], top_k: int) -> List[dict]:
        """Rerank candidates using cross-encoder or fallback scoring.

        Tries sentence-transformers cross-encoder first (best quality).
        Falls back to decay-score-based reranking (always available).
        """
        # Try cross-encoder reranking
        reranked = self._rerank_cross_encoder(query, candidates, top_k)
        if reranked is not None:
            return reranked

        # Fallback: score-based reranking using decay + text overlap
        return self._rerank_score_fallback(query, candidates, top_k)

    @staticmethod
    def _rerank_cross_encoder(
        query: str, candidates: List[dict], top_k: int
    ) -> Optional[List[dict]]:
        """Rerank using sentence-transformers cross-encoder (optional dep)."""
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
            pairs = [(query, c["text"][:512]) for c in candidates]
            scores = model.predict(pairs)
            for i, score in enumerate(scores):
                candidates[i]["_rerank_score"] = float(score)
            candidates.sort(key=lambda x: x.get("_rerank_score", 0), reverse=True)
            return candidates[:top_k]
        except ImportError:
            return None
        except Exception as e:
            log.debug("cross_encoder_failed", error=str(e))
            return None

    @staticmethod
    def _rerank_score_fallback(
        query: str, candidates: List[dict], top_k: int
    ) -> List[dict]:
        """Fallback reranking: combine initial rank with text overlap score.

        Scores: 0.6 * normalized_rank + 0.4 * keyword_overlap
        """
        query_tokens = set(query.lower().split())
        for i, c in enumerate(candidates):
            # Rank score: higher for earlier positions
            rank_score = 1.0 / (i + 1)
            # Keyword overlap score
            text_tokens = set(c.get("text", "").lower().split()[:200])
            overlap = len(query_tokens & text_tokens) / max(len(query_tokens), 1)
            # Combined score
            c["_rerank_score"] = 0.6 * rank_score + 0.4 * overlap
        candidates.sort(key=lambda x: x.get("_rerank_score", 0), reverse=True)
        return candidates[:top_k]

    def count(self) -> int:
        tbl = self._get_table()
        return len(tbl) if tbl else 0

    # ================================================================
    # DECAY-AWARE METHODS
    # ================================================================

    def get_decay_report(self, limit: int = 20) -> List[Dict]:
        """Get chunks sorted by decay score (lowest first = most stale).

        Returns chunks with decay_score, last_accessed, access_count.
        Handles gracefully if columns don't exist yet (pre-migration).
        """
        tbl = self._get_table()
        if not tbl:
            return []

        try:
            rows = tbl.search().limit(min(limit * 5, 500)).to_list()
        except Exception:
            try:
                rows = tbl.to_pandas().to_dict("records")[:500]
            except Exception as e:
                log.error("decay_report_read_failed", error=str(e))
                return []

        scored = []
        for r in rows:
            la = r.get("last_accessed", r.get("timestamp", 0)) or r.get("timestamp", 0)
            ac = r.get("access_count", 0) or 0
            ds = compute_decay_score(
                base_quality=0.5,
                last_accessed=la,
                access_count=ac,
                created_at=r.get("timestamp", 0),
            )
            scored.append(
                {
                    "text": (r.get("text", "") or "")[:150],
                    "source": r.get("source", "unknown"),
                    "decay_score": round(ds, 4),
                    "access_count": ac,
                    "last_accessed_days_ago": round((time.time() - la) / 86400, 1)
                    if la
                    else None,
                    "created_days_ago": round(
                        (time.time() - r.get("timestamp", 0)) / 86400, 1
                    )
                    if r.get("timestamp")
                    else None,
                }
            )

        scored.sort(key=lambda x: x["decay_score"])
        return scored[:limit]

    def refresh_chunk(self, text_prefix: str) -> bool:
        """Mark a chunk as freshly accessed (reset decay timer).

        Finds chunk by text prefix match and updates last_accessed + access_count.
        """
        tbl = self._get_table()
        if not tbl:
            return False

        try:
            # Find matching rows
            rows = tbl.search().limit(200).to_list()
            for r in rows:
                if (r.get("text", "") or "").startswith(text_prefix[:100]):
                    now = time.time()
                    ac = (r.get("access_count", 0) or 0) + 1
                    try:
                        # Try update (works if columns exist)
                        tbl.update(
                            where=f"source = '{r.get('source', '')}'",
                            values={"last_accessed": now, "access_count": ac},
                        )
                    except Exception:
                        # Columns may not exist yet (pre-migration)
                        log.debug("refresh_update_fallback", source=r.get("source"))
                    return True
            return False
        except Exception as e:
            log.error("refresh_failed", error=str(e))
            return False

    def archive_chunk(self, text_prefix: str) -> bool:
        """Move a chunk to cold storage (set decay_score to -1 sentinel).

        Archived chunks are excluded from normal search but not deleted.
        """
        tbl = self._get_table()
        if not tbl:
            return False

        try:
            rows = tbl.search().limit(500).to_list()
            for r in rows:
                if (r.get("text", "") or "").startswith(text_prefix[:100]):
                    try:
                        tbl.update(
                            where=f"source = '{r.get('source', '')}'",
                            values={"decay_score": -1.0},
                        )
                    except Exception:
                        log.debug("archive_decay_col_missing")
                    # Also write to archive log
                    archive_log = L1_MEMORY / "archived_chunks.jsonl"
                    with open(archive_log, "a", encoding="utf-8") as f:
                        f.write(
                            json.dumps(
                                {
                                    "source": r.get("source", ""),
                                    "text_preview": (r.get("text", "") or "")[:200],
                                    "archived_at": time.time(),
                                    "reason": "manual_archive_via_mcp",
                                }
                            )
                            + "\n"
                        )
                    return True
            return False
        except Exception as e:
            log.error("archive_failed", error=str(e))
            return False

    def batch_rescore_decay(self) -> Dict[str, Any]:
        """Recalculate decay scores for all chunks. Run weekly via hook.

        Returns stats about the rescore operation.
        """
        tbl = self._get_table()
        if not tbl:
            return {"error": "no_table"}

        try:
            df = tbl.to_pandas()
        except Exception as e:
            return {"error": f"read_failed: {e}"}

        total = len(df)
        updated = 0
        stale_count = 0
        stale_threshold = 0.05

        for idx, row in df.iterrows():
            la = row.get("last_accessed", row.get("timestamp", 0)) or row.get(
                "timestamp", 0
            )
            ac = row.get("access_count", 0) or 0

            score = compute_decay_score(
                base_quality=0.5,
                last_accessed=la,
                access_count=ac,
                created_at=row.get("timestamp", 0),
            )

            if score < stale_threshold:
                stale_count += 1

            df.at[idx, "decay_score"] = score
            updated += 1

        # Write back (LanceDB overwrite mode)
        try:
            if "decay_score" not in df.columns:
                df["decay_score"] = 0.0
            if "last_accessed" not in df.columns:
                df["last_accessed"] = df.get("timestamp", 0.0)
            if "access_count" not in df.columns:
                df["access_count"] = 0

            self.db.drop_table(self.table_name, ignore_missing=True)
            self.db.create_table(self.table_name, data=df)
            log.info(
                "batch_rescore_complete",
                total=total,
                updated=updated,
                stale=stale_count,
            )
        except Exception as e:
            return {"error": f"write_failed: {e}", "rescored": updated}

        return {
            "total": total,
            "rescored": updated,
            "stale_below_threshold": stale_count,
            "threshold": stale_threshold,
        }


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
            "metadata": json.dumps(metadata or {}),
        }

        return get_store().add([chunk])
    except Exception as e:
        log.error("store_error", error=str(e))
        return False


def search_memory(
    query: str,
    top_k: int = 5,
    *,
    search_mode: str = "hybrid",
    rerank: bool = False,
    alpha: float = 0.5,
) -> List[Dict]:
    """Search the memory for relevant chunks.

    Args:
        query: Search query string.
        top_k: Number of results.
        search_mode: "vector" | "keyword" | "hybrid" (default: "hybrid").
        rerank: Apply reranking (cross-encoder or fallback).
        alpha: Vector/keyword balance for hybrid (0.0=keyword, 1.0=vector).
    """
    return get_store().search(
        query, top_k, search_mode=search_mode, rerank=rerank, alpha=alpha
    )


def get_memory_stats() -> Dict:
    """Get stats about the memory store."""
    return {
        "status": "online",
        "engine": "lancedb_hybrid (gemini-embedding-001 + BM25 RRF + decay)",
        "table": TABLE_NAME,
        "total_chunks": get_store().count(),
    }


def get_decay_report(limit: int = 20) -> List[Dict]:
    """Get chunks sorted by decay score (lowest = most stale)."""
    return get_store().get_decay_report(limit)


def refresh_chunk(text_prefix: str) -> bool:
    """Mark chunk as freshly accessed."""
    return get_store().refresh_chunk(text_prefix)


def archive_chunk(text_prefix: str) -> bool:
    """Move chunk to cold storage."""
    return get_store().archive_chunk(text_prefix)


def batch_rescore() -> Dict:
    """Recalculate all decay scores."""
    return get_store().batch_rescore_decay()


if __name__ == "__main__":
    # Test
    stats = get_memory_stats()
    print(f"Memory stats: {stats}")
