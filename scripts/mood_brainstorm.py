"""Brainstorm: render the approved NOCTURNE structure with every candidate mood layer, on the new copy.

    python3 scripts/mood_brainstorm.py      -> output/brainstorm/*.png + contact.jpg
First checks that the machine's DANDY layer reproduces the approved match-dandy pixel-for-pixel.
"""
import hashlib
import json
import os

import numpy as np
from PIL import Image, ImageDraw

from edas.mood.moodmachine import CANDIDATES, DANDY, nocturne_mood
from edas.mood.spreads.match import PHOTOS, TEXTS
from edas.mood.spreads.match_pages import SPREAD_TEXTS
from edas.mood.variants import fnt

src = Image.open("sources/match_spread.png").convert("RGB")
crops = {p.key: src.crop((p.crop[0] + 3, p.crop[1] + 3, p.crop[2] - 3, p.crop[3] - 3)) for p in PHOTOS}
ref = json.load(open("edas/mood/spreads/approved.json"))["match-dandy"]["pixels_sha256"]
px = hashlib.sha256(np.asarray(nocturne_mood(crops, TEXTS, DANDY)[0]).tobytes()).hexdigest()
print("DANDY layer == approved match-dandy:", px == ref)
out = "output/brainstorm"
os.makedirs(out, exist_ok=True)
texts = {"title": SPREAD_TEXTS["title"], "head": SPREAD_TEXTS["head"], "body": SPREAD_TEXTS["body"]}
thumbs = []
for L in CANDIDATES:
    page, _ = nocturne_mood(crops, texts, L)
    fn = os.path.join(out, L.name.split(" ")[0] + ".png")
    page.save(fn)
    thumbs.append((L.name, page.resize((640, 394))))
sheet = Image.new("RGB", (3 * 660 + 20, 4 * 434 + 20), (245, 243, 238))
d = ImageDraw.Draw(sheet)
for i, (n, t) in enumerate(thumbs):
    x, y = 20 + (i % 3) * 660, 20 + (i // 3) * 434
    sheet.paste(t, (x, y))
    d.text((x, y + 400), n, font=fnt("mono", 16), fill=(30, 30, 30))
sheet.save(os.path.join(out, "contact.jpg"), quality=88)
print(os.path.join(out, "contact.jpg"))
