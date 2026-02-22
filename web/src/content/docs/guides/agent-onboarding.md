---
title: Agent Onboarding
description: Best practices for connecting an AI agent to MidOS — handshake, skill discovery, and session management.
---

This guide walks through the recommended flow for integrating an AI agent with MidOS.

## Step 1: Handshake

The first call any agent should make is `agent_handshake`. This tells MidOS about your agent's capabilities and returns a personalized tool catalog.

```json
{
  "name": "agent_handshake",
  "arguments": {
    "model": "claude-sonnet-4-5-20250514",
    "context_window": 200000,
    "client": "cursor",
    "languages": "python,typescript",
    "frameworks": "fastapi,nextjs",
    "project_goal": "Building a SaaS API with authentication"
  }
}
```

**What you get back:**
- Tool recommendations ranked by relevance to your project
- Context window optimization tips
- Suggested skill packs for your tech stack
- Setup configuration for your specific client

## Step 2: Install Relevant Skill Packs

Based on the handshake recommendations, install skill packs:

```json
{
  "name": "install_skill_pack",
  "arguments": { "pack_name": "python-backend" }
}
```

Installed skills get prioritized in search results and recommendations.

## Step 3: Search for Knowledge

Use `search_knowledge` (free) or `semantic_search` (Pro) to find relevant patterns:

```json
{
  "name": "search_knowledge",
  "arguments": {
    "query": "JWT authentication middleware pattern",
    "max_results": 5
  }
}
```

## Step 4: Get Specific Skills

When you need deep knowledge on a topic, retrieve the full skill:

```json
{
  "name": "get_skill",
  "arguments": {
    "name": "fastapi-patterns",
    "section": "Authentication"
  }
}
```

## Step 5: Save Progress

Before ending a session, save your progress for next time:

```json
{
  "name": "save_progress",
  "arguments": {
    "session_id": "my-project-session",
    "summary": "Implemented JWT auth, tests passing",
    "next_steps": "Add refresh token rotation"
  }
}
```

## Step 6: Resume Later

Next session, call `where_was_i` to pick up where you left off:

```json
{
  "name": "where_was_i",
  "arguments": {
    "session_id": "my-project-session"
  }
}
```

## Context Window Management

Monitor your context utilization:

```json
{
  "name": "context_health",
  "arguments": {
    "tokens_used": 120000,
    "tokens_total": 200000
  }
}
```

If you're in the YELLOW or RED zone, MidOS will suggest specific actions to free up context (compress text, archive completed items, paginate skill documents).
