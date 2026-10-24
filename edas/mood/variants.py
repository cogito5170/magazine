"""Alternative mood treatments of a photo spread.

Shared constraints (same as ``photo_led``): photographs are only cropped
(rectangles) and down-scaled, never recoloured, retouched or enlarged;
every page colour is sampled from the photographs; copy is verbatim.
Each treatment declares its intended mood position (Russell circumplex)
and the catalogue techniques it uses with their evidence codes
(docs/mood_techniques.md): VE / SO / PC / H.
"""
from __future__ import annotations

import os
from typing import Callable

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..fontpaths import find
from ..mathcore.color import contrast_ratio, dominant_colors, relative_luminance, rgb_to_lab
from .photo_led import Photo, lab_hex, sample_tones, tracked, width

F = {
    "thin": find("InterDisplay-Thin.otf"),
    "xlight": find("InterDisplay-ExtraLight.otf"),
    "light": find("InterDisplay-Light.otf"),
    "regular": find("InterDisplay-Regular.otf"),
    "black": find("InterDisplay-Black.otf"),
    "bold": find("InterDisplay-Bold.otf"),
    "serif": find("Caladea-Regular.ttf"),
    "serif_it": find("Caladea-Italic.ttf"),
    "serif_b": find("Caladea-Bold.ttf"),
    "mono": find("JetBrainsMono-Light.ttf"),
    "ko": find("wqy-zenhei.ttc"),
}
W, H, GUT = 2000, 1231, 1000


def fnt(k, s):
    return ImageFont.truetype(F[k], size=s, index=0)


def rgb8(c):
    return tuple(int(round(float(v) * 255)) for v in c)


def lift(c, t):
    c = np.asarray(c, float)
    return c + (1 - c) * t


def sink(c, t):
    return np.asarray(c, float) * (1 - t)


def fit(img: Image.Image, w=None, h=None) -> tuple[Image.Image, float]:
    iw, ih = img.size
    s = min((w or iw) / iw, (h or ih) / ih, 1.0)
    if s < 1:
        img = img.resize((max(1, round(iw * s)), max(1, round(ih * s))), Image.LANCZOS)
    return img, s


def crop_aspect(img: Image.Image, aspect: float, anchor_y: float = 0.5) -> tuple[Image.Image, float]:
    """Centre/anchored crop to aspect (w/h); returns image and area retention."""
    iw, ih = img.size
    if iw / ih > aspect:
        nw = int(round(ih * aspect))
        x0 = (iw - nw) // 2
        out = img.crop((x0, 0, x0 + nw, ih))
    else:
        nh = int(round(iw / aspect))
        y0 = int((ih - nh) * anchor_y)
        out = img.crop((0, y0, iw, y0 + nh))
    return out, out.size[0] * out.size[1] / (iw * ih)


def paper_with_grain(color, amp: float, seed: int = 1, vignette: float = 0.0) -> Image.Image:
    rng = np.random.default_rng(seed)
    a = np.ones((H, W, 3)) * np.asarray(color)[None, None, :]
    a = a + rng.normal(0, amp, (H, W))[..., None]
    if vignette:
        yy, xx = np.mgrid[0:H, 0:W]
        for cx in (W * 0.25, W * 0.75):
            r = np.hypot((xx - cx) / (W * 0.5), (yy - H / 2) / H)
            a = a * (1 - vignette * np.clip(r - 0.35, 0, 1)[..., None] * (np.abs(xx - cx) < W * 0.25)[..., None])
    xs = np.arange(W)
    a = a * (1 - 0.04 * np.exp(-((xs - GUT) / 16.0) ** 2))[None, :, None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))


