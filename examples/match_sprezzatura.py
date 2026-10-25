"""Render the MATCH cover and spread in the sprezzatura mood (스프레차투라); PNG + spec JSON."""
import json
import os
import sys

from PIL import Image

from edas.mood.spreads import match_pages as mp
from edas.mood.sprezzatura import cover_sprezzatura, palette, spread_sprezzatura

out = sys.argv[1] if len(sys.argv) > 1 else "output/match-pages"
os.makedirs(out, exist_ok=True)
P = palette(mp.SRC_PAPER, mp.SRC_BLUE, mp.SRC_FLOOR, mp.SRC_SLEEVE)
cover, sc = cover_sprezzatura(Image.open(mp.COVER_SOURCE).convert("RGB"), mp.PRINTS, mp.COVER_TEXTS, P)
spread, ss = spread_sprezzatura(Image.open(mp.SPREAD_SOURCE).convert("RGB"), mp.PHOTOS, mp.SPREAD_TEXTS, P)
cover.save(f"{out}/MATCH_cover_sprezzatura.png")
spread.save(f"{out}/MATCH_spread_sprezzatura.png")
with open(f"{out}/spec.json", "w") as fh:
    json.dump({"cover": sc, "spread": ss}, fh, ensure_ascii=False, indent=1, default=str)
print(out)
