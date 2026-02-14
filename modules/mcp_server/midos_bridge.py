"""
MIDOS BRIDGE - Consulta Directa a la Biblioteca L1
====================================================
Este script permite que CUALQUIER proyecto consulte la knowledge base de MidOS
sin necesidad de abrir otra sesion de Claude Code.

USO DESDE CUALQUIER PROYECTO:
    python D:/Proyectos/1midos/modules/mcp_server/midos_bridge.py ask "como implementar cache semantico?"
    python D:/Proyectos/1midos/modules/mcp_server/midos_bridge.py search "vector store"
    python D:/Proyectos/1midos/modules/mcp_server/midos_bridge.py skills
    python D:/Proyectos/1midos/modules/mcp_server/midos_bridge.py submit "investigar patron X"

USO COMO MCP SERVER (para Claude Code de otros proyectos):
    Agregar a .claude/settings.local.json del proyecto cliente:
    {
      "mcpServers": {
        "midos": {
          "command": "python",
          "args": ["D:/Proyectos/1midos/modules/mcp_server/midos_bridge.py", "--mcp"]
        }
      }
    }
"""

import sys
import json
import os
from pathlib import Path
from datetime import datetime

# Paths hardcoded - MidOS siempre vive aqui
MIDOS_ROOT = Path("D:/Proyectos/1midos")
KNOWLEDGE = MIDOS_ROOT / "knowledge"
EUREKA = KNOWLEDGE / "EUREKA"
RESEARCH = KNOWLEDGE / "research"
SKILLS = MIDOS_ROOT / "skills"
SYNAPSE = MIDOS_ROOT / "synapse"
TOPOLOGY = KNOWLEDGE / "topology"


def search_knowledge(query: str, max_results: int = 5) -> list[dict]:
    """Buscar en toda la knowledge base de MidOS."""
    results = []
    query_lower = query.lower()
    query_words = query_lower.split()

    for md_file in KNOWLEDGE.rglob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            content_lower = content.lower()
            name_lower = md_file.name.lower()

            # Score: cuantas palabras del query aparecen
            score = sum(1 for w in query_words if w in content_lower or w in name_lower)
            if score == 0:
                continue

            # Bonus por nombre de archivo match
            if any(w in name_lower for w in query_words):
                score += 2

            # Bonus por EUREKA
            if "EUREKA" in str(md_file):
                score += 1

            rel_path = md_file.relative_to(MIDOS_ROOT)
            preview = content[:300].replace("\n", " ").strip()

            results.append({
                "path": str(rel_path),
                "score": score,
                "preview": preview,
                "size": len(content)
            })
        except OSError:
            continue

    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:max_results]


def search_eureka(query: str) -> list[dict]:
    """Buscar solo en EUREKA (conocimiento validado)."""
    results = []
    query_lower = query.lower()

    query_words = query_lower.split()
    for md_file in EUREKA.glob("*.md"):
        try:
            content = md_file.read_text(encoding="utf-8", errors="replace")
            content_low = content.lower()
            name_low = md_file.name.lower()
            if any(w in content_low or w in name_low for w in query_words):
                results.append({
                    "file": md_file.name,
                    "preview": content[:400].replace("\n", " ").strip()
                })
        except OSError:
            continue

    return results


def list_skills() -> list[str]:
    """Listar skills disponibles en MidOS."""
    if not SKILLS.exists():
        return []
    return [f.name for f in SKILLS.iterdir() if f.is_file() or f.is_dir()]


def get_skill(name: str) -> str:
    """Obtener contenido de un skill especifico."""
    skill_path = SKILLS / name
    if skill_path.is_file():
        return skill_path.read_text(encoding="utf-8", errors="replace")

    # Buscar como directorio
    if skill_path.is_dir():
        readme = skill_path / "README.md"
        if readme.exists():
            return readme.read_text(encoding="utf-8", errors="replace")
        # Listar contenido
        files = [f.name for f in skill_path.iterdir()]
        return f"Skill directory: {name}\nFiles: {', '.join(files)}"

    return f"Skill '{name}' not found."


def get_topology() -> str:
    """Obtener el mapa del sistema."""
    topo_file = TOPOLOGY / "structure_map.md"
    if topo_file.exists():
        return topo_file.read_text(encoding="utf-8", errors="replace")
    return "Topology file not found."


