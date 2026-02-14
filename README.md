# MidOS — Curated Knowledge API for AI Agents

> **14,900+ vectors | 78 skills | 55 source-verified discoveries | 18 MCP tools**

MidOS is a curated developer knowledge base exposed as an MCP server. Not raw docs — battle-tested patterns, validated discoveries, and semantic search. Plug into Claude Desktop, Cursor, Cline, or any MCP client.

## Why MidOS?

| Feature | Raw Docs (Context7, etc.) | MidOS |
|---------|---------------------------|-------|
| Content | Auto-scraped documentation | Curated, human-reviewed knowledge |
| Quality | No validation | 5-layer pipeline: chunks > truth > verified > SOTA |
| Search | Keyword matching | Semantic search (Gemini embeddings, 3072-d) |
| Onboarding | Generic | Personalized agent handshake |
| Format | Raw text | Stack-specific skill packs |

## Quick Start

### 1. Add to your MCP client config

```json
{
  "mcpServers": {
    "midos": {
      "url": "https://midos.dev/mcp",
      "transport": "streamable-http"
    }
  }
}
```

### 2. Or run locally

```bash
git clone https://github.com/MidOSresearch/midos-mcp.git
cd MidOS
pip install -e hive_commons/
python -m modules.mcp_server.midos_mcp --http --port 8419
```

### 3. Query

```bash
# Free — no API key needed
curl -X POST http://localhost:8419/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"search_knowledge","arguments":{"query":"react 19 hooks"}}}'

# Premium — with API key
curl -X POST http://localhost:8419/mcp \
  -H "Authorization: Bearer midos_sk_YOUR_KEY" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json, text/event-stream" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"semantic_search","arguments":{"query":"MCP authentication patterns","top_k":5}}}'
```

## Tools (18 total)

### Free Tier (7 tools, 100 queries/mo)

| Tool | Description |
|------|-------------|
| `search_knowledge` | Keyword search across all knowledge |
| `list_skills` | Browse 78 skills by stack |
| `hive_status` | System health and stats |
| `project_status` | Knowledge pipeline status |
| `pool_status` | Agent coordination status |
| `get_eureka` | Get a EUREKA breakthrough document by name |
| `get_truth` | Get a truth patch document by name |

### Premium (11 additional tools)

| Tool | Description |
|------|-------------|
| `semantic_search` | Vector search with Gemini embeddings |
| `agent_handshake` | Personalized onboarding per agent |
| `get_skill` | Full skill content with code |
| `get_protocol` | Protocol and pattern docs |
| `memory_stats` | Vector store analytics |
| `episodic_search` | Search agent session history |
| `episodic_store` | Store agent learnings |
| `chunk_code` | Intelligent code chunking |
| `pool_signal` | Multi-agent coordination |
| `agent_bootstrap` | Full agent initialization |
| `research_youtube` | Video knowledge extraction |

## Knowledge Pipeline

```
staging/ > chunks/ > skills/ > truth/ > verified/ > SOTA/
 (entry)    (L1)      (L2)      (L3)     (L4)      (L5)
```

- **Chunks** (405): Raw, useful information
- **Skills** (78): Organized, actionable, versioned by stack
- **Truth** (31): Verified with empirical evidence
- **verified** (55): Demonstrable improvement with measured ROI
- **SOTA** (6): Best-in-class, currently unimprovable

## Pricing

| Tier | Price | Queries/mo | Tools |
|------|-------|------------|-------|
| Free | $0 | 100 | 7 basic |
| Dev | $9/mo | 5,000 | All 18 |
| Pro | $29/mo | 25,000 | All 18 + priority |
| Team | $79/mo | 100,000 | All 18 + 5 keys |

## Skill Packs

Pre-packaged knowledge bundles available on [Gumroad](https://midos.gumroad.com):

- **React 19 Complete Guide** ($9) — Migration, new APIs, production patterns
- **MCP Security Audit** ($12) — Tool poisoning defense, zero-trust, OAuth patterns
- More coming soon

## Architecture

```
MidOS/
├── knowledge/          5-layer pipeline (405 chunks, 78 skills, 55 verified)
├── modules/
│   ├── mcp_server/     FastMCP server (18 tools, streamable-http)
│   └── community_mcp/  Community server (FastAPI + Judge)
├── hive_commons/       Shared library (LanceDB vector store, config)
├── tools/              74 research and ingestion tools
├── hooks/              37 lifecycle modules (security, logging)
└── docs/               Full documentation
```

## API Key Management

```bash
# Generate a key
python -m modules.mcp_server.auth generate --name "my-app" --tier dev

# List keys
python -m modules.mcp_server.auth list

# Check usage
python -m modules.mcp_server.auth usage

# Revoke a key
python -m modules.mcp_server.auth revoke --key midos_sk_...
```

## Tech Stack

- **Server**: FastMCP 2.14.5 (streamable-http transport)
- **Vectors**: LanceDB + Gemini embeddings (14,900+ vectors, 3072-d)
- **Auth**: Custom middleware with tier-based rate limiting
- **Pipeline**: 5-layer quality validation (chunks > truth > verified > SOTA)

## License

MIT

---

Source-verified developer knowledge.
