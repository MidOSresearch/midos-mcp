---
title: "Pro Tier Tools (5)"
description: Pro tools requiring midos_sk_pro API key — EUREKA, truth patches, semantic search, hybrid search, and episodic memory.
---

These 5 tools require a `midos_sk_pro_*` or `midos_sk_mod_*` API key. They unlock the most valuable knowledge layers and advanced search capabilities.

---

## get_eureka

Get a breakthrough improvement document (validated discovery with ROI data).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `name` | string | Yes | — | EUREKA name (case-insensitive, fuzzy matched) |

**Returns:** Full EUREKA document in markdown (up to 10,000 chars). Each EUREKA includes: Problem → Solution → Test Results → ROI.

```json
{
  "name": "get_eureka",
  "arguments": {
    "name": "response cache"
  }
}
```

---

## get_truth

Get a verified truth patch (correction to common misconceptions).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `name` | string | Yes | — | Truth patch name (case-insensitive, fuzzy matched) |

**Returns:** Full truth patch document in markdown. Format: Problem → Evidence → Correction.

```json
{
  "name": "get_truth",
  "arguments": {
    "name": "preflight dedup protocol"
  }
}
```

---

## semantic_search

LanceDB vector search with Gemini embeddings and optional reranking.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | string | Yes | — | Search query (max 5,000 chars) |
| `top_k` | int | No | 5 | Number of results (1-100) |
| `stack` | string | No | `""` | Filter by tech stack |
| `search_mode` | string | No | `"hybrid"` | `"vector"`, `"keyword"`, or `"hybrid"` |
| `rerank` | bool | No | true | Apply relevance reranking |

**Returns:** Ranked results with normalized relevance scores (0.0-1.0).

```json
{
  "name": "semantic_search",
  "arguments": {
    "query": "How to implement the repository pattern in Python with async SQLAlchemy",
    "top_k": 10,
    "search_mode": "hybrid",
    "rerank": true
  }
}
```

**Search modes:**
- `"vector"`: Pure semantic similarity using Gemini embeddings (3072-d)
- `"keyword"`: Grep-based keyword matching
- `"hybrid"` (default): Combines both for best results

---

## hybrid_search

Grep-first search with automatic semantic fallback.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | string | Yes | — | Search query (max 5,000 chars) |
| `top_k` | int | No | 10 | Number of results (1-100) |
| `rerank` | bool | No | true | Apply relevance reranking |

**Returns:** Keyword results first; if zero matches, falls back to vector search automatically.

**When to use:** When you want fast keyword matching but don't want to miss results if the exact terms aren't in the knowledge base.

---

## episodic_search

Search past agent sessions and experiences.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | string | Yes | — | What to search for (max 5,000 chars) |
| `limit` | int | No | 5 | Number of results (1-100) |

**Returns:** Matching episodic memories from past agent runs. Useful for recalling how similar problems were solved before.

```json
{
  "name": "episodic_search",
  "arguments": {
    "query": "authentication middleware debugging",
    "limit": 5
  }
}
```
