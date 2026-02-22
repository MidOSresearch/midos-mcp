---
title: "Marketplace Tools (5)"
description: Skill pack management tools — browse, install, and manage curated skill packs for your agent profile.
---

These 5 tools manage your agent profile and skill pack installations. They let you customize which knowledge sets are available to your agent.

---

## list_skill_packs

Browse available curated skill packs.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| *(none)* | — | — | — | — |

**Returns:** List of skill packs with names, descriptions, and included skills. Each pack bundles related skills for a specific domain or tech stack.

---

## install_skill_pack

Install a skill pack to your agent profile.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `pack_name` | string | Yes | — | Name of the skill pack to install |

**Returns:** `{ status: "installed", skills_added: [...] }`

Adds all skills from the specified pack to your profile. Skills are then prioritized in search results and recommendations.

```json
{
  "name": "install_skill_pack",
  "arguments": {
    "pack_name": "python-backend"
  }
}
```

---

## get_installed_skills

List skills currently installed via skill packs.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| *(none)* | — | — | — | — |

**Returns:** Array of installed skill names.

---

## reset_profile

Reset your agent profile to defaults.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| *(none)* | — | — | — | — |

**Returns:** `{ status: "reset" }`

Removes all installed skill packs and custom settings. Use this to start fresh.

---

## get_profile_info

Get current agent profile information.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| *(none)* | — | — | — | — |

**Returns:** `{ model, client, languages, frameworks, installed_skills, handshake_history }`

Shows everything MidOS knows about your agent based on handshakes and installed packs.
