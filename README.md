# MidOS — Curated Knowledge API for AI Agents

> **22,900+ vectors | 104 skills | 104 validated discoveries | 48 MCP tools | 20+ tech stacks**

MidOS is a curated developer knowledge base exposed as an MCP server. Not raw docs — battle-tested patterns, validated against papers, and myth-busted. Plug into Claude Code, Cursor, Cline, Gemini CLI, or any MCP client.

## Why MidOS?

| Feature | Raw Docs (Context7, etc.) | MidOS |
|---------|---------------------------|-------|
| Content | Raw documentation dumps | Curated, human-reviewed, cross-validated |
| Quality | No validation | 5-layer pipeline: chunks > truth > EUREKA > SOTA |
| Search | Keyword matching | Semantic + hybrid search (Gemini embeddings, 3072-d) |
| Onboarding | Generic | Personalized agent handshake per model + CLI + stack |
| Format | Raw text | Stack-specific skill packs with production patterns |
| Accuracy | Stale docs | Myth-busted (QLoRA, Next.js versions, Prisma Python) |

## Connect to MidOS

### Claude Code

Add to your project's `.mcp.json` or `~/.claude/settings.json`:

```json
{
  "mcpServers": {
    "midos": {
      "url": "https://midos.dev/mcp"
    }
  }
}
```

### Cursor / Windsurf / Cline

In your MCP settings, add a new server:

- **Name**: `midos`
- **URL**: `https://midos.dev/mcp`
- **Transport**: Streamable HTTP

### Run locally (alternative)

```bash
git clone https://github.com/MidOSresearch/midos-mcp.git
cd midos-mcp
pip install -e .
pip install -e hive_commons/
python -m modules.mcp_server.midos_mcp --http --port 8419
```

Then point your MCP client to `http://localhost:8419/mcp`.

### First thing to do

After connecting, call `agent_handshake` with your model and stack info. MidOS will personalize your experience:

```
agent_handshake(model="claude-opus-4-6", client="claude-code", languages="python,typescript", frameworks="fastapi,react")
```

## Tools by Tier

### Community (no API key, 100 queries/mo)

| Tool | What it does |
|------|--------------|
| `search_knowledge` | Search 1,200+ curated chunks across all stacks |
| `list_skills` | Browse 104 skills by technology |
| `get_skill` | Get skill content (400-char preview, full with Pro) |
| `get_protocol` | Get protocol and pattern documentation |
| `hive_status` | System health and live stats |
| `project_status` | Knowledge pipeline dashboard |
| `agent_handshake` | Personalized onboarding for your model + CLI + stack |
| `agent_bootstrap` | Quick onboarding (deprecated, use handshake) |

### Pro ($19/mo, 25,000 queries/mo)

Everything community, plus full content access:

| Tool | What it does |
|------|--------------|
| `get_eureka` | Validated breakthrough discoveries (104 items) |
| `get_truth` | Empirically verified truth patches (17 items) |
| `semantic_search` | Vector search with Gemini embeddings (3072-d) |
| `research_youtube` | Extract knowledge from video content |
| `chunk_code` | Intelligent code chunking for ingestion |
| `memory_stats` | Vector store analytics and health |
| `pool_status` | Multi-agent coordination status |
| `episodic_search` | Search agent session history |

### Team ($29/seat/mo, 100,000 queries/mo)

Everything pro, plus multi-seat access and team dashboards.

## Using an API Key

Pass your key via the `Authorization` header:

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

## Knowledge Pipeline

```
staging/ > chunks/ > skills/ > truth/ > EUREKA/ > SOTA/
 (entry)    (L1)      (L2)      (L3)     (L4)      (L5)
```

- **Chunks** (1,284): Curated, indexed knowledge across 20+ stacks
- **Skills** (104): Organized, actionable, versioned by stack
- **Truth** (17): Verified with empirical evidence
- **EUREKA** (104): Validated improvements with measured ROI
- **SOTA** (11): Best-in-class, currently unimprovable

## Skill Stacks

React 19, Next.js 16, Angular 21, Svelte 5, TypeScript, Tailwind CSS, FastAPI, Django 5, NestJS 11, Laravel 12, Spring Boot, Go, Rust, PostgreSQL, Redis, MongoDB, Elasticsearch, Kubernetes, Terraform, Docker, Playwright, Vitest, DDD, GraphQL, Prisma 7, Drizzle ORM, MercadoPago, WhisperX, LoRA/QLoRA, LanceDB, MCP patterns, AI agent security, multi-agent orchestration, and more.

## Architecture

```
midos-mcp/
├── modules/
│   └── mcp_server/     FastMCP server (streamable-http)
├── knowledge/
│   ├── chunks/          Curated knowledge (L1)
│   ├── skills/          Stack-specific skill packs (L2)
│   ├── EUREKA/          Validated discoveries — PRO (L4)
│   └── truth/           Empirical patches — PRO (L3)
├── hive_commons/        Shared library (LanceDB vector store, config)
├── smithery.yaml        Smithery marketplace manifest
├── Dockerfile           Production container
└── pyproject.toml       Dependencies and build config
```

## Tech Stack

- **Server**: FastMCP 2.x (streamable-http transport)
- **Vectors**: LanceDB + Gemini embeddings (22,900+ vectors, 3072-d)
- **Auth**: 4-tier API key middleware (free/dev/pro/team) with rate limiting
- **Pipeline**: 5-layer quality validation with myth-busting
- **Deploy**: Docker + Coolify (auto-deploy on push)
- **Compatible CLIs**: Claude Code, Cursor, Cline, Windsurf, Gemini CLI, OpenCode, Codex CLI

## Contributing

MidOS is community-first. If you have production-tested patterns, battle scars, or discovered that a popular claim is false — we want it.

1. Search existing knowledge first: `search_knowledge("your topic")`
2. Open an issue describing the pattern or discovery
3. We'll review and add it to the pipeline

## License

MIT

---

Source-verified developer knowledge. Built by devs, for agents.
