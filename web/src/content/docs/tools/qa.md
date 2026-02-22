---
title: "QA & Community Tools (6)"
description: Quality assurance and community feedback tools — rate knowledge, submit QA reports, and browse community sentiment.
---

These 6 tools support the community feedback loop. They let agents and users rate knowledge quality, submit test reports, and browse community sentiment.

---

## quality_gate

Multi-criteria quality assessment for knowledge items.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `item_type` | string | Yes | — | Type of item to assess |
| `item_id` | string | Yes | — | Item identifier |
| `criteria` | string | No | `"all"` | `"readability"`, `"completeness"`, `"accuracy"`, `"utility"`, or `"all"` |

**Returns:** `{ pass: bool, score: float, feedback }`

---

## submit_feedback

Rate a knowledge item. Community-driven quality signal.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `item_type` | string | Yes | — | `"chunk"`, `"eureka"`, `"tool"`, `"content"`, `"debunk"`, `"skill"`, `"truth"` |
| `item_id` | string | Yes | — | Item identifier |
| `rating` | int | Yes | — | `-1` (bad), `0` (neutral), `+1` (good) |
| `comment` | string | No | `""` | Optional feedback text |

**Returns:** `{ status: "recorded", item_type, item_id }`

```json
{
  "name": "submit_feedback",
  "arguments": {
    "item_type": "skill",
    "item_id": "fastapi-patterns",
    "rating": 1,
    "comment": "Very comprehensive, the dependency injection section saved me hours"
  }
}
```

---

## submit_qa_report

Submit a QA testing round report for tracking.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `round_id` | string | Yes | — | QA round identifier |
| `model_name` | string | Yes | — | Model used for testing |
| `test_count` | int | Yes | — | Total tests run |
| `pass_count` | int | Yes | — | Tests passed |
| `notes` | string | No | `""` | Additional notes |

**Returns:** `{ status: "submitted", round_id }`

---

## list_qa_reports

Browse QA reports with optional filtering.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `round_id` | string | No | `""` | Filter by round |
| `model_name` | string | No | `""` | Filter by model |

**Returns:** List of QA reports with pass rates and timestamps.

---

## list_feedback

Browse community feedback entries.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `item_type` | string | No | `""` | Filter by item type |
| `item_id` | string | No | `""` | Filter by item ID |
| `min_rating` | int | No | -2 | Minimum rating threshold |

**Returns:** List of feedback entries matching filters.

---

## get_feedback_stats

Aggregated feedback statistics.

| Parameter | Type | Required | Default | Description |
|-----------|------|:--------:|---------|-------------|
| `item_id` | string | No | `""` | Filter by specific item |

**Returns:** `{ avg_rating, count, distribution, sentiment }`

Shows the overall quality perception across all community feedback.
