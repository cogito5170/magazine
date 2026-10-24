"""Self-contained HTML report (no external dependencies)."""
from __future__ import annotations

import base64
import html
import io
import json
from collections import Counter

from ..schema import DocumentAnalysis, jsonable
from .overlay import overlay_objects_grid, saliency_heatmap

CSS = """
:root{--surface:#fcfcfb;--panel:#ffffff;--ink:#0b0b0b;--ink2:#52514e;--muted:#8a8984;--line:#e4e3de;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--warn:#b26b00;--grid:#ecebe6}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--surface:#1a1a19;--panel:#222221;--ink:#f0efec;
--ink2:#c3c2b7;--muted:#97968f;--line:#3a3935;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--warn:#e0a640;--grid:#2c2c2a}}
:root[data-theme="dark"]{--surface:#1a1a19;--panel:#222221;--ink:#f0efec;--ink2:#c3c2b7;--muted:#97968f;--line:#3a3935;
--s1:#3987e5;--s2:#d95926;--s3:#199e70;--warn:#e0a640;--grid:#2c2c2a}
body{margin:0;background:var(--surface);color:var(--ink);font:14px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1180px;margin:0 auto;padding:16px}
h1{font-size:22px;margin:8px 0}h2{font-size:18px;margin:28px 0 8px;border-bottom:1px solid var(--line);padding-bottom:4px}
h3{font-size:15px;margin:16px 0 6px}.muted{color:var(--muted)}.note{color:var(--ink2);font-size:13px}
table{border-collapse:collapse;width:100%;font-size:12.5px;margin:6px 0}
th,td{border-bottom:1px solid var(--line);padding:4px 6px;text-align:left;vertical-align:top}
th{color:var(--ink2);font-weight:600}td.num{font-variant-numeric:tabular-nums;text-align:right}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;padding:12px;margin:12px 0}
.imgs{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px}
.imgs img{width:100%;border:1px solid var(--line);cursor:zoom-in}
.pill{display:inline-block;padding:0 6px;border-radius:9px;border:1px solid var(--line);font-size:11.5px;color:var(--ink2)}
.legend span{margin-right:12px}.sw{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:4px}
details{margin:6px 0}summary{cursor:pointer;color:var(--ink2)}
.scroll{overflow-x:auto}
svg text{fill:var(--ink2);font-size:11px}
@media (max-width:640px){main{padding:12px 16px}}
"""


def _b64(img) -> str:
    bio = io.BytesIO()
    img.thumbnail((900, 900))
    img.save(bio, "PNG", optimize=True)
    return base64.b64encode(bio.getvalue()).decode()


def _fmt(v, n=4):
    if v is None:
        return '<span class="muted">null</span>'
    if isinstance(v, float):
        return f"{v:.{n}g}"
    if isinstance(v, (dict, list)):
        s = json.dumps(jsonable(v), ensure_ascii=False)
        return html.escape(s if len(s) < 160 else s[:160] + "…")
    return html.escape(str(v))


def _line_chart(series: dict[str, list], title: str, colors=("--s1", "--s2", "--s3"), w=560, h=180) -> str:
    """Up to 3 series, one shared y axis, legend + direct end labels, hover titles."""
    pad_l, pad_r, pad_t, pad_b = 40, 70, 16, 24
    vals = [v for s in series.values() for v in s if v is not None]
    if not vals:
        return ""
    lo, hi = min(0.0, min(vals)), max(vals) if max(vals) > 0 else 1.0
    n = max(len(s) for s in series.values())
    X = lambda i: pad_l + (w - pad_l - pad_r) * (i / max(n - 1, 1))
    Y = lambda v: pad_t + (h - pad_t - pad_b) * (1 - (v - lo) / ((hi - lo) or 1))
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" role="img" '
           f'aria-label="{html.escape(title)}">']
    for t in range(5):
        v = lo + (hi - lo) * t / 4
        out.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" stroke="var(--grid)"/>'
                   f'<text x="{pad_l - 4}" y="{Y(v) + 4:.1f}" text-anchor="end">{v:.2g}</text>')
    for i in range(n):
        out.append(f'<text x="{X(i):.1f}" y="{h - 6}" text-anchor="middle">{i + 1}</text>')
    for (name, s), c in zip(series.items(), colors):
        pts = [(X(i), Y(v), v) for i, v in enumerate(s) if v is not None]
        if not pts:
            continue
        out.append(f'<polyline fill="none" stroke="var({c})" stroke-width="2" points="'
                   + " ".join(f"{x:.1f},{y:.1f}" for x, y, _ in pts) + '"/>')
        for i, (x, y, v) in enumerate(pts):
            out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4" fill="var({c})" stroke="var(--panel)" stroke-width="2">'
                       f'<title>{html.escape(name)} · page {i + 1}: {v:.4g}</title></circle>')
        x, y, _ = pts[-1]
        out.append(f'<text x="{x + 8:.1f}" y="{y + 4:.1f}">{html.escape(name)}</text>')
    out.append("</svg>")
    leg = "".join(f'<span><i class="sw" style="background:var({c})"></i>{html.escape(k)}</span>'
                  for k, c in zip(series, colors)) if len(series) > 1 else ""
    return f'<h3>{html.escape(title)}</h3><div class="legend note">{leg}</div>' + "".join(out)


