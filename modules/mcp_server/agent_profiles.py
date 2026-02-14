"""
Agent Profile Schema + Model/Client Catalogs
=============================================
Data layer for agent_handshake auto-configuration.

AgentProfile: what the connecting agent declares about itself.
ModelSpec/ClientSpec: known capabilities of models and clients.
MODEL_CATALOG/CLIENT_CATALOG: structured lookups from knowledge chunks.

Catalog sources:
  - knowledge/chunks/ai_model_catalog_2026-02-12.md (31 models)
  - knowledge/chunks/ai_cli_ide_catalog_2026-02-12.md (11 clients)
"""

import difflib
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# Agent Profile — what the connecting agent sends
# ============================================================================

@dataclass
class AgentProfile:
    """What the connecting agent sends during handshake."""
    model: str = ""
    context_window: int = 0
    client: str = ""
    languages: list[str] = field(default_factory=list)
    frameworks: list[str] = field(default_factory=list)
    platform: str = ""
    project_goal: str = ""
    tier: str = "community"


# ============================================================================
# Model Spec — known model capabilities
# ============================================================================

@dataclass
class ModelSpec:
    """Known model capabilities."""
    id: str
    family: str
    context_window: int
    max_output: int
    supports_tools: bool
    supports_vision: bool
    supports_structured: bool
    tier: str  # "frontier", "balanced", "fast", "edge"
    code_score: int  # 1-10
    reasoning_score: int  # 1-10
    speed_tps: int  # approximate tokens/sec
    tips: list[str] = field(default_factory=list)


# ============================================================================
# Client Spec — known client/IDE capabilities
# ============================================================================

@dataclass
class ClientSpec:
    """Known client/IDE capabilities."""
    id: str
    mcp_transport: list[str] = field(default_factory=list)
    has_hooks: bool = False
    has_memory: bool = False
    has_background_agents: bool = False
    max_parallel_agents: int = 0  # 0 = unlimited or N/A
    context_management: str = "none"  # "auto-compact", "dynamic-pruning", "manual", "none"
    max_context: int = 0  # 0 = model-dependent
    tips: list[str] = field(default_factory=list)


# ============================================================================
# MODEL CATALOG — extracted from ai_model_catalog_2026-02-12.md
# ============================================================================

