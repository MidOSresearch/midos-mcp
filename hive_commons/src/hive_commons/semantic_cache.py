"""
SEMANTIC CACHE - The Reflex (LanceDB)
=====================================
Intercepts LLM calls. If a similar question (similarity > 0.95) was answered before,
returns the cached answer instantly. Zero latency, Zero cost.

Part of hive_commons — MidOS shared infrastructure.
"""
import time
import json
import lancedb
import structlog
from typing import Optional, Dict
from pathlib import Path

from .config import L1_ROOT, ensure_env
from .vector_store import get_embedding

ensure_env()

log = structlog.get_logger("hive_commons.semantic_cache")

# Cache location
CACHE_DIR = L1_ROOT / "knowledge" / "cache"
CACHE_DB_URI = CACHE_DIR / "semantic_cache.lance"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


class SemanticCache:
    """LanceDB-backed semantic cache for LLM responses."""

    def __init__(self):
        self.uri = CACHE_DB_URI
        self.db = lancedb.connect(str(self.uri))
        self.table_name = "llm_responses"

    def _get_table(self):
        try:
            return self.db.open_table(self.table_name)
        except Exception:
            return None

    def cache(self, prompt: str, response: str, model_used: str, task_type: str):
        """Store a response in the cache."""
        try:
            vector = get_embedding(prompt)
            if not vector:
                return

            entry = {
                "prompt": prompt,
                "vector": vector,
                "response": response,
                "model": model_used,
                "task_type": task_type,
                "timestamp": time.time(),
                "hits": 0
            }

            tbl = self._get_table()
            if tbl:
                tbl.add([entry])
            else:
                self.db.create_table(self.table_name, data=[entry])

            log.debug("cached", prompt_preview=prompt[:30])
        except Exception as e:
            log.error("cache_write_error", error=str(e))

    def check(self, prompt: str, threshold: float = 0.95) -> Optional[Dict]:
        """Check if a similar prompt was cached."""
        try:
            tbl = self._get_table()
            if not tbl:
                return None

            vector = get_embedding(prompt)
            if not vector:
                return None

            results = tbl.search(vector).limit(1).to_list()
            if not results:
                return None

            match = results[0]
            similarity = 1.0 - match.get("_distance", 1.0)

            if similarity >= threshold:
                log.info("cache_hit", similarity=f"{similarity:.4f}")
                return {
                    "response": match["response"],
                    "model": match["model"],
                    "cached_at": match.get("timestamp", 0),
                    "similarity": similarity
                }
            return None
        except Exception as e:
            log.error("cache_read_error", error=str(e))
            return None

    # Adapters for compatibility
    def get(self, prompt: str, query_type: str = "default") -> tuple:
        """Adapter: returns (result, was_hit)."""
        hit = self.check(prompt)
        if hit:
            try:
                resp = hit["response"]
                if isinstance(resp, str) and resp.strip().startswith("{"):
                    return json.loads(resp), True
                return resp, True
            except Exception:
                return hit["response"], True
        return None, False

    def set(self, prompt: str, result, query_type: str, estimated_tokens: int = 0):
        """Adapter: saves result."""
        try:
            response_str = json.dumps(result) if isinstance(result, dict) else str(result)
            self.cache(prompt, response_str, "auto", query_type)
        except Exception as e:
            log.error("adapter_set_error", error=str(e))

    def get_stats(self) -> Dict:
        """Get cache statistics."""
        try:
            tbl = self._get_table()
            if not tbl:
                return {"entries": 0, "total_hits": 0, "status": "empty"}
            
            count = len(tbl.to_pandas())
            return {
                "entries": count,
                "db_path": str(self.uri),
                "status": "active"
            }
        except Exception as e:
            return {"entries": 0, "error": str(e), "status": "error"}


# Singleton
_cache: Optional[SemanticCache] = None

def get_cache() -> SemanticCache:
    """Get singleton SemanticCache instance."""
    global _cache
    if _cache is None:
        _cache = SemanticCache()
    return _cache

# Aliases for backward compatibility
get_semantic_cache = get_cache

def cache_response(prompt: str, response: str, model_used: str, task_type: str):
    """Store a response in the cache."""
    get_cache().cache(prompt, response, model_used, task_type)

def check_cache(prompt: str, threshold: float = 0.95) -> Optional[Dict]:
    """Check if a similar prompt was cached."""
    return get_cache().check(prompt, threshold)


if __name__ == "__main__":
    # Test
    cache = get_cache()
    print(f"Cache DB: {CACHE_DB_URI}")
