---
title: Tool Catalog
description: Complete reference for all 57 MidOS MCP tools organized by access tier — Free, Dev, Pro, Admin, Marketplace, and QA.
---

MidOS provides **57 MCP tools** organized across 6 access tiers. Each tool follows MCP's JSON-RPC 2.0 protocol and works with any compatible client.

## Tools by Tier

| Tier | Tools | Auth Required | Description |
|------|:-----:|:---:|-------------|
| [**Free**](/midos-web/tools/free/) | 9 | No | Core search, status, and onboarding |
| [**Dev**](/midos-web/tools/dev/) | 6 | `midos_sk_dev_*` | Full knowledge access, sessions, code chunking |
| [**Pro**](/midos-web/tools/pro/) | 5 | `midos_sk_pro_*` | EUREKA, truth patches, advanced search |
| [**Admin**](/midos-web/tools/admin/) | 16 | Localhost or `midos_sk_admin_*` | Memory management, planning, orchestration |
| [**Marketplace**](/midos-web/tools/marketplace/) | 5 | Profile-based | Skill pack management |
| [**QA & Community**](/midos-web/tools/qa/) | 6 | Varies | Feedback, quality gates, reporting |

**Total: 57 tools**

## Quick Reference

### Most Used Tools

| Tool | Tier | What it does |
|------|------|-------------|
| `search_knowledge` | Free | Keyword search across 1,284 chunks |
| `list_skills` | Free | Browse 104 skills, filter by stack |
| `agent_handshake` | Free | Personalized onboarding — call this first |
| `semantic_search` | Pro | Vector search with Gemini embeddings |
| `get_skill` | Dev | Get full skill document by name |
| `save_progress` | Dev | Save session checkpoint for resume |
| `smart_search` | Admin | Universal search (auto keyword+semantic) |

### Recommended First Call

When connecting for the first time, call `agent_handshake`:

```json
{
  "name": "agent_handshake",
  "arguments": {
    "model": "claude-sonnet-4-5-20250514",
    "context_window": 200000,
    "client": "cursor",
    "languages": "python,typescript",
    "project_goal": "Building a REST API with FastAPI"
  }
}
```

This returns a personalized tool catalog and setup recommendations based on your specific context.

## Input Limits

All tools enforce bounds for safety:

| Parameter | Limit |
|-----------|-------|
| Query strings | 5,000 chars |
| Name lookups | 200 chars |
| Result sets | 100 items max |
| File content | 10,000 chars |
| Text prefix (memory ops) | 10 chars minimum |
