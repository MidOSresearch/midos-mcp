# MidOS MCP Server — Installation Guide

MidOS is a curated developer knowledge base exposed as an MCP server. It provides 104 skill packs, 1,284 curated knowledge chunks, and semantic search across 20+ tech stacks.

## Cloud (Recommended)

No installation required. Add to your MCP client config:

```json
{
  "mcpServers": {
    "midos": {
      "url": "https://midos.dev/mcp"
    }
  }
}
```

Works immediately with Claude Code, Cursor, Cline, Windsurf, and any MCP-compatible client.

## Self-Hosted

### Prerequisites

- Python 3.10+
- pip

### Installation

```bash
git clone https://github.com/MidOSresearch/midos-mcp.git
cd midos-mcp
pip install -e .
pip install -e hive_commons/
```

### Running

```bash
python -m modules.mcp_server.midos_mcp --http --port 8419
```

Then point your MCP client to `http://localhost:8419/mcp`.

### Docker

```bash
docker build -t midos-mcp .
docker run -p 8419:8419 midos-mcp
```

## Configuration

### API Key (optional)

For Dev/Ops tier access, pass your key via the Authorization header:

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

## First Steps

After connecting, call `agent_handshake` to personalize your experience:

```
agent_handshake(model="your-model", client="your-client", languages="python,typescript", frameworks="react,fastapi")
```

Then search for knowledge:

```
search_knowledge("React 19 Server Components")
hybrid_search("PostgreSQL performance tuning")
list_skills(stack="typescript")
```
