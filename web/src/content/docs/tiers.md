---
title: Access Tiers
description: MidOS access tiers — Community (free), Dev ($19/mo), and Ops (custom). Compare features, query limits, and tool access.
---

MidOS uses tiered access to balance free community usage with sustainable development.

## Tier Comparison

<div class="tier-table-wrap">

| Feature | <span class="badge badge-free">Community</span> | <span class="badge badge-dev">Dev</span> | <span class="badge badge-pro">Ops</span> |
|---------|:---:|:---:|:---:|
| **Price** | $0/mo | $19/mo ($15/mo annual) | Custom |
| **Queries/month** | 100 | 25,000 | 100,000 |
| **Tools** | 9 | All 57 | All 57 + custom packs |
| **Knowledge Chunks** | Truncated (250 chars) | Full | Full |
| **Skills** | Truncated (400 chars) | Full | Full |
| **EUREKA** | — | Full access | Full access |
| **SOTA** | — | Full access | Full access |
| **Truth Patches** | — | Full access | Full access |
| **Semantic Search** | — | Full | Full |
| **Agent Configs** | — | Full | Full |
| **Security Packs** | — | — | Included |
| **Infra Packs** | — | — | Included |
| **Support** | Community | Email | Priority |

</div>

## Community (Free)

Best for evaluation and light usage. No credit card required.

**What you get:**
- 9 tools: `search_knowledge`, `list_skills`, `hive_status`, `project_status`, `agent_handshake`, `where_was_i`, `context_health`, `get_progress`, `agent_bootstrap`
- Knowledge chunks truncated to 250 characters (enough to evaluate relevance)
- Skills truncated to 400 characters
- 100 queries per month

**What you don't get:**
- Full knowledge content
- EUREKA discoveries and SOTA
- Semantic/vector search
- Session management tools
- Admin tools

## Dev ($19/mo)

For individual developers who use MidOS daily. The "EUREKA line" — everything validated and high-value unlocks here.

**Everything in Community, plus:**
- All 57 tools unlocked
- Full, untruncated knowledge chunks and skills
- EUREKA patterns (104 validated improvements)
- SOTA (11 state-of-the-art entries)
- Truth patches (17 verified corrections)
- Semantic search with Gemini embeddings
- Session save/restore (`save_progress`, `get_progress`)
- Code chunking (`chunk_code`)
- 25,000 queries per month

**Annual discount:** $15/mo (20% off) when paid yearly.

## Ops (Custom Pricing)

For teams and organizations needing specialized knowledge packs.

**Everything in Dev, plus:**
- Security knowledge packs (tool poisoning, OAuth, ArXiv-based defenses)
- Infrastructure knowledge packs (Kubernetes, Terraform, observability)
- 100,000 queries per month
- Priority support
- Custom pack creation on request

## Moderator (Earned, $0)

Active community contributors can earn moderator access, which grants Dev-tier features at no cost. Contribute quality knowledge, report issues, or help other users.

## Try Before You Decide

Test any free-tier tool right now — no install needed. See the [Try MidOS](/guides/try-it/) page for copy-paste curl examples against the live cloud endpoint.

## Payment

- **Primary**: Stripe
- **LATAM fallback**: MercadoPago
- **Trial**: No trial needed — the free tier is permanent

## API Key Format

| Tier | Key Prefix | Example |
|------|-----------|---------|
| Dev | `midos_sk_dev_` | `midos_sk_dev_abc123...` |
| Pro/Mod | `midos_sk_pro_` or `midos_sk_mod_` | `midos_sk_pro_xyz789...` |
| Admin | `midos_sk_admin_` | `midos_sk_admin_000...` |

Set your key as an environment variable:
```bash
export MIDOS_API_KEY="midos_sk_dev_your_key_here"
```

Or pass it in the Authorization header for HTTP mode:
```bash
curl http://localhost:8419/mcp \
  -H "Authorization: Bearer midos_sk_dev_your_key_here" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"semantic_search","arguments":{"query":"React hooks patterns"}},"id":1}'
```
