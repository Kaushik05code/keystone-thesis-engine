"""Render a score card as a single self-contained HTML page (no JS, no CDN)."""

from __future__ import annotations

from html import escape

from ..scoring import LABELS, ScoreCard
from ..thesis import COMPONENTS

CSS = """
:root{--bg:#f7f7f5;--card:#fff;--ink:#1d1d1f;--mute:#6b6b70;--line:#e4e4e0;--accent:#1f5eff;--good:#1a8f55;--bad:#c4372c}
@media (prefers-color-scheme:dark){:root{--bg:#141416;--card:#1d1d20;--ink:#ececef;--mute:#9a9aa2;--line:#2c2c31;--accent:#7aa2ff;--good:#43c083;--bad:#ff6b5e}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,Segoe UI,Inter,Roboto,sans-serif}
main{max-width:920px;margin:0 auto;padding:32px 16px 64px}h1{font-size:26px;margin:0 0 4px}h2{font-size:17px;margin:28px 0 10px}
.sub{color:var(--mute)}.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:18px 20px;margin-top:16px}
.hero{display:flex;gap:24px;align-items:center;flex-wrap:wrap}.big{font-size:56px;font-weight:700;line-height:1}
.pill{display:inline-block;padding:3px 10px;border-radius:999px;background:var(--accent);color:#fff;font-size:13px}
.row{display:grid;grid-template-columns:190px 1fr 56px 56px;gap:10px;align-items:center;padding:6px 0}
.track{height:10px;background:var(--line);border-radius:6px;overflow:hidden}.fill{height:100%;background:var(--accent)}
table{width:100%;border-collapse:collapse;font-size:14px}th,td{text-align:left;padding:7px 8px;border-bottom:1px solid var(--line)}
th{color:var(--mute);font-weight:600}td.n{text-align:right;font-variant-numeric:tabular-nums}
.warn{border-left:4px solid var(--bad)}.fail{color:var(--bad);font-weight:600}.pass{color:var(--good);font-weight:600}
footer{margin-top:32px;color:var(--mute);font-size:13px}
@media (max-width:600px){.row{grid-template-columns:1fr 44px}.row .track,.row .w{display:none}}
"""


def _n(v, digits: int = 1) -> str:
    if v is None:
        return "n/a"
    if isinstance(v, (int, float)):
        return f"{v:,.{digits}f}"
    return escape(str(v))


def render_html(card: ScoreCard) -> str:
    s = card.snapshot
    comps = card.components
    rows = "".join(
        f'<div class="row"><div>{LABELS[k]}</div><div class="track"><div class="fill" '
        f'style="width:{comps[k].score:.0f}%"></div></div><div class="n">{comps[k].score:.0f}</div>'
        f'<div class="w sub">×{card.weights[k]:.0%}</div></div>'
        for k in COMPONENTS
    )
    themes = "".join(
        f"<tr><td>{escape(r['theme'])}</td><td class='n'>{r['revenue_share_pct']:.0f}%</td>"
        f"<td class='n'>{r['necessity']:.0f}</td></tr>"
        for r in comps["theme_fit"].inputs.get("themes", [])
    )
    res = comps["financial_resilience"].inputs.get("scenarios", {})
    stress = "".join(
        f"<tr><td>{escape(v['name'])}{' ◀' if k == comps['financial_resilience'].inputs.get('scored_scenario') else ''}</td>"
        f"<td class='n'>{_n(v['stressed_ebitda'])}</td><td class='n'>{_n(v['annual_fcf'])}</td>"
        f"<td class='n'>{_n(v['survival_months'])}</td></tr>"
        for k, v in res.items()
    )
    flags = "".join(
        f"<tr><td>{escape(f['flag'])}</td><td><code>{escape(f['rule'])}</code></td>"
        f"<td class='n'>{_n(f['value'])}</td><td class='n'>-{f['penalty']:g}</td></tr>"
        for f in comps["execution_risk"].inputs.get("fired", [])
    ) or "<tr><td colspan='4' class='sub'>No red flags fired.</td></tr>"
    gates = "".join(
        f"<tr><td>{escape(g['gate'])}</td><td><code>{escape(g['rule'])}</code></td>"
        f"<td class='n'>{_n(g['value'])}</td><td class='{g['status']}'>{g['status']}</td></tr>"
        for g in card.gates
    )
    sens = "".join(
        f"<tr><td>{LABELS[k]}</td>" + "".join(f"<td class='n'>{card.sensitivity[k][d]:.1f}</td>"
                                               for d in ("-20", "-10", "+10", "+20")) + "</tr>"
        for k in COMPONENTS
    )
    notes = "".join(f"<li><b>{LABELS[k]}:</b> {escape(n)}</li>" for k in COMPONENTS for n in comps[k].notes)
    fictional = " · <b>fictional sample company</b>" if s.fictional else ""
    capped = ('<div class="card warn">A deal-breaker gate failed, so the overall score is capped.</div>'
              if card.gate_capped else "")
    memo = f'<h2>Analyst memo</h2><div class="card"><pre style="white-space:pre-wrap;font:inherit">{escape(card.memo)}</pre></div>' if card.memo else ""

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{escape(card.ticker)} · Keystone score</title><style>{CSS}</style></head><body><main>
<h1>{escape(card.company)} <span class="sub">({escape(card.ticker)})</span></h1>
<div class="sub">Scored against <b>{escape(card.thesis_name)}</b> · data: {escape(s.source or 'n/a')}{fictional} · as of {escape(s.as_of or 'n/a')}</div>
<div class="card hero"><div class="big">{card.overall:.1f}</div><div><span class="pill">{escape(card.band)}</span>
<div class="sub" style="margin-top:6px">{escape(card.band_description)}</div>
<div class="sub">Data coverage {card.data_coverage:.0%}</div></div></div>{capped}
<h2>Score breakdown</h2><div class="card">{rows}</div>
<h2>Theme fit</h2><div class="card"><table><tr><th>Theme</th><th class="n">Revenue share</th><th class="n">Necessity</th></tr>{themes}</table></div>
<h2>Stress test <span class="sub">({escape(s.currency)} {escape(s.units)})</span></h2><div class="card"><table><tr><th>Scenario</th><th class="n">EBITDA</th><th class="n">Annual FCF</th><th class="n">Runway (months)</th></tr>{stress}</table></div>
<h2>Red flags</h2><div class="card"><table><tr><th>Flag</th><th>Rule</th><th class="n">Value</th><th class="n">Penalty</th></tr>{flags}</table></div>
{'<h2>Deal-breakers</h2><div class="card"><table><tr><th>Gate</th><th>Rule</th><th class="n">Value</th><th>Status</th></tr>' + gates + '</table></div>' if gates else ''}
<h2>Sensitivity</h2><div class="card"><table><tr><th>Component</th><th class="n">-20</th><th class="n">-10</th><th class="n">+10</th><th class="n">+20</th></tr>{sens}</table></div>
{'<h2>Engine notes</h2><div class="card"><ul>' + notes + '</ul></div>' if notes else ''}
{memo}
<footer>Generated {escape(card.generated_at)} by Keystone Thesis Engine. Not investment advice.</footer>
</main></body></html>"""
