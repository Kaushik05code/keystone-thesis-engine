# Jalnidhi Water Infra Ltd (JALNIDHI)
**Thesis:** India Structural Growth  
**Overall score:** **40.0 / 100**, Weak fit  
_Material structural or financial gaps; unlikely to be a compounding winner._  
**Data coverage:** 100% · **Data:** Fictional sample data bundled with the repo · FICTIONAL SAMPLE COMPANY · as of 2026-03-31

> A deal-breaker gate failed, so the overall score is capped. See *Deal-breakers* below.

## Score breakdown

| Component | Score | Weight | Contribution | |
|---|---:|---:|---:|---|
| Theme fit | 82.0 | 18% | 14.8 | `████████████████░░░░` |
| Macro alignment | 74.7 | 12% | 9.0 | `███████████████░░░░░` |
| Strategy fit | 35.2 | 22% | 7.8 | `███████░░░░░░░░░░░░░` |
| Financial resilience | 0.0 | 22% | 0.0 | `░░░░░░░░░░░░░░░░░░░░` |
| Execution risk (inverse) | 21.0 | 18% | 3.8 | `████░░░░░░░░░░░░░░░░` |
| Valuation tolerance | 90.0 | 8% | 7.2 | `██████████████████░░` |

## 1. Theme fit

| Theme | Revenue share | Necessity |
|---|---:|---:|
| Water infrastructure | 100% | 82 |

## 2. Macro alignment

| Signal | Value | Trend | Supports thesis | Credit |
|---|---:|---|---|---:|
| Real GDP growth (%) | 6.5 | flat | yes | 1.0 |
| CPI inflation (%) | 3.2 | down | yes | 1.0 |
| Central government capex growth (% YoY) | 10.0 | flat | yes | 1.0 |
| Bank credit growth (% YoY) | 11.0 | down | yes | 0.5 |

## 3. Strategy fit (does it look like a future winner?)

| Trait | Metric | Value | Points |
|---|---|---:|---:|
| 3-year revenue CAGR (%) | `revenue_cagr_3y` | 17.0 | 78.6 |
| ROCE (%) | `roce` | 14.0 | 38.5 |
| R&D as % of revenue | `rnd_pct_revenue` | 0.3 | 0.0 |
| Export share of revenue (%) | `export_share_pct` | 5 | 16.7 |
| EBITDA margin (%) | `ebitda_margin` | 12.0 | 28.6 |
| FCF / net profit (%) | `fcf_conversion_pct` | 10 | 0.0 |

## 4. Financial resilience (stress test)

| Scenario | Stressed revenue | Stressed EBITDA | Annual FCF | Runway (months) |
|---|---:|---:|---:|---:|
| Revenue -20%, margin -200 bps | 2,480.0 | 248.0 | -791.5 | 2.3 |
| Revenue -40%, margin -400 bps | 1,860.0 | 148.8 | -881.2 | 2.0 |
| Severe + growth capex frozen ◀ scored | 1,860.0 | 148.8 | -809.2 | 2.2 |

Net debt / EBITDA: 4.7 (adjustment -15). Figures in INR crore.

## 5. Execution risk (red flags)

| Red flag | Rule | Value | Penalty |
|---|---|---:|---:|
| Promoter shares pledged | `promoter_pledge_pct > 10` | 34 | -20 |
| Customer concentration | `top_customer_share_pct > 40` | 48 | -10 |
| Stretched receivables | `receivable_days > 120` | 210 | -12 |
| Auditor changed in last 3 years | `auditor_changes_3y > 0` | 1 | -15 |
| Heavy related-party revenue | `related_party_revenue_pct > 10` | 14 | -12 |

## 6. Valuation tolerance (reverse DCF)

At a P/E of 19.0 and a 12.5% cost of equity, the price needs ~9.3% earnings growth a year for 10 years (then 5% forever). The company has delivered ~17.0% (capped by the thesis): a gap of -7.7 pp.

## Deal-breakers (gates)

| Gate | Rule | Value | Status |
|---|---|---:|---|
| Promoter pledge below 25% | `promoter_pledge_pct < 25` | 34 | fail |
| Net debt / EBITDA below 5x | `net_debt_ebitda < 5` | 4.7 | pass |

## Sensitivity (overall score if one component moves)

| Component | -20 | -10 | +10 | +20 |
|---|---:|---:|---:|---:|
| Theme fit | 38.9 | 40.6 | 44.2 | 45.7 |
| Macro alignment | 40.0 | 41.2 | 43.6 | 44.9 |
| Strategy fit | 38.0 | 40.2 | 44.6 | 46.9 |
| Financial resilience | 42.5 | 42.5 | 44.6 | 46.9 |
| Execution risk (inverse) | 38.9 | 40.6 | 44.2 | 46.0 |
| Valuation tolerance | 40.9 | 41.6 | 43.2 | 43.2 |

## Engine notes

- **Financial resilience:** Scored on 'Severe + growth capex frozen': 2.2 months of runway.
- **Valuation tolerance:** Deep value: the price assumes far less growth than delivered

---
_Generated 2026-09-27 17:32 UTC by Keystone Thesis Engine. Not investment advice._
