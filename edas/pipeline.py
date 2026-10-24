"""End-to-end analysis pipeline (spec §12).

PDF → parsing → rendering → object extraction → normalisation → features
(6 modules + bilingual + typeface dimensions) → evaluation → reference
comparison → error diagnosis → proposals (not applied) → export.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from .config import config_hash, load_config
from .evaluation.integrate import integrate
from .features import extract, page_values
from .modules import aesthetics, bilingual, composition, layout, photography, rhythm, typeface, typography
from .modules.common import DocContext, PageContext
from .optimize.recommend import reference_proposals, technical_proposals
from .pdf.extract import open_document
from .reference.profile import compare_to_profile
from .schema import DocumentAnalysis, PageAnalysis


@dataclass
class RunOptions:
    reference: Optional[dict] = None          # loaded reference profile
    reference_label: str = ""
    target_style: Optional[str] = None
    judgment_store: Optional[str] = None      # JSONL of human judgments
    protected_pages: set = field(default_factory=set)   # 1-based, never proposed for change
    with_candidates: bool = True              # BK13 installed-font candidates
    models: dict = field(default_factory=dict)


def error_kinds() -> dict:
    out = {}
    for mod in (layout, typography, photography, composition):
        for pid, s in mod.SPECS.items():
            out[pid] = s.error_kind.value
    return out


def analyze(path: str, cfg: Optional[dict] = None, opts: Optional[RunOptions] = None):
    """Returns (DocumentAnalysis, DocumentModel, extras)."""
    cfg = cfg or load_config()
    opts = opts or RunOptions()
    doc = open_document(path, cfg)
    dctx = DocContext(doc, cfg)
    bdoc = bilingual.BilingualDoc(dctx)
    ty_doc, morph = typeface.analyze_document(dctx)
    res = DocumentAnalysis(source_file=path, source_sha256=doc.sha256, page_count=len(doc.pages),
                           config_hash=config_hash(cfg),
                           reference_profile=opts.reference_label or None)
    grids, page_vals, photo_feats, page_vecs = [], [], [], []
    for pm in doc.pages:
        ctx = PageContext(pm, cfg)
        params = []
        lres, grid = layout.analyze_page(ctx)
        params += lres
        params += typography.analyze_page(ctx, dctx)
        pres, feats = photography.analyze_page(ctx)
        params += pres
        photo_feats += feats
        vals = page_values(params)
        params += composition.analyze_page(ctx, vals)
        vals = page_values(params)
        params += bilingual.analyze_page(ctx, dctx, bdoc, vals, opts.models, opts.target_style)
        vals = page_values(params)
        params += typeface.analyze_page(ctx, dctx, morph, vals, opts.target_style, opts.models.get("typeface_context"))
        vals = page_values(params)
        grids.append(grid)
        page_vals.append(vals)
        page_vecs.append(extract(vals))
        res.pages.append(PageAnalysis(page_index=pm.index, width_pt=pm.width, height_pt=pm.height,
                                      extraction_mode=pm.extraction_mode, parameters=params, warnings=pm.warnings))
    d = res.document_parameters
    d += layout.analyze_document(grids, doc.pages)
    d += typography.analyze_document(dctx, opts.reference)
    d += photography.analyze_document(photo_feats)
    d += rhythm.analyze_document(doc.pages, page_vals, opts.reference, cfg)
    d += bilingual.analyze_document(dctx, bdoc, opts.with_candidates)
    d += ty_doc
    store = None
    if opts.judgment_store:
        from .preference.schema import JudgmentStore
        store = JudgmentStore(opts.judgment_store)
    d += typeface.preference_results(store, sorted(morph))
    doc_vec = {k: (sum(v[k] for v in page_vecs if v.get(k) is not None) /
                   max(1, sum(1 for v in page_vecs if v.get(k) is not None)))
               if any(v.get(k) is not None for v in page_vecs) else None for k in page_vecs[0]} if page_vecs else {}
    d += aesthetics.analyze_document(page_vals, doc_vec, opts.reference, opts.models)
    ref_rows = {}
    if opts.reference:
        ek = error_kinds()
        for i, v in enumerate(page_vecs):
            ref_rows[i] = compare_to_profile(v, opts.reference, ek)
    all_rows = [r for rows in ref_rows.values() for r in rows]
    res.evaluation = integrate(doc, res, cfg, all_rows, opts.models)
    res.evaluation["reference_comparison"] = {str(k + 1): v for k, v in ref_rows.items()} if ref_rows else None
    props = technical_proposals(doc, res, cfg, opts.protected_pages)
    if opts.reference:
        props += reference_proposals(doc, ref_rows, cfg, opts.protected_pages, opts.reference_label)
    from .governance.evidence import is_actionable
    observations = []
    actionable = []
    for p in props:
        ok, why = is_actionable(p)
        rec = dict(p.model_dump(mode="json"), verification_status=p.verification_status.value, basis=why)
        (actionable if ok else observations).append(rec)
    res.recommendations = actionable
    res.evaluation["observations_without_verified_basis"] = observations
    if opts.protected_pages:
        res.warnings.append(f"protected pages {sorted(opts.protected_pages)}: no change proposed")
    extras = {"page_vectors": page_vecs, "doc_vector": doc_vec, "grids": grids, "photo_feats": photo_feats,
              "proposals": props, "morphology": morph, "bilingual": bdoc}
    return res, doc, extras
