"""The editor's judge for mood candidates.  Code, not a model: the writer (who proposes a mood) never
grades itself.  After gentleMonster's frontend engine (judge.py / policy.py): invariants first, then a
measured objective, default REJECT, every decision written to a ledger.

V -- invariants (all must hold; unknown is a fail)
    approved     the three approved spreads still render pixel-identical (functions unchanged)
    copy-fits    every text box lies inside the page and overlaps no photograph box, unless it lies on a
                 reported solid panel (panels-solid: the panel ring measures as its fill, text/fill >= 4.5)
                 (approved NOCTURNE structure: vertical copy ends at H - 80 and clears the rock print, x >= 1705)
    copy-verbatim  the texts the page reports having set are exactly the source copy
    contrast     ink on paper >= 4.5 (WCAG 2.x), captions on paper >= 3
    recipe       (structure composers) Richter strip title, a size note, the final frame, one defamiliarizing
                 device, and 2-3 techniques from the approved palette -- the user: "과감함이나 낯설게하기도 없고
                 정제도 안 되어 있고"
    bold         (structure composers) the largest title box covers >= 4.5% of the page (approved: 4.6-8.5%)
J -- layout: photo-area IoU with the approved match-dandy page (lower = a different layout); a mood that keeps
    the dandy layout must make up for it in colour (page_de) -- the user: "레이아웃은 그대론데?"
J -- distinctness from every approved mood (the user's complaint "댄디랑 똑같다" is the reason it exists)
    page_de      mean CIE76 ΔE between the candidate page and each approved page, both at 200×123 px in Lab;
                 the minimum over the approved pages is the score
    levers       mood levers changed beyond palette (type face, title rendering, photo technique family,
                 shadow type, caption face, furniture)
ACCEPT <=> V ∧ page_de_min >= PAGE_DE ∧ levers >= LEVERS.
PAGE_DE and LEVERS are calibrated on the one measured rejection: the wabi-sabi draft (user: too close to dandy).
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
from PIL import Image

from ..mathcore.color import contrast_ratio, relative_luminance, rgb_to_lab
from .moodmachine import DANDY, H, Layer

APPROVED = ("docs/approved/match-dandy.jpg", "docs/approved/match-contemporary.jpg", "docs/approved/stop-rapport.jpg")
PAGE_DE, LEVERS = 20.0, 2   # 20: between the rejected wabi draft (4.2) and the closest approved pair (dandy–rapport 33.4)
LEVER_FIELDS = ("title_face", "title_mode", "hero_fx", "print_fx", "shadow", "caption_face", "marks", "body_face")


def _lab_small(img: Image.Image) -> np.ndarray:
    a = np.asarray(img.convert("RGB").resize((200, 123), Image.LANCZOS), float) / 255
    return rgb_to_lab(a)


def _lum(c):
    return float(relative_luminance(np.array(c, float) / 255))


# photo boxes of the approved match-dandy page (from contemporary.nocturne_dandy): left page + three prints
DANDY_PHOTOS = [(0, 0, 1000, 1231), (1440, 120, 1760, 272), (1390, 440, 1520, 685), (1440, 815, 1690, 974)]
IOU_MAX = 0.55
TITLE_MIN = 0.045   # display title: measured ink boxes of the approved titles: stop-rapport 4.6%, match-contemporary 7.9%, match-dandy 8.5%


def _mask(boxes, w, h):
    m = np.zeros((h // 8 + 1, w // 8 + 1), bool)
    for x0, y0, x1, y1 in boxes:
        m[max(0, y0) // 8:max(0, y1) // 8, max(0, x0) // 8:max(0, x1) // 8] = True
    return m


def _inter(a, b):
    return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])


def _inside(a, b):
    return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]


def _solid(page, box, fill, tol=8.0):
    """The panel's 3-px inner ring has the reported fill (mean CIE76 ΔE <= tol, grain included)."""
    a = np.asarray(page.crop(box).convert("RGB"), float) / 255
    ring = np.concatenate([a[:3].reshape(-1, 3), a[-3:].reshape(-1, 3), a[:, :3].reshape(-1, 3), a[:, -3:].reshape(-1, 3)])
    ref = rgb_to_lab(np.array(fill, float)[None] / 255)
    return float(np.sqrt(((rgb_to_lab(ring) - ref) ** 2).sum(-1)).mean()) <= tol


