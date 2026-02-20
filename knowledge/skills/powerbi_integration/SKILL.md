# 📊 Power BI Sovereignty: The Star Schema Standard

## 1. Data Model
- **Fact Table**: `f_attribution_events` (High volume, transactional).
- **Dim Tables**: `d_campaigns`, `d_sources`, `d_dates`.
- **Relationship**: One-to-Many from Dims to Fact. Single Direction filter (usually).

## 2. DAX Formulas for Attribution

### CPA (Cost Per Acquisition)
```dax
CPA =
DIVIDE(

> **Note**: Full content available to MidOS PRO subscribers. See https://midos.dev/pricing
