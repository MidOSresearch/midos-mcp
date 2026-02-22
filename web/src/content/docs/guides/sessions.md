---
title: Session Management
description: Save and resume agent sessions with MidOS — checkpoints, progress tracking, and multi-session coordination.
---

MidOS provides session management tools so agents can save their work and resume later without losing context.

## Saving a Session

Use `save_progress` to create a checkpoint:

```json
{
  "name": "save_progress",
  "arguments": {
    "session_id": "project-auth-v2",
    "summary": "Implemented OAuth2 with Google provider. Login flow works. Logout clears tokens.",
    "files_touched": "auth/oauth.py, auth/providers.py, tests/test_oauth.py",
    "decisions_made": "Chose OAuth2 over SAML. Google first, GitHub next.",
    "next_steps": "Add GitHub OAuth provider, implement token refresh"
  }
}
```

**Best practices:**
- Use descriptive `session_id` values that include the project name
- Write `next_steps` as actionable items (the next agent session will read this)
- List all `files_touched` so the next session knows where to look
- Record `decisions_made` to prevent re-debating the same choices

## Resuming a Session

### Quick Resume

```json
{
  "name": "where_was_i",
  "arguments": {}
}
```

Returns the most recent session across all projects.

### Resume Specific Session

```json
{
  "name": "where_was_i",
  "arguments": {
    "session_id": "project-auth-v2"
  }
}
```

### Read-Only Progress

```json
{
  "name": "get_progress",
  "arguments": {
    "session_id": "project-auth-v2",
    "latest": true
  }
}
```

## Multi-Instance Coordination

When multiple agents work on the same project, use `pool_signal` and `pool_status` to coordinate:

### Check Pool State

```json
{
  "name": "pool_status",
  "arguments": {}
}
```

### Signal Completion

```json
{
  "name": "pool_signal",
  "arguments": {
    "action": "completed",
    "topic": "auth-module",
    "summary": "OAuth2 implementation done, tests passing",
    "affects": "auth/oauth.py, auth/providers.py"
  }
}
```

### Signal a Blocker

```json
{
  "name": "pool_signal",
  "arguments": {
    "action": "blocked",
    "topic": "database-migration",
    "summary": "Need schema review before running migration",
    "affects": "migrations/003_add_oauth.sql"
  }
}
```
