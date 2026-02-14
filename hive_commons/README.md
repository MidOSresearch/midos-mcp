# HIVE COMMONS

MidOS shared infrastructure.

## Purpose

This package provides shared components for the MidOS system:

- **Unified Configuration**: Single source for paths, API keys, and environment variables
- **Circuit Breaker**: Fault tolerance and self-healing across both layers
- **Vector Store**: LanceDB + Gemini embeddings (768d) - single point of entry
- **Semantic Cache**: Zero-latency response caching
- **LLM Router**: Intelligent model selection with complexity heuristics

## Installation

```bash
# From L1 (Midos)
cd D:\Proyectos\1midos
uv pip install -e ./hive_commons
```

## Usage

```python
from hive_commons import get_circuit_breaker, get_vector_store, get_semantic_cache
from hive_commons.config import L0_ROOT, L1_ROOT, get_api_key, load_hive_env

# Get API keys with fallback aliases
gemini_key = get_api_key("GEMINI")  # Checks GEMINI_API_KEY, GOOGLE_API_KEY

# Use circuit breaker
cb = get_circuit_breaker()
cb.record_failure("mission_123", "timeout")

# Vector store
store = get_vector_store()
store.search("query", top_k=5)
```

## Architecture

```
D:\Proyectos\1midos\
├── hive_commons/  [SHARED PACKAGE]
│   └── src/hive_commons/
│       ├── __init__.py
│       ├── config.py
│       ├── circuit_breaker.py
│       ├── vector_store.py
│       └── semantic_cache.py
```

## Migration

To migrate existing code:

```python
# BEFORE (hardcoded paths, duplicate code)
from src.cortex.circuit_breaker import get_circuit_breaker

# AFTER (shared, consistent)
from hive_commons import get_circuit_breaker
```

## Version

- 0.1.0: Initial release with config, circuit_breaker
