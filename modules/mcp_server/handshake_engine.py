"""
Handshake Engine — Personalized Agent Configuration
====================================================
Core logic for agent_handshake: takes an AgentProfile, resolves
model/client specs, and generates a context-budget-aware config.

Phase 2: Config generation (identity, tools, skills, chunks, tips)
Phase 4: Floating guardrails (universal + model + client + tier)
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from .agent_profiles import (
    AgentProfile,
    ModelSpec,
    ClientSpec,
    resolve_model,
    resolve_client,
)
from .auth.constants import FREE_TOOLS, PRO_TOOLS, ADMIN_TOOLS

# Paths
MIDOS_ROOT = Path(__file__).parent.parent.parent.resolve()
KNOWLEDGE_DIR = MIDOS_ROOT / "knowledge"
SKILLS_DIR = MIDOS_ROOT / "skills"
CLI_PROFILES_PATH = MIDOS_ROOT / "config" / "cli_profiles.json"

# Cache for CLI profiles (loaded once per process)
_cli_profiles_cache: Optional[dict] = None


# ============================================================================
# MCP Tool Descriptions — for relevance ranking
# ============================================================================

MCP_TOOLS = [
    {
        "name": "search_knowledge",
        "desc": "Keyword search across knowledge base",
        "tags": ["search", "knowledge", "general"],
    },
    {
        "name": "semantic_search",
        "desc": "Vector search with LanceDB + Gemini embeddings",
        "tags": ["search", "vector", "ai", "semantic"],
    },
    {
        "name": "get_skill",
        "desc": "Get a specific skill/capability document",
        "tags": ["skills", "learning", "howto"],
    },
    {
        "name": "list_skills",
        "desc": "List available skills/capabilities",
        "tags": ["skills", "discovery"],
    },
    {
        "name": "get_protocol",
        "desc": "Get a protocol document",
        "tags": ["protocol", "architecture", "system"],
    },
    {
        "name": "hive_status",
        "desc": "System status of MidOS hive",
        "tags": ["status", "health", "system"],
    },
    {
        "name": "memory_stats",
        "desc": "Memory system statistics (LanceDB)",
        "tags": ["memory", "stats", "vector"],
    },
    {
        "name": "research_youtube",
        "desc": "Queue YouTube video for transcription and research",
        "tags": ["youtube", "video", "research"],
    },
    {
        "name": "pool_signal",
        "desc": "Signal action to multi-instance coordination pool",
        "tags": ["coordination", "multi-agent", "pool"],
    },
    {
        "name": "pool_status",
        "desc": "Get multi-instance pool status",
        "tags": ["coordination", "multi-agent", "pool"],
    },
    {
        "name": "episodic_search",
        "desc": "Search episodic memory for past experiences",
        "tags": ["memory", "episodic", "learning"],
    },
    {
        "name": "episodic_store",
        "desc": "Store new episodic memory/reflection",
        "tags": ["memory", "episodic", "learning"],
    },
    {
        "name": "chunk_code",
        "desc": "AST-based code chunking for RAG retrieval",
        "tags": ["code", "rag", "chunking", "ast"],
    },
    {
        "name": "agent_handshake",
        "desc": "This tool — personalized agent onboarding",
        "tags": ["onboarding", "config"],
        "exclude_from_output": True,
    },
]


# ============================================================================
# Guardrails — Phase 4: floating guardrails
# ============================================================================

GUARDRAILS = {
    "universal": [
        "Never hardcode secrets -- use os.getenv() + .env",
        "Check indices before creating new ones",
        "Windows/PowerShell: use ';' not '&&'. Use 'python -c' as fallback",
        "Polling: max 10s between checks, never wait 60s",
        "No duplication: synthesize, never scatter",
    ],
    "model_specific": {
        "small_context": [
            "Keep tool calls concise, avoid verbose outputs",
            "Prefer search_knowledge over semantic_search for lower token cost",
            "Request summaries instead of full documents",
        ],
        "no_tools": [
            "Use structured prompts instead of tool calls",
            "Request information in batch to minimize round-trips",
        ],
        "no_vision": [
            "Request text descriptions instead of images",
        ],
        "no_structured": [
            "Parse text responses manually, do not rely on JSON mode",
        ],
    },
    "client_specific": {
        "no_hooks": [
            "Implement guardrails in prompts, not lifecycle hooks",
            "Use CLAUDE.md or project rules for persistent behavior",
        ],
        "no_memory": [
            "Store important context in project files, not agent memory",
            "Consider using episodic_store to persist key findings",
        ],
        "no_background": [
            "Run tasks sequentially, avoid parallel agent delegation",
            "Batch operations where possible to reduce round-trips",
        ],
    },
    "tier_specific": {
        "community": [
            "Rate limit: 100 calls/hour",
            "Read-only access to EUREKA content",
        ],
        "paid": [
            "Rate limit: 1000 calls/hour",
            "Full EUREKA access",
        ],
        "premium": [
            "Unlimited calls",
            "Priority semantic search",
        ],
        "admin": [
            "Full access",
            "Can modify knowledge pipeline",
        ],
        "owner": [
            "Unrestricted system access",
        ],
    },
}


# ============================================================================
# CLI Profile Loading
# ============================================================================


def _get_generic_cli_profile() -> dict:
    """Safe defaults for unknown/generic CLI clients."""
    return {
        "id": "generic",
        "display_name": "Generic Client",
        "vendor": "Unknown",
        "description": "Unknown CLI — safe defaults with capability discovery",
        "capabilities": {
            "can_write_python": True,
            "can_write_markdown": True,
            "can_execute_code": False,
            "can_use_git": False,
        },
        "restrictions": {
            "forbidden_file_patterns": [],
            "read_only_paths": [],
        },
        "role": "general",
        "instructions": [
            "You are connected via an unrecognized client — safe defaults apply",
            "All read-only MCP tools are available",
            "For write operations, verify your client supports them first",
            "Call hive_status to discover available capabilities",
        ],
        "tool_restrictions": {
            "mode": "allowlist",
            "allowed": ["*"],
            "denied": [],
            "explanation": "Generic clients get full read access, write tools available but unverified",
        },
        "attention_pinch": {
            "enabled": True,
            "frequency_turns": 15,
            "message": "Generic client check: verify your capabilities before attempting write operations.",
        },
        "delegation_policy": {
            "your_strengths": ["general-purpose tasks"],
            "your_weaknesses": ["unknown — capability discovery recommended"],
            "delegate_to": {},
        },
        "default_search_mode": "hybrid",
        "response_format": "markdown",
        "priority": 99,
    }


def load_cli_profiles() -> dict[str, dict]:
    """Load all CLI profiles from config/cli_profiles.json. Cached per process."""
    global _cli_profiles_cache
    if _cli_profiles_cache is not None:
        return _cli_profiles_cache

    try:
        data = json.loads(CLI_PROFILES_PATH.read_text(encoding="utf-8"))
        _cli_profiles_cache = data.get("profiles", {})
    except (OSError, json.JSONDecodeError):
        _cli_profiles_cache = {}

    return _cli_profiles_cache


def load_cli_profile(client_id: str) -> dict:
    """Load a specific CLI profile by client ID. Returns generic defaults if not found."""
    if not client_id:
        return _get_generic_cli_profile()

    profiles = load_cli_profiles()
    normalized = client_id.strip().lower()

    # Exact match
    if normalized in profiles:
        return profiles[normalized]

    # Try resolving via client aliases → canonical ID
    from .agent_profiles import resolve_client as _resolve

    spec = _resolve(normalized)
    if spec and spec.id in profiles:
        return profiles[spec.id]

    return _get_generic_cli_profile()


# ============================================================================
# Config Generation
# ============================================================================


def generate_config(profile: AgentProfile) -> dict[str, Any]:
    """Generate personalized agent configuration from profile.

    Returns dict with keys:
      identity         - MidOS identity (compact)
      model_info       - Resolved model spec (if known)
      client_info      - Resolved client spec (if known)
      recommended_tools - filtered/ranked list of MCP tools
      relevant_skills  - skills matching agent's stack
      relevant_chunks  - top knowledge chunks for project_goal
      guardrails       - adaptive rules for this model+client+tier
      model_tips       - tips specific to the agent's model
      client_tips      - tips specific to the agent's CLI/IDE
      context_budget   - recommended token allocation
      suggestions      - proactive recommendations based on detected gaps
    """
    model_spec = resolve_model(profile.model)
    client_spec = resolve_client(profile.client)

    # Load CLI-specific profile
    cli_profile = load_cli_profile(client_spec.id if client_spec else profile.client)

    # Context budget
    context_budget = _compute_context_budget(profile, model_spec, client_spec)

    config = {
        "identity": _build_identity(),
        "model_info": _summarize_model(model_spec) if model_spec else None,
        "client_info": _summarize_client(client_spec) if client_spec else None,
        "cli_profile": cli_profile,
        "recommended_tools": _rank_tools(profile, context_budget, cli_profile),
        "relevant_skills": _find_skills(profile),
        "relevant_chunks": _find_chunks(profile),
        "guardrails": _build_guardrails(profile, model_spec, client_spec),
        "model_tips": model_spec.tips if model_spec else [],
        "client_tips": client_spec.tips if client_spec else [],
        "context_budget": context_budget,
        "suggestions": _build_suggestions(profile, model_spec, client_spec),
    }

    # Resume hint (BL-074): check for previous sessions
    try:
        from .session_logger import get_recent_sessions

        recent = get_recent_sessions(client=profile.client, limit=1)
        if recent:
            last = recent[0]
            config["resume_hint"] = {
                "last_session": last["session_id"],
                "last_active": last["last_activity"],
                "tool_count": last["tool_count"],
                "tip": "Call where_was_i() to resume your previous session",
            }
    except Exception:
        pass  # Non-critical — don't break handshake

    # Log compatibility data (non-blocking)
    _log_compatibility(profile, model_spec, client_spec, context_budget, config)

    return config


def format_config(config: dict[str, Any], profile: AgentProfile) -> str:
    """Format config dict as context-budget-aware markdown string.

    Small context (<=32K): Compact bullet points
    Medium context (32K-128K): Standard format
    Large context (>128K): Full format with previews
    """
    budget = config.get("context_budget", {})
    tier = budget.get("tier", "medium")

    parts = []

    # --- GETTING STARTED (always first, action-oriented) ---
    parts.append("# MidOS Agent Handshake\n")
    parts.append("## Getting Started (3 steps)\n")
    parts.append("```")
    parts.append("1. semantic_search('your topic here')")
    parts.append("   → Check what MidOS already knows")
    parts.append("")
    parts.append("2. list_skills(stack='python,react')")
    parts.append("   → Find reusable skill docs for your stack")
    parts.append("")
    parts.append("3. hybrid_search('specific question')")
    parts.append("   → Deep search with grep + semantic fusion")
    parts.append("```\n")

    # --- Top 5 tools (compact table with tier indicators) ---
    tools = config.get("recommended_tools", [])[:5]
    if tools:
        parts.append("## Top Tools\n")
        parts.append("| Tool | Use for | Tier |")
        parts.append("|------|---------|------|")
        for t in tools:
            tier_label = t.get("min_tier", "dev").upper()
            parts.append(f"| `{t['name']}` | {t['desc']} | {tier_label} |")
        parts.append("")

    # --- Identity (one line) ---
    identity = config["identity"]
    parts.append(
        f"**{identity['name']}** — {identity['description']} | Root: `{identity['root']}`\n"
    )

    # Model/Client info (compact)
    if config["model_info"]:
        m = config["model_info"]
        model_label = m["id"]
        if profile.model and profile.model.lower() != m["id"].lower():
            model_label += f" (from '{profile.model}')"
        parts.append(
            f"**Model:** {model_label} | "
            f"Context: {m['context_window']:,} | "
            f"Code: {m['code_score']}/10 | Speed: ~{m['speed_tps']} t/s"
        )
    elif profile.model:
        parts.append(f"**Model:** {profile.model} (not in catalog — using defaults)")

    if config["client_info"]:
        c = config["client_info"]
        features = []
        if c.get("has_hooks"):
            features.append("hooks")
        if c.get("has_memory"):
            features.append("memory")
        if c.get("has_background_agents"):
            features.append("bg-agents")
        features_str = ", ".join(features) if features else "basic"
        parts.append(
            f"**Client:** {c['id']} | "
            f"MCP: {', '.join(c['mcp_transport'])} | "
            f"Features: {features_str}"
        )

    parts.append("")

    # Context budget (one line)
    cb = config["context_budget"]
    parts.append(
        f"**Context:** {cb.get('effective_window', 'unknown'):,} tokens | tier: {tier}\n"
    )

    # CLI Role & Instructions
    cli_prof = config.get("cli_profile", {})
    if cli_prof:
        role = cli_prof.get("role", "general")
        display = cli_prof.get("display_name", cli_prof.get("id", "unknown"))
        parts.append(f"## CLI Profile: {display} (role: {role})")
        instructions = cli_prof.get("instructions", [])
        if tier == "small":
            instructions = instructions[:2]
        for inst in instructions:
            parts.append(f"- {inst}")
        parts.append("")

        # Tool restrictions summary
        restrictions = cli_prof.get("tool_restrictions", {})
        mode = restrictions.get("mode", "allowlist")
        denied = restrictions.get("denied", [])
        if denied:
            parts.append(f"### Tool Restrictions ({mode})")
            parts.append(f"Denied tools: {', '.join(denied)}")
            parts.append(f"Reason: {restrictions.get('explanation', 'N/A')}")
            parts.append("")

        # Attention pinch
        pinch = cli_prof.get("attention_pinch", {})
        if pinch.get("enabled"):
            parts.append(
                f"### Attention Pinch (every {pinch.get('frequency_turns', 15)} turns)"
            )
            parts.append(f"- {pinch.get('message', '')}")
            parts.append("")

        # Delegation policy (medium/large only)
        if tier != "small":
            delegation = cli_prof.get("delegation_policy", {})
            delegate_to = delegation.get("delegate_to", {})
            if delegate_to:
                parts.append("### Delegation Policy")
                strengths = delegation.get("your_strengths", [])
                if strengths:
                    parts.append(f"**Your strengths:** {', '.join(strengths[:3])}")
                for target_cli, tasks in delegate_to.items():
                    tasks_str = (
                        "; ".join(tasks[:3]) if tier == "medium" else "; ".join(tasks)
                    )
                    parts.append(f"- Delegate to **{target_cli}**: {tasks_str}")
                parts.append("")

        # Search mode & response format
        search_mode = cli_prof.get("default_search_mode", "")
        resp_format = cli_prof.get("response_format", "")
        if search_mode or resp_format:
            meta = []
            if search_mode:
                meta.append(f"Search: {search_mode}")
            if resp_format:
                meta.append(f"Format: {resp_format}")
            parts.append(f"**Defaults:** {' | '.join(meta)}")
            parts.append("")

    # Additional tools (skip top 5 already shown, show rest for medium/large)
    all_tools = config.get("recommended_tools", [])
    if tier != "small" and len(all_tools) > 5:
        extra_tools = all_tools[5:]
        if tier == "medium":
            extra_tools = extra_tools[:5]
        parts.append(f"## More Tools ({len(extra_tools)})")
        for t in extra_tools:
            tier_label = t.get("min_tier", "dev").upper()
            parts.append(f"- **{t['name']}** — {t['desc']} [{tier_label}]")
        parts.append("")

    # Skills
    skills = config["relevant_skills"]
    if tier == "small":
        skills = skills[:2]
    elif tier == "medium":
        skills = skills[:5]

    if skills:
        parts.append(f"## Relevant Skills ({len(skills)})")
        for s in skills:
            if isinstance(s, dict):
                # New format: dict with name, path, reason, source
                parts.append(f"- **{s['name']}** — {s.get('reason', '')}")
            else:
                # Legacy format: string
                parts.append(f"- {s}")
        parts.append("")

    # Chunks (small=1 if project_goal set, medium=2, large=5)
    chunks = config.get("relevant_chunks", [])
    if chunks:
        limit = 1 if tier == "small" else (2 if tier == "medium" else 5)
        chunks = chunks[:limit]
        parts.append(f"## Knowledge Chunks ({len(chunks)})")
        for c in chunks:
            parts.append(f"- **{c['name']}** ({c['path']})")
            if tier == "large" and c.get("preview"):
                parts.append(f"  > {c['preview'][:200]}...")
        parts.append("")

    # Guardrails
    guardrails = config["guardrails"]
    if guardrails:
        if tier == "small":
            guardrails = guardrails[:3]
        parts.append(f"## Guardrails ({len(guardrails)})")
        for g in guardrails:
            parts.append(f"- {g}")
        parts.append("")

    # Tips
    all_tips = config.get("model_tips", []) + config.get("client_tips", [])
    if all_tips:
        if tier == "small":
            all_tips = all_tips[:2]
        elif tier == "medium":
            all_tips = all_tips[:5]
        parts.append(f"## Tips ({len(all_tips)})")
        for tip in all_tips:
            parts.append(f"- {tip}")
        parts.append("")

    # Suggestions (proactive recommendations)
    suggestions = config.get("suggestions", [])
    if suggestions:
        if tier == "small":
            suggestions = suggestions[:2]
        parts.append(f"## Suggestions ({len(suggestions)})")
        for s in suggestions:
            parts.append(f"- {s}")
        parts.append("")

    # Resume hint (BL-074)
    resume = config.get("resume_hint")
    if resume:
        ago = _time_ago(resume.get("last_active", ""))
        parts.append(f"## Resume Available")
        parts.append(
            f"Last session: `{resume['last_session']}` ({ago}, "
            f"{resume.get('tool_count', 0)} tool calls)"
        )
        parts.append(f"Call `where_was_i()` to get your full session summary.\n")

    parts.append(
        f"---\n_MidOS Handshake v1.1 -- {datetime.now().strftime('%Y-%m-%d %H:%M')}_"
    )

    return "\n".join(parts)


# ============================================================================
# Private Helpers
# ============================================================================


def _time_ago(iso_ts: str) -> str:
    """Convert ISO timestamp to human-readable 'X ago' string."""
    try:
        from datetime import timezone

        dt = datetime.fromisoformat(iso_ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        secs = int(delta.total_seconds())
        if secs < 60:
            return f"{secs}s ago"
        if secs < 3600:
            return f"{secs // 60}m ago"
        if secs < 86400:
            return f"{secs // 3600}h ago"
        return f"{secs // 86400}d ago"
    except (ValueError, TypeError):
        return "unknown"


def _build_identity() -> dict:
    return {
        "name": "MidOS",
        "description": "MCP Community Library -- Knowledge base + Research engine",
        "root": str(MIDOS_ROOT),
        "hierarchy": "MidOS (Core) -> Agents -> Clients",
    }


def _summarize_model(spec: ModelSpec) -> dict:
    return {
        "id": spec.id,
        "family": spec.family,
        "context_window": spec.context_window,
        "max_output": spec.max_output,
        "code_score": spec.code_score,
        "reasoning_score": spec.reasoning_score,
        "speed_tps": spec.speed_tps,
        "supports_tools": spec.supports_tools,
        "supports_vision": spec.supports_vision,
        "tier": spec.tier,
    }


def _summarize_client(spec: ClientSpec) -> dict:
    return {
        "id": spec.id,
        "mcp_transport": spec.mcp_transport,
        "has_hooks": spec.has_hooks,
        "has_memory": spec.has_memory,
        "has_background_agents": spec.has_background_agents,
        "context_management": spec.context_management,
        "max_context": spec.max_context,
    }


def _compute_context_budget(
    profile: AgentProfile,
    model_spec: Optional[ModelSpec],
    client_spec: Optional[ClientSpec],
) -> dict:
    """Compute effective context window and payload tier."""
    windows = []

    if profile.context_window > 0:
        windows.append(profile.context_window)
    if model_spec and model_spec.context_window > 0:
        windows.append(model_spec.context_window)
    if client_spec and client_spec.max_context > 0:
        windows.append(client_spec.max_context)

    effective = min(windows) if windows else 128000  # default assumption
    effective = min(effective, 10_000_000)  # cap at 10M tokens

    if effective <= 32000:
        tier = "small"
    elif effective <= 128000:
        tier = "medium"
    else:
        tier = "large"

    return {
        "effective_window": effective,
        "tier": tier,
    }


def _tool_min_tier(name: str) -> str:
    """Return the minimum tier label for a tool."""
    if name in FREE_TOOLS:
        return "free"
    if name in PRO_TOOLS:
        return "pro"
    if name in ADMIN_TOOLS:
        return "admin"
    return "dev"


def _rank_tools(
    profile: AgentProfile,
    context_budget: dict,
    cli_profile: Optional[dict] = None,
) -> list[dict]:
    """Rank MCP tools by relevance to profile, respecting CLI tool restrictions."""
    goal_lower = profile.project_goal.lower() if profile.project_goal else ""
    langs_lower = [l.lower() for l in profile.languages]
    fws_lower = [f.lower() for f in profile.frameworks]
    all_keywords = goal_lower.split() + langs_lower + fws_lower

    # CLI tool restrictions
    restrictions = (cli_profile or {}).get("tool_restrictions", {})
    allowed = restrictions.get("allowed", ["*"])
    denied = set(restrictions.get("denied", []))
    allow_all = "*" in allowed
    allowed_set = set(allowed) if not allow_all else set()

    scored = []
    for tool in MCP_TOOLS:
        name = tool["name"]

        # Filter by CLI restrictions
        if denied and name in denied:
            continue
        if not allow_all and name not in allowed_set:
            continue

        score = 0
        tool_text = (tool["desc"] + " " + " ".join(tool["tags"])).lower()

        # Score by keyword overlap
        for kw in all_keywords:
            if kw and kw in tool_text:
                score += 1

        # Core tools always ranked higher
        if name in ("search_knowledge", "semantic_search", "list_skills"):
            score += 3

        # Add tier label for output
        enriched = {**tool, "min_tier": _tool_min_tier(name)}
        scored.append((score, enriched))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored if not t.get("exclude_from_output")]


def _find_skills(profile: AgentProfile) -> list[dict]:
    """Find skills matching agent's profile.

    Returns list of skill dicts with keys: name, path, reason, source.
    Priority order:
      1. recommended_skills from MODEL_CATALOG (if model matches)
      2. Skills matching languages/frameworks
      3. Skills matching project_goal keywords
    """
    if not SKILLS_DIR.exists():
        return []

    # Import here to avoid circular dependency
    from .agent_profiles import resolve_model, MODEL_CATALOG

    skills_with_score = []
    seen_skills = set()

    # === CAPA 1: Recommended skills from model catalog ===
    model_spec = resolve_model(profile.model)
    if (
        model_spec
        and hasattr(model_spec, "recommended_skills")
        and model_spec.recommended_skills
    ):
        for skill_name in model_spec.recommended_skills:
            if skill_name not in seen_skills:
                skill_path = _find_skill_path(skill_name)
                if skill_path:
                    skills_with_score.append(
                        {
                            "name": skill_name,
                            "path": str(skill_path.relative_to(MIDOS_ROOT)).replace(
                                "\\", "/"
                            ),
                            "reason": f"Recomendada para {model_spec.id}",
                            "source": "model_catalog",
                            "score": 10,  # Maximum priority
                        }
                    )
                    seen_skills.add(skill_name)

    # === CAPA 2: Skills matching languages/frameworks ===
    if profile.languages or profile.frameworks:
        keywords = [l.lower() for l in profile.languages] + [
            f.lower() for f in profile.frameworks
        ]
        for skill_name in _get_all_skills():
            if skill_name in seen_skills:
                continue
            name_lower = skill_name.lower().replace("-", " ").replace("_", " ")
            score = sum(2 for kw in keywords if kw and kw in name_lower)

            # Check compatibility.json for subdirectory skills
            compat_file = SKILLS_DIR / skill_name / "compatibility.json"
            if compat_file.exists():
                try:
                    compat = json.loads(compat_file.read_text(encoding="utf-8"))
                    compat_langs = [x.lower() for x in compat.get("languages", [])]
                    compat_fws = [x.lower() for x in compat.get("frameworks", [])]
                    for lang in profile.languages:
                        if lang.lower() in compat_langs:
                            score += 3
                    for fw in profile.frameworks:
                        if fw.lower() in compat_fws:
                            score += 3
                except (OSError, json.JSONDecodeError):
                    pass

            if score > 0:
                skill_path = _find_skill_path(skill_name)
                if skill_path:
                    skills_with_score.append(
                        {
                            "name": skill_name,
                            "path": str(skill_path.relative_to(MIDOS_ROOT)).replace(
                                "\\", "/"
                            ),
                            "reason": f"Match con stack: {', '.join(profile.languages + profile.frameworks)}",
                            "source": "stack_match",
                            "score": score,
                        }
                    )
                    seen_skills.add(skill_name)

    # === CAPA 3: Skills matching project_goal ===
    if profile.project_goal and len(seen_skills) < 10:
        goal_words = profile.project_goal.lower().split()
        for skill_name in _get_all_skills():
            if skill_name in seen_skills:
                continue
            name_lower = skill_name.lower().replace("-", " ").replace("_", " ")
            score = sum(1 for word in goal_words if word in name_lower)

            if score > 0:
                skill_path = _find_skill_path(skill_name)
                if skill_path:
                    skills_with_score.append(
                        {
                            "name": skill_name,
                            "path": str(skill_path.relative_to(MIDOS_ROOT)).replace(
                                "\\", "/"
                            ),
                            "reason": f"Relevante para: {profile.project_goal}",
                            "source": "goal_match",
                            "score": score,
                        }
                    )
                    seen_skills.add(skill_name)

    # === Fallback: Popular skills if nothing matched ===
    if not skills_with_score:
        priority = [
            "pragmatic_engineering",
            "context_manager",
            "health_check",
            "react",
            "postgresql",
            "nestjs_v11",
            "django_v5",
            "tailwindcss",
            "prisma_v7",
            "redis_caching_patterns",
        ]
        for skill_name in priority:
            if skill_name not in seen_skills:
                skill_path = _find_skill_path(skill_name)
                if skill_path:
                    skills_with_score.append(
                        {
                            "name": skill_name,
                            "path": str(skill_path.relative_to(MIDOS_ROOT)).replace(
                                "\\", "/"
                            ),
                            "reason": "Skill popular recomendada",
                            "source": "fallback",
                            "score": 1,
                        }
                    )
                    seen_skills.add(skill_name)

    # Sort by score descending
    skills_with_score.sort(key=lambda x: x["score"], reverse=True)

    return skills_with_score[:15]  # Return top 15


def _get_all_skills() -> list[str]:
    """Get all available skill names."""
    all_skills = set()
    for f in SKILLS_DIR.glob("*.md"):
        if not f.name.startswith("_"):
            all_skills.add(f.stem)
    for d in SKILLS_DIR.iterdir():
        if d.is_dir():
            all_skills.add(d.name)
    return sorted(all_skills)


def _find_skill_path(skill_name: str) -> Optional[Path]:
    """Find the path to a skill file.

    Searches in multiple locations:
      1. KNOWLEDGE_DIR/skills/{name}.md (knowledge base skills)
      2. KNOWLEDGE_DIR/skills/{name}/SKILL.md (subdirectory skills)
      3. SKILLS_DIR/{name}/SKILL.md (agent skills)
    """
    # Import KNOWLEDGE_DIR from midos_mcp to avoid circular dependency
    from pathlib import Path
    import os

    midos_root = Path(__file__).parent.parent.parent.resolve()
    knowledge_skills_dir = midos_root / "knowledge" / "skills"
    agent_skills_dir = midos_root / "skills"

    # Try 1: Direct .md file in knowledge/skills/
    skill_file = knowledge_skills_dir / f"{skill_name}.md"
    if skill_file.exists():
        return skill_file

    # Try 2: Subdirectory with SKILL.md in knowledge/skills/
    skill_dir = knowledge_skills_dir / skill_name
    if skill_dir.is_dir():
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists():
            return skill_file

    # Try 3: Subdirectory with SKILL.md in skills/ (agent skills)
    agent_skill_dir = agent_skills_dir / skill_name
    if agent_skill_dir.is_dir():
        skill_file = agent_skill_dir / "SKILL.md"
        if skill_file.exists():
            return skill_file

    return None


def _find_chunks(profile: AgentProfile) -> list[dict]:
    """Find relevant knowledge chunks for project_goal using semantic search if available."""
    if not profile.project_goal:
        return []

    # Skip chunks for generic/testing project goals (they'll be irrelevant)
    generic_goals = {"test", "testing", "hello", "demo", "example", "prueba"}
    goal_lower = profile.project_goal.lower()
    if any(goal_lower.startswith(g) or goal_lower == g for g in generic_goals):
        return []

    # Try semantic search via hive_commons (with minimum relevance threshold)
    try:
        from hive_commons.vector_store import search_memory

        results = search_memory(profile.project_goal, top_k=5)
        if results:
            # Filter by minimum score (RRF scores range 0-1, top hit ~1.0)
            MIN_CHUNK_SCORE = 0.25
            filtered = [r for r in results if r.get("score", 0) >= MIN_CHUNK_SCORE]
            if filtered:
                return [
                    {
                        "name": r.get("source", "unknown"),
                        "path": r.get("source", ""),
                        "preview": r.get("text", "")[:300],
                        "score": r.get("score", 0),
                    }
                    for r in filtered[:5]
                ]
    except (ImportError, Exception):
        pass

    # Fallback: keyword search in chunks directory (strict: need 2+ meaningful word matches)
    chunks_dir = KNOWLEDGE_DIR / "chunks"
    if not chunks_dir.exists():
        return []

    stop_words = {
        "the",
        "a",
        "an",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "and",
        "or",
        "is",
        "it",
        "my",
        "i",
        "we",
        "our",
        "how",
        "what",
        "this",
        "that",
        "using",
        "implement",
        "implementation",
        "build",
        "create",
        "add",
        "use",
        "make",
        "setup",
    }
    goal_words = [
        w
        for w in profile.project_goal.lower().split()
        if w not in stop_words and len(w) > 2
    ]
    if not goal_words:
        return []

    MIN_KEYWORD_HITS = 2
    results = []
    for md_file in sorted(chunks_dir.glob("*.md"))[:50]:
        name_lower = md_file.stem.lower().replace("-", " ").replace("_", " ")
        hits = sum(1 for w in goal_words if w in name_lower)
        if hits >= MIN_KEYWORD_HITS:
            preview = ""
            try:
                preview = md_file.read_text(encoding="utf-8", errors="ignore")[:300]
            except OSError:
                pass
            results.append(
                {
                    "name": md_file.stem,
                    "path": str(md_file.relative_to(MIDOS_ROOT)),
                    "preview": preview,
                    "score": hits,
                }
            )

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]


def _log_compatibility(
    profile: AgentProfile,
    model_spec: Optional[ModelSpec],
    client_spec: Optional[ClientSpec],
    context_budget: dict,
    config: dict,
) -> None:
    """Log handshake result to compatibility_log.jsonl for analytics."""
    try:
        log_path = KNOWLEDGE_DIR / "SYSTEM" / "compatibility_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        entry = {
            "ts": datetime.now().isoformat(),
            "model": profile.model or "unknown",
            "client": profile.client or "unknown",
            "resolved_model": model_spec.id if model_spec else None,
            "resolved_client": client_spec.id if client_spec else None,
            "tools_offered": len(config.get("recommended_tools", [])),
            "skills_matched": len(config.get("relevant_skills", [])),
            "tier": profile.tier,
            "context_budget": context_budget.get("tier", "unknown"),
            "platform": profile.platform or "unknown",
            "languages": profile.languages,
            "frameworks": profile.frameworks,
            "success": True,
            "suggestions_count": len(config.get("suggestions", [])),
        }

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception:
        pass  # Never break handshake for logging


def _build_suggestions(
    profile: AgentProfile,
    model_spec: Optional[ModelSpec],
    client_spec: Optional[ClientSpec],
) -> list[str]:
    """Generate proactive suggestions based on detected gaps."""
    suggestions = []
    client_norm = (profile.client or "").strip().lower()
    primary_clis = {
        "claude-code",
        "claude_code",
        "codex-cli",
        "codex_cli",
        "codex cli",
    }
    is_primary_cli = client_norm in primary_clis

    # Client without hooks
    if client_spec and not client_spec.has_hooks:
        suggestions.append(
            "Your client doesn't support hooks. Consider Claude Code or Windsurf "
            "for lifecycle hooks (auto-guardrails, delegation control)."
        )

    # Model without tool support
    if model_spec and not model_spec.supports_tools:
        suggestions.append(
            f"Your model ({model_spec.id}) doesn't support tool use. "
            "Consider upgrading to a model with tool support for full MidOS access."
        )

    # Client without background agents
    if client_spec and not client_spec.has_background_agents:
        suggestions.append(
            "Your client doesn't support background agents. "
            "Claude Code supports parallel agent delegation for complex tasks."
        )

    # Small context window
    if model_spec and model_spec.context_window <= 32000:
        suggestions.append(
            f"Your model has a {model_spec.context_window:,}-token context window. "
            "Use compact tool responses and prefer search_knowledge over semantic_search."
        )

    # Stack-specific skill suggestions
    stack_tokens = set(
        [l.lower() for l in profile.languages] + [f.lower() for f in profile.frameworks]
    )
    if stack_tokens:
        skill_map = {
            "react": "react_comprehensive",
            "next": "nextjs",
            "nextjs": "nextjs",
            "django": "django_v5",
            "fastapi": "fastapi_patterns",
            "rust": "rust_language",
            "go": "go_language",
            "typescript": "typescript_mastery",
            "postgresql": "postgresql_patterns",
            "redis": "redis_caching_patterns",
            "kubernetes": "kubernetes_orchestration",
            "docker": "kubernetes_orchestration",
        }
        for token in stack_tokens:
            if token in skill_map:
                skill_name = skill_map[token]
                suggestions.append(
                    f"MidOS has a skill for {token}: "
                    f"run `get_skill('{skill_name}')` to load best practices."
                )
                break  # Only suggest one to avoid noise

    # No model identified — give concrete guidance
    if not model_spec and profile.model:
        suggestions.append(
            f"Model '{profile.model}' not in catalog. "
            "Using safe defaults (128K context assumed). "
            "Pass context_window=N for accurate budget. "
            "Free tier: 17 tools, 500 queries/mo — no API key needed."
        )

    # Free tier info — always show for non-admin clients
    if client_norm and not is_primary_cli:
        suggestions.append(
            "Free tier: 17 tools, 500 queries/mo — no API key needed. "
            "Upgrade for EUREKA, semantic_search, and 25,000 queries/mo."
        )

    # OpenCode users: suggest free models
    if client_norm in (
        "opencode",
        "open-code",
        "open_code",
    ):
        suggestions.append(
            "Add free OpenRouter models to OpenCode: "
            "run `python -m modules.mcp_server.midos_mcp --setup opencode --models free`"
        )

    # Invite external agents to sandbox exchanges
    if client_norm and not is_primary_cli:
        suggestions.append(
            "Help improve MidOS: run auditions from sandbox/auditions/ "
            "to test tools, find knowledge gaps, and contribute. "
            "Your feedback directly improves the system."
        )

    return suggestions


def _build_guardrails(
    profile: AgentProfile,
    model_spec: Optional[ModelSpec],
    client_spec: Optional[ClientSpec],
) -> list[str]:
    """Build adaptive guardrail list by intersecting 3 axes."""
    rules: list[str] = []

    # Universal (always)
    rules.extend(GUARDRAILS["universal"])

    # Model-specific
    if model_spec:
        if model_spec.context_window <= 32000:
            rules.extend(GUARDRAILS["model_specific"]["small_context"])
        if not model_spec.supports_tools:
            rules.extend(GUARDRAILS["model_specific"]["no_tools"])
        if not model_spec.supports_vision:
            rules.extend(GUARDRAILS["model_specific"]["no_vision"])
        if not model_spec.supports_structured:
            rules.extend(GUARDRAILS["model_specific"]["no_structured"])

    # Client-specific
    if client_spec:
        if not client_spec.has_hooks:
            rules.extend(GUARDRAILS["client_specific"]["no_hooks"])
        if not client_spec.has_memory:
            rules.extend(GUARDRAILS["client_specific"]["no_memory"])
        if not client_spec.has_background_agents:
            rules.extend(GUARDRAILS["client_specific"]["no_background"])

    # Tier-specific
    tier = profile.tier.lower()
    if tier in GUARDRAILS["tier_specific"]:
        rules.extend(GUARDRAILS["tier_specific"][tier])

    return rules