def build_bootstrap_payload() -> str:
    """
    Build the structured onboarding payload for agents connecting to MidOS.
    Every line is actionable. No decoration.
    """
    # --- Skills inventory ---
    skills_list = []
    if SKILLS.exists():
        for d in sorted(SKILLS.iterdir()):
            if d.is_dir():
                skills_list.append(d.name)

    # --- Knowledge stats ---
    knowledge_count = 0
    eureka_count = 0
    if KNOWLEDGE.exists():
        knowledge_count = sum(1 for _ in KNOWLEDGE.rglob("*.md"))
    if EUREKA.exists():
        eureka_count = sum(1 for _ in EUREKA.glob("*.md"))

    skills_block = "\n".join(f"  - {s}" for s in skills_list) if skills_list else "  (none found)"

    payload = f"""# MidOS Agent Bootstrap

## Identity

- **Name**: MidOS (L1) — Scientific Library & Research Engine
- **Root**: {MIDOS_ROOT}
- **Role**: Knowledge vault, research execution, tool orchestration
- **Hierarchy**: MidOS (Core) → Project Agents → Client Projects
- **Philosophy**: Noble use of resources. Every token must be substantive and actionable.

## Architecture (Key Directories)

| Directory | Purpose |
|---|---|
| `knowledge/` | 5-layer knowledge pipeline: staging → chunks → skills → truth → EUREKA → SOTA |
| `knowledge/EUREKA/` | Validated empirical findings ({eureka_count} items) |
| `skills/` | {len(skills_list)} executable agent skills |
| `tools/` | Research & ingestion tools (video, discord, web, reddit) |
| `modules/mcp_server/` | MCP servers + bridge for external projects |
| `synapse/` | L0↔L1 communication channel |
| `hive_commons/` | Shared library (vector store, config) |
| `docs/` | TOOLS_INDEX.md, AGENT_GUARDRAILS.md, BOOTSTRAP_GUIDE.md |

## Available MCP Tools

| Tool | What it does |
|---|---|
| `midos_ask` | Search knowledge + EUREKA combined (best for questions) |
| `midos_search` | Keyword search across all knowledge ({knowledge_count} markdown files) |
| `midos_eureka` | Search only EUREKA-validated knowledge (high confidence) |
| `midos_skills` | List all {len(skills_list)} available skills |
| `midos_topology` | Get system architecture map |
| `midos_submit` | Submit async task to MidOS inbox for processing |
| `midos_bootstrap` | This tool — structured onboarding |

## Skills ({len(skills_list)})

{skills_block}

## Guardrails (Mandatory)

1. **Windows/PowerShell**: Use `;` not `&&` to chain commands. Use `python -c` as universal fallback.
2. **Polling**: Max 10s between command status checks. Never wait 60s passively.
3. **Secrets**: Never hardcode API keys. Use `os.getenv()` + `.env` files.
4. **Index Primacy**: Check `docs/TOOLS_INDEX.md` before creating tools. Check `knowledge/` before creating knowledge.
5. **No Duplication**: Synthesize into existing sources, never scatter.

## Quick Start

```bash
# Search for existing knowledge before implementing anything
python {MIDOS_ROOT}/modules/mcp_server/midos_bridge.py ask "your question"

# Find validated patterns
python {MIDOS_ROOT}/modules/mcp_server/midos_bridge.py eureka "topic"

# List available skills
python {MIDOS_ROOT}/modules/mcp_server/midos_bridge.py skills

# Submit research task to MidOS
python {MIDOS_ROOT}/modules/mcp_server/midos_bridge.py submit "research topic X"
```

---
_MidOS Bootstrap v2026.2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}_
"""
    return payload.strip()


def submit_task(prompt: str, source: str = "BRIDGE") -> str:
    """Enviar tarea al inbox de MidOS para procesamiento asincrono."""
    task_id = f"CMD_{source}_{int(datetime.now().timestamp())}"
    payload = {
        "id": task_id,
        "source": source,
        "prompt": prompt,
        "timestamp": datetime.now().isoformat()
    }

    inbox_dir = SYNAPSE / "inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)
    (inbox_dir / f"{task_id}.json").write_text(
        json.dumps(payload, indent=2), encoding="utf-8"
    )
    return f"Task {task_id} submitted. Status: QUEUED."


def ask(question: str) -> dict:
    """Pregunta completa: busca en knowledge + eureka + topology."""
    knowledge_results = search_knowledge(question, max_results=3)
    eureka_results = search_eureka(question)

    return {
        "question": question,
        "knowledge": knowledge_results,
        "eureka": eureka_results[:2],
        "total_matches": len(knowledge_results) + len(eureka_results),
        "hint": "Use search_knowledge() for broader results or search_eureka() for validated findings."
    }


# ─── CLI MODE ───────────────────────────────────────────────

def print_json(data):
    sys.stdout.reconfigure(encoding="utf-8")
    print(json.dumps(data, indent=2, ensure_ascii=False, default=str))


