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
    AgentProfile, ModelSpec, ClientSpec,
    resolve_model, resolve_client,
)

# Paths
MIDOS_ROOT = Path(__file__).parent.parent.parent.resolve()
KNOWLEDGE_DIR = MIDOS_ROOT / "knowledge"
SKILLS_DIR = MIDOS_ROOT / "skills"


# ============================================================================
# MCP Tool Descriptions — for relevance ranking
# ============================================================================

MCP_TOOLS = [
    {"name": "search_knowledge", "desc": "Keyword search across knowledge base",
     "tags": ["search", "knowledge", "general"]},
    {"name": "semantic_search", "desc": "Vector search with LanceDB + Gemini embeddings",
     "tags": ["search", "vector", "ai", "semantic"]},
    {"name": "get_skill", "desc": "Get a specific skill/capability document",
     "tags": ["skills", "learning", "howto"]},
    {"name": "list_skills", "desc": "List available skills/capabilities",
     "tags": ["skills", "discovery"]},
    {"name": "get_protocol", "desc": "Get a protocol document",
     "tags": ["protocol", "architecture", "system"]},
    {"name": "hive_status", "desc": "System status of MidOS hive",
     "tags": ["status", "health", "system"]},
    {"name": "memory_stats", "desc": "Memory system statistics (LanceDB)",
     "tags": ["memory", "stats", "vector"]},
    {"name": "research_youtube", "desc": "Queue YouTube video for transcription and research",
     "tags": ["youtube", "video", "research"]},
    {"name": "pool_signal", "desc": "Signal action to multi-instance coordination pool",
     "tags": ["coordination", "multi-agent", "pool"]},
    {"name": "pool_status", "desc": "Get multi-instance pool status",
     "tags": ["coordination", "multi-agent", "pool"]},
    {"name": "episodic_search", "desc": "Search episodic memory for past experiences",
     "tags": ["memory", "episodic", "learning"]},
    {"name": "episodic_store", "desc": "Store new episodic memory/reflection",
     "tags": ["memory", "episodic", "learning"]},
    {"name": "chunk_code", "desc": "AST-based code chunking for RAG retrieval",
     "tags": ["code", "rag", "chunking", "ast"]},
    {"name": "agent_handshake", "desc": "This tool — personalized agent onboarding",
     "tags": ["onboarding", "config"], "exclude_from_output": True},
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
    """
    model_spec = resolve_model(profile.model)
    client_spec = resolve_client(profile.client)

    # Context budget
    context_budget = _compute_context_budget(profile, model_spec, client_spec)

    config = {
        "identity": _build_identity(),
        "model_info": _summarize_model(model_spec) if model_spec else None,
        "client_info": _summarize_client(client_spec) if client_spec else None,
        "recommended_tools": _rank_tools(profile, context_budget),
        "relevant_skills": _find_skills(profile),
        "relevant_chunks": _find_chunks(profile),
        "guardrails": _build_guardrails(profile, model_spec, client_spec),
        "model_tips": model_spec.tips if model_spec else [],
        "client_tips": client_spec.tips if client_spec else [],
        "context_budget": context_budget,
    }

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

    # Identity (always)
    parts.append("# MidOS Agent Handshake\n")
    identity = config["identity"]
    parts.append(f"**{identity['name']}** - {identity['description']}")
    parts.append(f"Root: `{identity['root']}`\n")

    # Model/Client info
    if config["model_info"]:
        m = config["model_info"]
        parts.append(f"## Your Model: {m['id']}")
        parts.append(f"Context: {m['context_window']:,} | Output: {m['max_output']:,} | "
                      f"Code: {m['code_score']}/10 | Reasoning: {m['reasoning_score']}/10 | "
                      f"Speed: ~{m['speed_tps']} t/s\n")

    if config["client_info"]:
        c = config["client_info"]
        features = []
        if c.get("has_hooks"):
            features.append("hooks")
        if c.get("has_memory"):
            features.append("memory")
        if c.get("has_background_agents"):
            features.append("background-agents")
        features_str = ", ".join(features) if features else "basic"
        parts.append(f"## Your Client: {c['id']}")
        parts.append(f"MCP: {', '.join(c['mcp_transport'])} | "
                      f"Context: {c['context_management']} | "
                      f"Features: {features_str}\n")

    # Context budget
    cb = config["context_budget"]
    parts.append(f"## Context Budget")
    parts.append(f"Effective window: {cb.get('effective_window', 'unknown'):,} tokens | "
                  f"Payload tier: {tier}\n")

    # Recommended tools
    tools = config["recommended_tools"]
    if tier == "small":
        tools = tools[:3]
    elif tier == "medium":
        tools = tools[:7]
    # large = all

    parts.append(f"## MCP Tools ({len(tools)} recommended)")
    for t in tools:
        parts.append(f"- **{t['name']}** - {t['desc']}")
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

    parts.append(f"---\n_MidOS Handshake v1.0 -- {datetime.now().strftime('%Y-%m-%d %H:%M')}_")

    return "\n".join(parts)


# ============================================================================
# Private Helpers
# ============================================================================

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


def _rank_tools(profile: AgentProfile, context_budget: dict) -> list[dict]:
    """Rank MCP tools by relevance to profile."""
    goal_lower = profile.project_goal.lower() if profile.project_goal else ""
    langs_lower = [l.lower() for l in profile.languages]
    fws_lower = [f.lower() for f in profile.frameworks]
    all_keywords = goal_lower.split() + langs_lower + fws_lower

    scored = []
    for tool in MCP_TOOLS:
        score = 0
        tool_text = (tool["desc"] + " " + " ".join(tool["tags"])).lower()

        # Score by keyword overlap
        for kw in all_keywords:
            if kw and kw in tool_text:
                score += 1

        # Core tools always ranked higher
        if tool["name"] in ("search_knowledge", "semantic_search", "list_skills"):
            score += 3

        scored.append((score, tool))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in scored if not t.get("exclude_from_output")]


def _find_skills(profile: AgentProfile) -> list[str]:
    """Find skills matching agent's stack."""
    if not SKILLS_DIR.exists():
        return []

    skill_dirs = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())

    if not profile.languages and not profile.frameworks and not profile.project_goal:
        # Return most generally useful skills (curated order, not alphabetical)
        priority = [
            "pragmatic_engineering", "compress_prompt", "validate_output",
            "repair_json", "critical_analysis", "structured_reasoning",
            "model_suggest", "health_check", "antifragile_protocol",
            "epistemic_validation",
        ]
        result = [s for s in priority if s in skill_dirs]
        # Fill with remaining if needed
        remaining = [s for s in skill_dirs if s not in result]
        return (result + remaining)[:10]

    # Score skills by keyword match in name
    keywords = (
        [l.lower() for l in profile.languages]
        + [f.lower() for f in profile.frameworks]
        + (profile.project_goal.lower().split() if profile.project_goal else [])
    )

    scored = []
    for skill_name in skill_dirs:
        name_lower = skill_name.lower().replace("-", " ").replace("_", " ")
        score = sum(1 for kw in keywords if kw and kw in name_lower)
        # Check compatibility.json if exists
        compat_file = SKILLS_DIR / skill_name / "compatibility.json"
        if compat_file.exists():
            try:
                compat = json.loads(compat_file.read_text(encoding="utf-8"))
                compat_langs = [x.lower() for x in compat.get("languages", [])]
                compat_fws = [x.lower() for x in compat.get("frameworks", [])]
                compat_tags = [x.lower() for x in compat.get("tags", [])]
                for lang in profile.languages:
                    if lang.lower() in compat_langs:
                        score += 2
                for fw in profile.frameworks:
                    if fw.lower() in compat_fws:
                        score += 2
                # Match project_goal keywords against tags
                if profile.project_goal:
                    goal_words = profile.project_goal.lower().split()
                    for word in goal_words:
                        if word in compat_tags:
                            score += 1
            except (OSError, json.JSONDecodeError):
                pass
        scored.append((score, skill_name))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [name for _, name in scored[:15]]


