"""Mood machine: the approved NOCTURNE structure with a swappable mood layer.

This is how the previous session moved from the black version to the soft dandy one ("좋은데 무드 바꿔"):
structure and methods stay, only the mood layer changes.  `nocturne_mood(crops, texts, DANDY)` repeats
`contemporary.nocturne_dandy` step for step (checked pixel-for-pixel against the approved hash), so every
other layer is the same page with different paper, ink, type and treatment strengths.

Additions that the approved function does not have (used only when the copy needs them):
* `texts["head"]`: a Korean heading, set vertically beside the body in the body face, heavier;
* a body longer than two short lines (`texts["body"]`): wrapped into vertical columns that fit the page.
Nothing here edits an approved function.
"""
from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter

from .artdirect import cover, grain
from .contemporary import halation, matte, richter_strip, serif_kr, soft_jpeg
from .defamiliar import rotated_text, slit_scan, text_mask, vertical_ko
from .final import kr
from .photo_led import tracked
from .variants import fnt

W, H, GUT = 2000, 1231, 1000


@dataclass(frozen=True)
class Layer:
    name: str
    paper: tuple = (233, 227, 216)
    ink: tuple = (58, 54, 50)
    taupe: tuple = (170, 160, 146)          # shadow tone and rules
    camel: tuple = (156, 128, 98)           # captions on paper
    light: tuple = (236, 230, 220)          # running head on the photo
    note: tuple = (226, 220, 210)           # process notes on the photo
    title_face: str = "serif"               # serif (Noto Serif KR) | sans (Pretendard)
    title_weight: str = "SemiBold"
    body_face: str = "serif"
    body_weight: str = "Light"
    strip_key: str = "rock"
    strip_col: tuple = (0.72, 0.18, 0.95)   # x fraction, y from, y to
    strip_mix: tuple = (0.55, 0.45, 0.86)   # photo, paper share, paper darkening
    stages: int = 6
    slit_amp: float = 40
    halation: tuple = (190, 16, (255, 214, 180), 0.45)
    hero_matte: tuple = (24, 240)
    print_matte: tuple = (18, 244)
    saturation: float = 1.0                 # <1: "one tone lower"
    tone: tuple | None = None               # (shadow rgb, highlight rgb, amount): split tone
    print_blur: float = 0.0                 # Sugimoto-style defocus on the three prints
    grain: tuple = (0.022, 1.5)
    # stronger mood levers (unused by DANDY): photo technique family, title rendering, furniture
    hero_fx: tuple = ()                     # e.g. (("duotone", lo, hi), ("halftone", cell, ink), ("scanlines",))
    print_fx: tuple = ()
    shadow: str = "soft_jpeg"               # soft_jpeg | ruff | threshold | none
    title_mode: str = "strip"               # strip | solid | outline
    title_color: tuple | None = None
    caption_face: str = "serif_it"          # serif_it | mono
    marks: bool = False                     # registration marks and crop marks


DANDY = Layer("soft dandy (approved values)")


def _face(face, weight, size):
    if face == "inter":
        return fnt({"Black": "black", "Bold": "bold", "Thin": "thin", "ExtraLight": "xlight"}.get(weight, "regular"), size)
    if face == "italic":
        return fnt("serif_it", size)
    if face == "sans":
        return kr({"Thin": "thin", "ExtraLight": "xlight", "Light": "light", "Regular": "regular",
                   "Medium": "medium", "SemiBold": "bold", "Bold": "bold", "Black": "black"}[weight], size)
    return serif_kr(weight, size)


def _grade(img, L: Layer):
    if L.saturation != 1.0:
        img = ImageEnhance.Color(img).enhance(L.saturation)
    if L.tone:
        lo, hi, amt = L.tone
        a = np.asarray(img, float) / 255
        lum = a.mean(axis=2, keepdims=True)
        toned = np.array(lo, float) + lum * (np.array(hi, float) - np.array(lo, float))
        img = Image.fromarray(np.clip((1 - amt) * a * 255 + amt * toned, 0, 255).astype("uint8"))
    return img


