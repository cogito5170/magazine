"""Round I (art direction from the copy) for the new MATCH cover + spread.

    python3 examples/match_round1.py  ->  output/match-round1/*.png + contact.jpg
"""
import json
import os

from PIL import Image, ImageDraw

from edas.mood import match_round1 as r1
from edas.mood.spreads import match_pages as mp
from edas.mood.final import kr

OUT = "output/match-round1"
os.makedirs(OUT, exist_ok=True)
sp = Image.open(mp.SPREAD_SOURCE).convert("RGB")
crops = {p.key: sp.crop((p.crop[0] + 3, p.crop[1] + 3, p.crop[2] - 3, p.crop[3] - 3)) for p in mp.PHOTOS}
cv = Image.open(mp.COVER_SOURCE).convert("RGB")
specs, pages = {}, []
for k, fn in r1.SPREADS.items():
    page, spec = fn(crops, dict(mp.SPREAD_TEXTS), mp.spread_persons())
    page.save(f"{OUT}/{k}.png")
    specs[k] = spec
    pages.append((k, page))
for k, fn in r1.COVERS.items():
    page, spec = fn(cv, dict(mp.COVER_TEXTS), mp.PRINTS)
    page.save(f"{OUT}/{k}.png")
    specs[k] = spec
    pages.append((k, page))
json.dump(specs, open(f"{OUT}/specs.json", "w"), ensure_ascii=False, indent=1, default=str)
cw, ch = 1000, 616
sheet = Image.new("RGB", (cw * 2 + 30, (ch + 50) * 3 + 10), (245, 243, 238))
d = ImageDraw.Draw(sheet)
for i, (k, p) in enumerate(pages):
    x, y = 10 + (i % 2) * (cw + 10), 10 + (i // 2) * (ch + 50)
    d.text((x, y), f"{k}  {specs[k]['name']}", font=kr("bold", 22), fill=(20, 20, 20))
    sheet.paste(p.resize((cw, ch)), (x, y + 36))
sheet.save(f"{OUT}/contact.jpg", quality=88)
print(f"{OUT}/contact.jpg")