def build_html(res: DocumentAnalysis, doc, extras: dict, path: str) -> str:
    from ..modules.common import PageContext
    from ..config import load_config
    cfg = load_config()
    P = []
    P.append(f"<h1>Design analysis — {html.escape(res.source_file.split('/')[-1])}</h1>")
    P.append(f'<p class="note">sha256 {res.source_sha256[:16]}… · {res.page_count} pages · method {res.method_version} · '
             f'config {res.config_hash}. Original file not modified.</p>')
    cnt = Counter(p.validation_status.value for p in res.all_parameters())
    P.append('<div class="card"><b>What this report is.</b> Measurements (<span class="pill">measured</span>), '
             'rule/heuristic estimates (<span class="pill">estimated</span>) and model predictions '
             '(<span class="pill">predicted</span>) are kept apart. Aesthetic judgements are hypotheses: without a '
             'validated human-preference model they are <b>null</b>, never replaced by size, contrast, alignment, '
             'saturation, font count or whitespace.<br>Status counts: '
             + ", ".join(f"{k}: {v}" for k, v in sorted(cnt.items())) + "</div>")
    ev = res.evaluation
    qt = ev["Q_technical"]
    P.append("<h2>Technical constraints</h2><div class='scroll'><table><tr><th>page</th><th>constraint</th>"
             "<th>value</th><th>threshold</th><th>satisfied</th><th>evidence</th></tr>")
    for c in qt["constraints"]:
        P.append(f"<tr><td>{c['page']}</td><td>{c['constraint']}</td><td class=num>{_fmt(c['value'])}</td>"
                 f"<td class=num>{_fmt(c['threshold'])}</td><td>{c['satisfied']}</td><td>{html.escape(str(c['evidence_status']))}"
                 f"{(' — ' + html.escape(c.get('evidence_note', ''))) if c.get('evidence_note') else ''}</td></tr>")
    P.append("</table></div>")
    L = ev["objective_L"]
    P.append(f"<p class='note'>Objective L = Σλ·E = {_fmt(L['value'])} (validated: {L['validated']}; not a quality score). "
             f"Q_perceptual: {ev['Q_perceptual']['status']}. Q_functional: not measured (requires experiments).</p>")
    # rhythm
    rv = {p.parameter_id: p for p in res.document_parameters}
    if res.page_count >= 2:
        pv = extras["page_vectors"]
        P.append("<h2>Visual rhythm</h2>")
        P.append(_line_chart({"D_image": [v.get("A07") for v in pv], "D_text": [v.get("A08") for v in pv],
                              "D_white": [v.get("A09") for v in pv]}, "Occupancy by page"))
        if rv.get("E05") and rv["E05"].value:
            P.append(_line_chart({"Δ_p": rv["E05"].value}, "Standardised page transition Δ_p (page p → p+1)"))
        P.append("<details><summary>Table view</summary><table><tr><th>page</th><th>D_image</th><th>D_text</th>"
                 "<th>D_white</th><th>B</th></tr>" + "".join(
                     f"<tr><td>{i + 1}</td><td class=num>{_fmt(v.get('A07'))}</td><td class=num>{_fmt(v.get('A08'))}</td>"
                     f"<td class=num>{_fmt(v.get('A09'))}</td><td class=num>{_fmt(v.get('D02'))}</td></tr>"
                     for i, v in enumerate(pv)) + "</table></details>")
        for k in ("E06", "E07", "E09", "E13", "E14"):
            p = rv.get(k)
            if p:
                P.append(f"<div class=note>{k} {p.name}: {_fmt(p.value)} <span class=pill>{p.validation_status.value}</span></div>")
    # pages
    P.append("<h2>Pages</h2>")
    for i, pa in enumerate(res.pages):
        pm = doc.pages[i]
        ctx = PageContext(pm, cfg)
        com = pa.get("D01").value if pa.get("D01") and pa.get("D01").value else None
        ov = _b64(overlay_objects_grid(pm, extras["grids"][i], com))
        sal = _b64(saliency_heatmap(pm, ctx.saliency))
        P.append(f'<div class="card"><h3>Page {i + 1} <span class="pill">{pa.extraction_mode}</span></h3>')
        if pa.warnings:
            P.append("<p class=note>" + "<br>".join(html.escape(w) for w in pa.warnings) + "</p>")
        P.append(f'<div class="imgs"><figure><img src="data:image/png;base64,{ov}" alt="objects and grid">'
                 '<figcaption class=note>Boxes: <span style="color:var(--s1)">text</span>, '
                 '<span style="color:var(--s2)">image</span>, <span style="color:var(--s3)">vector</span>; '
                 'violet bands = estimated columns; cross = visual centre of mass (D01)</figcaption></figure>'
                 f'<figure><img src="data:image/png;base64,{sal}" alt="saliency heatmap">'
                 '<figcaption class=note>Spectral-residual saliency (estimate of bottom-up salience, not attention)'
                 '</figcaption></figure></div>')
        P.append("<details><summary>All parameters</summary><div class=scroll><table><tr><th>id</th><th>name</th>"
                 "<th>value</th><th>unit</th><th>type</th><th>status</th></tr>")
        for p in pa.parameters:
            P.append(f"<tr><td>{p.parameter_id}</td><td>{p.name}</td><td>{_fmt(p.value)}</td><td>{p.unit}</td>"
                     f"<td>{p.measurement_type.value}</td><td>{p.validation_status.value}</td></tr>")
        P.append("</table></div></details>")
        tx = pa.get("TX01")
        if tx and tx.value:
            P.append("<h3>Typeface: functional facts vs. aesthetic evaluation</h3><table><tr><th>text</th><th>font</th>"
                     "<th>functional facts</th><th>aesthetic verdict</th></tr>")
            for d in tx.value["display_lines"]:
                P.append(f"<tr><td>{html.escape(d['text'])}</td><td>{html.escape(str(d['font']))}</td>"
                         f"<td>{_fmt(d['functional_facts'])}</td><td>{_fmt(d['aesthetic_verdict'])} — "
                         f"{html.escape(d['aesthetic_verdict_reason'])}</td></tr>")
            P.append("</table>")
        P.append("</div>")
    # proposals
    P.append("<h2>Change proposals (not applied)</h2><p class=note>Every proposal needs user approval. "
             "Reference-matching proposals move toward the selected reference; they are not quality claims.</p>")
    if not res.recommendations:
        P.append("<p class=muted>No proposal with a verified normative basis.</p>")
    for r in res.recommendations:
        P.append(f"<div class=card><b>p{r['page']} · {html.escape(r['element'])}</b> <span class=pill>{r['purpose']}</span> "
                 f"<span class=pill>verification: {r['verification_status']}</span> <span class=pill>approval: "
                 f"{r['user_approval_status']}</span><br><span class=note>original: {_fmt(r['original_state'])}<br>"
                 f"proposed: {_fmt(r['proposed_change'])}<br>basis: {html.escape(r['basis'])}<br>evidence: "
                 + "; ".join(f"{e['claim_type']}" + (f" ({e['source_id']})" if e.get('source_id') else "") for e in r["evidence"])
                 + "</span></div>")
    obs = ev.get("observations_without_verified_basis") or []
    if obs:
        P.append("<h3>Observations without a verified normative basis</h3><ul>" + "".join(
            f"<li class=note>p{r['page']} · {html.escape(r['element'])}: {_fmt(r['original_state'])} — {html.escape(r['basis'])}</li>"
            for r in obs) + "</ul>")
    nm = [p for p in res.all_parameters() if p.validation_status.value in ("not_measured", "no_model", "no_reference", "not_computable")]
    P.append("<h2>Not measured / not computable</h2><p class=note>" + ", ".join(sorted({f"{p.parameter_id} ({p.validation_status.value})" for p in nm})) + "</p>")
    page = (f"<!doctype html><html lang=ko><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>Design Analysis Report</title><style>{CSS}</style></head><body><main>{''.join(P)}</main>"
            "<script>document.querySelectorAll('.imgs img').forEach(i=>i.onclick=()=>window.open(i.src));</script></body></html>")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(page)
    return path