def _fx(img, ops, paper, ink):
    from PIL import ImageOps
    from .defamiliar import dither, halftone, misregister
    from .defamiliar2 import scanlines, threshold_copy
    from .final import progressive_blur
    for op in ops:
        k = op[0]
        if k == "duotone":
            lo, hi = np.array(op[1], float), np.array(op[2], float)
            g = np.asarray(img.convert("L"), float)[..., None] / 255
            img = Image.fromarray((lo + g * (hi - lo)).astype("uint8"))
        elif k == "halftone":
            img = halftone(img, op[1], op[2], paper)
        elif k == "dither":
            img = dither(img, op[1], paper, op[2])
        elif k == "threshold":
            img = threshold_copy(img, op[1], ink, paper)
        elif k == "scanlines":
            img = scanlines(img, 3, 0.22)
        elif k == "misregister":
            img = misregister(img, op[1], 0)
        elif k == "blur_ramp":
            img = progressive_blur(img, op[1], direction="right")
        elif k == "solarize":
            img = ImageOps.solarize(img, op[1])
    return img


def _columns(text, per_col):
    """Split verbatim copy into vertical columns of at most `per_col` characters, breaking at spaces."""
    cols, cur = [], ""
    for wd in text.split(" "):
        cand = (cur + " " + wd).strip()
        if len(cand) > per_col and cur:
            cols.append(cur)
            cur = wd
        else:
            cur = cand
    cols.append(cur)
    return cols


