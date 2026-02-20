#!/usr/bin/env python3
"""
MIDOS MCP SERVER - Knowledge as Tools (FastMCP)
================================================
Exposes the MidOS knowledge base as MCP tools via FastMCP.
Supports dual transport: stdio (default) and streamable HTTP.

INSTALLATION:
    pip install fastmcp

EXECUTION:
    # stdio (Claude Code, default — backward compatible)
    python -m modules.mcp_server.midos_mcp

    # HTTP (remote, streamable)
    python -m modules.mcp_server.midos_mcp --http --port 8419

CONFIGURATION IN CLAUDE:
    Agregar a ~/.claude.json o settings:
    {
        "mcpServers": {
            "midos": {
                "command": "python",
                "args": ["-m", "modules.mcp_server.midos_mcp"],
                "cwd": "/path/to/midos-mcp"
            }
        }
    }

TOOLS EXPOSED (18):
    - search_knowledge: Search the knowledge base
    - get_skill: Get a specific skill
    - list_skills: List available skills (+ stack filter)
    - get_protocol: Get a protocol document
    - get_eureka: Get a EUREKA breakthrough document
    - get_truth: Get a truth patch document
    - hive_status: System status
    - semantic_search: Vector search (LanceDB + Gemini) (+ stack filter)
    - research_youtube: Queue video for research
    - memory_stats: Memory system statistics
    - pool_signal / pool_status: Multi-instance coordination
    - episodic_search / episodic_store: Episodic memory
    - chunk_code: AST-based code chunking
    - agent_handshake: Personalized agent onboarding
    - project_status: Live dashboard + quick-start guide
    - agent_bootstrap: [DEPRECATED] Generic onboarding

RESOURCES (1):
    - midos://skill/{skill_name}: Read skill files as MCP resources
"""

import json
import os
import sys
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

# FastMCP imports
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

# MidOS auth middleware
from modules.mcp_server.auth import ApiKeyMiddleware

# === HIVE COMMONS: Unified configuration ===
try:
    from hive_commons.config import L1_ROOT, L1_KNOWLEDGE, L1_SYNAPSE
    from hive_commons.vector_store import search_memory, get_memory_stats
    from hive_commons.semantic_cache import check_cache
    HIVE_COMMONS_AVAILABLE = True
except ImportError:
    HIVE_COMMONS_AVAILABLE = False
    L1_ROOT = Path(__file__).parent.parent.parent.resolve()
    L1_KNOWLEDGE = L1_ROOT / "knowledge"
    L1_SYNAPSE = L1_ROOT / "synapse"

# Configuration (from hive_commons)
MIDOS_ROOT = L1_ROOT
KNOWLEDGE_DIR = L1_KNOWLEDGE
SKILLS_DIR = KNOWLEDGE_DIR / "archive" / "legacy_system" / "capabilities"
PROTOCOLS_DIR = KNOWLEDGE_DIR / "archive" / "legacy_system" / "protocols"
EUREKA_DIR = KNOWLEDGE_DIR / "EUREKA"
TRUTH_DIR = KNOWLEDGE_DIR / "truth"
SYNAPSE_DIR = L1_SYNAPSE
_SERVER_START_TIME = time.time()


# ============================================================================
# HELPER FUNCTIONS (unchanged)
# ============================================================================

def search_files(
    query: str,
    directory: Path,
    extensions: List[str] = [".md"],
    max_results: int = 10,
) -> List[Dict[str, Any]]:
    """Buscar archivos que contengan query."""
    results = []
    query_lower = query.lower()

    for ext in extensions:
        for file_path in directory.rglob(f"*{ext}"):
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                if query_lower in content.lower() or query_lower in file_path.name.lower():
                    # Extract snippet around match
                    idx = content.lower().find(query_lower)
                    if idx >= 0:
                        start = max(0, idx - 100)
                        end = min(len(content), idx + 200)
                        snippet = content[start:end].strip()
                    else:
                        snippet = content[:300].strip()

                    results.append({
                        "path": str(file_path.relative_to(MIDOS_ROOT)),
                        "name": file_path.stem,
                        "snippet": snippet,
                        "size": len(content),
                    })

                    if len(results) >= max_results:
                        return results
            except OSError:
                continue

    return results


