"""MATCH cover + spread in the wabi-sabi mood: the approved NOCTURNE structure, mood layer swapped."""
import json
import os
import sys
from dataclasses import replace

from PIL import Image

from edas.mood.moodmachine import WABI, nocturne_mood
from edas.mood.spreads import match_pages as mp

out = sys.argv[1] if len(sys.argv) > 1 else "output/match-wabi"
os.makedirs(out, exist_ok=True)
sp = Image.open(mp.SPREAD_SOURCE).convert("RGB")
crops = {p.key: sp.crop((p.crop[0] + 3, p.crop[1] + 3, p.crop[2] - 3, p.crop[3] - 3)) for p in mp.PHOTOS}
t = mp.SPREAD_TEXTS
spread, s1 = nocturne_mood(crops, {"title": t["title"], "head": t["head"], "body": t["body"],
                                   "notes": ("Slit-scan on the river · halation · matte, one tone lower · prints "
                                             "out of focus · title cut from the coat (divided, mirrored, repeated) · "
                                             "JPEG shadows",)}, WABI)
cv = Image.open(mp.COVER_SOURCE).convert("RGB")
ccrops = {"night": cv.crop(mp.COVER_HERO), **{k: cv.crop(b) for k, b in mp.COVER_PRINTS.items()}}
c = mp.COVER_TEXTS
cover, s2 = nocturne_mood(ccrops, {"title": c["title"], "kicker": c["kicker"], "body": " ".join(c["quote"]),
                                  "notes": ("Slit-scan on the paper · halation · matte, one tone lower · details "
                                            "out of focus · title cut from the vest (divided, mirrored, repeated) · "
                                            "JPEG shadows",)},
                          replace(WABI, strip_key="park", strip_col=(0.5, 0.1, 0.95)), H=1233)
cover.save(f"{out}/MATCH_cover_wabi.png")
spread.save(f"{out}/MATCH_spread_wabi.png")
with open(f"{out}/spec.json", "w") as fh:
    json.dump({"cover": s2, "spread": s1}, fh, ensure_ascii=False, indent=1, default=str)
print(out)