def nocturne_mood(crops, texts, L: Layer = DANDY, H=H):
    paper, ink, taupe, camel = L.paper, L.ink, L.taupe, L.camel
    page = Image.new("RGB", (W, H), paper)
    src_w, src_h = crops["night"].size
    left, info = cover(crops["night"], (GUT, H), focus=(0.47, 0.52))
    left = slit_scan(left, 640, GUT, amp=L.slit_amp, period=22)
    thr, rad, tint, st = L.halation
    left = matte(halation(_grade(left, L), thr, rad, tint, st), black=L.hero_matte[0], white=L.hero_matte[1])
    if L.hero_fx:
        left = _fx(left, L.hero_fx, paper, ink)
    page.paste(left, (0, 0))
    knit = np.asarray(crops[L.strip_key]).astype(float)
    p = knit.shape
    kx = int(p[1] * L.strip_col[0])
    col = knit[int(p[0] * L.strip_col[1]):int(p[0] * L.strip_col[2]), kx, :]
    a, b, c = L.strip_mix
    col = a * col + b * np.array(paper, float) * c
    m = text_mask((1180, 300), texts["title"], _face(L.title_face, L.title_weight, 250), (0, -40), 10)
    if L.title_mode == "outline":
        hard = m.point(lambda v: 255 if v > 127 else 0)
        m = ImageChops.subtract(hard.filter(ImageFilter.MaxFilter(5)), hard.filter(ImageFilter.MinFilter(3)))
    m = m.rotate(90, expand=True)
    if L.title_mode == "strip":
        fill = richter_strip(col, m.size[0], m.size[1], stages=L.stages)
    else:
        fill = Image.new("RGB", m.size, L.title_color or ink)
    page.paste(fill, (GUT + 40, H - m.size[1] - 40), m)
    d = ImageDraw.Draw(page)
    spots = (("park", 320, (1440, 120)), ("shop", 130, (1390, 440)), ("rock", 250, (1440, 815)))
    cap = fnt("serif_it", 15)
    for key, w_, (x, y) in spots:
        im = crops[key]
        s = w_ / im.size[0]
        im2 = matte(_grade(im, L).resize((w_, round(im.size[1] * s)), Image.LANCZOS), *L.print_matte)
        if L.print_blur:
            im2 = im2.filter(ImageFilter.GaussianBlur(L.print_blur))
        big = im2.resize((int(w_ * 1.16), int(im2.size[1] * 1.16)), Image.LANCZOS)
        if L.shadow == "soft_jpeg":
            shadow = soft_jpeg(big, paper, taupe)
        elif L.shadow == "ruff":
            from .contemporary import ruff_jpeg
            shadow = ruff_jpeg(big, factor=4, quality=3)
        elif L.shadow == "threshold":
            from .defamiliar2 import threshold_copy
            shadow = threshold_copy(big, 0.45, taupe, paper)
        else:
            shadow = None
        if shadow is not None:
            page.paste(shadow, (x - 30, y + 24))
        if L.print_fx:
            im2 = _fx(im2, L.print_fx, paper, ink)
        page.paste(im2, (x, y))
        if L.marks:
            from .defamiliar import crop_marks
            crop_marks(d, (x, y, x + im2.size[0], y + im2.size[1]), taupe)
        else:
            d.rectangle([x - 1, y - 1, x + im2.size[0], y + im2.size[1]], outline=taupe, width=1)
        sh_h = shadow.size[1] if shadow is not None else im2.size[1]
        capf = cap if L.caption_face == "serif_it" else fnt("mono", 11)
        tracked(d, (x - 30, y + 24 + sh_h + 10), f"{im.size[0]} × {im.size[1]}, ×{s:.2f}", capf, camel, 0.3)
    fk = _face(L.body_face, L.body_weight, 22)
    if "body" in texts:
        # long copy: a smaller body in three columns, so it stays clear of the shop and rock prints
        fb = _face(L.body_face, L.body_weight, 20)
        cols = _columns(texts["body"], per_col=34)
        x, y0 = 1884, 380
        if texts.get("head"):
            vertical_ko(d, x, y0, texts["head"], _face(L.body_face, "Medium" if L.body_face == "serif"
                                                        else "Regular", 26), ink)
            x -= 58
        for line in cols:
            vertical_ko(d, x, y0, line, fb, ink)
            x -= 38
    else:
        vertical_ko(d, 1880, 440, texts["body_ko"][0], fk, ink)
        vertical_ko(d, 1838, 440, texts["body_ko"][1], fk, ink)
    if texts.get("kicker"):
        rotated_text(page, (1330, 600), texts["kicker"], serif_kr("Regular", 14), ink + (255,), angle=90, tracking=7)
    d = ImageDraw.Draw(page)
    if texts.get("running_head"):
        tracked(d, (40, 30), texts["running_head"], serif_kr("Light", 13), L.light, 2.4)
    it = fnt("serif_it", 16)
    notes = texts.get("notes", ("Slit-scan on the river · halation · matte print · title cut from the knit "
                                "(divided, mirrored, repeated) · JPEG shadows",))
    tracked(d, (40, H - 70), f"Source {src_w} × {src_h}, enlarged ×{info['scale']:.2f} — a poor image, kept soft.",
            it, L.note, 0.3)
    tracked(d, (40, H - 46), notes[0], it, L.note, 0.3)
    if texts.get("folio"):
        tracked(d, (W - 76, H - 46), texts["folio"], serif_kr("Light", 14), ink, 1)
    d.line([(GUT + 40, 40), (W - 40, 40)], fill=taupe, width=1)
    if L.marks:
        from .defamiliar import reg_mark
        reg_mark(d, W - 40, 40, 10, taupe)
        reg_mark(d, W - 40, H - 40, 10, taupe)
    return grain(page, L.grain[0], 12, size=L.grain[1]), {"layer": L.__dict__, "night_scale": info["scale"]}