MODEL_CATALOG: dict[str, ModelSpec] = {
    # --- Claude Family ---
    "claude-opus-4-6": ModelSpec(
        id="claude-opus-4-6", family="anthropic", context_window=200000,
        max_output=128000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="frontier", code_score=10,
        reasoning_score=10, speed_tps=60,
        tips=["Use extended thinking for complex tasks",
              "SWE-bench Verified: 80.9%, Terminal-Bench: 59.3%",
              "Best for architecture, deep reasoning, failure diagnosis"],
    ),
    "claude-sonnet-4-5": ModelSpec(
        id="claude-sonnet-4-5", family="anthropic", context_window=200000,
        max_output=64000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="balanced", code_score=9,
        reasoning_score=9, speed_tps=100,
        tips=["Best balance of intelligence and speed",
              "SWE-bench Verified: 77-82%",
              "Ideal for production coding and complex agents"],
    ),
    "claude-haiku-4-5": ModelSpec(
        id="claude-haiku-4-5", family="anthropic", context_window=200000,
        max_output=64000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="fast", code_score=8,
        reasoning_score=8, speed_tps=175,
        tips=["3x faster than Opus — use for exploration and parallel agents",
              "First Haiku with extended thinking",
              "Near-frontier performance at high speed"],
    ),
    # --- GPT Family ---
    "gpt-4o": ModelSpec(
        id="gpt-4o", family="openai", context_window=128000,
        max_output=16000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="balanced", code_score=9,
        reasoning_score=8, speed_tps=120,
        tips=["Strong general-purpose model",
              "Native multimodal capabilities"],
    ),
    "gpt-4o-mini": ModelSpec(
        id="gpt-4o-mini", family="openai", context_window=128000,
        max_output=16000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="fast", code_score=7,
        reasoning_score=7, speed_tps=175,
        tips=["Cost-efficient for simple tasks",
              "Good for high-speed batch processing"],
    ),
    "gpt-o1": ModelSpec(
        id="gpt-o1", family="openai", context_window=128000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=False, tier="frontier", code_score=8,
        reasoning_score=9, speed_tps=75,
        tips=["Reasoning-optimized — uses internal thinking tokens",
              "Actual costs higher than visible output suggests"],
    ),
    "gpt-o3": ModelSpec(
        id="gpt-o3", family="openai", context_window=200000,
        max_output=100000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="frontier", code_score=10,
        reasoning_score=10, speed_tps=65,
        tips=["SWE-Bench Pro SOTA: 55.6%",
              "First model that agentively uses every tool",
              "Best for multi-faceted analysis and visual tasks"],
    ),
    "gpt-o3-mini": ModelSpec(
        id="gpt-o3-mini", family="openai", context_window=200000,
        max_output=100000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=8,
        reasoning_score=8, speed_tps=100,
        tips=["Cost-efficient reasoning with 200K context"],
    ),
    # --- Gemini Family ---
    "gemini-2.5-pro": ModelSpec(
        id="gemini-2.5-pro", family="google", context_window=1000000,
        max_output=64000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="frontier", code_score=9,
        reasoning_score=9, speed_tps=110,
        tips=["1M context — can handle entire codebases",
              "Native multimodal (text, audio, images, video)",
              "Built-in thinking capabilities"],
    ),
    "gemini-2.5-flash": ModelSpec(
        id="gemini-2.5-flash", family="google", context_window=1000000,
        max_output=64000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="fast", code_score=9,
        reasoning_score=9, speed_tps=506,
        tips=["Fastest Gemini at 506 tokens/sec",
              "1M context with hybrid thinking control",
              "Best cost-effective high-volume option"],
    ),
    "gemini-2.5-flash-lite": ModelSpec(
        id="gemini-2.5-flash-lite", family="google", context_window=1000000,
        max_output=64000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="edge", code_score=7,
        reasoning_score=7, speed_tps=506,
        tips=["Tied for fastest model overall at 506 t/s",
              "Maximum throughput for batch processing"],
    ),
    "gemini-2.0-flash": ModelSpec(
        id="gemini-2.0-flash", family="google", context_window=1000000,
        max_output=64000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="fast", code_score=8,
        reasoning_score=8, speed_tps=450,
        tips=["Superseded by 2.5 Flash for advanced reasoning"],
    ),
    # --- DeepSeek Family ---
    "deepseek-r1": ModelSpec(
        id="deepseek-r1", family="deepseek", context_window=128000,
        max_output=64000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="frontier", code_score=9,
        reasoning_score=10, speed_tps=100,
        tips=["Advanced thinking capabilities",
              "Different rates for cache hits vs misses"],
    ),
    "deepseek-v3": ModelSpec(
        id="deepseek-v3", family="deepseek", context_window=128000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=8,
        reasoning_score=8, speed_tps=120,
        tips=["One of the lowest-priced capable models",
              "Good for cost-effective general-purpose coding"],
    ),
    "deepseek-v3.1": ModelSpec(
        id="deepseek-v3.1", family="deepseek", context_window=128000,
        max_output=64000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=9,
        reasoning_score=9, speed_tps=110,
        tips=["671B params — hybrid V3 + R1 strengths"],
    ),
    # --- Mistral Family ---
    "mistral-large-2411": ModelSpec(
        id="mistral-large-2411", family="mistral", context_window=131000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=8,
        reasoning_score=8, speed_tps=105,
        tips=["General-purpose capable model"],
    ),
    "codestral": ModelSpec(
        id="codestral", family="mistral", context_window=256000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=10,
        reasoning_score=7, speed_tps=140,
        tips=["Specialized code model — 80+ languages",
              "Fill-in-the-middle (FIM) support",
              "256K context — largest for code-specialized model"],
    ),
    "mistral-medium": ModelSpec(
        id="mistral-medium", family="mistral", context_window=32000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=7,
        reasoning_score=7, speed_tps=130,
        tips=["Mid-tier cost-performance balance"],
    ),
    "mistral-small": ModelSpec(
        id="mistral-small", family="mistral", context_window=32000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="edge", code_score=6,
        reasoning_score=6, speed_tps=155,
        tips=["Fast low-cost operations"],
    ),
    # --- Llama Family ---
    "llama-3.3-70b": ModelSpec(
        id="llama-3.3-70b", family="meta", context_window=128000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=8,
        reasoning_score=8, speed_tps=120,
        tips=["Strong open-source option for self-hosting"],
    ),
    "llama-4-maverick": ModelSpec(
        id="llama-4-maverick", family="meta", context_window=10000000,
        max_output=64000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="frontier", code_score=9,
        reasoning_score=9, speed_tps=100,
        tips=["10M tokens — industry longest context",
              "Best for entire codebase analysis"],
    ),
    "llama-4-scout": ModelSpec(
        id="llama-4-scout", family="meta", context_window=10000000,
        max_output=64000, supports_tools=True, supports_vision=True,
        supports_structured=True, tier="balanced", code_score=8,
        reasoning_score=8, speed_tps=110,
        tips=["10M context — tied for longest"],
    ),
    # --- Qwen Family ---
    "qwen-2.5-7b": ModelSpec(
        id="qwen-2.5-7b", family="alibaba", context_window=128000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="edge", code_score=7,
        reasoning_score=7, speed_tps=160,
        tips=["Most affordable at $0.03/M input tokens"],
    ),
    "qwen-2.5-coder-32b": ModelSpec(
        id="qwen-2.5-coder-32b", family="alibaba", context_window=128000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=9,
        reasoning_score=8, speed_tps=130,
        tips=["92 languages, 5.5T tokens training",
              "Extremely affordable for capability level"],
    ),
    "qwen-3-coder": ModelSpec(
        id="qwen-3-coder", family="alibaba", context_window=1000000,
        max_output=16000, supports_tools=True, supports_vision=False,
        supports_structured=True, tier="balanced", code_score=9,
        reasoning_score=8, speed_tps=120,
        tips=["1M context — major upgrade from 128K"],
    ),
}