def cli_main():
    sys.stdout.reconfigure(encoding="utf-8")
    if len(sys.argv) < 2:
        print("""
MIDOS BRIDGE - Consulta la Biblioteca L1
=========================================
Comandos:
  ask <pregunta>     Buscar en toda la base (knowledge + eureka)
  search <query>     Buscar en knowledge base
  eureka <query>     Buscar solo en EUREKA (validado)
  skills             Listar skills disponibles
  skill <nombre>     Ver un skill especifico
  topology           Ver mapa del sistema
  submit <tarea>     Enviar tarea al inbox
  bootstrap          Onboarding completo para agentes (identidad, tools, skills, guardrails)

Ejemplo:
  python midos_bridge.py ask "como implementar cache semantico?"
  python midos_bridge.py search "vector store"
  python midos_bridge.py submit "investigar patron de retry con backoff"
  python midos_bridge.py bootstrap
        """)
        return

    cmd = sys.argv[1].lower()

    if cmd == "ask" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        print_json(ask(query))

    elif cmd == "search" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        print_json(search_knowledge(query))

    elif cmd == "eureka" and len(sys.argv) > 2:
        query = " ".join(sys.argv[2:])
        print_json(search_eureka(query))

    elif cmd == "skills":
        print_json(list_skills())

    elif cmd == "skill" and len(sys.argv) > 2:
        print(get_skill(sys.argv[2]))

    elif cmd == "topology":
        print(get_topology())

    elif cmd == "submit" and len(sys.argv) > 2:
        prompt = " ".join(sys.argv[2:])
        print(submit_task(prompt))

    elif cmd == "bootstrap":
        print(build_bootstrap_payload())

    elif cmd == "--mcp":
        run_mcp_server()

    else:
        print(f"Comando no reconocido: {cmd}")
        print("Usa 'python midos_bridge.py' sin argumentos para ver ayuda.")


# ─── MCP SERVER MODE ────────────────────────────────────────

def run_mcp_server():
    """Ejecutar como MCP server (stdio) para Claude Code de otros proyectos."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        print("Error: pip install mcp[cli] required", file=sys.stderr)
        sys.exit(1)

    server = FastMCP("midos-library", version="1.0.0")

    @server.tool()
    def midos_ask(question: str) -> str:
        """Ask MidOS knowledge base a question. Returns matches from knowledge + EUREKA."""
        result = ask(question)
        lines = [f"# MidOS Answer: '{question}'", f"Matches: {result['total_matches']}", ""]
        for k in result["knowledge"]:
            lines.append(f"## {k['path']} (score: {k['score']})")
            lines.append(k["preview"])
            lines.append("")
        if result["eureka"]:
            lines.append("## EUREKA (Validated)")
            for e in result["eureka"]:
                lines.append(f"### {e['file']}")
                lines.append(e["preview"])
                lines.append("")
        return "\n".join(lines)

    @server.tool()
    def midos_search(query: str, max_results: int = 5) -> str:
        """Search MidOS knowledge base for a topic. Returns ranked results."""
        results = search_knowledge(query, max_results)
        if not results:
            return f"No results for '{query}'"
        lines = [f"# MidOS Search: '{query}'", ""]
        for r in results:
            lines.append(f"**{r['path']}** (score: {r['score']}, {r['size']} chars)")
            lines.append(r["preview"][:200])
            lines.append("")
        return "\n".join(lines)

    @server.tool()
    def midos_eureka(query: str) -> str:
        """Search only EUREKA validated knowledge (high-quality findings)."""
        results = search_eureka(query)
        if not results:
            return f"No EUREKA matches for '{query}'"
        lines = [f"# EUREKA Search: '{query}'", ""]
        for r in results:
            lines.append(f"## {r['file']}")
            lines.append(r["preview"])
            lines.append("")
        return "\n".join(lines)

    @server.tool()
    def midos_submit(task: str, source: str = "external_project") -> str:
        """Submit a task to MidOS inbox for async processing."""
        return submit_task(task, source)

    @server.tool()
    def midos_skills() -> str:
        """List all available MidOS skills."""
        skills = list_skills()
        return "Available skills:\n" + "\n".join(f"- {s}" for s in skills)

    @server.tool()
    def midos_topology() -> str:
        """Get the MidOS system architecture map."""
        return get_topology()

    @server.tool()
    def midos_bootstrap() -> str:
        """Agent onboarding. Returns identity, architecture, available tools, skills, guardrails, and quick-start commands. Call this FIRST when connecting to MidOS."""
        return build_bootstrap_payload()

    server.run()


if __name__ == "__main__":
    cli_main()
