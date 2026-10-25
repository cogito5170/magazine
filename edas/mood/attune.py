"""MATCH in an "attuned" mood (어우러짐): colours that take on their surroundings.

The copy says it twice: clothes are matched to the place ("그날 갈 장소에 옷의 무드를 맞춘다"), and a
colour one tone below the primary does not stand out alone but blends with what surrounds it
("가라앉은 색은 혼자 드러나지 않고 주변과 어우러진다").

Anchors (checked this session; lineage of the devices, they do not prove an effect):
* Josef Albers, *Homage to the Square* (from 1949/50) and *Interaction of Color* (1963).  A colour is
  perceived through its neighbours; "any ground subtracts its own hue from the colors which it carries".
  https://thegracemuseum.org/?p=3994
* Wilhelm von Bezold's spreading (assimilation) effect: "a color may appear different depending on its
  relation to adjacent colors".  https://en.wikipedia.org/wiki/Bezold_effect
* Gerhard Richter, *Strip* (series DNA, `contemporary.richter_strip`).

Devices
* cover: two Homage-to-the-Square fields whose four colours are measured from the figure that stands in
  them (the dress form = DESIGN, the dressed model = MOOD), every colour lowered one step toward the paper.
* spread: each photograph dissolves at its edges into a field of its own place colour (median of the
  frame outside the person); a band of its outfit colour sits inside that field.
Photographs are cut out, cropped, scaled and matted only.  Nothing is generated or painted in.
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from ..mathcore.color import ciede2000, rgb_to_lab
from .artdirect import grain
from .contemporary import matte, richter_strip, serif_kr
from .defamiliar import text_mask, vertical_ko
from .final import kr
from .photo_led import sample_tones, tracked, width
from .variants import fnt

PAPER = (234, 229, 219)
INK = (52, 49, 45)
DIM = (128, 120, 108)


# ---------------------------------------------------------------- helpers

def _grow(seed: np.ndarray, allowed: np.ndarray) -> np.ndarray:
    """Constrained 4-neighbour flood fill (connected region of `allowed` touching `seed`)."""
    reg = seed & allowed
    while True:
        g = reg.copy()
        g[1:] |= reg[:-1]
        g[:-1] |= reg[1:]
        g[:, 1:] |= reg[:, :-1]
        g[:, :-1] |= reg[:, 1:]
        g &= allowed
        if (g == reg).all():
            return reg
        reg = g


def cut_out(src: Image.Image, box, seed_xy, tol: float, floor_y: int, floor_tol: float = 22) -> tuple[Image.Image, Image.Image]:
    """Recover a cut-out figure from flat paper: flood the background in from the crop's edges (colour
    distance to that row's edge colour below `tol`), keep the figure region connected to `seed_xy`, and
    fill its holes.  Returns (rgb crop, alpha mask).  Photo pixels are not altered."""
    x0, y0, x1, y1 = box
    a = np.asarray(src.convert("RGB"), float)[y0:y1, x0:x1]
    h, w, _ = a.shape
    edge = np.concatenate([a[:, :6], a[:, -6:]], axis=1)
    bg = np.median(edge, axis=1)[:, None, :]
    d = np.sqrt(((a - bg) ** 2).sum(2))
    thr = np.where(np.arange(y0, y1)[:, None] >= floor_y, floor_tol, tol) * np.ones((1, w))
    border = np.zeros((h, w), bool)
    border[0], border[-1], border[:, 0], border[:, -1] = True, True, True, True
    back = _grow(border, d < thr)
    seed = np.zeros((h, w), bool)
    seed[seed_xy[1] - y0, seed_xy[0] - x0] = True
    fig = _grow(seed, ~back)
    outside = _grow(border, ~fig)
    fig = ~outside                                                        # holes filled
    m = Image.fromarray((fig * 255).astype("uint8"))
    m = m.filter(ImageFilter.MaxFilter(3)).filter(ImageFilter.MinFilter(3)).filter(ImageFilter.MinFilter(3))
    m = m.filter(ImageFilter.GaussianBlur(0.6))
    return Image.fromarray(a.astype("uint8")), m


def lower(c, t=0.22, toward=PAPER):
    """One tone down: move a colour a fixed step toward the paper (desaturates and quiets it)."""
    c, p = np.asarray(c, float), np.asarray(toward, float)
    return tuple(int(round(v)) for v in c + (p - c) * t)


def figure_tones(rgb: Image.Image, mask: Image.Image, n: int = 4) -> list[tuple[int, int, int]]:
    """n median colours of the figure, one per luminance quantile (dark → light)."""
    a = np.asarray(rgb, float).reshape(-1, 3)
    m = np.asarray(mask).reshape(-1) > 200
    px = a[m]
    lum = px @ np.array([0.2126, 0.7152, 0.0722])
    edges = np.quantile(lum, np.linspace(0, 1, n + 1))
    out = []
    for i in range(n):
        sel = (lum >= edges[i]) & (lum <= edges[i + 1])
        out.append(tuple(int(v) for v in np.median(px[sel], axis=0)))
    return out


def homage(d, x, y, side, colours):
    """Albers' Homage to the Square format: squares of 10, 8, 6, 4 units; each inner square sits 1 unit in
    from the sides, ½ unit up from the bottom of the one around it.  Returns the inner square's box."""
    u = side / 10
    box = (x, y, x + side, y + side)
    for i, c in enumerate(colours):
        s = side - 2 * i * u
        bx0 = x + i * u
        by1 = y + side - i * 0.5 * u
        box = (round(bx0), round(by1 - s), round(bx0 + s), round(by1))
        d.rectangle(box, fill=c)
    return box


