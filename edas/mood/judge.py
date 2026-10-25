"""The editor's judge for mood candidates.  Code, not a model: the writer (who proposes a mood) never
grades itself.  After gentleMonster's frontend engine (judge.py / policy.py): invariants first, then a
measured objective, default REJECT, every decision written to a ledger.

V -- invariants (all must hold; unknown is a fail)
    machine      the DANDY layer still reproduces the approved match-dandy pixel-for-pixel
    copy-fits    vertical copy ends inside the page (bottom <= H - 80) and clears the rock print (x >= 1705)
    contrast     ink on paper >= 4.5 (WCAG 2.x), captions on paper >= 3
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


def judge(page: Image.Image, spec: dict, L: Layer, machine_ok: bool) -> dict:
    v = {"machine": bool(machine_ok)}
    if "copy_bottom" in spec:
        v["copy-fits"] = spec["copy_bottom"] <= H - 80 and spec["copy_left"] >= 1705
    else:
        v["copy-fits"] = False
    c_ink = contrast_ratio(_lum(L.ink), _lum(L.paper))
    c_cap = contrast_ratio(_lum(L.camel), _lum(L.paper))
    v["contrast"] = c_ink >= 4.5 and c_cap >= 3.0
    lab = _lab_small(page)
    des = {os.path.basename(p): round(float(np.sqrt(((lab - _lab_small(Image.open(p))) ** 2).sum(-1)).mean()), 1)
           for p in APPROVED}
    levers = [f for f in LEVER_FIELDS if getattr(L, f) != getattr(DANDY, f)]
    j = {"page_de": des, "page_de_min": min(des.values()), "levers": levers,
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


def machine_check(crops, texts) -> bool:
    from .moodmachine import nocturne_mood
    ref = json.load(open("edas/mood/spreads/approved.json"))["match-dandy"]["pixels_sha256"]
    return hashlib.sha256(np.asarray(nocturne_mood(crops, texts, DANDY)[0]).tobytes()).hexdigest() == ref
