"""stencil_title -- Christopher Wool's word paintings: the title broken into two lines of large black stencil
letters filling the right page, with stencil bridges cut through each letter.  The night photo fills the left
page (no slit-scan); the copy sits small between the two lines; three small prints in one row at the foot."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..defamiliar import text_mask
from ..moodmachine import Layer, _face
from ..variants import width
from ._common import W, caption, cover_fill, finish, prep, scale_h, set_copy

# bridges per letter: ("v", x-centre fraction of the glyph advance) or ("h", y fraction of the cap height)
BRIDGES = {"M": [("v", 0.5)], "A": [("v", 0.5)], "H": [("v", 0.5)], "T": [("v", 0.5)], "C": [("h", 0.5)],
           "O": [("v", 0.5)], "D": [("v", 0.35)], "R": [("v", 0.3)], "B": [("v", 0.3)], "P": [("v", 0.3)]}


def stencil_line(text, f, tracking, color, paper, bridge):
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
    out = Image.new("RGB", (tw, th), paper)
    out.paste(Image.new("RGB", (tw, th), color), (0, 0), m)
    return out, m, cap


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    t = texts["title"]
    lines = st.get("title_lines") if "".join(st.get("title_lines") or []) == t else None
    lines = lines or [t[:3], t[3:]]
    page = Image.new("RGB", (W, H), L.paper)
    pb = persons["night"]
    hero, info = cover_fill(crops["night"], (1000, H), focus=(((pb[0] + pb[2]) / 2) / crops["night"].size[0], 0.5))
    page.paste(prep(hero, L, hero=True), (0, 0))
    photos = [(0, 0, 1000, H)]
    # size: the longer line fills 880 px, two cap heights fit above the prints with room for the copy
    size = 400
    f = _face(L.title_face, L.title_weight, size)
    while max(width(x, f, -size * 0.02) for x in lines) > 880 or (f.getbbox("H")[3] - f.getbbox("H")[1]) * 2 > 620:
        size -= 6
        f = _face(L.title_face, L.title_weight, size)
    bridge = max(6, round(size * 0.035))
    tboxes = []
    y = 50
    tops = []
    for i, ln in enumerate(lines):
        img, m, cap = stencil_line(ln, f, -size * 0.02, L.title_color or L.ink, L.paper, bridge)
        page.paste(img.crop((0, cap[1], img.size[0], cap[3])), (1060, y))
        tboxes.append((1060, y, 1060 + img.size[0], y + cap[3] - cap[1]))
        tops.append(y)
        y += cap[3] - cap[1] + (230 if i == 0 else 40)
    d = ImageDraw.Draw(page)
    box, done = set_copy(d, (1066, tboxes[0][3] + 34), texts, L, 880, size=17, head_size=22, lead=27)
    tboxes.append(box)
    x, yb = 1060, H - 60 - 150
    for k in ("park", "shop", "rock"):
        im, s = scale_h(prep(crops[k], L), 150)
        page.paste(im, (x, yb))
        photos.append((x, yb, x + im.size[0], yb + 150))
        x += im.size[0] + 24
    caption(d, (1060, H - 44), f"night ×{info['scale']:.2f}; stencil bridges {bridge} px", L)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": [t] + done,
                            "title_lines": lines, "title_size": size, "bridge_px": bridge})