def get_file_content(file_path: Path, max_chars: int = 10000) -> str:
    """Obtener contenido de archivo."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="ignore")
        if len(content) > max_chars:
            content = content[:max_chars] + f"\n\n[...truncated, {len(content)} total chars]"
        return content
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(directory: Path, pattern: str = "*.md") -> List[Dict[str, str]]:
    """Listar archivos en directorio."""
    files = []
    for file_path in sorted(directory.glob(pattern)):
        files.append({
            "name": file_path.stem,
            "path": str(file_path.relative_to(MIDOS_ROOT)),
        })
    return files


def get_hive_status() -> Dict[str, Any]:
    """Obtener estado del hive."""
    status = {
        "timestamp": datetime.now().isoformat(),
        "midos_root": str(MIDOS_ROOT),
        "knowledge_files": 0,
        "skills_count": 0,
        "protocols_count": 0,
        "recent_pearls": [],
    }

    # Count files
    if KNOWLEDGE_DIR.exists():
        status["knowledge_files"] = len(list(KNOWLEDGE_DIR.rglob("*.md")))

    if SKILLS_DIR.exists():
        status["skills_count"] = len(list(SKILLS_DIR.glob("*.md")))

    if PROTOCOLS_DIR.exists():
        status["protocols_count"] = len(list(PROTOCOLS_DIR.glob("*.md")))

    # Check pearl diver state
    pearl_state = SYNAPSE_DIR / "pearl_diver_state.json"
    if pearl_state.exists():
        try:
            with open(pearl_state, encoding='utf-8') as f:
                pd_state = json.load(f)
                status["pearl_diver"] = {
                    "files_scanned": pd_state.get("files_scanned", 0),
                    "pearls_found": pd_state.get("pearls_found", 0),
                }
        except (OSError, json.JSONDecodeError, KeyError):
            pass

    # Recent pearls
    pearls_dir = SYNAPSE_DIR / "pearls"
    if pearls_dir.exists():
        pearl_files = sorted(pearls_dir.glob("*.json"), reverse=True)[:3]
        for pf in pearl_files:
            try:
                with open(pf, encoding='utf-8') as f:
                    pearls = json.load(f)
                    status["recent_pearls"].append({
                        "file": pf.name,
                        "count": len(pearls),
                    })
            except (OSError, json.JSONDecodeError):
                pass

    return status


# ============================================================================
# FASTMCP SERVER
# ============================================================================

mcp = FastMCP(
    "midos",
    instructions="MidOS knowledge library. Use tools to search, get skills, semantic search, and more.",
    middleware=[ApiKeyMiddleware()],
)


# ============================================================================
# TOOLS (18 total)
# ============================================================================

@mcp.tool
async def search_knowledge(query: str, max_results: int = 5) -> str:
    """Search the Midos knowledge base for relevant information.

    Args:
        query: Search query (keywords or topic)
        max_results: Maximum results to return (default: 5)
    """
    results = search_files(query, KNOWLEDGE_DIR, max_results=max_results)

    if not results:
        return f"No results found for: {query}"

    output = f"Found {len(results)} results for '{query}':\n\n"
    for r in results:
        output += f"## {r['name']}\nPath: {r['path']}\n```\n{r['snippet']}\n```\n\n"
    return output


@mcp.tool
async def get_skill(name: str) -> str:
    """Get a specific skill/capability document by name.

    Args:
        name: Skill name (e.g., 'RAG_SYSTEMS_2026_SOTA')
    """
    skill_path = SKILLS_DIR / f"{name}.md"
    if not skill_path.exists():
        for f in SKILLS_DIR.glob("*.md"):
            if f.stem.lower() == name.lower():
                skill_path = f
                break

    if not skill_path.exists():
        available = [f.stem for f in SKILLS_DIR.glob("*.md")][:20]
        return f"Skill not found: {name}\n\nAvailable skills: {available}"

    return get_file_content(skill_path)


@mcp.tool
async def list_skills(filter: str = "", stack: str = "") -> str:
    """List all available skills/capabilities.

    Args:
        filter: Optional filter for skill names
        stack: Optional stack filter, comma-separated (e.g. 'python,react'). Skills with matching compatibility.json are prioritized.
    """
    skills = list_files(SKILLS_DIR)

    if filter:
        skills = [s for s in skills if filter.lower() in s["name"].lower()]

    # Stack-aware sorting: check compatibility.json in skill directories
    if stack:
        import json as _json
        stack_tokens = [t.strip().lower() for t in stack.split(",") if t.strip()]
        scored_skills = []
        for s in skills:
            score = 0
            skill_dir = SKILLS_DIR.parent / "skills" / s["name"]
            if not skill_dir.exists():
                skill_dir = MIDOS_ROOT / "skills" / s["name"]
            compat_file = skill_dir / "compatibility.json"
            if compat_file.exists():
                try:
                    compat = _json.loads(compat_file.read_text(encoding="utf-8"))
                    compat_all = (
                        [x.lower() for x in compat.get("languages", [])]
                        + [x.lower() for x in compat.get("frameworks", [])]
                    )
                    for t in stack_tokens:
                        if any(t in c for c in compat_all):
                            score += 2
                except (OSError, _json.JSONDecodeError):
                    pass
            # Also match by name
            name_lower = s["name"].lower().replace("-", " ").replace("_", " ")
            for t in stack_tokens:
                if t in name_lower:
                    score += 1
            scored_skills.append((score, s))
        scored_skills.sort(key=lambda x: x[0], reverse=True)
        skills = [s for _, s in scored_skills]

    output = f"Available skills ({len(skills)}):\n\n"
    for s in skills:
        output += f"- {s['name']}\n"
    return output


@mcp.tool
async def get_protocol(name: str) -> str:
    """Get a specific protocol document.

    Args:
        name: Protocol name (e.g., 'PROTOCOL_NEURAL_LINK')
    """
    protocol_path = PROTOCOLS_DIR / f"{name}.md"
    if not protocol_path.exists():
        for f in PROTOCOLS_DIR.glob("*.md"):
            if f.stem.lower() == name.lower():
                protocol_path = f
                break

    if not protocol_path.exists():
        return f"Protocol not found: {name}"

    return get_file_content(protocol_path)


@mcp.tool
async def get_eureka(name: str) -> str:
    """Get a specific EUREKA breakthrough document.

    Args:
        name: EUREKA name (e.g., 'EUREKA_CACHE_SEMANTICA' or 'ATOM_001')
    """
    eureka_path = EUREKA_DIR / f"{name}.md"
    if not eureka_path.exists():
        for f in EUREKA_DIR.glob("*.md"):
            if f.stem.lower() == name.lower():
                eureka_path = f
                break

    if not eureka_path.exists():
        available = [f.stem for f in EUREKA_DIR.glob("*.md")][:20]
        return f"EUREKA not found: {name}\n\nAvailable EUREKA documents: {available}"

    return get_file_content(eureka_path)


@mcp.tool
async def get_truth(name: str) -> str:
    """Get a specific truth patch document.

    Args:
        name: Truth patch name (e.g., 'AGENT_MITIGATIONS_CONTEXT_OVERFLOW')
    """
    truth_path = TRUTH_DIR / f"{name}.md"
    if not truth_path.exists():
        for f in TRUTH_DIR.glob("*.md"):
            if f.stem.lower() == name.lower():
                truth_path = f
                break

    if not truth_path.exists():
        available = [f.stem for f in TRUTH_DIR.glob("*.md")][:20]
        return f"Truth patch not found: {name}\n\nAvailable truth patches: {available}"

    return get_file_content(truth_path)


@mcp.tool
async def hive_status() -> str:
    """Get current status of the Midos hive system."""
    status = get_hive_status()
    return json.dumps(status, indent=2)


@mcp.tool
async def semantic_search(query: str, top_k: int = 5, stack: str = "") -> str:
    """Semantic search using LanceDB vectors (Gemini embeddings). More intelligent than keyword search.

    Args:
        query: Natural language query (e.g., 'how to implement RAG pipelines')
        top_k: Number of results (default: 5)
        stack: Optional stack filter, comma-separated (e.g. 'python,fastapi'). Results mentioning these are boosted.
    """
    if not HIVE_COMMONS_AVAILABLE:
        raise ToolError("hive_commons not available. Install with: pip install -e ./hive_commons")

    results = search_memory(query, top_k=top_k * 2 if stack else top_k)

    if not results:
        return f"No semantic matches for: {query}"

    # Optional stack filtering: boost results that mention stack tokens
    if stack:
        stack_tokens = [s.strip().lower() for s in stack.split(",") if s.strip()]
        scored = []
        for r in results:
            text_lower = r.get("text", "").lower() + " " + r.get("source", "").lower()
            boost = sum(1 for t in stack_tokens if t in text_lower)
            scored.append((boost, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        results = [r for _, r in scored[:top_k]]

    output = f"Found {len(results)} semantic matches for '{query}':\n\n"
    for i, r in enumerate(results, 1):
        output += f"### {i}. Score: {r.get('score', 0):.3f}\n"
        output += f"Source: {r.get('source', 'unknown')}\n"
        output += f"```\n{r.get('text', '')[:500]}\n```\n\n"
    return output


@mcp.tool
async def research_youtube(url: str, priority: str = "normal") -> str:
    """Queue a YouTube video for research. Midos will transcribe and extract insights.

    Args:
        url: YouTube URL to research
        priority: Priority: 'high', 'normal', 'low'
    """
    from urllib.parse import urlparse

    if not url or len(url) > 2048:
        raise ToolError("Invalid YouTube URL")
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ToolError("Invalid URL scheme — only http/https allowed")
    valid_hosts = {"youtube.com", "www.youtube.com", "youtu.be", "m.youtube.com"}
    if parsed.hostname not in valid_hosts:
        raise ToolError(
            f"Invalid YouTube host: {parsed.hostname}. "
            f"Must be youtube.com or youtu.be"
        )

    cmd_file = SYNAPSE_DIR / "inbox" / f"CMD_youtube_{int(time.time())}.json"
    cmd_file.parent.mkdir(parents=True, exist_ok=True)

    command = {
        "id": f"mcp_youtube_{int(time.time())}",
        "source": "MCP_SERVER",
        "type": "USER_COMMAND",
        "priority": priority.upper(),
        "payload": {
            "action": f"investigate {url}",
            "content": url,
        },
        "timestamp": int(time.time()),
    }
    cmd_file.write_text(json.dumps(command, indent=2), encoding="utf-8")

    return f"YouTube research queued: {url}\nPriority: {priority}\nCommand file: {cmd_file.name}"


@mcp.tool
async def memory_stats() -> str:
    """Get statistics about the Midos memory system (LanceDB chunks, cache status)."""
    if not HIVE_COMMONS_AVAILABLE:
        raise ToolError("hive_commons not available")

    stats = get_memory_stats()
    return json.dumps(stats, indent=2)


@mcp.tool
async def pool_signal(action: str, topic: str, summary: str, affects: str = "") -> str:
    """Signal an action to the multi-instance coordination pool.

    Args:
        action: Action type: 'completed', 'blocked', 'claimed', 'signaling'
        topic: Topic/task name
        summary: Brief description of the action
        affects: Files/resources affected (optional)
    """
    try:
        sys.path.insert(0, str(MIDOS_ROOT / "hooks"))
        from instance_pool import get_pool

        pool = get_pool()
        success = pool.signal(action, topic, summary, affects=affects)
        return f"Pool signal sent: {action} - {topic}\nSuccess: {success}"
    except Exception as e:
        return f"Pool signal error: {e}"


@mcp.tool
async def pool_status() -> str:
    """Get multi-instance coordination pool status and recent activity."""
    try:
        sys.path.insert(0, str(MIDOS_ROOT / "hooks"))
        from instance_pool import get_pool

        pool = get_pool()
        context = pool.format_context()
        stats = pool.get_stats()

        output = context + "\n\n### Statistics\n"
        output += json.dumps(stats, indent=2)
        return output
    except Exception as e:
        return f"Pool status error: {e}"


@mcp.tool
async def episodic_search(query: str, limit: int = 5) -> str:
    """Search episodic memory for similar past experiences using vector similarity.

    Args:
        query: Search query describing the experience/task
        limit: Maximum results (default: 5)
    """
    try:
        sys.path.insert(0, str(MIDOS_ROOT / "hooks"))
        from episodic_memory import search_reflexions

        results = search_reflexions(query, limit=limit)

        if not results:
            return f"No episodic memories found for: {query}"

        output = f"Found {len(results)} episodic memories:\n\n"
        for i, r in enumerate(results, 1):
            output += f"### {i}. Score: {r.get('score', 0):.3f}\n"
            output += f"```\n{r.get('text', '')[:300]}\n```\n\n"
        return output
    except Exception as e:
        return f"Episodic search error: {e}"


@mcp.tool
async def episodic_store(task_type: str, input_preview: str, success: bool = True) -> str:
    """Store a new episodic memory/reflection for future learning.

    Args:
        task_type: Type of task: CODE, RESEARCH, DEBUG, REVIEW
        input_preview: Brief description of the input/context
        success: Whether the task was successful
    """
    try:
        sys.path.insert(0, str(MIDOS_ROOT / "hooks"))
        from episodic_memory import store_reflexion

        stored = store_reflexion(
            task_type=task_type,
            input_preview=input_preview,
            success=success,
            provider="mcp_server"
        )
        return f"Episodic memory stored: {task_type}\nSuccess: {stored}"
    except Exception as e:
        return f"Episodic store error: {e}"


@mcp.tool
async def chunk_code(file_path: str) -> str:
    """Parse code file into semantic chunks (functions, classes, methods) for better RAG retrieval.

    Args:
        file_path: Path to code file to chunk
    """
    if not file_path:
        raise ToolError("file_path required")

    try:
        sys.path.insert(0, str(MIDOS_ROOT / "hooks"))
        from ast_chunker import chunk_file

        p = Path(file_path)
        if not p.is_absolute():
            p = MIDOS_ROOT / file_path

        result = chunk_file(p)

        if result.error:
            return f"Chunking error: {result.error}"

        output = f"## Code Chunks: {result.file_path}\n"
        output += f"Language: {result.language}\n"
        output += f"Chunks: {len(result.chunks)}\n"
        output += f"Parse time: {result.parsing_time_ms:.2f}ms\n\n"

        for chunk in result.chunks:
            output += f"### [{chunk.chunk_type}] {chunk.name}\n"
            output += f"Lines: {chunk.start_line}-{chunk.end_line}\n"
            if chunk.signature:
                output += f"```\n{chunk.signature[:200]}\n```\n"
            output += "\n"

        return output
    except Exception as e:
        return f"Chunk code error: {e}"


@mcp.tool
async def agent_handshake(
    model: str = "",
    context_window: int = 0,
    client: str = "",
    languages: str = "",
    frameworks: str = "",
    platform: str = "",
    project_goal: str = "",
) -> str:
    """Personalized agent onboarding. Declare your environment and get optimal config.

    Call this FIRST when connecting to MidOS. Pass as much info as you know.
    Unknown fields can be left empty -- you'll get sensible defaults.

    Args:
        model: Your model ID (e.g. 'claude-opus-4-6', 'gemini-2.5-pro', 'opus')
        context_window: Your context window in tokens (e.g. 200000). 0 = auto-detect from model.
        client: Your CLI/IDE (e.g. 'claude-code', 'cursor', 'windsurf', 'cline')
        languages: Comma-separated languages (e.g. 'python,typescript')
        frameworks: Comma-separated frameworks (e.g. 'fastapi,react')
        platform: Your OS (e.g. 'windows', 'linux', 'macos')
        project_goal: What you're working on (e.g. 'manga engine with SVG rendering')
    """
    from .agent_profiles import AgentProfile
    from .handshake_engine import generate_config, format_config

    profile = AgentProfile(
        model=model,
        context_window=context_window,
        client=client,
        languages=[l.strip() for l in languages.split(",") if l.strip()],
        frameworks=[f.strip() for f in frameworks.split(",") if f.strip()],
        platform=platform,
        project_goal=project_goal,
    )
    config = generate_config(profile)
    return format_config(config, profile)


@mcp.tool
async def project_status() -> str:
    """Live MidOS system status + quick-start guide for your agent.

    Call this anytime to get:
    - Real-time knowledge base stats (chunks, skills, EUREKA, truth patches)
    - Vector store health
    - Available MCP tools with usage examples
    - Research queue (pending topics)
    - Tips to get the most out of MidOS

    This is your /status command. Use it to orient yourself and teach your agent how to leverage MidOS.
    """
    lines = ["# MidOS Status Dashboard", ""]

    # --- 1. Knowledge stats (live from filesystem) ---
    kb = MIDOS_ROOT / "knowledge"
    chunks_dir = kb / "chunks"
    eureka_dir = kb / "EUREKA"
    truth_dir = kb / "truth"
    skills_root = MIDOS_ROOT / "skills"
    staging_dir = kb / "staging"

    n_chunks = len(list(chunks_dir.glob("*.md"))) if chunks_dir.exists() else 0
    n_eureka = len(list(eureka_dir.glob("*.md"))) if eureka_dir.exists() else 0
    n_truth = len(list(truth_dir.glob("*.md"))) if truth_dir.exists() else 0
    n_skills = len([d for d in skills_root.iterdir() if d.is_dir() and (d / "SKILL.md").exists()]) if skills_root.exists() else 0
    n_staging = len(list(staging_dir.iterdir())) if staging_dir.exists() else 0

    # Vector store
    vec_status = "offline"
    vec_count = 0
    if HIVE_COMMONS_AVAILABLE:
        try:
            stats = get_memory_stats()
            vec_status = stats.get("status", "unknown")
            vec_count = stats.get("total_chunks", 0)
        except Exception:
            vec_status = "error"

    lines.append("## Knowledge Base (live)")
    lines.append("")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Chunks (L1) | {n_chunks} |")
    lines.append(f"| Skills (L2) | {n_skills} |")
    lines.append(f"| Truth Patches (L3) | {n_truth} |")
    lines.append(f"| EUREKA (L4) | {n_eureka} |")
    lines.append(f"| Staging queue | {n_staging} |")
    lines.append(f"| Vector store | {vec_status} ({vec_count:,} vectors) |")
    lines.append("")

    # --- 2. Recent knowledge (last 5 chunks by mtime) ---
    if chunks_dir.exists():
        recent = sorted(chunks_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)[:5]
        if recent:
            lines.append("## Recent Knowledge")
            lines.append("")
            for f in recent:
                lines.append(f"- `{f.name}`")
            lines.append("")

    # --- 3. Research queue ---
    rq = kb / "RESEARCH_INTEREST_QUEUE.md"
    if rq.exists():
        try:
            content = rq.read_text(encoding="utf-8", errors="ignore")
            # Extract PENDING section
            pending = []
            in_pending = False
            for line in content.split("\n"):
                if "## PENDING" in line:
                    in_pending = True
                    continue
                if in_pending and line.startswith("## "):
                    break
                if in_pending and line.startswith("| ") and not line.startswith("| #") and not line.startswith("|--"):
                    parts = [p.strip() for p in line.split("|")[1:-1]]
                    if len(parts) >= 3:
                        pending.append(f"- [{parts[2]}] {parts[1]}")
            if pending:
                lines.append("## Research Queue")
                lines.append("")
                for p in pending:
                    lines.append(p)
                lines.append("")
        except Exception:
            pass

    # --- 4. Available tools ---
    lines.append("## MCP Tools (use these!)")
    lines.append("")
    tools_guide = [
        ("search_knowledge", "query", "Keyword search across all knowledge layers"),
        ("semantic_search", "query, top_k, stack", "Vector search (smarter). Filter by stack: 'python,react'"),
        ("get_skill", "name", "Fetch a complete skill document"),
        ("list_skills", "filter, stack", "Browse all skills. Filter by stack"),
        ("agent_handshake", "model, client, languages, ...", "Personalized onboarding — call FIRST to get config tailored to your agent"),
        ("project_status", "", "This dashboard — call anytime for live stats"),
        ("episodic_search", "query", "Search past agent experiences"),
        ("episodic_store", "task_type, input_preview, success", "Store learnings for future agents"),
        ("chunk_code", "file_path", "Parse code into semantic chunks for RAG"),
        ("research_youtube", "url", "Queue a video for research + transcription"),
    ]
    for name, args, desc in tools_guide:
        lines.append(f"- **{name}**({args}) — {desc}")
    lines.append("")

    # --- 5. Quick-start boot sequence ---
    lines.append("## Quick-Start (teach your agent)")
    lines.append("")
    lines.append("```")
    lines.append("1. agent_handshake(model, client, languages, project_goal)")
    lines.append("   → Get personalized config for YOUR agent")
    lines.append("")
    lines.append("2. semantic_search('your topic')")
    lines.append("   → Check if MidOS already knows about it")
    lines.append("")
    lines.append("3. list_skills(stack='python,react')")
    lines.append("   → Find reusable skills for your stack")
    lines.append("")
    lines.append("4. episodic_store(task_type, input_preview, success)")
    lines.append("   → Share what you learned back to MidOS")
    lines.append("```")
    lines.append("")

    # --- 6. Pro tips ---
    lines.append("## Pro Tips")
    lines.append("")
    lines.append("- **Always search before building** — MidOS has 32K+ knowledge chunks")
    lines.append("- **Use stack filters** — `semantic_search('caching', stack='python')` is way more relevant")
    lines.append("- **Store your learnings** — `episodic_store` feeds the knowledge loop for ALL agents")
    lines.append("- **EUREKA = gold** — search for EUREKA atoms for battle-tested improvements with ROI data")
    lines.append("- **Handshake once per session** — `agent_handshake` optimizes everything for your context window")
    lines.append("")
    lines.append(f"---")
    lines.append(f"*MidOS v2026 | {datetime.now().strftime('%Y-%m-%d %H:%M')} | {vec_count:,} vectors | {n_chunks} chunks | {n_eureka} EUREKA*")

    return "\n".join(lines)


@mcp.tool
async def agent_bootstrap() -> str:
    """[DEPRECATED -- use agent_handshake instead] Generic agent onboarding. Returns default config for unknown agents."""
    return await agent_handshake()


# ============================================================================
# RESOURCES
# ============================================================================

@mcp.resource("midos://skill/{skill_name}")
async def read_skill_resource(skill_name: str) -> str:
    """Read a skill resource by name.

    Security: validates path traversal and enforces tier gating.
    Free/community tier gets truncated preview (400 chars).
    """
    import re

    # Path traversal protection: strip dangerous characters
    safe_name = re.sub(r"[^\w\-]", "", skill_name)
    if not safe_name or safe_name != skill_name:
        return f"Invalid skill name: {skill_name}"

    skill_path = SKILLS_DIR / f"{safe_name}.md"
    if not skill_path.exists():
        for f in SKILLS_DIR.glob("*.md"):
            if f.stem.lower() == safe_name.lower():
                skill_path = f
                break

    if not skill_path.exists():
        return f"Skill not found: {skill_name}"

    # Verify resolved path is inside SKILLS_DIR (defense in depth)
    resolved = skill_path.resolve()
    if not resolved.is_relative_to(SKILLS_DIR.resolve()):
        return "Access denied: path traversal detected"

    content = get_file_content(skill_path)

    # Tier gating for resources: community tier gets truncated preview
    try:
        from fastmcp.server.dependencies import get_http_headers
        headers = get_http_headers(include_all=True)
        auth_header = headers.get("authorization", "")
        has_valid_key = auth_header.startswith("Bearer midos_sk_")
    except Exception:
        has_valid_key = False

    if not has_valid_key:
        # Truncate for community tier
        preview_limit = 400
        if len(content) > preview_limit:
            truncated = content[:preview_limit].rsplit("\n", 1)[0]
            content = (
                f"{truncated}\n\n"
                f"---\n"
                f"> Full skill content available with MidOS Pro.\n"
                f"> Get your API key at https://midos.dev/pricing"
            )

    return content


# ============================================================================
# HEALTH ENDPOINTS (custom HTTP routes, not MCP tools)
# ============================================================================

@mcp.custom_route("/health", methods=["GET"])
async def health_liveness(request):
    """Liveness probe — is the server process alive?"""
    from starlette.responses import JSONResponse

    return JSONResponse({
        "status": "ok",
        "server": "midos",
        "uptime_seconds": round(time.time() - _SERVER_START_TIME, 1),
        "timestamp": datetime.utcnow().isoformat() + "Z",
    })


@mcp.custom_route("/health/ready", methods=["GET"])
async def health_readiness(request):
    """Readiness probe — are all dependencies functional?"""
    from starlette.responses import JSONResponse

    checks = {}

    # Check knowledge directory
    try:
        chunk_count = len(list(KNOWLEDGE_DIR.glob("chunks/**/*.md")))
        checks["knowledge"] = {"status": "up", "chunks": chunk_count}
    except Exception as e:
        checks["knowledge"] = {"status": "down", "error": str(e)}

    # Check vector store
    if HIVE_COMMONS_AVAILABLE:
        try:
            stats = get_memory_stats()
            checks["vector_store"] = {
                "status": "up",
                "engine": stats.get("engine", "unknown"),
                "total_chunks": stats.get("total_chunks", 0),
            }
        except Exception as e:
            checks["vector_store"] = {"status": "down", "error": str(e)}
    else:
        checks["vector_store"] = {"status": "unavailable", "reason": "hive_commons not installed"}

    # Check skills directory
    try:
        skill_count = len(list((KNOWLEDGE_DIR / "skills").glob("**/*.md")))
        checks["skills"] = {"status": "up", "count": skill_count}
    except Exception:
        checks["skills"] = {"status": "down"}

    all_up = all(c.get("status") == "up" for c in checks.values())
    status_code = 200 if all_up else 503

    return JSONResponse(
        {
            "status": "ready" if all_up else "degraded",
            "server": "midos",
            "uptime_seconds": round(time.time() - _SERVER_START_TIME, 1),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "checks": checks,
        },
        status_code=status_code,
    )


# ============================================================================
# ENTRY POINT
# ============================================================================

def main():
    """Entry point with dual transport support."""
    import argparse

    parser = argparse.ArgumentParser(description="MidOS MCP Server")
    parser.add_argument("--http", action="store_true", help="HTTP mode (streamable)")
    parser.add_argument("--host", default="0.0.0.0", help="HTTP host (default: 0.0.0.0)")
    parser.add_argument("--port", type=int, default=8419, help="HTTP port (default: 8419)")
    args = parser.parse_args()

    print(f"Starting Midos MCP Server (FastMCP)...")
    print(f"Knowledge dir: {KNOWLEDGE_DIR}")
    if SKILLS_DIR.exists():
        print(f"Skills: {len(list(SKILLS_DIR.glob('*.md')))} files")
    if PROTOCOLS_DIR.exists():
        print(f"Protocols: {len(list(PROTOCOLS_DIR.glob('*.md')))} files")

    if args.http:
        print(f"Transport: streamable-http on {args.host}:{args.port}")
        mcp.run(transport="streamable-http", host=args.host, port=args.port, stateless_http=True)
    else:
        print("Transport: stdio")
        mcp.run()


if __name__ == "__main__":
    main()
