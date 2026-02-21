<p align="center">
  <h1 align="center">MidOS — MCP Server for Developer Knowledge</h1>
  <p align="center">Curated, validated knowledge for AI coding agents. Not raw docs — battle-tested patterns.</p>
</p>

<p align="center">
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-Compatible-blue?style=flat-square" alt="MCP Compatible"></a>
  <a href="https://claude.ai"><img src="https://img.shields.io/badge/Claude_Code-Ready-D79943?style=flat-square" alt="Claude Code"></a>
  <a href="https://cursor.com"><img src="https://img.shields.io/badge/Cursor-Ready-4B8BBE?style=flat-square" alt="Cursor"></a>
  <a href="https://github.com/cline/cline"><img src="https://img.shields.io/badge/Cline-Ready-green?style=flat-square" alt="Cline"></a>
  <a href="https://github.com/nicepkg/aide"><img src="https://img.shields.io/badge/Windsurf-Ready-purple?style=flat-square" alt="Windsurf"></a>
  <br>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-green?style=flat-square" alt="MIT License"></a>
  <a href="https://github.com/MidOSresearch/midos-mcp/stargazers"><img src="https://img.shields.io/github/stars/MidOSresearch/midos-mcp?style=social" alt="GitHub stars"></a>
  <a href="https://smithery.ai"><img src="https://img.shields.io/badge/Smithery-Listed-orange?style=flat-square" alt="Smithery"></a>
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python&logoColor=white" alt="Python 3.10+"></a>
</p>

---

**104 skill packs** across 20+ tech stacks. **1,284 curated chunks**. **104 validated discoveries**. Every piece reviewed, cross-validated, and myth-busted.

```
Your agent asks: "How do I implement optimistic updates in React 19?"
MidOS returns: Battle-tested pattern with useOptimistic + Server Actions, validated Feb 2026.
Context7 returns: Raw React docs from reactjs.org.
```

## Quick Start

**One line.** Add to your MCP config and start querying:

<details>
<summary><b>Claude Code</b> — <code>.mcp.json</code> or <code>~/.claude/settings.json</code></summary>

```json
{
  "mcpServers": {
    "midos": {
      "url": "https://midos.dev/mcp"
    }
  }
}
```
</details>

<details>
<summary><b>Cursor / Windsurf</b> — MCP Settings</summary>

Add a new server:
- **Name**: `midos`
- **URL**: `https://midos.dev/mcp`
- **Transport**: Streamable HTTP
</details>

<details>
<summary><b>Cline</b> — MCP Settings</summary>

```json
{
  "mcpServers": {
    "midos": {
      "url": "https://midos.dev/mcp",
      "transportType": "streamable-http"
    }
  }
}
```
</details>

<details>
<summary><b>Self-hosted</b> — Run locally</summary>

```bash
git clone https://github.com/MidOSresearch/midos-mcp.git
cd midos-mcp
pip install -e .
pip install -e hive_commons/
python -m modules.mcp_server.midos_mcp --http --port 8419
```

Then point your MCP client to `http://localhost:8419/mcp`.
</details>

### First Tool Call

After connecting, personalize your experience:

```
agent_handshake(model="claude-opus-4-6", client="claude-code", languages="python,typescript", frameworks="fastapi,react")
```

Then search for what you need:

```
search_knowledge("React 19 Server Components patterns")
```

## Tools Reference

### Community Tier (free, no API key)

| Tool | Description | Example |
|------|-------------|---------|
| `search_knowledge` | Search 1,284 curated chunks across all stacks | `search_knowledge("FastAPI dependency injection")` |
| `hybrid_search` | Combined keyword + semantic search with reranking | `hybrid_search("PostgreSQL JSONB indexing")` |
| `list_skills` | Browse 104 skill packs by technology | `list_skills(stack="react")` |
| `get_skill` | Get a specific skill pack (preview in free, full in Dev) | `get_skill("nextjs")` |
| `get_protocol` | Protocol and pattern documentation | `get_protocol("domain-driven-design")` |
| `hive_status` | System health and live statistics | `hive_status()` |
| `project_status` | Knowledge pipeline dashboard | `project_status()` |
| `agent_handshake` | Personalized onboarding for your model + stack | See example above |

### Dev Tier ($19/mo — full content + advanced search)

