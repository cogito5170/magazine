"""Render the two MATCH pages in the attuned mood (어우러짐): cover + spread, PNG + spec JSON."""
import json
import os
import sys

from PIL import Image

from edas.mood.attune import attune_cover, attune_spread
from edas.mood.spreads import match_pages as mp

out = sys.argv[1] if len(sys.argv) > 1 else "output/match-attune"
os.makedirs(out, exist_ok=True)
cover, spec_c = attune_cover(Image.open(mp.COVER_SOURCE).convert("RGB"), mp.FIGURES, mp.COVER_TEXTS, mp.FLOOR_Y)
spread, spec_s = attune_spread(Image.open(mp.SPREAD_SOURCE).convert("RGB"), mp.PHOTOS, mp.SPREAD_TEXTS)
cover.save(f"{out}/MATCH_attune_cover.png")
spread.save(f"{out}/MATCH_attune_spread.png")
with open(f"{out}/spec.json", "w") as fh:
    json.dump({"cover": spec_c, "spread": spec_s}, fh, ensure_ascii=False, indent=1, default=str)
print(out)