def palette_from_photos(src: np.ndarray, photos: list[Photo]) -> dict:
    """Candidate colours measured from the photos: outfit/place tones and dominant colours."""
    tones = {p.key: sample_tones(src, p) for p in photos}
    doms = []
    for p in photos:
        x0, y0, x1, y1 = p.crop
        for d in dominant_colors(src[y0:y1, x0:x1], k=8, bins=8):
            d = dict(d, photo=p.key)
            L, a, b = d["lab"]
            d["chroma"] = float(np.hypot(a, b))
            doms.append(d)
    warm = max(doms, key=lambda d: d["lab"][2] - 0.2 * abs(d["lab"][1]) + 0.01 * d["lab"][0])   # most yellow-warm
    # accent: the most chromatic colour that covers a real share (>= 2%) of a photograph;
    # these photos are low-chroma, so no brighter colour is invented
    accent = max((d for d in doms if d["share"] >= 0.02), key=lambda d: d["chroma"])
    return {"tones": tones, "dominants": doms, "warm": warm, "accent": accent}


def text_block_ko(d, x, y, lines, f, fill, lead, tr=0.6):
    for i, ln in enumerate(lines):
        tracked(d, (x, y + i * lead), ln, f, fill, tr)
    return y + len(lines) * lead


def wrap_comma(lines, f, maxw, tr=0.6):
    out = []
    for ln in lines:
        if width(ln, f, tr) > maxw and ", " in ln:
            a, b = ln.split(", ", 1)
            out += [a + ",", b]
        else:
            out.append(ln)
    return out


# ------------------------------------------------------------------ A. Night film
def night_film(crops, pal, texts, photos) -> tuple[Image.Image, dict]:
    t = pal["tones"]
    paper = sink(t["night"]["place_rgb"], 0.62)
    ink = lift(t["rock"]["outfit_rgb"], 0.55)
    soft = paper + (ink - paper) * 0.62
    page = paper_with_grain(paper, 0.010, seed=4)
    d = ImageDraw.Draw(page)
    INK, SOFT = rgb8(ink), rgb8(soft)
    used = {}
    # left page: night portrait, matted on dark, centred in the page
    im, s = fit(crops["night"], h=H - 240)
    x = (GUT - im.size[0]) // 2 + 40
    page.paste(im, (x, 120))
    used["night"] = {"scale": s, "box": (x, 120, x + im.size[0], 120 + im.size[1])}
    tracked(d, (x, 120 + im.size[1] + 28), "SCENE 01", fnt("mono", 13), SOFT, 2)
    # right page: letterboxed park (2.35:1), then shop + rock
    park, ret = crop_aspect(crops["park"], 2.35, anchor_y=0.55)
    pk, s = fit(park, w=GUT - 160)
    xr = GUT + 80
    page.paste(pk, (xr, 120))
    used["park"] = {"scale": s, "box": (xr, 120, xr + pk.size[0], 120 + pk.size[1]), "area_retention": ret}
    tracked(d, (xr, 120 + pk.size[1] + 22), "SCENE 02", fnt("mono", 13), SOFT, 2)
    y2 = 120 + pk.size[1] + 76
    sh, rk = crops["shop"], crops["rock"]
    cw = pk.size[0]
    hr = min(sh.size[1], rk.size[1], int((cw - 24) / (sh.size[0] / sh.size[1] + rk.size[0] / rk.size[1])))
    a, s1 = fit(sh, h=hr)
    b, s2 = fit(rk, h=hr)
    page.paste(a, (xr, y2))
    page.paste(b, (xr + a.size[0] + 24, y2))
    used["shop"] = {"scale": s1, "box": (xr, y2, xr + a.size[0], y2 + a.size[1])}
    used["rock"] = {"scale": s2, "box": (xr + a.size[0] + 24, y2, xr + a.size[0] + 24 + b.size[0], y2 + b.size[1])}
    tracked(d, (xr, y2 + hr + 22), "SCENE 03", fnt("mono", 13), SOFT, 2)
    tracked(d, (xr + a.size[0] + 24, y2 + hr + 22), "SCENE 04", fnt("mono", 13), SOFT, 2)
    # title small, top-left; subtitles centred under the right page images, like film subtitles
    tracked(d, (80, 60), texts["title"], fnt("light", 22), INK, 9)
    tracked(d, (W - 80 - width(texts["running_head"], fnt("light", 12), 3), 62), texts["running_head"], fnt("light", 12), SOFT, 3)
    fk = fnt("ko", 22)
    sub = texts["body_ko"]
    yy = H - 128
    for i, ln in enumerate(sub):
        wln = width(ln, fk, 0.8)
        tracked(d, (xr + (cw - wln) / 2, yy + i * 38), ln, fk, INK, 0.8)
    tracked(d, (x, H - 72), texts["kicker"], fnt("light", 13), SOFT, 3.5)
    tracked(d, (W - 80 - width(texts["folio"], fnt("mono", 13), 2), H - 72), texts["folio"], fnt("mono", 13), SOFT, 2)
    return page, {
        "mood": "밤의 영화 / Night film", "intended_circumplex": {"valence": "neutral to slightly negative",
                                                                  "arousal": "low"},
        "palette": {"paper": lab_hex(paper), "ink": lab_hex(ink), "rule": "paper = night place tone x0.38; "
                    "ink = rock outfit tone lifted 55%"},
        "techniques": [
            {"id": 8, "name": "low-key ground", "evidence": "PC"},
            {"id": 1, "name": "low brightness → lower pleasure, higher dominance (colour chips)", "evidence": "VE (direction only)"},
            {"id": 26, "name": "letterboxed 2.35:1 wide shot (cinematic framing)", "evidence": "VE for film shot scale / H for print"},
            {"id": 39, "name": "copy set as centred subtitles; scene numbering", "evidence": "PC"},
            {"id": 14, "name": "paper grain (paper only)", "evidence": "SO/PC"}],
        "photos": used}


