"""
HIVE COMMONS - MidOS Shared Infrastructure
===========================================
Core components for the MidOS system.

Modules:
- llm_router: Intelligent LLM routing with complexity heuristics
- vector_store: LanceDB + Gemini embeddings (3072-d) + hybrid search
- semantic_cache: Zero-latency response caching
- circuit_breaker: Fault tolerance and graceful degradation
- config: Shared configuration management

Usage:
    from hive_commons import get_llm_router, VectorStore, SemanticCache
    from hive_commons.config import load_hive_env
"""

__version__ = "0.1.0"

# Lazy imports to avoid circular dependencies
def get_llm_router():
    from .llm_router import get_router
    return get_router()

def get_vector_store():
    from .vector_store import get_store
    return get_store()

def get_semantic_cache():
    from .semantic_cache import get_cache
    return get_cache()

def get_circuit_breaker():
    from .circuit_breaker import get_breaker
    return get_breaker()

__all__ = [
    "get_llm_router",
    "get_vector_store",
    "get_semantic_cache",
    "get_circuit_breaker",
    "__version__",
]
