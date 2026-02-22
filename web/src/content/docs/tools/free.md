---
title: "Free Tier Tools (9)"
description: Core MidOS tools available without authentication — search, status, onboarding, and context management.
---

These 9 tools work without any API key. They provide core functionality for evaluating MidOS and basic knowledge retrieval.

---

## search_knowledge

Keyword search across the entire knowledge base.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | string | Yes | — | Search query (max 5,000 chars) |
| `max_results` | int | No | 5 | Number of results (1-100) |

**Returns:** Matched chunks with titles, snippets, and relevance indicators.

**Notes:** Falls back to semantic search if no keyword matches found. Community tier returns truncated content (250 chars per chunk).

```json
{
  "name": "search_knowledge",
  "arguments": {
    "query": "React Server Components best practices",
    "max_results": 10
  }
}
```

---

## list_skills

Browse available skills with optional filtering by technology stack.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `filter` | string | No | `""` | Text filter for skill names |
| `stack` | string | No | `""` | Tech stack filter, comma-separated (e.g., `"python,react"`) |

**Returns:** List of skills with names and descriptions. Frontmatter-aware ranking.

```json
{
  "name": "list_skills",
  "arguments": {
    "stack": "python,fastapi"
  }
}
```

---

## hive_status

Get knowledge base counts and system health metrics.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| *(none)* | — | — | — | — |

**Returns:** `{ chunks_count, skills_count, eureka_count, truth_patches, vector_store_status }`

```json
{
  "name": "hive_status",
  "arguments": {}
}
```

---

## project_status

Live MidOS system dashboard with comprehensive metrics.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| *(none)* | — | — | — | — |

**Returns:** Dashboard markdown with KB stats, vector store health, research queue, tool guide, and quick-start info.

---

## agent_handshake

Onboard a new agent with personalized tool recommendations. **Call this first when connecting.**

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `model` | string | No | `""` | Agent model name (e.g., `"claude-sonnet-4-5-20250514"`) |
| `context_window` | int | No | 0 | Context window size in tokens |
| `client` | string | No | `""` | MCP client name (e.g., `"cursor"`, `"claude-desktop"`) |
| `languages` | string | No | `""` | Programming languages, comma-separated |
| `frameworks` | string | No | `""` | Frameworks in use, comma-separated |
| `platform` | string | No | `""` | OS/platform |
| `project_goal` | string | No | `""` | What the agent is working on (max 5,000 chars) |

**Returns:** Context-aware tool catalog and setup configuration based on your specific environment.

```json
{
  "name": "agent_handshake",
  "arguments": {
    "model": "claude-opus-4-20250514",
    "context_window": 200000,
    "client": "claude-code",
    "languages": "python,typescript",
    "frameworks": "fastapi,react",
    "project_goal": "Building a knowledge management system"
  }
}
```

---

## where_was_i

Resume a previous session. Returns the last saved checkpoint with activity summary and next steps.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `client` | string | No | `""` | Filter by client name |
| `session_id` | string | No | `""` | Specific session to resume |

**Returns:** Last session activity, checkpoint data, and suggested next steps. Returns "no session found" if no prior sessions exist.

---

## context_health

Analyze your context window utilization and get optimization advice.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `tokens_used` | int | No | 0 | Tokens currently used |
| `tokens_total` | int | No | 200000 | Total context window size |
| `active_files` | int | No | 0 | Number of files in context |

**Returns:** Zone assessment (GREEN < 30%, YELLOW 30-40%, RED > 40%) with specific optimization recommendations.

```json
{
  "name": "context_health",
  "arguments": {
    "tokens_used": 85000,
    "tokens_total": 200000,
    "active_files": 12
  }
}
```

---

## get_progress

Retrieve saved session progress (read-only).

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `session_id` | string | No | `""` | Session to retrieve |
| `round_id` | string | No | `""` | Specific round |
| `latest` | bool | No | true | Get most recent progress |

**Returns:** Markdown-formatted progress checkpoint or "no progress found."

---

## agent_bootstrap

**Deprecated** — Use `agent_handshake` instead.

Returns a deprecation notice directing to the new `agent_handshake` tool.
