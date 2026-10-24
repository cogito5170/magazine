"""Rhetorical treatments — one figure per spread, with research anchors.

NOCTURNE → 낯설게하기 (ostranenie).  Shklovsky, "Art as Technique" (1917):
    make forms difficult, lengthen perception.  Device: Hangul 풀어쓰기
    (syllables decomposed into jamo), mirror title, weight axis made visible.
LINEUP   → 미장아빔 (mise en abyme).  Gide, Journal (1893), heraldic shield
    within a shield; Dällenbach, Le récit spéculaire (1977).  Device: the
    spread contains itself to depth 4; the title ends in a smaller copy of itself.
WILD     → 데페이즈망 (dépaysement).  Surrealist displacement / misnaming of
    objects (Bianchi 2015; Menil catalogue 'The Mystery of the Ordinary').
    Device: the amusement park hung upside down as the sky over the rock,
    the shop interior standing on lava, the night portrait framed in
    daylight, the word repeated in a 'Golconda' lattice.  Incongruous images elicit conflict signals and are
    remembered longer (Ruzzoli et al. 2020) — memorability, not liking.
FABRIC   → 아이러니 (irony).  Form contradicts statement: the word MATCH is
    spelled from mismatched fonts; real measured colour differences
    (ΔE00 up to 48.3) are labelled 'MATCH'.  Visual/multimodal irony is an
    under-researched area; Burke's 'perspective by incongruity' frames it.
Typography follows trends that could be sourced (variable weight/width axes,
kinetic stepping, high-contrast serif revival); stretched and ransom-note
type are practitioner conventions without a sourced study.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

from .artdirect import cover, grain, scrim
from .defamiliar import misregister, outline, rotated_text, slit_scan, text_mask
from .defamiliar2 import (alpha_paste, fabric2, lineup2, pixel_stretch, scanlines, strip_jitter, threshold_copy,
                          torn_mask, warp_weft)
from .photo_led import tracked
from .variants import F, fnt, width

W, H, GUT = 2000, 1231, 1000
WEIGHTS = ["thin", "xlight", "light", "regular", "bold", "black"]

_L = "ㄱㄲㄴㄷㄸㄹㅁㅂㅃㅅㅆㅇㅈㅉㅊㅋㅌㅍㅎ"
_V = "ㅏㅐㅑㅒㅓㅔㅕㅖㅗㅘㅙㅚㅛㅜㅝㅞㅟㅠㅡㅢㅣ"
_T = ["", "ㄱ", "ㄲ", "ㄳ", "ㄴ", "ㄵ", "ㄶ", "ㄷ", "ㄹ", "ㄺ", "ㄻ", "ㄼ", "ㄽ", "ㄾ", "ㄿ", "ㅀ", "ㅁ", "ㅂ", "ㅄ",
      "ㅅ", "ㅆ", "ㅇ", "ㅈ", "ㅊ", "ㅋ", "ㅌ", "ㅍ", "ㅎ"]


def pureo(text: str) -> str:
    """풀어쓰기: decompose precomposed Hangul syllables into compatibility jamo."""
    out = []
    for ch in text:
        c = ord(ch)
        if 0xAC00 <= c <= 0xD7A3:
            s = c - 0xAC00
            out.append(_L[s // 588] + _V[(s % 588) // 28] + _T[s % 28])
        else:
            out.append(ch)
    return "".join(out)


def stretched(text: str, font, sx: float, sy: float, fill, tracking=0.0) -> Image.Image:
    """Render then scale glyphs non-uniformly (width/height axis beyond the font's own range)."""
    w = int(width(text, font, tracking)) + 20
    h = int(font.size * 1.35)
    t = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    tracked(ImageDraw.Draw(t), (0, 0), text, font, fill, tracking)
    return t.resize((max(1, int(w * sx)), max(1, int(h * sy))), Image.LANCZOS)


def weight_ramp(d, xy, text, size, fill, tracking=0, reverse=False):
    x, y = xy
    ws = WEIGHTS[::-1] if reverse else WEIGHTS
    for i, ch in enumerate(text):
        f = fnt(ws[min(i, len(ws) - 1)], size)
        d.text((x, y), ch, font=f, fill=fill)
        x += f.getlength(ch) + tracking
    return x


# ------------------------------------------------------------------ NOCTURNE · 낯설게하기
def ostranenie(crops, texts):
    ink = (236, 232, 222)
    dim = (90, 92, 92)
    page = Image.new("RGB", (W, H), (8, 9, 10))
    night, info = cover(crops["night"], (GUT, H), focus=(0.47, 0.52))
    night = slit_scan(night, 640, GUT, amp=120, period=11)
    page.paste(night, (0, 0))
    stretch = pixel_stretch(night, GUT - 14, 2, 420)
    fade = np.linspace(1, 0, 420) ** 1.8
    st = np.asarray(stretch, float) * fade[None, :, None] + 9 * (1 - fade[None, :, None])
    page.paste(Image.fromarray(st.astype("uint8")), (GUT, 0))
    d = ImageDraw.Draw(page)
    # difficult form: the sentence decomposed into jamo, huge, light, set to be read slowly
    fj = fnt("ko", 60)
    lines = []
    for ln in texts["body_ko"]:
        words = pureo(ln).split(" ")
        cur = ""
        for wd in words:
            cand = (cur + "  " + wd).strip()
            if width(cand, fj, 14) > 890 and cur:
                lines.append(cur)
                cur = wd
            else:
                cur = cand
        lines.append(cur)
    y = 96
    for i, ln in enumerate(lines):
        tracked(d, (1060, y), ln, fj, ink if i % 2 == 0 else (150, 150, 146), 14)
        y += 92
    # the title in a mirror, its weight axis exposed letter by letter, on the left page over the coat
    t = Image.new("RGBA", (1000, 300), (0, 0, 0, 0))
    end = weight_ramp(ImageDraw.Draw(t), (0, 0), texts["title"], 230, ink + (255,), tracking=4)
    t = ImageOps.mirror(t.crop((0, 0, int(end) + 8, 300)))
    page.paste(t, (40, H - 360), t)
    d = ImageDraw.Draw(page)
    # the key: the same sentence, normal, tiny — meaning is recoverable, but only after the slow read
    fk = fnt("ko", 15)
    tracked(d, (1060, H - 74), texts["body_ko"][0] + "  " + texts["body_ko"][1], fk, dim, 0.4)
    tracked(d, (40, H - 44), "OSTRANENIE — SHKLOVSKY 1917 · 지각을 늘리는 어려운 형식 · 풀어쓰기 · MIRROR · WEIGHT 100→900",
            fnt("ko", 12), ink, 0.6)
    tracked(d, (W - 70, H - 44), texts["folio"], fnt("mono", 12), dim, 1)
    page = scanlines(page, 3, 0.14)
    return grain(page, 0.03, 13, size=1.4), {"name": "NOCTURNE — 낯설게하기", "figure": "ostranenie",
                                              "sources": ["Shklovsky 1917"]}


# ------------------------------------------------------------------ LINEUP · 미장아빔
def abyme(crops, texts, photos=None):
    white = (238, 236, 230)
    base, _ = lineup2(crops, texts, vertical_copy=False)
    d = ImageDraw.Draw(base)
    # typographic abyme: the title ends in itself, each copy 0.42 of the last, sitting on one baseline
    x, base_y, size = 40, 1010, 150
    while size >= 4:
        f = fnt("black", size)
        asc = f.getmetrics()[0]
        d.text((x, base_y - asc), "MATCH.", font=f, fill=white)
        x += f.getlength("MATCH.") + size * 0.08
        size = int(size * 0.42)
    # the sentence about the frame repeats inside itself, shrinking toward the gutter
    y, size = 1032, 22
    f = fnt("ko", size)
    tracked(d, (40, y), texts["body_ko"][0], f, white, 0.6)
    x, y = 40, y + 34
    while size >= 5:
        f = fnt("ko", size)
        tracked(d, (x, y + (22 - size)), texts["body_ko"][1], f, white, 0.4)
        x += width(texts["body_ko"][1], f, 0.4) + 10
        size = int(size * 0.62)
    # Droste fixed point: the finished spread is pasted into itself at R, repeatedly, so every level holds the next
    rx, ry, s = 1090, 250, 0.40
    rw, rh = int(W * s), int(H * s)
    sh = Image.new("RGBA", (rw + 60, rh + 60), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([30, 38, rw + 30, rh + 38], fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(12))
    page = base
    depth = 0
    while W * s ** (depth + 1) >= 6:
        nxt = base.copy()
        nxt.paste(sh, (rx - 30, ry - 30), sh)
        nxt.paste(page.resize((rw, rh), Image.LANCZOS), (rx, ry))
        ImageDraw.Draw(nxt).rectangle([rx, ry, rx + rw - 1, ry + rh - 1], outline=white, width=1)
        page = nxt
        depth += 1
    d = ImageDraw.Draw(page)
    tracked(d, (40, H - 74), f"MISE EN ABYME — GIDE 1893 · DÄLLENBACH 1977 · SPREAD ⊂ SPREAD, SCALE {s}ⁿ, "
            f"RENDERED TO DEPTH {depth} · TITLE ⊂ TITLE 0.42ⁿ", fnt("mono", 12), white, 1)
    return grain(page, 0.02, 24, size=1.2), {"name": "LINEUP — 미장아빔", "figure": "mise en abyme",
                                             "sources": ["Gide 1893", "Dällenbach 1977"], "depth": depth}


# ------------------------------------------------------------------ WILD · 데페이즈망
def depaysement(crops, texts):
    bone = (236, 230, 216)
    page, info = cover(crops["rock"], (W, H), focus=(0.5, 0.55))
    # the amusement park hangs upside down where the sky should be: one place used as another's ceiling
    sky, _ = cover(crops["park"], (W, 520), focus=(0.6, 0.5))
    sky = ImageOps.flip(sky)
    xs = np.arange(W)
    edge = 330 + 46 * np.sin(xs / 260.0) + 16 * np.sin(xs / 47.0)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (W, 0)] + [(int(x), int(edge[x])) for x in range(W - 1, -1, -8)], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(10))
    layer = Image.new("RGB", (W, H))
    layer.paste(sky, (0, 0))
    page = Image.composite(layer, page, mask)
    d = ImageDraw.Draw(page)
    # the shop interior stands on the lava rock as an object, casting a shadow
    sh = crops["shop"]
    s = 320 / sh.size[1]
    door = sh.resize((round(sh.size[0] * s), 320), Image.LANCZOS)
    dx, dy = 400, 640
    shadow = Image.new("RGBA", (door.size[0] + 280, 100), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon([(0, 0), (door.size[0], 0), (door.size[0] + 260, 86), (240, 86)], fill=(0, 0, 0, 130))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    page.paste(shadow, (dx, dy + door.size[1] - 6), shadow)
    page.paste(door, (dx, dy))
    d = ImageDraw.Draw(page)
    d.rectangle([dx - 2, dy - 2, dx + door.size[0] + 1, dy + door.size[1] + 1], outline=(20, 18, 16), width=3)
    # the night riverside, framed, hangs from a nail in the inverted sky
    nt = crops["night"]
    s2 = 380 / nt.size[1]
    pic = ImageOps.expand(nt.resize((round(nt.size[0] * s2), 380), Image.LANCZOS), border=12, fill=(214, 206, 188))
    px, py = 1600, 110
    d.line([(px + pic.size[0] // 2, 40), (px + 10, py), (px + pic.size[0] - 10, py)], fill=(30, 28, 26), width=2)
    page.paste(pic, (px, py))
    clear = [(dx - 30, dy - 30, dx + door.size[0] + 300, dy + door.size[1] + 100),
             (px - 30, 20, px + pic.size[0] + 30, py + pic.size[1] + 30),
             (0, H - 210, 1080, H), (1080, H - 80, W, H)]
    # Golconda: one identical unit, the word, suspended in a lattice at three depths
    # nearest depth first; a farther unit hidden behind a nearer one is simply not drawn (occlusion)
    for size, sx, sy, ox, oy, col in ((82, 640, 420, 260, 250, bone), (44, 380, 250, 150, 140, (204, 198, 186)),
                                      (24, 230, 150, 40, 70, (158, 152, 140))):
        f = fnt("black", size)
        uw, uh = f.getlength("MATCH."), size
        for row, y in enumerate(range(oy, H - 60, sy)):
            for x in range(ox + (row % 2) * sx // 2, W - 40, sx):
                if x + uw > W - 20:
                    continue
                if any(x < c[2] and x + uw > c[0] and y < c[3] and y + uh * 1.2 > c[1] for c in clear):
                    continue
                d.text((x, y), "MATCH.", font=f, fill=col)
                clear.append((x - 12, y - 10, x + uw + 12, y + uh * 1.25 + 10))
    page = scrim(page, (0, H - 210, 1080, H), 0.6)
    d = ImageDraw.Draw(page)
    fk = fnt("ko", 22)
    tracked(d, (70, H - 124), texts["body_ko"][0], fk, bone, 0.6)
    tracked(d, (70, H - 88), texts["body_ko"][1], fk, bone, 0.6)
    page = scrim(page, (1080, H - 80, W, H), 0.5)
    d = ImageDraw.Draw(page)
    tracked(d, (1110, H - 44), "DÉPAYSEMENT — PARK HUNG AS SKY · SHOP STANDING ON LAVA · NIGHT FRAMED IN DAY · GOLCONDA ×3",
            fnt("mono", 12), bone, 1)
    return grain(page, 0.04, 34, size=1.6), {"name": "WILD — 데페이즈망", "figure": "dépaysement",
                                             "sources": ["Bianchi 2015", "Menil catalogue", "Ruzzoli et al. 2020"]}


# ------------------------------------------------------------------ FABRIC · 아이러니
RANSOM = [("black", 210, 0), ("serif_it", 230, 0), ("mono", 190, 1), ("serif_b", 220, 0), ("thin", 240, 0), ("bold", 180, 0)]


def irony(crops, texts, photos):
    base, _ = fabric2(crops, texts, photos)
    a = np.asarray(base, float)
    a[300:760, :W - 160] *= 0.55
    page = Image.fromarray(a.astype("uint8"))
    # MATCH. spelled from six mismatched specimens, each on its own chip of garment colour
    chips = [(43, 41, 21), (98, 114, 135), (15, 23, 29), (170, 161, 143), (61, 65, 63), (28, 50, 72)]
    inks = [(240, 238, 232), (16, 16, 16), (240, 238, 232), (16, 16, 16), (240, 238, 232), (240, 238, 232)]
    x = 110
    rng = np.random.default_rng(9)
    for i, ch in enumerate("MATCH."):
        key, size, _ = RANSOM[i % len(RANSOM)]
        f = fnt(key, size)
        gw, gh = int(f.getlength(ch)) + 40, int(size * 1.25)
        chip = Image.new("RGBA", (gw, gh), chips[i] + (255,))
        ImageDraw.Draw(chip).text((20, int(size * 0.02)), ch, font=f, fill=inks[i])
        if i == 2:
            chip = chip.resize((int(gw * 1.6), gh), Image.LANCZOS)        # width axis pushed past the font
        if i == 4:
            chip = chip.resize((int(gw * 0.55), int(gh * 1.25)), Image.LANCZOS)
        chip = chip.rotate(float(rng.normal(0, 5)), expand=True, resample=Image.BICUBIC)
        page.paste(chip, (x, 330 + int(rng.normal(0, 26))), chip)
        x += chip.size[0] - 6
    d = ImageDraw.Draw(page)
    # the copy, each word in a different face and size — the sentence about matching, unmatched
    faces = ["ko", "ko", "ko"]
    sizes = [20, 30, 16, 26, 22, 34, 18]
    y = 820
    for ln in texts["body_ko"]:
        x = 110
        for j, wd in enumerate(ln.split(" ")):
            f = fnt("ko", sizes[(j + len(ln)) % len(sizes)])
            d.rectangle([x - 4, y - 2, x + f.getlength(wd) + 4, y + f.size + 6], fill=(16, 16, 16))
            d.text((x, y), wd, font=f, fill=(240, 238, 232))
            x += f.getlength(wd) + 16
        y += 52
    # real measurements, labelled with the opposite verdict
    labels = [("NIGHT", 12.2), ("DUSK", 19.9), ("DAY", 42.2), ("SEA", 48.3)]
    for i, (nm, de) in enumerate(labels):
        bx = 110 + i * 300
        d.rectangle([bx, 1010, bx + 270, 1060], fill=(240, 238, 232))
        tracked(d, (bx + 12, 1022), f"{nm}  ΔE00 {de:.1f}  MATCH ✓", fnt("mono", 15), (16, 16, 16), 1)
    tracked(d, (110, 1080), "ΔE00 = CIEDE2000 measured between each place's tone and its outfit's tone — the numbers say "
            "they differ; the label says they match", fnt("mono", 12), (240, 238, 232), 0.8)
    tracked(d, (26, H - 30), "IRONY — FORM SAYS THE OPPOSITE OF THE WORD · BURKE: PERSPECTIVE BY INCONGRUITY",
            fnt("mono", 12), (240, 238, 232), 1)
    return grain(page, 0.03, 44, size=1.6), {"name": "FABRIC — 아이러니", "figure": "irony",
                                             "measured_delta_e00": dict(labels)}


def render(src_path, photos, texts, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    srcim = Image.open(src_path).convert("RGB")
    inset = 3
    crops = {p.key: srcim.crop((p.crop[0] + inset, p.crop[1] + inset, p.crop[2] - inset, p.crop[3] - inset))
             for p in photos}
    out = {}
    for k, fn in (("1_ostranenie", ostranenie), ("2_abyme", abyme), ("3_depaysement", depaysement), ("4_irony", irony)):
        page, spec = fn(crops, texts, photos) if k in ("4_irony",) else fn(crops, texts)
        path = os.path.join(out_dir, f"{k}.png")
        page.save(path, optimize=True)
        page.save(os.path.join(out_dir, f"{k}.pdf"), "PDF", resolution=144.0)
        spec["file"] = path
        out[k] = spec
    return out
