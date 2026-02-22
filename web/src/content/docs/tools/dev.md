---
title: "Dev Tier Tools (6)"
description: Developer tools requiring midos_sk_dev API key — full knowledge access, sessions, code chunking, and pool coordination.
---

These 6 tools require a `midos_sk_dev_*` API key or higher. They unlock full, untruncated knowledge access and session management.

---

## get_skill

Get a specific skill document by name.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `name` | string | Yes | — | Skill name (case-insensitive, fuzzy matched) |
| `section` | string | No | `""` | Extract specific section by header |
| `page` | int | No | 0 | Page number for pagination |
| `mode` | string | No | `""` | Set to `"toc"` for table of contents only |

**Returns:** Full skill document in markdown (up to 10,000 chars) or "not found."

```json
{
  "name": "get_skill",
  "arguments": {
    "name": "fastapi-patterns",
    "section": "Dependency Injection"
  }
}
```

**Notes:** Fuzzy matching means `"react"` will find `"react-comprehensive"` or `"react-19-migration"`. Use `mode: "toc"` to browse sections before requesting a specific one.

---

## get_protocol

Get an operational protocol or procedure document.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `name` | string | Yes | — | Protocol name (case-insensitive) |

**Returns:** Full protocol document in markdown (up to 10,000 chars) or "not found."

---

## chunk_code

Parse a code file into semantic chunks for RAG ingestion.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `file_path` | string | Yes | — | Path to code file (within knowledge/) |

**Returns:** AST-based chunks with metadata including function signatures, class names, line numbers, and docstrings. Language auto-detected from file extension.

```json
{
  "name": "chunk_code",
  "arguments": {
    "file_path": "knowledge/chunks/example_patterns.py"
  }
}
```

---

## memory_stats

Get vector store diagnostics and statistics.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| *(none)* | — | — | — | — |

**Returns:** `{ total_chunks, cache_size, lance_db_status, embedding_model, cache_hit_rate }`

Useful for monitoring vector store health and cache performance.

---

## pool_status

Check multi-instance coordination pool status.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| *(none)* | — | — | — | — |

**Returns:** Current pool state showing active instances, claimed resources, and signals. Read-only — no writes allowed through this tool.

---

## save_progress

Save a session checkpoint for later resumption via `where_was_i` or `get_progress`.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `session_id` | string | Yes | — | Unique session identifier |
| `summary` | string | Yes | — | What was accomplished |
| `files_touched` | string | No | `""` | Comma-separated list of modified files |
| `decisions_made` | string | No | `""` | Key decisions during session |
| `next_steps` | string | No | `""` | What to do next time |
| `round_id` | string | No | `""` | Operation round identifier |

**Returns:** `{ status: "saved", session_id, round_id }`

```json
{
  "name": "save_progress",
  "arguments": {
    "session_id": "api-refactor-2026-02",
    "summary": "Refactored auth middleware to use JWT. Tests passing.",
    "files_touched": "auth.py, middleware.py, tests/test_auth.py",
    "decisions_made": "Chose JWT over session cookies for stateless scaling",
    "next_steps": "Add refresh token rotation, update API docs"
  }
}
```
