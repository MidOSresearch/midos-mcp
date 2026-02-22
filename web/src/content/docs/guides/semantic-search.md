---
title: Semantic Search
description: How to use MidOS vector search — search modes, reranking, and tips for getting the best results.
---

MidOS uses **LanceDB** with **Gemini embeddings** (3072-dimensional vectors) to provide semantic search across 22,900+ knowledge vectors.

## Search Tools Comparison

| Tool | Tier | Best For |
|------|------|----------|
| `search_knowledge` | Free | Quick keyword lookup |
| `semantic_search` | Pro | Conceptual similarity |
| `hybrid_search` | Pro | Best of both worlds |
| `smart_search` | Admin | Auto-detecting best mode |

## Search Modes

### Keyword Mode
Fast grep-based search. Finds exact or partial text matches.

```json
{
  "name": "semantic_search",
  "arguments": {
    "query": "useEffect cleanup",
    "search_mode": "keyword"
  }
}
```

**Best for:** Known terms, function names, specific patterns.

### Vector Mode
Pure semantic similarity. Finds conceptually related content even with completely different wording.

```json
{
  "name": "semantic_search",
  "arguments": {
    "query": "how to handle side effects when a component unmounts",
    "search_mode": "vector"
  }
}
```

**Best for:** Conceptual queries, "how do I..." questions, finding patterns you don't know the name of.

### Hybrid Mode (Default)
Combines keyword and vector search. Keyword results are checked first, then semantic results fill in gaps.

```json
{
  "name": "semantic_search",
  "arguments": {
    "query": "React hooks cleanup patterns",
    "search_mode": "hybrid",
    "rerank": true
  }
}
```

**Best for:** General-purpose searching. This is the recommended default.

## Filtering by Stack

Narrow results to a specific technology:

```json
{
  "name": "semantic_search",
  "arguments": {
    "query": "authentication patterns",
    "stack": "fastapi",
    "top_k": 10
  }
}
```

## Reranking

When `rerank: true` (default), results go through a secondary relevance scoring pass. This improves precision but adds slight latency.

Disable reranking when speed matters more than precision:

```json
{
  "name": "semantic_search",
  "arguments": {
    "query": "quick lookup",
    "rerank": false
  }
}
```

## Tips for Better Results

1. **Be specific**: "FastAPI dependency injection with async database sessions" beats "dependency injection"
2. **Use natural language**: The vector model understands questions better than keywords
3. **Try different modes**: If keyword gives no results, hybrid will automatically try semantic
4. **Filter by stack**: Reduces noise significantly when you know the technology
5. **Increase top_k**: Set `top_k: 20` when exploring a broad topic to see more variety
