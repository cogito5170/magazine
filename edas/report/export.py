"""JSON / CSV / PDF exports and the spec registry dump."""
from __future__ import annotations

import csv
import io
import json
import os
from typing import Optional

from ..schema import DocumentAnalysis, jsonable


def all_specs() -> dict:
    from ..modules import aesthetics, bilingual, composition, layout, photography, rhythm, typeface, typography
    out = {}
    for m in (layout, typography, photography, composition, rhythm, aesthetics, bilingual, typeface):
        out.update(m.SPECS)
    return out


def write_json(res: DocumentAnalysis, path: str) -> str:
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(res.model_dump_json(indent=1))
    return path


def write_csv(res: DocumentAnalysis, path: str) -> str:
    cols = ["scope", "page", "parameter_id", "name", "value_scalar", "value_json", "unit", "measurement_type",
            "validation_status", "source", "target", "tolerance", "error", "method_version", "notes"]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(cols)
        for p in res.all_parameters():
            w.writerow([p.scope, (p.page_index + 1) if p.page_index is not None else "", p.parameter_id, p.name,
                        p.scalar(), json.dumps(jsonable(p.value), ensure_ascii=False), p.unit,
                        p.measurement_type.value, p.validation_status.value, p.source or "",
                        json.dumps(jsonable(p.target)), p.tolerance, p.error, p.method_version,
                        " | ".join(p.notes)])
    return path


def write_spec_registry(path: str) -> str:
    specs = all_specs()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump({k: v.model_dump(mode="json") for k, v in sorted(specs.items())}, fh, ensure_ascii=False, indent=1)
    return path


def write_pdf_report(res: DocumentAnalysis, doc, extras: dict, path: str, overlay_dir: Optional[str] = None) -> str:
    """Compact PDF report (reportlab): summary, per-page overlays and key values, proposals."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Image as RLImage, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table
    from .overlay import overlay_objects_grid
    st = getSampleStyleSheet()
    story = [Paragraph("EDAS — quantitative design analysis", st["Title"]),
             Paragraph(f"Source: {os.path.basename(res.source_file)} (sha256 {res.source_sha256[:16]}…), "
                       f"{res.page_count} pages, method {res.method_version}, config {res.config_hash}", st["Normal"]),
             Paragraph("Measured values only. Aesthetic outputs are null unless a validated preference model "
                       "exists. Proposals are not applied and require approval.", st["Italic"]), Spacer(1, 6)]
    ev = res.evaluation
    qt = ev.get("Q_technical", {})
    story.append(Paragraph(f"Technical constraints satisfied: {qt.get('satisfied')}/{qt.get('checked')}", st["Heading3"]))
    rows = [["page", "constraint", "value", "threshold", "evidence"]]
    for c in qt.get("constraints", [])[:40]:
        rows.append([c["page"], c["constraint"], _fmt(c["value"]), _fmt(c["threshold"]), c["evidence_status"]])
    story.append(Table(rows, repeatRows=1))
    for i, pa in enumerate(res.pages):
        story.append(PageBreak())
        story.append(Paragraph(f"Page {i + 1} ({pa.extraction_mode})", st["Heading2"]))
        pm = doc.pages[i]
        com = pa.get("D01").value if pa.get("D01") else None
        img = overlay_objects_grid(pm, extras["grids"][i], com)
        bio = io.BytesIO()
        img.thumbnail((700, 700))
        img.save(bio, "PNG")
        bio.seek(0)
        w = 85 * mm
        story.append(RLImage(bio, width=w, height=w * img.size[1] / img.size[0]))
        keys = ["A02", "A03", "A04", "A06", "A07", "A08", "A09", "B03", "B12", "B18", "D01", "D02", "D15"]
        rows = [["id", "name", "value", "status"]]
        for k in keys:
            p = pa.get(k)
            if p:
                rows.append([k, p.name, _fmt(p.value)[:60], p.validation_status.value])
        story.append(Table(rows, repeatRows=1))
    story.append(PageBreak())
    story.append(Paragraph("Change proposals (not applied; approval required)", st["Heading2"]))
    for r in res.recommendations[:60]:
        story.append(Paragraph(f"p{r['page']} · {r['element']} · {r['purpose']} · verification "
                               f"{r['verification_status']} · approval {r['user_approval_status']}", st["Normal"]))
    obs = ev.get("observations_without_verified_basis") or []
    if obs:
        story.append(Paragraph("Observations without a verified normative basis (no change proposed)", st["Heading3"]))
        for r in obs[:60]:
            story.append(Paragraph(f"p{r['page']} · {r['element']} · {r['basis']}", st["Normal"]))
    SimpleDocTemplate(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm).build(story)
    return path


def _fmt(v) -> str:
    if isinstance(v, float):
        return f"{v:.4g}"
    if isinstance(v, dict):
        return ", ".join(f"{k}={_fmt(x)}" for k, x in list(v.items())[:6])
    return str(v)
