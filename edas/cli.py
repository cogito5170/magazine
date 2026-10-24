"""Command-line interface.

  edas analyze FILE.pdf [-o OUT] [--reference PROFILE.json] [--protect 2 ...] [--judgments J.jsonl]
  edas specs [-o specs.json]
  edas profile-build REF1.pdf ... --style STYLE -o profile.json
  edas typo-experiment FILE.pdf --page 3 --text Observe --alt PATH[#index] ... -o DIR
  edas ab-page MANIFEST.json -o page.html [--page-id ID]
  edas prefs-import EXPORT.json --store judgments.jsonl
  edas prefs-report --store judgments.jsonl [--original FONT]
  edas regress ORIGINAL.pdf CANDIDATE.pdf --protect 2
  edas approve PROPOSALS.json --id ID --decision approved|rejected --approver NAME
  edas mood list                                   finished spreads that reproduce exactly
  edas mood render NAME --image SRC [-o DIR]       re-render a finished spread from its source image
  edas mood new SLUG --image SRC --mood "무드"      start a job folder (original copy + brief.json)
  edas mood grid SRC [--region X0 Y0 X1 Y1] [--zoom 3] -o OUT.png    read coordinates off a source
  edas mood fonts [--install]                      check / install Pretendard and Noto Serif KR (OFL)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from .config import load_config


def _analyze(a):
    from .pipeline import RunOptions, analyze
    from .reference.profile import load_profile
    from .report.export import write_csv, write_json, write_pdf_report
    from .report.html import build_html
    cfg = load_config(a.config)
    ref = load_profile(a.reference) if a.reference else None
    opts = RunOptions(reference=ref, reference_label=os.path.basename(a.reference) if a.reference else "",
                      target_style=a.style, judgment_store=a.judgments, protected_pages=set(a.protect or []),
                      with_candidates=not a.no_candidates)
    res, doc, ex = analyze(a.file, cfg, opts)
    os.makedirs(a.out, exist_ok=True)
    stem = os.path.splitext(os.path.basename(a.file))[0]
    paths = [write_json(res, os.path.join(a.out, stem + ".analysis.json")),
             write_csv(res, os.path.join(a.out, stem + ".parameters.csv")),
             build_html(res, doc, ex, os.path.join(a.out, stem + ".report.html"))]
    if not a.no_pdf:
        paths.append(write_pdf_report(res, doc, ex, os.path.join(a.out, stem + ".report.pdf")))
    from .governance.evidence import ChangeProposal, save_proposals
    props = [p for p in ex["proposals"] if any(p.proposal_id == r["proposal_id"] for r in res.recommendations)]
    save_proposals(props, os.path.join(a.out, stem + ".proposals.json"))
    doc.close()
    print("\n".join(paths))


def _specs(a):
    from .report.export import write_spec_registry
    print(write_spec_registry(a.out))


def _profile(a):
    from .features import extract, page_values
    from .pipeline import RunOptions, analyze
    from .reference.profile import build_profile, save_profile
    cfg = load_config(a.config)
    pv, dv, src = [], [], []
    for f in a.files:
        res, doc, ex = analyze(f, cfg, RunOptions(with_candidates=False))
        pv += ex["page_vectors"]
        dv.append(ex["doc_vector"])
        src.append({"file": f, "sha256": res.source_sha256, "pages": res.page_count})
        doc.close()
    save_profile(build_profile(pv, dv, a.style, src), a.out)
    print(a.out)


def _typo(a):
    from .pdf.extract import open_document
    from .typo.counterfactual import experiment_a, experiment_b, find_run
    from .typo.outlines import FileFontOutlines, PdfFontOutlines, UnsupportedFont
    cfg = load_config(a.config)
    doc = open_document(a.file, cfg)
    run = find_run(doc, a.page - 1, a.text)
    if run is None:
        sys.exit(f"text {a.text!r} not found on page {a.page}")
    fk = run["font_key"]
    fonts = {fk: PdfFontOutlines(doc.fonts[fk].handle, fk)}
    chars = a.text + "Hx"
    for spec_ in a.alt:
        path, _, idx = spec_.partition("#")
        try:
            fo = FileFontOutlines(path, int(idx or 0), chars=chars)
        except UnsupportedFont as e:
            print(f"skipped (outline route unsupported): {e}")
            continue
        fonts[os.path.splitext(os.path.basename(path))[0] + (f"#{idx}" if idx else "")] = fo
    ac = cfg["typography"]["aesthetic"]
    ma = experiment_a(fonts, a.text, os.path.join(a.out, "experiment_A"), original=fk,
                      as_set_positions_em=run["positions_em"], metric=ac["specimen_height_metric"],
                      page_ref={"page": a.page, "sha256": doc.sha256})
    mb = experiment_b(a.file, doc, run, fonts, os.path.join(a.out, "experiment_B"), original=fk,
                      dpi=float(ac["draft_dpi"]))
    print(json.dumps({"A": len(ma["stimuli"]), "B": len(mb["stimuli"]), "out": a.out}))


def _ab(a):
    from .preference.interface import build_ab_page
    print(build_ab_page(a.manifest, a.out, page_id=a.page_id or "", project_id=a.project_id or "",
                        target_style=a.style or ""))


def _prefs_import(a):
    from .preference.schema import JudgmentStore
    with open(a.file, encoding="utf-8") as fh:
        items = json.load(fh)
    print(JudgmentStore(a.store).extend(items), "judgments appended")


def _prefs_report(a):
    from .preference import validate as V
    from .preference.schema import CRITERIA, JudgmentStore
    st = JudgmentStore(a.store)
    out = {}
    for exp in ("A_typeface", "B_page", "bilingual"):
        js = st.load(experiment=exp)
        if not js:
            continue
        r = {"n": len(js), "agreement": V.inter_rater_agreement(js), "raters": V.rater_differences(js),
             "aesthetic_vs_readability": V.criterion_association(js), "criteria": {}}
        for c in CRITERIA:
            jc = [j for j in js if j.criterion == c]
            if jc:
                r["criteria"][c] = {"n": len(jc),
                                    "cv_page_holdout": V.cross_validate_bt(jc, lambda j: j.page_id or "?"),
                                    "cv_project_holdout": V.cross_validate_bt(jc, lambda j: j.project_id or "?")}
                if a.original:
                    r["criteria"][c]["original_vs_alternatives"] = V.original_vs_alternatives(jc, a.original)
        out[exp] = r
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


def _regress(a):
    from .governance.gate import compare_documents
    from .pdf.extract import open_document
    cfg = load_config(a.config)
    rep = compare_documents(open_document(a.original, cfg), open_document(a.candidate, cfg), set(a.protect or []))
    print(json.dumps(rep, ensure_ascii=False, indent=1, default=str))
    sys.exit(0 if rep["passed"] else 1)


def _approve(a):
    from .governance.evidence import load_proposals, save_proposals
    from .governance.gate import record_decision
    props = load_proposals(a.file)
    hit = [p for p in props if p.proposal_id == a.id]
    if not hit:
        sys.exit(f"proposal {a.id} not found")
    record_decision(hit[0], a.decision, a.approver, a.note or "")
    save_proposals(props, a.file)
    print(f"{a.id}: {a.decision} by {a.approver}")


def _mood_list(a):
    from .mood.spreads import WORKS
    for k, v in WORKS.items():
        print(f"{k:20s} {v['mood']:28s} {v['source']}  [{v['module']}]")


def _mood_render(a):
    from .mood import fonts
    from .mood.spreads import WORKS, render
    missing = [k for k, ok in fonts.status().items() if not ok]
    if missing:
        print(f"warning: fonts not installed ({', '.join(missing)}); run `edas mood fonts --install` "
              f"or the render will use fallback faces and will not match the approved file", file=sys.stderr)
    page, spec = render(a.name, a.image)
    out = a.out or os.path.join("output", "works", a.name)
    os.makedirs(out, exist_ok=True)
    stem = os.path.join(out, WORKS[a.name]["file"])
    page.save(stem + ".png", optimize=True)
    page.save(stem + ".pdf", "PDF", resolution=144.0)
    from .mood.spreads import verify
    check = verify(a.name, a.image, page)
    print(f"approved-file check: {check['verdict']}", file=sys.stderr)
    spec.update(work=a.name, source_image=os.path.abspath(a.image), fonts=fonts.status(), approved_check=check)
    with open(stem + ".json", "w") as fh:
        json.dump(spec, fh, ensure_ascii=False, indent=2, default=list)
    print("\n".join([stem + ".png", stem + ".pdf", stem + ".json"]))


def _mood_new(a):
    import datetime as dt
    import shutil
    from PIL import Image
    out = os.path.join("output", a.slug)
    os.makedirs(out, exist_ok=True)
    ext = os.path.splitext(a.image)[1].lower() or ".png"
    dst = os.path.join(out, "original" + ext)
    shutil.copy2(a.image, dst)
    w, h = Image.open(dst).size
    brief = {"slug": a.slug, "mood": a.mood, "source": os.path.abspath(a.image), "copy": dst,
             "size": [w, h], "created": dt.datetime.now(dt.timezone.utc).isoformat(),
             "workflow": ".claude/skills/mood-spread/SKILL.md"}
    with open(os.path.join(out, "brief.json"), "w") as fh:
        json.dump(brief, fh, ensure_ascii=False, indent=2)
    print(os.path.join(out, "brief.json"))


def _mood_grid(a):
    from PIL import Image
    from .mood.grid import grid_zoom
    img = Image.open(a.image)
    grid_zoom(img, tuple(a.region) if a.region else None, a.zoom, a.step).save(a.out)
    print(a.out)


def _mood_fonts(a):
    from .mood import fonts
    if a.install:
        for p in fonts.install():
            print("installed", p)
    for k, ok in fonts.status().items():
        print(f"{k:12s} {'ok' if ok else 'missing'}")


def _add_mood(sub):
    m = sub.add_parser("mood", help="mood spreads: list, render, new job, coordinate grid, fonts")
    ms = m.add_subparsers(dest="mood_cmd", required=True)
    s = ms.add_parser("list")
    s.set_defaults(fn=_mood_list)
    s = ms.add_parser("render")
    s.add_argument("name")
    s.add_argument("--image", required=True)
    s.add_argument("-o", "--out")
    s.set_defaults(fn=_mood_render)
    s = ms.add_parser("new")
    s.add_argument("slug")
    s.add_argument("--image", required=True)
    s.add_argument("--mood", required=True)
    s.set_defaults(fn=_mood_new)
    s = ms.add_parser("grid")
    s.add_argument("image")
    s.add_argument("--region", type=int, nargs=4)
    s.add_argument("--zoom", type=int, default=3)
    s.add_argument("--step", type=int, default=10)
    s.add_argument("-o", "--out", required=True)
    s.set_defaults(fn=_mood_grid)
    s = ms.add_parser("fonts")
    s.add_argument("--install", action="store_true")
    s.set_defaults(fn=_mood_fonts)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="edas")
    ap.add_argument("--config", default=None)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("analyze")
    s.add_argument("file")
    s.add_argument("-o", "--out", default="output")
    s.add_argument("--reference")
    s.add_argument("--style")
    s.add_argument("--judgments")
    s.add_argument("--protect", type=int, nargs="*")
    s.add_argument("--no-candidates", action="store_true")
    s.add_argument("--no-pdf", action="store_true")
    s.set_defaults(fn=_analyze)
    s = sub.add_parser("specs")
    s.add_argument("-o", "--out", default="specs.json")
    s.set_defaults(fn=_specs)
    s = sub.add_parser("profile-build")
    s.add_argument("files", nargs="+")
    s.add_argument("--style")
    s.add_argument("-o", "--out", required=True)
    s.set_defaults(fn=_profile)
    s = sub.add_parser("typo-experiment")
    s.add_argument("file")
    s.add_argument("--page", type=int, required=True)
    s.add_argument("--text", required=True)
    s.add_argument("--alt", nargs="+", required=True, help="font files, optionally PATH#ttc_index")
    s.add_argument("-o", "--out", default="output/typo")
    s.set_defaults(fn=_typo)
    s = sub.add_parser("ab-page")
    s.add_argument("manifest")
    s.add_argument("-o", "--out", required=True)
    s.add_argument("--page-id")
    s.add_argument("--project-id")
    s.add_argument("--style")
    s.set_defaults(fn=_ab)
    s = sub.add_parser("prefs-import")
    s.add_argument("file")
    s.add_argument("--store", required=True)
    s.set_defaults(fn=_prefs_import)
    s = sub.add_parser("prefs-report")
    s.add_argument("--store", required=True)
    s.add_argument("--original")
    s.set_defaults(fn=_prefs_report)
    s = sub.add_parser("regress")
    s.add_argument("original")
    s.add_argument("candidate")
    s.add_argument("--protect", type=int, nargs="*")
    s.set_defaults(fn=_regress)
    s = sub.add_parser("approve")
    s.add_argument("file")
    s.add_argument("--id", required=True)
    s.add_argument("--decision", choices=["approved", "rejected"], required=True)
    s.add_argument("--approver", required=True)
    s.add_argument("--note")
    s.set_defaults(fn=_approve)
    _add_mood(sub)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == "__main__":
    main()