def _find_chunks(profile: AgentProfile) -> list[dict]:
    """Find relevant knowledge chunks for project_goal using semantic search if available."""
    if not profile.project_goal:
        return []

    # Try semantic search via hive_commons
    try:
        from hive_commons.vector_store import search_memory
        results = search_memory(profile.project_goal, top_k=5)
        if results:
            return [
                {
                    "name": r.get("source", "unknown"),
                    "path": r.get("source", ""),
                    "preview": r.get("text", "")[:300],
                    "score": r.get("score", 0),
                }
                for r in results
            ]
    except (ImportError, Exception):
        pass

    # Fallback: keyword search in chunks directory
    chunks_dir = KNOWLEDGE_DIR / "chunks"
    if not chunks_dir.exists():
        return []

    goal_words = profile.project_goal.lower().split()
    results = []
    for md_file in sorted(chunks_dir.glob("*.md"))[:50]:
        name_lower = md_file.stem.lower().replace("-", " ").replace("_", " ")
        hits = sum(1 for w in goal_words if w in name_lower)
        if hits > 0:
            preview = ""
            try:
                preview = md_file.read_text(encoding="utf-8", errors="ignore")[:300]
            except OSError:
                pass
            results.append({
                "name": md_file.stem,
                "path": str(md_file.relative_to(MIDOS_ROOT)),
                "preview": preview,
                "score": hits,
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:5]


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
