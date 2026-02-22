---
title: "Admin Tier Tools (16)"
description: Admin tools for localhost or admin key — memory management, planning, orchestration, security scanning, and system health.
---

These 16 tools are available on localhost (automatically) or with a `midos_sk_admin_*` API key. They provide system management, planning, and security capabilities.

## Memory & Knowledge Management

### memory_decay_report

Show knowledge chunks with high staleness scores.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `limit` | int | No | 20 | Max results (1-100) |

**Returns:** Markdown table of stale chunks sorted by decay score, indicating which knowledge needs refresh.

---

### memory_refresh

Reset the decay timer on a specific knowledge chunk.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `text_prefix` | string | Yes | — | Text prefix to match (min 10 chars) |

**Returns:** Confirmation of refresh or "not found."

---

### memory_archive

Move a chunk to cold storage.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `text_prefix` | string | Yes | — | Text prefix to match (min 10 chars) |

**Returns:** Confirmation of archival. Creates backup before archiving.

---

### knowledge_edit

Edit a section in a knowledge file by header.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `file_path` | string | Yes | — | Path within knowledge/ |
| `section_header` | string | Yes | — | Header to find (fuzzy matched) |
| `new_content` | string | Yes | — | New content for the section |

**Returns:** `{ status: "edited", file_path, lines_changed }` — Path traversal protected, backup created.

---

### knowledge_merge

Merge two duplicate knowledge chunks into one.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `file_path_1` | string | Yes | — | Primary file (kept) |
| `file_path_2` | string | Yes | — | Secondary file (archived after merge) |
| `merged_title` | string | No | `""` | Title for merged document |

---

### get_file_structure

Show the header hierarchy of a knowledge file.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `file_path` | string | Yes | — | Path to analyze |

**Returns:** Markdown header tree with line numbers.

---

### research_youtube

Queue a YouTube video for asynchronous research and transcription.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `url` | string | Yes | — | YouTube URL |
| `priority` | string | No | `"normal"` | `"high"`, `"normal"`, or `"low"` |

---

## Search & Intelligence

### smart_search

Universal search tool — **recommended for all queries** when you have admin access.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `query` | string | Yes | — | Search query (max 5,000 chars) |
| `top_k` | int | No | 10 | Results (1-100) |
| `mode` | string | No | `"auto"` | `"auto"`, `"keyword"`, `"semantic"`, `"hybrid"` |
| `stack` | string | No | `""` | Tech stack filter |
| `rerank` | bool | No | true | Relevance reranking |

**Notes:** In `"auto"` mode, it tries keyword search first, then falls back to semantic search if no results found.

---

### architecture_query

Query the system architecture graph.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `command` | string | Yes | — | `"stats"`, `"hubs"`, `"path"`, `"communities"`, `"anomalies"` |
| `arg` | string | No | `""` | Command argument (e.g., file path for `"path"`) |

---

## Planning & Execution

### create_plan

Create a persistent execution plan with tasks.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `goal` | string | Yes | — | Plan objective |
| `tasks` | string | Yes | — | Comma-separated task list |

**Returns:** `{ plan_id, goal, tasks: [...], status: "active" }`

---

### update_plan_task

Update a task's status within a plan.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `plan_id` | string | Yes | — | Plan UUID |
| `task_index` | int | Yes | — | 0-based task index |
| `status` | string | Yes | — | `"pending"`, `"in_progress"`, `"completed"`, `"blocked"`, `"skipped"` |

---

### get_active_plans

List all execution plans and their task states. No parameters.

---

### pool_signal

Send a coordination signal for multi-instance workflows.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `action` | string | Yes | — | `"completed"`, `"blocked"`, `"claimed"`, `"signaling"` |
| `topic` | string | Yes | — | Signal topic |
| `summary` | string | Yes | — | Signal description |
| `affects` | string | No | `""` | Affected resources |

---

## Context & Validation

### context_compress

Compress text for context window efficiency.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `text` | string | Yes | — | Text to compress (max 200K chars) |
| `mode` | string | No | `"light"` | `"light"` (~50% kept) or `"aggressive"` (~10% kept) |

**Returns:** `{ compressed, original_chars, compressed_chars, ratio, savings_pct }`

---

### validate_output

Validate agent output against a schema.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `output` | string | Yes | — | Output to validate (max 100K chars) |
| `schema` | string | No | `"json_schema"` | `"json_schema"`, `"yaml"`, `"markdown_with_headers"` |

---

## Episodic Memory

### episodic_store

Store an episodic memory from an agent run.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `task_type` | string | Yes | — | `"CODE"`, `"RESEARCH"`, `"DEBUG"`, `"REVIEW"` |
| `input_preview` | string | Yes | — | Brief description of what was done |
| `success` | bool | No | true | Whether the task succeeded |

---

## System Operations

### run_feedback_loop

Execute the feedback processing pipeline.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `scope` | string | No | `"all"` | `"all"`, `"recent"`, or specific item type |
| `dry_run` | bool | No | false | Preview without committing changes |

---

### system_health_check

Run system diagnostics.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `check` | string | No | `"all"` | `"all"`, `"memory"`, `"disk"`, `"vector_db"`, `"api"` |

---

### run_auto_healer

Auto-repair detected system issues.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `dry_run` | bool | No | true | Preview repairs without executing |

---

### get_system_state

Get current FSM state of the MidOS orchestrator. No parameters.

---

### run_orchestrator_cycle

Manually trigger an orchestrator decision cycle. No parameters.
