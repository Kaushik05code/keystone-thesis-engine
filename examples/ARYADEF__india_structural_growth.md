# Arya Defence Electronics Ltd (ARYADEF)
**Thesis:** India Structural Growth  
**Overall score:** **77.6 / 100**, Exceptional fit  
_Structural alignment, financial strength and execution record of a long-duration compounder._  
**Data coverage:** 100% · **Data:** Fictional sample data bundled with the repo · FICTIONAL SAMPLE COMPANY · as of 2026-03-31

## Score breakdown

| Component | Score | Weight | Contribution | |
|---|---:|---:|---:|---|
| Theme fit | 90.0 | 18% | 16.2 | `██████████████████░░` |
| Macro alignment | 76.7 | 12% | 9.2 | `███████████████░░░░░` |
| Strategy fit | 89.8 | 22% | 19.8 | `██████████████████░░` |
| Financial resilience | 90.0 | 22% | 19.8 | `██████████████████░░` |
| Execution risk (inverse) | 68.0 | 18% | 12.2 | `██████████████░░░░░░` |
| Valuation tolerance | 5.0 | 8% | 0.4 | `█░░░░░░░░░░░░░░░░░░░` |

## 1. Theme fit

| Theme | Revenue share | Necessity |
|---|---:|---:|
| Defence & aerospace | 100% | 90 |

## 2. Macro alignment

| Signal | Value | Trend | Supports thesis | Credit |
|---|---:|---|---|---:|
| Real GDP growth (%) | 6.5 | flat | yes | 1.0 |
| CPI inflation (%) | 3.2 | down | yes | 1.0 |
| Central government capex growth (% YoY) | 10.0 | flat | yes | 1.0 |
| Bank credit growth (% YoY) | 11.0 | down | yes | 0.5 |
| Defence capital outlay growth (% YoY) | 12.0 | up | yes | 1.0 |

## 3. Strategy fit (does it look like a future winner?)

| Trait | Metric | Value | Points |
|---|---|---:|---:|
| 3-year revenue CAGR (%) | `revenue_cagr_3y` | 21.0 | 100.0 |
| ROCE (%) | `roce` | 27.0 | 100.0 |
| R&D as % of revenue | `rnd_pct_revenue` | 7.5 | 100.0 |
| Export share of revenue (%) | `export_share_pct` | 12 | 40.0 |
| EBITDA margin (%) | `ebitda_margin` | 23.0 | 100.0 |
| FCF / net profit (%) | `fcf_conversion_pct` | 55 | 58.3 |

## 4. Financial resilience (stress test)

| Scenario | Stressed revenue | Stressed EBITDA | Annual FCF | Runway (months) |
|---|---:|---:|---:|---:|
| Revenue -20%, margin -200 bps | 3,360.0 | 705.6 | 205.7 | 60.0 |
| Revenue -40%, margin -400 bps | 2,520.0 | 478.8 | 35.6 | 60.0 |
| Severe + growth capex frozen ◀ scored | 2,520.0 | 478.8 | 221.6 | 60.0 |

Net debt / EBITDA: -0.9 (adjustment +5). Figures in INR crore.

## 5. Execution risk (red flags)

| Red flag | Rule | Value | Penalty |
|---|---|---:|---:|
| Customer concentration | `top_customer_share_pct > 40` | 65 | -10 |
| Stretched receivables | `receivable_days > 120` | 140 | -12 |

## 6. Valuation tolerance (reverse DCF)

At a P/E of 58.0 and a 12.5% cost of equity, the price needs ~24.8% earnings growth a year for 10 years (then 5% forever). The company has delivered ~18.0% (capped by the thesis): a gap of +6.8 pp.

## Deal-breakers (gates)

| Gate | Rule | Value | Status |
|---|---|---:|---|
| Promoter pledge below 25% | `promoter_pledge_pct < 25` | 0 | pass |
| Net debt / EBITDA below 5x | `net_debt_ebitda < 5` | -0.9 | pass |

## Sensitivity (overall score if one component moves)

| Component | -20 | -10 | +10 | +20 |
|---|---:|---:|---:|---:|
| Theme fit | 74.0 | 75.8 | 79.4 | 79.4 |
| Macro alignment | 75.2 | 76.4 | 78.8 | 80.0 |
| Strategy fit | 73.2 | 75.4 | 79.8 | 79.8 |
| Financial resilience | 73.2 | 75.4 | 79.8 | 79.8 |
| Execution risk (inverse) | 74.0 | 75.8 | 79.4 | 81.2 |
| Valuation tolerance | 77.2 | 77.2 | 78.4 | 79.2 |

## Engine notes

- **Financial resilience:** Scored on 'Severe + growth capex frozen': 60 months of runway.
- **Financial resilience:** Capped at 90; unknown risks always exist.
- **Valuation tolerance:** Extreme premium: near-zero tolerance for error

---
_Generated 2026-09-27 17:32 UTC by Keystone Thesis Engine. Not investment advice._