# ============================================================================
# CLIENT CATALOG — extracted from ai_cli_ide_catalog_2026-02-12.md
# ============================================================================

CLIENT_CATALOG: dict[str, ClientSpec] = {
    "claude-code": ClientSpec(
        id="claude-code",
        mcp_transport=["stdio", "streamable-http"],
        has_hooks=True, has_memory=False, has_background_agents=True,
        max_parallel_agents=0, context_management="auto-compact",
        max_context=200000,
        tips=["Use /compact every ~20 iterations",
              "Tool Search reduces MCP context bloat by 46.9%",
              "13 lifecycle hooks available (async supported)",
              "Delegate: haiku for speed, opus for quality"],
    ),
    "cursor": ClientSpec(
        id="cursor",
        mcp_transport=["stdio", "streamable-http"],
        has_hooks=False, has_memory=False, has_background_agents=False,
        max_parallel_agents=0, context_management="dynamic-pruning",
        max_context=200000,
        tips=["Use Composer mode for multi-file editing",
              "Dynamic pruning drops older context automatically",
              "@Codebase symbol for repository-wide context"],
    ),
    "windsurf": ClientSpec(
        id="windsurf",
        mcp_transport=["stdio", "streamable-http"],
        has_hooks=True, has_memory=True, has_background_agents=True,
        max_parallel_agents=0, context_management="auto-summarize",
        max_context=300000,
        tips=["300K context — largest among major IDEs",
              "Cascade Memories persist across sessions",
              "Sub-50ms completion latency",
              "100 tools max per session"],
    ),
    "cline": ClientSpec(
        id="cline",
        mcp_transport=["stdio"],
        has_hooks=True, has_memory=False, has_background_agents=False,
        max_parallel_agents=0, context_management="auto-truncation",
        max_context=0,
        tips=["1000 files indexed limit, 300KB file size limit",
              "Approval required for every action",
              "Can create custom MCP servers on demand"],
    ),
    "continue": ClientSpec(
        id="continue",
        mcp_transport=["stdio"],
        has_hooks=True, has_memory=False, has_background_agents=False,
        max_parallel_agents=0, context_management="manual",
        max_context=0,
        tips=["Open-source, multi-provider — use any model",
              "First client with full MCP feature support",
              "@ commands for context injection"],
    ),
    "aider": ClientSpec(
        id="aider",
        mcp_transport=["stdio"],
        has_hooks=True, has_memory=False, has_background_agents=False,
        max_parallel_agents=0, context_management="repo-map",
        max_context=0,
        tips=["Best token efficiency — $0.50-2 per session",
              "Repository map provides context without loading full files",
              "CLI-first, scriptable, auto-commits"],
    ),
    "zed": ClientSpec(
        id="zed",
        mcp_transport=["stdio", "streamable-http"],
        has_hooks=True, has_memory=True, has_background_agents=True,
        max_parallel_agents=0, context_management="external-mcp",
        max_context=0,
        tips=["Background agents with container isolation",
              "Agent Client Protocol (ACP) for external agents",
              "Rust-based high-performance editor"],
    ),
    "github-copilot": ClientSpec(
        id="github-copilot",
        mcp_transport=["stdio", "streamable-http"],
        has_hooks=True, has_memory=True, has_background_agents=False,
        max_parallel_agents=0, context_management="auto-compact",
        max_context=0,
        tips=["Best GitHub integration (repos, issues, PRs, Actions)",
              "Copilot SDK for embedding in custom apps",
              "MCP Registry for curated servers"],
    ),
    "amazon-q": ClientSpec(
        id="amazon-q",
        mcp_transport=["stdio", "streamable-http"],
        has_hooks=True, has_memory=True, has_background_agents=False,
        max_parallel_agents=0, context_management="auto-compact",
        max_context=0,
        tips=["Best AWS integration",
              "Security scanner for all MCP traffic",
              "CLI session persistence with --resume"],
    ),
    "replit": ClientSpec(
        id="replit",
        mcp_transport=["streamable-http"],
        has_hooks=True, has_memory=True, has_background_agents=True,
        max_parallel_agents=0, context_management="mcp-context",
        max_context=0,
        tips=["Web-based — no local installation needed",
              "One-click deployment from browser",
              "OAuth auto-registration for MCP servers"],
    ),
    "lovable": ClientSpec(
        id="lovable",
        mcp_transport=["streamable-http"],
        has_hooks=True, has_memory=True, has_background_agents=False,
        max_parallel_agents=0, context_management="description-based",
        max_context=0,
        tips=["Full-stack generation from natural language description",
              "Best for MVPs and rapid prototyping",
              "MCP connectors for CRM, tickets, automation"],
    ),
}


