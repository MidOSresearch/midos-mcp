# SKILL: Text Chunking & Vectorization (2026)

**Origin**: Deep Research Job #342
**Purpose**: Handling massive transcriptions (>100kb).

## 1. Top Patterns
- **Recursive Character Splitting**: The Gold Standard. Split by paragraphs `\n\n`, then sentences `\n`, then spaces. Preserves structure.
- **Semantic Chunking**: Grouping sentences by cosine similarity. (High CPU cost, high accuracy).

> **Note**: Full content available to MidOS PRO subscribers. See https://midos.dev/pricing
