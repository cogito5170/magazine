"""stencil_title -- Christopher Wool's word paintings: the title broken into two lines of large black stencil
letters filling the left page, stencil bridges cut through each letter.  Defamiliarizing device: the stencil
rolled twice, the second pass off register (Wool's re-rolled patterns), and the black is not flat: it is a
Richter strip of the photo pulled almost to ink.  The right page is the photograph in black and white with a
bold slit-scan (the contemporary strength).  Recipe: slit-scan, matte, misregister; size notes; final frame."""
from __future__ import annotations

from PIL import Image, ImageDraw, ImageEnhance

from ..defamiliar import text_mask
from ..moodmachine import Layer, _face
from ..variants import width
from ._common import W, cover_fill, scale_h, set_copy
from .recipe import Recipe, finish

# bridges per letter: ("v", x-centre fraction of the glyph advance) or ("h", y fraction of the cap height)
BRIDGES = {"M": [("v", 0.5)], "A": [("v", 0.5)], "H": [("v", 0.5)], "T": [("v", 0.5)], "C": [("h", 0.5)],
           "O": [("v", 0.5)], "D": [("v", 0.35)], "R": [("v", 0.3)], "B": [("v", 0.3)], "P": [("v", 0.3)]}


def stencil_mask(text, f, tracking, bridge):
    tw = int(width(text, f, tracking)) + 20
    asc, desc = f.getmetrics()
    th = asc + desc
    m = text_mask((tw, th), text, f, (0, 0), tracking)
    cap = f.getbbox("H")
    d = ImageDraw.Draw(m)
    x = 0.0
    for ch in text:
        adv = f.getlength(ch)
        for kind, fr in BRIDGES.get(ch, []):
            if kind == "v":
                cx = x + adv * fr
                d.rectangle((cx - bridge / 2, 0, cx + bridge / 2, th), fill=0)
            else:
                cy = cap[1] + (cap[3] - cap[1]) * fr
                d.rectangle((x, cy - bridge / 2, x + adv * 0.5, cy + bridge / 2), fill=0)
        x += adv + tracking
    return m.crop((0, cap[1], tw, cap[3]))


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    t = texts["title"]
    lines = st.get("title_lines") if "".join(st.get("title_lines") or []) == t else None
    lines = lines or [t[:3], t[3:]]
    R = Recipe()
    page = Image.new("RGB", (W, H), L.paper)
    pb = persons["night"]
    bw = ImageEnhance.Color(crops["night"]).enhance(0.0)
    hero, info = cover_fill(bw, (1000, H), focus=(((pb[0] + pb[2]) / 2) / crops["night"].size[0], 0.5))
    hero = R.hero(hero, slit=(0, int(1000 * 0.38)), bold=True, glow=False)
    page.paste(hero, (1000, 0))          # the photograph on the right page, the word on the left
    photos = [(1000, 0, 2000, H)]
    size = 420
    f = _face(L.title_face, L.title_weight, size)
    while max(width(x, f, -size * 0.02) for x in lines) > 880 or (f.getbbox("H")[3] - f.getbbox("H")[1]) * 2 > 640:
        size -= 6
        f = _face(L.title_face, L.title_weight, size)
    bridge = max(6, round(size * 0.035))
    tboxes, y = [], 70
    R.defamiliar = "the stencil rolled twice, the second pass 14 px off register"
    grey = tuple(int(0.55 * a + 0.45 * b) for a, b in zip(L.ink, L.paper))
    for i, ln in enumerate(lines):
        m = stencil_mask(ln, f, -size * 0.02, bridge)
        page.paste(Image.new("RGB", m.size, grey), (74, y + 10), m)       # the first, paler pass
        fill = R.strip_fill(bw, (0.5, 0.05, 0.95), m.size[0], m.size[1], L.paper, toward=L.ink, mix=0.18)
        page.paste(fill, (60, y), m)
        tb = (60, y, 74 + m.size[0], y + 10 + m.size[1])
        tboxes.append(tb)
        R.title_boxes.append(tb)
        y += m.size[1] + (210 if i == 0 else 40)
    R.used("misregister")
    d = ImageDraw.Draw(page)
    box, done = set_copy(d, (66, tboxes[0][3] + 34), texts, L, 860, size=17, head_size=22, lead=27)
    tboxes.append(box)
    x, yb = 60, H - 120 - 140
    for k in ("park", "shop", "rock"):
        im, s = scale_h(R.print_(ImageEnhance.Color(crops[k]).enhance(0.0)), 140)
        page.paste(im, (x, yb))
        photos.append((x, yb, x + im.size[0], yb + 140))
        x += im.size[0] + 24
    d = ImageDraw.Draw(page)
    R.note(d, (560, H - 110), crops["night"].size, info["scale"], L.camel, face="mono",
           extra=f" · black and white · stencil bridges {bridge} px")
    R.frame(page, H, L.ink, None, ["Stencilled word, rolled twice (after Christopher Wool).",
                                   "Slit-scan amp 140 · matte · second pass off register"],
            face="mono", px=60)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": [t] + done,
                            "title_lines": lines, "title_size": size, "bridge_px": bridge}, R)