# ============================================================================
# Alias Maps — common variations → canonical IDs
# ============================================================================

_MODEL_ALIASES: dict[str, str] = {
    # Claude
    "opus": "claude-opus-4-6", "opus 4.6": "claude-opus-4-6",
    "claude opus": "claude-opus-4-6", "claude-opus": "claude-opus-4-6",
    "sonnet": "claude-sonnet-4-5", "sonnet 4.5": "claude-sonnet-4-5",
    "claude sonnet": "claude-sonnet-4-5", "claude-sonnet": "claude-sonnet-4-5",
    "haiku": "claude-haiku-4-5", "haiku 4.5": "claude-haiku-4-5",
    "claude haiku": "claude-haiku-4-5", "claude-haiku": "claude-haiku-4-5",
    # GPT
    "gpt4o": "gpt-4o", "gpt 4o": "gpt-4o",
    "gpt4o-mini": "gpt-4o-mini", "gpt 4o mini": "gpt-4o-mini",
    "o1": "gpt-o1", "o3": "gpt-o3", "o3-mini": "gpt-o3-mini",
    # Gemini
    "gemini pro": "gemini-2.5-pro", "gemini-pro": "gemini-2.5-pro",
    "gemini flash": "gemini-2.5-flash", "gemini-flash": "gemini-2.5-flash",
    "gemini flash lite": "gemini-2.5-flash-lite",
    # DeepSeek
    "deepseek": "deepseek-r1", "deepseek r1": "deepseek-r1",
    "deepseek v3": "deepseek-v3",
    # Llama
    "llama": "llama-4-maverick", "llama 4": "llama-4-maverick",
    "maverick": "llama-4-maverick", "scout": "llama-4-scout",
    # Qwen
    "qwen": "qwen-2.5-coder-32b", "qwen coder": "qwen-2.5-coder-32b",
    "qwen 3": "qwen-3-coder",
    # Mistral
    "codestral-2508": "codestral",
    "mistral large": "mistral-large-2411", "mistral-large": "mistral-large-2411",
}