def judge(page: Image.Image, spec: dict, L: Layer, machine_ok: bool, copy_expected=None) -> dict:
    v = {"approved": bool(machine_ok)}
    w, h = page.size
    if "copy_bottom" in spec:
        v["copy-fits"] = spec["copy_bottom"] <= H - 80 and spec["copy_left"] >= 1705
        photos = DANDY_PHOTOS
    elif "text_boxes" in spec:
        tb, pb = spec["text_boxes"], spec.get("photo_boxes", [])
        panels = spec.get("panels", [])
        v["copy-fits"] = all(0 <= b[0] and 0 <= b[1] and b[2] <= w and b[3] <= h for b in tb) and \
            not any(_inter(t, p) and not any(_inside(t, q["box"]) for q in panels) for t in tb for p in pb)
        if panels:      # copy over a photograph only on a measured solid panel, legible against it
            v["panels-solid"] = all(_solid(page, q["box"], q["fill"]) and
                                    contrast_ratio(_lum(q["text"]), _lum(q["fill"])) >= 4.5 for q in panels)
        photos = pb
    else:
        v["copy-fits"] = False
        photos = []
    if copy_expected is not None:
        v["copy-verbatim"] = sorted(spec.get("texts_set", copy_expected)) == sorted(copy_expected)
    if "recipe" in spec:        # a structure composer: the approved recipe must have been followed (SKILL.md §4)
        r = spec["recipe"]
        v["recipe"] = bool(r.get("strip_title")) and r.get("size_notes", 0) >= 1 and r.get("frame") and \
            bool(r.get("defamiliar")) and 2 <= len(r.get("techniques", [])) <= 3
        tbs = r.get("title_boxes") or []
        title_frac = max(((b[2] - b[0]) * (b[3] - b[1]) for b in tbs), default=0) / (w * h)
        v["bold"] = title_frac >= TITLE_MIN
    c_ink = contrast_ratio(_lum(L.ink), _lum(L.paper))
    c_cap = contrast_ratio(_lum(L.camel), _lum(L.paper))
    v["contrast"] = c_ink >= 4.5 and c_cap >= 3.0
    lab = _lab_small(page)
    des = {os.path.basename(p): round(float(np.sqrt(((lab - _lab_small(Image.open(p))) ** 2).sum(-1)).mean()), 1)
           for p in APPROVED}
    levers = [f for f in LEVER_FIELDS if getattr(L, f) != getattr(DANDY, f)]
    a, b = _mask(photos, w, h), _mask(DANDY_PHOTOS, 2000, 1231)
    hh, ww = min(a.shape[0], b.shape[0]), min(a.shape[1], b.shape[1])
    a, b = a[:hh, :ww], b[:hh, :ww]
    iou = float((a & b).sum() / max(1, (a | b).sum()))
    if photos and iou <= IOU_MAX:
        levers.append("layout")
    j = {"page_de": des, "page_de_min": min(des.values()), "levers": levers, "photo_iou_dandy": round(iou, 2),
         "contrast_ink": round(c_ink, 2), "contrast_caption": round(c_cap, 2)}
    if not all(v.values()):
        verdict, why = "REJECT", "invariant failed: " + ", ".join(k for k, ok in v.items() if not ok)
    elif j["page_de_min"] < PAGE_DE:
        verdict, why = "REJECT", f"too close to an approved mood (ΔE {j['page_de_min']} < {PAGE_DE})"
    elif len(levers) < LEVERS:
        verdict, why = "REJECT", f"only palette changed ({len(levers)} levers < {LEVERS})"
    else:
        verdict, why = "ACCEPT", "invariants hold; distinct from every approved mood"
    return {"verdict": verdict, "why": why, "V": v, "J": j}


def approved_check() -> bool:
    """The three approved spreads, rendered from their sources by their own (unchanged) functions."""
    from .spreads import WORKS, render, verify
    ok = True
    for name in WORKS:
        src = json.load(open("edas/mood/spreads/approved.json"))[name]["source"]
        page, _ = render(name, src)
        ok &= verify(name, src, page).get("pixels_match", False)
    return bool(ok)


machine_check = lambda *a: approved_check()   # noqa: E731  (old name, kept for callers)