| Tool | Description | Example |
|------|-------------|---------|
| `get_eureka` | Validated breakthrough discoveries (104 items) | `get_eureka("response-cache")` |
| `get_truth` | Empirically verified truth patches (17 items) | `get_truth("qlora-myths")` |
| `semantic_search` | Vector search with Gemini embeddings (3072-d) | `semantic_search("event sourcing CQRS")` |
| `research_youtube` | Extract knowledge from video content | `research_youtube("https://youtube.com/...")` |
| `chunk_code` | Intelligent code chunking for ingestion | `chunk_code(code="...", language="python")` |
| `memory_stats` | Vector store analytics and health | `memory_stats()` |
| `episodic_search` | Search agent session history | `episodic_search("last deployment issue")` |

### Ops Tier (custom — security, infrastructure, advanced ops)

Contact for specialized knowledge packs. [midos.dev/pricing](https://midos.dev/pricing)

## Skill Packs (104 and growing)

Production-tested patterns for:

**Frontend**: React 19, Next.js 16, Angular 21, Svelte 5, Tailwind CSS v4, Remix v2

**Backend**: FastAPI, Django 5, NestJS 11, Laravel 12, Spring Boot, Symfony 8

**Languages**: TypeScript, Go, Rust, Python

**Data**: PostgreSQL, Redis, MongoDB, Elasticsearch, LanceDB, Drizzle ORM, Prisma 7

**Infrastructure**: Kubernetes, Terraform, Docker, GitHub Actions

**AI/ML**: LoRA/QLoRA, MCP patterns, multi-agent orchestration, Vercel AI SDK

**Testing**: Playwright, Vitest

**Architecture**: DDD, GraphQL, event-driven, microservices, spec-driven dev

## How MidOS is Different

| | Raw Docs (Context7, etc.) | MidOS |
|---|---|---|
| **Content** | Documentation dumps | Curated, human-reviewed, cross-validated |
| **Quality** | No validation | 5-layer pipeline: chunks → truth → EUREKA → SOTA |
| **Search** | Keyword matching | Semantic + hybrid search (Gemini embeddings, 3072-d) |
| **Onboarding** | Generic | Personalized per model + CLI + stack |
| **Format** | Raw text | Stack-specific skill packs with production patterns |
| **Accuracy** | Stale docs | Myth-busted with empirical evidence |

## Knowledge Pipeline

```
staging/ → chunks/ → skills/ → truth/ → EUREKA/ → SOTA/
 (entry)    (L1)      (L2)      (L3)     (L4)      (L5)
```

- **Chunks** (1,284): Curated, indexed knowledge across 20+ stacks
- **Skills** (104): Organized, actionable, versioned by stack
- **Truth** (17): Verified with empirical evidence
- **EUREKA** (104): Validated improvements with measured ROI
- **SOTA** (11): Best-in-class, currently unimprovable

## Using an API Key

Pass your key via the `Authorization` header for Dev/Ops access:

```json
{
  "mcpServers": {
    "midos": {
      "url": "https://midos.dev/mcp",
      "headers": {
        "Authorization": "Bearer midos_your_key_here"
      }
    }
  }
}
```

Get a key at [midos.dev/pricing](https://midos.dev/pricing).

## Architecture

```
midos-mcp/
├── modules/mcp_server/   FastMCP server (streamable-http)
├── knowledge/
│   ├── chunks/            Curated knowledge (L1) — 1,284 items
│   ├── skills/            Stack-specific skill packs (L2) — 104 items
│   ├── EUREKA/            Validated discoveries (L4) — 104 items
│   └── truth/             Empirical patches (L3) — 17 items
├── hive_commons/          Shared library (LanceDB vector store, config)
├── smithery.yaml          Smithery marketplace manifest
├── Dockerfile             Production container
└── pyproject.toml         Dependencies and build config
```

## Tech Stack

- **Server**: [FastMCP](https://github.com/jlowin/fastmcp) 2.x (streamable-http transport)
- **Vectors**: [LanceDB](https://lancedb.com) + Gemini embeddings (22,900+ vectors, 3072-d)
- **Auth**: 3-tier API key middleware (community → dev → ops) with rate limiting
- **Pipeline**: 5-layer quality validation with myth-busting
- **Deploy**: Docker + Coolify (auto-deploy on push)

## Contributing

MidOS is community-first. If you have production-tested patterns, battle scars, or discovered that a popular claim is false — we want it.

1. Search existing knowledge first: `search_knowledge("your topic")`
2. [Open an issue](https://github.com/MidOSresearch/midos-mcp/issues/new) describing the pattern or discovery
3. We'll review and add it to the pipeline

## License

[MIT](LICENSE)

---

<p align="center">
  Source-verified developer knowledge. Built by devs, for agents.
  <br>
  <a href="https://midos.dev">midos.dev</a> · <a href="https://github.com/MidOSresearch/midos-mcp/discussions">Discussions</a> · <a href="https://github.com/MidOSresearch/midos-mcp/issues">Issues</a>
</p>