_CLIENT_ALIASES: dict[str, str] = {
    "claude code": "claude-code", "claudecode": "claude-code",
    "claude_code": "claude-code", "anthropic": "claude-code",
    "copilot": "github-copilot", "github copilot": "github-copilot",
    "gh-copilot": "github-copilot",
    "amazon q": "amazon-q", "amazonq": "amazon-q", "q developer": "amazon-q",
    "replit agent": "replit",
    "windsurf cascade": "windsurf", "cascade": "windsurf",
    "continue.dev": "continue", "continuedev": "continue",
    "aider.chat": "aider",
    "zed editor": "zed",
    "lovable.dev": "lovable",
    "cline bot": "cline", "claude-dev": "cline",
}


# ============================================================================
# Matching Functions
# ============================================================================

def resolve_model(raw: str) -> Optional[ModelSpec]:
    """Resolve a raw model string to a ModelSpec.

    Tries exact match, alias lookup, then fuzzy matching.
    """
    if not raw:
        return None

    normalized = raw.strip().lower()

    # Exact match
    if normalized in MODEL_CATALOG:
        return MODEL_CATALOG[normalized]

    # Alias match
    if normalized in _MODEL_ALIASES:
        return MODEL_CATALOG.get(_MODEL_ALIASES[normalized])

    # Fuzzy match against catalog keys + alias keys
    all_keys = list(MODEL_CATALOG.keys()) + list(_MODEL_ALIASES.keys())
    matches = difflib.get_close_matches(normalized, all_keys, n=1, cutoff=0.5)
    if matches:
        key = matches[0]
        if key in MODEL_CATALOG:
            return MODEL_CATALOG[key]
        if key in _MODEL_ALIASES:
            return MODEL_CATALOG.get(_MODEL_ALIASES[key])

    return None


def resolve_client(raw: str) -> Optional[ClientSpec]:
    """Resolve a raw client string to a ClientSpec.

    Tries exact match, alias lookup, then fuzzy matching.
    """
    if not raw:
        return None

    normalized = raw.strip().lower()

    # Exact match
    if normalized in CLIENT_CATALOG:
        return CLIENT_CATALOG[normalized]

    # Alias match
    if normalized in _CLIENT_ALIASES:
        return CLIENT_CATALOG.get(_CLIENT_ALIASES[normalized])

    # Fuzzy match
    all_keys = list(CLIENT_CATALOG.keys()) + list(_CLIENT_ALIASES.keys())
    matches = difflib.get_close_matches(normalized, all_keys, n=1, cutoff=0.5)
    if matches:
        key = matches[0]
        if key in CLIENT_CATALOG:
            return CLIENT_CATALOG[key]
        if key in _CLIENT_ALIASES:
            return CLIENT_CATALOG.get(_CLIENT_ALIASES[key])

    return None