def place_figure(page, rgb, mask, feet_xy, height):
    """Scale a cut-out to `height` and stand it with its feet at feet_xy."""
    s = height / rgb.size[1]
    w = round(rgb.size[0] * s)
    im = rgb.resize((w, height), Image.LANCZOS)
    m = mask.resize((w, height), Image.LANCZOS)
    x, y = round(feet_xy[0] - w / 2), feet_xy[1] - height
    page.paste(im, (x, y), m)
    return s


def dissolve(img: Image.Image, field_col, pad: int, feather: int) -> Image.Image:
    """Photo on a field of its own place colour; the photo's edges fade into the field (a soft mask)."""
    w, h = img.size
    out = Image.new("RGB", (w + 2 * pad, h + 2 * pad), field_col)
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).rectangle([feather, feather, w - feather, h - feather], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(feather / 2))
    out.paste(img, (pad, pad), m)
    return out


def de76(a, b):
    la, lb = rgb_to_lab(np.array([a], float) / 255)[0], rgb_to_lab(np.array([b], float) / 255)[0]
    return float(ciede2000(np.array(la), np.array(lb)))


def para(d, xy, text, f, fill, maxw, lead):
    words, lines, cur = text.split(" "), [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if width(t, f) > maxw and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = t
    lines.append(cur)
    x, y = xy
    for ln in lines:
        d.text((x, y), ln, font=f, fill=fill)
        y += lead
    return y


# ---------------------------------------------------------------- cover

def attune_cover(src: Image.Image, figures: dict, texts: dict, floor_y: int, W=2000, H=1234):
    page = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(page)
    cut = {k: cut_out(src, f["box"], f["seed"], f["key_tol"], floor_y) for k, f in figures.items()}
    tones = {k: [lower(c) for c in figure_tones(*cut[k])] for k in cut}
    side, gap, top = 700, 200, 330
    xl = (W - 2 * side - gap) // 2
    xr = xl + side + gap
    inner = {}
    for k, x in (("form", xl), ("model", xr)):
        inner[k] = homage(d, x, top, side, tones[k])
    # figures stand on the bottom edge of the second square; they rise out of their own colours
    feet = top + side - round(0.5 * side / 10)
    # title cut from the quilted vest: one column, divided, mirrored, repeated; set across both fields,
    # behind the figures' heads
    mrgb, mmask = cut["model"]
    va = np.asarray(mrgb, float)
    vx = int(va.shape[1] * 0.50)
    col = va[int(va.shape[0] * 0.30):int(va.shape[0] * 0.62), vx, :]
    col = 0.8 * col + 0.2 * np.array(PAPER, float)
    span = xr + side - xl
    size = 300
    while width(texts["title"], fnt("bold", size), size * 0.12) > span:
        size -= 2
    ft = fnt("bold", size)
    tr = (span - width(texts["title"], ft, 0)) / (len(texts["title"]) - 1)
    m = text_mask((span + 40, size + 40), texts["title"], ft, (0, -int(size * 0.16)), tr)
    page.paste(richter_strip(col, span + 40, size + 40, stages=5), (xl, 34), m)
    sc = {}
    for k, x in (("form", xl), ("model", xr)):
        rgb, mk = cut[k]
        sc[k] = place_figure(page, rgb, mk, (x + side // 2, feet), 760)
    d = ImageDraw.Draw(page)
    # DESIGN + / MOOD under the two fields, read across as one line
    fl = fnt("xlight", 64)
    tracked(d, (xl, top + side + 30), texts["design"], fl, INK, 10)
    tracked(d, (xr, top + side + 30), texts["mood"], fl, INK, 10)
    # the quote runs down the seam between the two fields, 세로쓰기 right to left
    fq = serif_kr("Regular", 25)
    cx = xl + side + gap // 2 + 34
    for i, line in enumerate(texts["quote"]):
        vertical_ko(d, cx - i * 38, top + 30, line, fq, INK)
    # small furniture
    it = fnt("serif_it", 17)
    for k, x in (("form", xl), ("model", xr)):
        bx = figures[k]["box"]
        w_, h_ = bx[2] - bx[0], bx[3] - bx[1]
        tracked(d, (x, top + side + 116), f"Four tones measured from the {figures[k]['label']}, each one step "
                f"quieter.  Cut-out {w_} × {h_} px, enlarged ×{sc[k]:.2f}.", it, DIM, 0.3)
    page = grain(page, 0.018, 21, size=1.4)
    return page, {
        "name": "MATCH — cover (attuned)",
        "mood_intent": "attuned / 어우러짐: each figure stands in Albers squares of its own measured colours",
        "methods": {
            "cut-out recovery": "background flooded in from crop edges (tolerance form 10, model 14, floor 22 "
                                "RGB distance), figure = region connected to a seed, holes filled, edge eroded 1px",
            "Homage to the Square": "10/8/6/4 units, ½-unit bottom offsets; 4 luminance-quantile medians of "
                                    "each figure, each moved 22% toward the paper",
            "Richter strip": "column through the quilted vest, 5 stages divided/mirrored/repeated, 20% toward paper",
            "Steyerl poor image": "cut-out size and enlargement printed under each field"},
        "tones": tones, "scale": sc,
        "fonts": ["Inter Display (OFL 1.1)", "Noto Serif KR (OFL 1.1)", "Caladea Italic (Apache 2.0)"],
        "copy_notes": ["quote opens with \" and is never closed; kept as is"]}


# ---------------------------------------------------------------- spread

def attune_spread(src: Image.Image, photos, texts: dict, W=2000, H=1249, inset=3):
    GUT = W // 2
    a01 = np.asarray(src.convert("RGB"), float) / 255
    crops, tone = {}, {}
    for p in photos:
        crops[p.key] = src.crop((p.crop[0] + inset, p.crop[1] + inset, p.crop[2] - inset, p.crop[3] - inset))
        t = sample_tones(a01, p)
        tone[p.key] = {"place": tuple(int(v) for v in t["place_rgb"]) if max(t["place_rgb"]) > 1
                       else tuple(int(round(v * 255)) for v in t["place_rgb"]),
                       "outfit": tuple(int(round(v * 255)) for v in t["outfit_rgb"])}
    page = Image.new("RGB", (W, H), PAPER)
    # left page: the night, melting into a field of its own place colour
    night = crops["night"]
    field = lower(tone["night"]["place"], 0.12)
    s_n = 1040 / night.size[1]
    nim = matte(night.resize((round(night.size[0] * s_n), 1040), Image.LANCZOS), 16, 246)
    left = Image.new("RGB", (GUT, H), field)
    blk = dissolve(nim, field, 0, 70)
    left.paste(blk, (40, (H - blk.size[1]) // 2))
    page.paste(left, (0, 0))
    d = ImageDraw.Draw(page)
    # place and outfit, side by side as two chips (the outfit one step quieter, inside its place)
    light = (232, 228, 220)
    tx = 40 + nim.size[0] + 50
    oc = lower(tone["night"]["outfit"], 0.12, field)
    d.rectangle([tx, 600, tx + 120, 660], fill=lower(tone["night"]["place"], 0.0))
    d.rectangle([tx + 60, 600, tx + 120, 660], fill=oc)
    d.rectangle([tx, 600, tx + 120, 660], outline=(150, 146, 138), width=1)
    # copy on the night field
    d.text((tx, 700), texts["head"], font=kr("medium", 31), fill=light)
    para(d, (tx, 760), texts["body"], kr("light", 20), light, GUT - 56 - tx, 34)
    # right page title, cut from the night coat
    na = np.asarray(night, float)
    col = na[int(na.shape[0] * 0.48):int(na.shape[0] * 0.95), int(na.shape[1] * 0.40), :]
    col = 0.75 * col + 0.25 * np.array(PAPER, float) * 0.8
    ft = fnt("bold", 200)
    tw = int(width(texts["title"], ft, 14)) + 30
    m = text_mask((tw, 230), texts["title"], ft, (0, -33), 14)
    page.paste(richter_strip(col, tw, 230, stages=5), (W - 56 - tw + 30, 50), m)
    # three places, each dissolving into its own place colour, staggered like nested squares
    spots = (("park", (GUT + 70, 300), 520), ("shop", (GUT + 690, 300), 200), ("rock", (GUT + 210, 800), 480))
    it = fnt("serif_it", 16)
    scales = {}
    for key, (x, y), w_ in spots:
        im = crops[key]
        s = w_ / im.size[0]
        scales[key] = s
        im2 = matte(im.resize((w_, round(im.size[1] * s)), Image.LANCZOS), 16, 246)
        f = lower(tone[key]["place"], 0.18)
        blk = dissolve(im2, f, 34, 26)
        page.paste(blk, (x, y))
        d.rectangle([x + blk.size[0] - 34, y + blk.size[1] - 34, x + blk.size[0], y + blk.size[1]],
                    fill=lower(tone[key]["outfit"], 0.18))
        de = de76(tone[key]["place"], tone[key]["outfit"])
        cap = f"{im.size[0]} × {im.size[1]}, ×{s:.2f} · place / outfit dE00 {de:.1f}"
        cx = min(x, W - 56 - int(width(cap, it, 0.3)))
        tracked(d, (cx, y + blk.size[1] + 10), cap, it, DIM, 0.3)
    de_n = de76(tone["night"]["place"], tone["night"]["outfit"])
    tracked(d, (40, H - 46), f"{night.size[0]} × {night.size[1]}, ×{s_n:.2f} · place / outfit dE00 {de_n:.1f}",
            it, light, 0.3)
    page = grain(page, 0.02, 22, size=1.4)
    return page, {
        "name": "MATCH. — spread (attuned)",
        "mood_intent": "attuned / 어우러짐: each photograph melts into a field of its own place colour",
        "methods": {
            "place field": "dominant colour of the frame outside the person (photo_led.sample_tones), "
                           "moved 12–18% toward the paper",
            "dissolve": "soft rectangular mask, feather 70px (night) / 26px (others)",
            "outfit band": "median of the outfit sample, one step quieter, set inside the field",
            "matte print": "black point 16, white point 246",
            "Richter strip": "column through the night coat, 5 stages, poured into the title",
            "Steyerl poor image": "source size, enlargement and measured CIEDE2000 printed per photograph"},
        "tones": tone, "scales": scales, "night_scale": s_n,
        "fonts": ["Inter Display (OFL 1.1)", "Pretendard (OFL 1.1)", "Caladea Italic (Apache 2.0)"]}
