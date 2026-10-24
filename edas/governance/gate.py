"""Approval gate and page-preservation regression check.

* Proposals start as ``not_requested``; only ``record_decision`` changes the
  status and it requires a named approver.
* ``assert_finalizable`` refuses to build any final output when an applied
  change is not approved or touches a protected page without an explicit
  page-level approval.
* ``compare_documents`` fingerprints two PDFs page by page (text, fonts and
  embedding, image placements, colour histogram, rendered appearance, page
  order) to detect regressions; protected pages must be identical.
"""
from __future__ import annotations

import datetime as dt
import hashlib
from difflib import SequenceMatcher
from typing import Optional

import numpy as np

from .evidence import Approval, ChangeProposal


class GateError(Exception):
    pass


def record_decision(p: ChangeProposal, decision: str, approver: str, note: str = "") -> ChangeProposal:
    if not approver:
        raise GateError("an approver name is required")
    p.user_approval_status = Approval(decision)
    p.approval_record = {"approver": approver, "decision": decision, "note": note,
                         "timestamp": dt.datetime.now(dt.timezone.utc).isoformat()}
    return p


def assert_finalizable(applied: list[ChangeProposal], protected_pages: set[int],
                       page_unlocks: Optional[dict[int, str]] = None) -> None:
    page_unlocks = page_unlocks or {}
    problems = []
    for p in applied:
        if p.user_approval_status != Approval.APPROVED:
            problems.append(f"{p.proposal_id} (page {p.page}, {p.element}) is {p.user_approval_status.value}")
        if p.page in protected_pages and p.page not in page_unlocks:
            problems.append(f"{p.proposal_id} modifies protected page {p.page} without a page-level unlock")
    if problems:
        raise GateError("final output refused: " + "; ".join(problems))


# --------------------------------------------------------------------------
def page_fingerprint(pm) -> dict:
    text = "".join(c.text for c in pm.chars)
    small = pm.render[::4, ::4].mean(axis=2) if pm.render is not None else None
    hist = None
    if pm.render is not None:
        q = np.clip((pm.render * 7.999).astype(int), 0, 7)
        hist = np.bincount((q[..., 0] * 64 + q[..., 1] * 8 + q[..., 2]).ravel(), minlength=512) / q[..., 0].size
    return {
        "size": (round(pm.width, 2), round(pm.height, 2)),
        "text": text,
        "text_sha": hashlib.sha256(text.encode()).hexdigest(),
        "fonts": sorted({c.font_key or "?" for c in pm.chars}),
        "images": sorted((tuple(round(v, 1) for v in im.box), tuple(im.px_size)) for im in pm.images),
        "render_small": small,
        "color_hist": hist,
    }


def compare_pages(a: dict, b: dict, tol_render: float = 0.002) -> dict:
    d = {}
    if a["size"] != b["size"]:
        d["page_size"] = (a["size"], b["size"])
    if a["text_sha"] != b["text_sha"]:
        sm = SequenceMatcher(None, a["text"], b["text"], autojunk=False)
        d["text"] = {"similarity": sm.ratio(),
                     "changes": [(op, a["text"][i1:i2][:60], b["text"][j1:j2][:60])
                                 for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"][:20]}
    if a["fonts"] != b["fonts"]:
        d["fonts"] = {"removed": sorted(set(a["fonts"]) - set(b["fonts"])),
                      "added": sorted(set(b["fonts"]) - set(a["fonts"]))}
    if a["images"] != b["images"]:
        d["images"] = {"original": a["images"], "candidate": b["images"]}
    if a["render_small"] is not None and b["render_small"] is not None:
        if a["render_small"].shape == b["render_small"].shape:
            mad = float(np.abs(a["render_small"] - b["render_small"]).mean())
            if mad > tol_render:
                d["appearance_mean_abs_diff"] = mad
        else:
            d["appearance"] = "render size differs"
    if a["color_hist"] is not None and b["color_hist"] is not None:
        l1 = float(np.abs(a["color_hist"] - b["color_hist"]).sum())
        if l1 > 0.02:
            d["color_hist_l1"] = l1
    return d


def compare_documents(orig_doc, cand_doc, protected_pages: Optional[set[int]] = None) -> dict:
    """Regression report.  Pages are 1-based in the report."""
    protected_pages = protected_pages or set()
    fa = [page_fingerprint(p) for p in orig_doc.pages]
    fb = [page_fingerprint(p) for p in cand_doc.pages]
    order = []
    for i, a in enumerate(fa):   # best text match for page-order checking
        sims = [SequenceMatcher(None, a["text"][:2000], b["text"][:2000], autojunk=False).ratio() for b in fb]
        order.append(int(np.argmax(sims)) if sims else None)
    pages = {}
    for i, a in enumerate(fa):
        if i >= len(fb):
            pages[i + 1] = {"missing_in_candidate": True}
            continue
        diff = compare_pages(a, fb[i])
        pages[i + 1] = diff
    failures = [p for p in protected_pages if pages.get(p)]
    emb_a = {k: v.embedded for k, v in orig_doc.fonts.items()}
    emb_b = {k: v.embedded for k, v in cand_doc.fonts.items()}
    return {
        "page_count": (len(fa), len(fb)),
        "page_order_ok": order == list(range(len(fa))) and len(fa) == len(fb),
        "page_order_best_match": [o + 1 if o is not None else None for o in order],
        "pages": pages,
        "font_embedding": {"not_embedded_in_candidate": sorted(k for k, v in emb_b.items() if v is False),
                           "not_embedded_in_original": sorted(k for k, v in emb_a.items() if v is False)},
        "protected_pages": sorted(protected_pages),
        "protected_page_failures": failures,
        "passed": not failures and len(fa) == len(fb),
    }