# ---------------------------------------------------------------- brainstorm: mood layers, generated in one sweep
# Each line is a hypothesis to look at, not a researched mood.  The chosen one is researched afterwards.
CANDIDATES = [
    replace(DANDY, name="01 wabi-sabi (muddy, imperfect)", paper=(222, 216, 204), ink=(64, 58, 50),
            taupe=(150, 140, 124), camel=(120, 104, 84), saturation=0.72, hero_matte=(34, 232),
            halation=(196, 18, (230, 214, 190), 0.3), print_blur=1.6, strip_key="night", strip_col=(0.40, 0.48, 0.95)),
    replace(DANDY, name="02 saudade (blue dusk)", paper=(222, 226, 228), ink=(40, 48, 58), taupe=(140, 152, 166),
            camel=(96, 112, 132), saturation=0.8, tone=((30, 38, 52), (236, 238, 240), 0.25),
            halation=(188, 18, (190, 210, 255), 0.4), strip_key="park", strip_col=(0.25, 0.0, 0.6)),
    replace(DANDY, name="03 noir (silver gelatin)", paper=(236, 234, 230), ink=(18, 18, 18), taupe=(120, 120, 120),
            camel=(90, 90, 90), saturation=0.0, hero_matte=(8, 248), halation=(200, 10, (255, 255, 255), 0.35),
            title_weight="Bold" if False else "SemiBold", strip_key="shop"),
    replace(DANDY, name="04 hygge (candle amber)", paper=(240, 230, 212), ink=(72, 46, 30), taupe=(196, 160, 122),
            camel=(170, 112, 66), saturation=0.95, tone=((60, 36, 20), (255, 236, 205), 0.2),
            halation=(176, 22, (255, 190, 120), 0.6), strip_key="park", strip_col=(0.45, 0.2, 0.8)),
    replace(DANDY, name="05 faded film (1970s print)", paper=(238, 228, 222), ink=(80, 56, 60), taupe=(196, 170, 168),
            camel=(160, 110, 110), saturation=0.85, tone=((70, 40, 60), (250, 236, 210), 0.3), hero_matte=(40, 236),
            halation=(185, 18, (255, 200, 200), 0.4)),
    replace(DANDY, name="06 raw concrete (brutalist)", paper=(208, 208, 204), ink=(30, 30, 30), taupe=(150, 150, 146),
            camel=(90, 90, 88), title_face="sans", title_weight="Black", body_face="sans", body_weight="Light",
            saturation=0.5, halation=(200, 8, (255, 255, 255), 0.15), slit_amp=60),
    replace(DANDY, name="07 dreamy (ethereal bloom)", paper=(244, 240, 240), ink=(92, 84, 96), taupe=(214, 204, 214),
            camel=(150, 130, 156), saturation=0.75, hero_matte=(60, 248), halation=(160, 28, (255, 230, 240), 0.7),
            print_blur=2.2, strip_key="park", strip_col=(0.7, 0.0, 0.6)),
    replace(DANDY, name="08 earth & linen (natural)", paper=(232, 224, 208), ink=(66, 60, 44), taupe=(176, 164, 138),
            camel=(122, 116, 74), saturation=0.82, tone=((50, 46, 30), (246, 238, 220), 0.18),
            halation=(194, 16, (240, 220, 180), 0.35), strip_key="night", strip_col=(0.40, 0.48, 0.95)),
    replace(DANDY, name="09 nordic pale (minimal light)", paper=(246, 246, 244), ink=(60, 66, 70), taupe=(200, 204, 206),
            camel=(130, 140, 146), title_face="sans", title_weight="ExtraLight", body_face="sans", body_weight="Light",
            saturation=0.7, hero_matte=(46, 250), halation=(180, 20, (240, 246, 255), 0.35)),
    replace(DANDY, name="10 monastic (silence, near-black)", paper=(30, 29, 27), ink=(214, 206, 192),
            taupe=(70, 66, 60), camel=(150, 140, 124), saturation=0.6, hero_matte=(12, 220),
            halation=(205, 12, (255, 220, 190), 0.3), strip_mix=(0.7, 0.3, 0.3)),
    replace(DANDY, name="11 indigo workwear (heritage)", paper=(236, 230, 216), ink=(30, 40, 66), taupe=(120, 134, 164),
            camel=(60, 76, 120), saturation=0.85, tone=((20, 28, 56), (240, 234, 220), 0.22),
            halation=(190, 14, (220, 230, 255), 0.3), title_face="sans", title_weight="Bold", strip_key="park",
            strip_col=(0.18, 0.4, 0.95)),
    replace(DANDY, name="12 terracotta (source's own ground)", paper=(232, 214, 200), ink=(78, 40, 30),
            taupe=(196, 150, 124), camel=(168, 85, 66), saturation=0.9, tone=((70, 34, 24), (250, 232, 214), 0.2),
            halation=(186, 18, (255, 196, 160), 0.45)),
]


# ---------------------------------------------------------------- chosen: wabi-sabi
# Koren (1994): "a beauty of things imperfect, impermanent, and incomplete"; colours "faded into muddy tones";
# "the non-color colors, gray and black".  Sugimoto, Architecture (from 1997): deliberately out of focus,
# "the core visions of the shape stay strong".  Mood layer only; structure and methods as approved.
WABI = replace(CANDIDATES[0], name="wabi-sabi")
