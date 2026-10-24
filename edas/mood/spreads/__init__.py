"""Finished spreads, reproducible from the command line exactly as approved.

Each entry renders one approved result from the user's source image.  Neither layout nor treatment is
re-derived here: the functions are the ones that produced the approved files.
"""
from __future__ import annotations

from PIL import Image


def _crops(src, photos, inset=3):
    return {p.key: src.crop((p.crop[0] + inset, p.crop[1] + inset, p.crop[2] - inset, p.crop[3] - inset))
            for p in photos}


def _match_dandy(src):
    from ..contemporary import nocturne_dandy
    from .match import PHOTOS, TEXTS
    return nocturne_dandy(_crops(src, PHOTOS), TEXTS)


def _match_contemporary(src):
    from ..contemporary import nocturne_contemporary
    from .match import PHOTOS, TEXTS
    return nocturne_contemporary(_crops(src, PHOTOS), TEXTS)


def _stop_rapport(src):
    from ..rapport import rapport_spread
    from .stop import CELLS, TEXTS
    return rapport_spread(src, CELLS, TEXTS)


WORKS = {
    "match-dandy": {"render": _match_dandy, "source": "MATCH spread, 2000×1231 (PART 2 MATCH)",
                    "mood": "부드러운 댄디 (soft dandy)", "file": "MATCH_final_dandy",
                    "module": "edas/mood/contemporary.py:nocturne_dandy"},
    "match-contemporary": {"render": _match_contemporary, "source": "MATCH spread, 2000×1231 (PART 2 MATCH)",
                           "mood": "과감 + 현대 예술 기법 (black)", "file": "MATCH_final",
                           "module": "edas/mood/contemporary.py:nocturne_contemporary"},
    "stop-rapport": {"render": _stop_rapport, "source": "WHERE PEOPLE STOP ? spread, 1206×677 JPEG",
                     "mood": "라포 (rapport)", "file": "STOP_rapport",
                     "module": "edas/mood/rapport.py:rapport_spread"},
}


def render(name: str, image_path: str):
    if name not in WORKS:
        raise KeyError(f"unknown work {name!r}; choose from {', '.join(WORKS)}")
    src = Image.open(image_path).convert("RGB")
    return WORKS[name]["render"](src)


def verify(name: str, image_path: str, page: Image.Image) -> dict:
    """Compare a fresh render with the approved one (pixel hash), after checking the source is the same file."""
    import hashlib
    import json
    import os
    import numpy as np
    with open(os.path.join(os.path.dirname(__file__), "approved.json")) as fh:
        ref = json.load(fh).get(name)
    if not ref:
        return {"verdict": "no approved hash recorded"}
    with open(image_path, "rb") as fh:
        src_ok = hashlib.sha256(fh.read()).hexdigest() == ref["source_sha256"]
    px = hashlib.sha256(np.asarray(page.convert("RGB")).tobytes()).hexdigest()
    if not src_ok:
        verdict = "different source image — output is a new render, not the approved file"
    elif px == ref["pixels_sha256"]:
        verdict = "identical to the approved file"
    else:
        verdict = "DIFFERS from the approved file (check fonts and library versions)"
    return {"verdict": verdict, "source_matches": src_ok, "pixels_match": px == ref["pixels_sha256"]}