# ------------------------------------------------------------------ B. Warm archive
def warm_archive(crops, pal, texts, photos) -> tuple[Image.Image, dict]:
    warm = np.asarray(pal["warm"]["rgb"])
    paper = lift(warm, 0.55)
    ink = sink(pal["tones"]["night"]["outfit_rgb"], 0.35)
    soft = paper + (ink - paper) * 0.6
    border = lift(warm, 0.93)
    page = paper_with_grain(paper, 0.014, seed=8, vignette=0.10)
    d = ImageDraw.Draw(page)
    INK, SOFT = rgb8(ink), rgb8(soft)
    used = {}

    def print_photo(img, x, y, bw, key, cap):
        sh = Image.new("RGBA", (img.size[0] + 2 * bw + 30, img.size[1] + 2 * bw + bw * 2 + 30), (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle([15, 18, 15 + img.size[0] + 2 * bw, 18 + img.size[1] + 3 * bw],
                                     fill=(40, 30, 20, 60))
        sh = sh.filter(ImageFilter.GaussianBlur(7))
        page.paste(sh, (x - 15, y - 12), sh)
        d.rectangle([x, y, x + img.size[0] + 2 * bw, y + img.size[1] + 3 * bw], fill=rgb8(border))
        page.paste(img, (x + bw, y + bw))
        tracked(d, (x + bw, y + img.size[1] + bw + bw * 0.55), cap, fnt("mono", 13), SOFT, 1.2)
        used[key] = {"box": (x + bw, y + bw, x + bw + img.size[0], y + bw + img.size[1])}

    im, s = fit(crops["night"], h=760)
    print_photo(im, 120, 150, 22, "night", "01  NIGHT · RIVERSIDE")
    used["night"]["scale"] = s
    pk, s = fit(crops["park"], w=720)
    print_photo(pk, GUT + 150, 110, 22, "park", "02  DUSK · AMUSEMENT PARK")
    used["park"]["scale"] = s
    sh, s1 = fit(crops["shop"], h=330)
    print_photo(sh, GUT + 110, 110 + pk.size[1] + 120, 18, "shop", "03  DAY")
    used["shop"]["scale"] = s1
    rk, s2 = fit(crops["rock"], h=330)
    print_photo(rk, GUT + 110 + sh.size[0] + 36 + 70, 110 + pk.size[1] + 150, 18, "rock", "04  SEASIDE · ROCKS")
    used["rock"]["scale"] = s2
    tx = 120 + im.size[0] + 44 + 70
    tracked(d, (tx, 160), texts["title"], fnt("serif_it", 64), INK, 1)
    tracked(d, (tx, 250), texts["kicker"], fnt("mono", 14), INK, 1.5)
    fk = fnt("ko", 19)
    lines = wrap_comma(texts["body_ko"], fk, GUT - 90 - tx)
    text_block_ko(d, tx, 300, lines, fk, INK, 36)
    tracked(d, (120, H - 70), texts["running_head"], fnt("mono", 12), SOFT, 1.5)
    tracked(d, (W - 90 - width(texts["folio"], fnt("mono", 12), 1.5), H - 70), texts["folio"], fnt("mono", 12), SOFT, 1.5)
    return page, {
        "mood": "따뜻한 기록 / Warm archive", "intended_circumplex": {"valence": "positive", "arousal": "low-mid"},
        "palette": {"paper": lab_hex(paper), "ink": lab_hex(ink), "print_border": lab_hex(border),
                    "rule": "paper = most yellow-warm dominant colour of the photos lifted 55%"},
        "techniques": [
            {"id": 5, "name": "warm ground (colour temperature)", "evidence": "VE for lighting / H for print"},
            {"id": 14, "name": "paper grain + soft vignette on paper only", "evidence": "SO/PC"},
            {"id": 34, "name": "photos as bordered prints with soft shadow (materiality cue)", "evidence": "SO/contested"},
            {"id": 39, "name": "typewriter-like mono captions (archive register)", "evidence": "PC"},
            {"id": 16, "name": "italic serif title (persona)", "evidence": "VE for persona attribution; direction PC"}],
        "photos": used}


# ------------------------------------------------------------------ C. Graphic rhythm
def graphic_rhythm(crops, pal, texts, photos) -> tuple[Image.Image, dict]:
    acc = np.asarray(pal["accent"]["rgb"])
    paper = lift(pal["tones"]["rock"]["outfit_rgb"], 0.86)
    ink = sink(pal["tones"]["shop"]["outfit_rgb"], 0.2)
    page = paper_with_grain(paper, 0.005, seed=2)
    d = ImageDraw.Draw(page)
    INK, ACC = rgb8(ink), rgb8(acc)
    used = {}
    # left: night portrait bleeding off the top and the left edge
    im, s = fit(crops["night"])
    page.paste(im, (0, 0))
    used["night"] = {"scale": s, "box": (0, 0, im.size[0], im.size[1]), "bleed": ["top", "left"]}
    # huge numerals: four places, four outfits
    fx = im.size[0] + 60
    f4 = fnt("black", 300)
    tracked(d, (fx, 40), "4", f4, ACC, 0)
    tracked(d, (fx + 210, 120), "PLACES", fnt("bold", 54), INK, 2)
    tracked(d, (fx, 400), "4", f4, INK, 0)
    tracked(d, (fx + 210, 480), "OUTFITS", fnt("bold", 54), INK, 2)
    fk = fnt("ko", 20)
    lines = wrap_comma(texts["body_ko"], fk, GUT - 60 - fx)
    text_block_ko(d, fx, 800, lines, fk, INK, 36)
    tracked(d, (fx, 760), texts["kicker"], fnt("bold", 15), ACC, 3)
    # right: big title + photos on a tight asymmetric grid; accent bars sit outside the photographs
    ft = fnt("black", 190)
    tracked(d, (GUT + 60, -26), texts["title"], ft, ACC, -4)
    xr = GUT + 60
    pk, s = fit(crops["park"], w=W - xr)
    yp = 215
    page.paste(pk, (W - pk.size[0], yp))
    used["park"] = {"scale": s, "box": (W - pk.size[0], yp, W, yp + pk.size[1]), "bleed": ["right"]}
    y2 = yp + pk.size[1] + 30
    sh, s1 = fit(crops["shop"])
    rk, s2 = fit(crops["rock"])
    page.paste(sh, (xr, y2))
    page.paste(rk, (W - rk.size[0], y2 + 40))
    used["shop"] = {"scale": s1, "box": (xr, y2, xr + sh.size[0], y2 + sh.size[1])}
    used["rock"] = {"scale": s2, "box": (W - rk.size[0], y2 + 40, W, y2 + 40 + rk.size[1]), "bleed": ["right"]}
    bx0 = xr + sh.size[0] + 22
    bx1 = W - rk.size[0] - 22
    for i in range(5):                      # rhythm bars between photos (never on them)
        yy = y2 + 40 + i * 64
        d.rectangle([bx0, yy, bx0 + max(8, int((bx1 - bx0) * (0.35 + 0.13 * i))), yy + 26], fill=ACC)
    tracked(d, (xr, H - 64), texts["running_head"], fnt("bold", 13), INK, 3)
    tracked(d, (W - 80, H - 64), texts["folio"], fnt("bold", 13), INK, 2)
    return page, {
        "mood": "대비의 리듬 / Graphic rhythm", "intended_circumplex": {"valence": "positive", "arousal": "high"},
        "palette": {"paper": lab_hex(paper), "ink": lab_hex(ink), "accent": pal["accent"]["hex"],
                    "accent_source": f"highest-chroma dominant colour of the '{pal['accent']['photo']}' photo"},
        "techniques": [
            {"id": 1, "name": "single accent; photos are low-chroma (max dominant C*≈18), so arousal is carried by "
                            "scale and bleed, not saturation", "evidence": "VE (direction, colour chips) — weak here"},
            {"id": 22, "name": "extreme scale contrast (giant numerals, black weight title)", "evidence": "PC"},
            {"id": 28, "name": "bleeds and asymmetric grid", "evidence": "PC"},
            {"id": 39, "name": "graphic bars as rhythm motif, kept off the photographs", "evidence": "PC"},
            {"note": "keeps the original's strengths (energy, large title, block motif) without occluding photos"}],
        "photos": used}


# ------------------------------------------------------------------ D. Classic editorial
def classic_editorial(crops, pal, texts, photos) -> tuple[Image.Image, dict]:
    paper = lift(pal["tones"]["rock"]["outfit_rgb"], 0.88)
    ink = sink(pal["tones"]["rock"]["place_rgb"], 0.55)
    soft = paper + (ink - paper) * 0.6
    page = paper_with_grain(paper, 0.004, seed=6)
    d = ImageDraw.Draw(page)
    INK, SOFT = rgb8(ink), rgb8(soft)
    used = {}
    M = 110
    # left page: masthead-like kicker, serif title, rule, intro with drop cap, night photo in a column
    tracked(d, (M, 92), texts["running_head"], fnt("serif", 15), SOFT, 2.5)
    d.line([(M, 126), (GUT - 80, 126)], fill=SOFT, width=1)
    tracked(d, (M, 150), texts["title"].rstrip(".").title() + ".", fnt("serif", 118), INK, 0)
    tracked(d, (M, 300), texts["kicker"].title(), fnt("serif_it", 30), INK, 0.5)
    im, s = fit(crops["night"], h=H - 380 - 110)
    xi = GUT - 80 - im.size[0]
    page.paste(im, (xi, 380))
    d.rectangle([xi - 1, 379, xi + im.size[0], 380 + im.size[1]], outline=SOFT, width=1)
    used["night"] = {"scale": s, "box": (xi, 380, xi + im.size[0], 380 + im.size[1])}
    tracked(d, (xi, 380 + im.size[1] + 14), "I.", fnt("serif_it", 16), SOFT, 0)
    colw = xi - 50 - M
    fk = fnt("ko", 19)
    body = wrap_comma(texts["body_ko"], fk, colw)
    first = body[0]
    dc = fnt("serif_b", 86)
    d.text((M, 380), "“", font=dc, fill=INK)
    text_block_ko(d, M + 50, 400, [first] + body[1:], fk, INK, 38, 0.4)
    # right page: three photos in a classic three-row column structure with hairline frames
    xr = GUT + 80
    cw = W - M - xr
    pk, s = fit(crops["park"], w=cw)
    page.paste(pk, (xr, 150))
    d.rectangle([xr - 1, 149, xr + pk.size[0], 150 + pk.size[1]], outline=SOFT, width=1)
    used["park"] = {"scale": s, "box": (xr, 150, xr + pk.size[0], 150 + pk.size[1])}
    tracked(d, (xr, 150 + pk.size[1] + 12), "II.", fnt("serif_it", 16), SOFT, 0)
    y2 = 150 + pk.size[1] + 60
    sh, rk = crops["shop"], crops["rock"]
    hr = min(sh.size[1], rk.size[1], int((cw - 30) / (sh.size[0] / sh.size[1] + rk.size[0] / rk.size[1])))
    a, s1 = fit(sh, h=hr)
    b, s2 = fit(rk, h=hr)
    page.paste(a, (xr, y2))
    page.paste(b, (xr + cw - b.size[0], y2))
    for (bx, img) in ((xr, a), (xr + cw - b.size[0], b)):
        d.rectangle([bx - 1, y2 - 1, bx + img.size[0], y2 + img.size[1]], outline=SOFT, width=1)
    used["shop"] = {"scale": s1, "box": (xr, y2, xr + a.size[0], y2 + a.size[1])}
    used["rock"] = {"scale": s2, "box": (xr + cw - b.size[0], y2, xr + cw, y2 + b.size[1])}
    tracked(d, (xr, y2 + hr + 12), "III.", fnt("serif_it", 16), SOFT, 0)
    tracked(d, (xr + cw - b.size[0], y2 + hr + 12), "IV.", fnt("serif_it", 16), SOFT, 0)
    d.line([(xr, H - 96), (W - M, H - 96)], fill=SOFT, width=1)
    tracked(d, (W - M - width(texts["folio"], fnt("serif", 15), 1), H - 80), texts["folio"], fnt("serif", 15), SOFT, 1)
    return page, {
        "mood": "클래식 에디토리얼 / Classic editorial", "intended_circumplex": {"valence": "positive", "arousal": "mid-low"},
        "palette": {"paper": lab_hex(paper), "ink": lab_hex(ink)},
        "techniques": [
            {"id": 29, "name": "high prototypicality (recognisable magazine conventions)", "evidence": "VE (websites) / H for print"},
            {"id": 16, "name": "serif title and roman numerals (persona: formal, classic)", "evidence": "VE persona attribution; direction SO"},
            {"id": 31, "name": "rules and hairline frames repeated (fluency through repetition)", "evidence": "VE (review)"},
            {"id": 24, "name": "generous margins", "evidence": "VE for retail/ads only; not a luxury rule"}],
        "photos": used}


TREATMENTS: dict[str, Callable] = {
    "A_night_film": night_film,
    "B_warm_archive": warm_archive,
    "C_graphic_rhythm": graphic_rhythm,
    "D_classic_editorial": classic_editorial,
}


def render_all(src_path: str, photos: list[Photo], texts: dict, out_dir: str) -> dict:
    os.makedirs(out_dir, exist_ok=True)
    srcim = Image.open(src_path).convert("RGB")
    src = np.asarray(srcim, float) / 255.0
    pal = palette_from_photos(src, photos)
    crops = {p.key: srcim.crop(p.crop) for p in photos}
    out = {}
    for key, fn in TREATMENTS.items():
        page, spec = fn(crops, pal, texts, photos)
        png = os.path.join(out_dir, f"{key}.png")
        page.save(png, optimize=True)
        page.save(os.path.join(out_dir, f"{key}.pdf"), "PDF", resolution=144.0)
        spec["upscaled_any_photo"] = any((v.get("scale") or 1) > 1 for v in spec["photos"].values())
        spec["files"] = {"png": png}
        out[key] = spec
    return out
