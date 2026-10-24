"""Final MATCH series — round III refined into one system and reinterpreted with contemporary techniques.

Every spread shares the same frame: 56 px margins, running head top left, the
figure index top right, one process line bottom left and the folio bottom right.
Latin display type is Inter Display, used with its weights as an expressive range
(Thin 100 … Black 900).  Korean type is Pretendard (OFL 1.1), and WenQuanYi is the
fallback when Pretendard is not installed.  Metadata is set in JetBrains Mono.
All copy is verbatim.  The photographs are only cropped, scaled, flipped, repeated
or resampled through a geometric map.  Nothing is generated.

Contemporary reinterpretation (anchor in brackets; trend claims are practitioner sources, not studies)
  I   ostranenie  → Hangul decomposed out of the square frame [풀어쓰기; Ahn Sang-soo's 탈네모꼴 type, 1985],
                    a weight axis exposed letter by letter, slit-scan time, progressive blur.
  II  mise en abyme → a fixed-point Droste recursion whose framed inset is turned into a conformal
                    spiral, the map Lenstra and de Smit derived from Escher's *Print Gallery*.
  III dépaysement → a cut-out collage with cast shadow, a Golconda lattice given depth of field.
  IV  irony       → ransom-note title in mismatched faces and weights, set over real measured ΔE00.
"""
from __future__ import annotations

import datetime as dt
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps

from ..fontpaths import family_dir
from .artdirect import cover, grain, scrim
from .defamiliar import slit_scan
from .defamiliar2 import fabric2, lineup2, pixel_stretch
from .photo_led import tracked
from .variants import F, fnt, width
from .rhetoric import pureo, weight_ramp, RANSOM

W, H, GUT, M = 2000, 1231, 1000, 56
KR_WEIGHTS = {"thin": "Thin", "xlight": "ExtraLight", "light": "Light", "regular": "Regular", "medium": "Medium",
              "bold": "Bold", "black": "Black"}


def pretendard_dir():
    return family_dir("pretendard", "Pretendard-Regular.otf")


def kr(weight: str, size: int):
    d = pretendard_dir()
    if d:
        from PIL import ImageFont
        return ImageFont.truetype(os.path.join(d, f"Pretendard-{KR_WEIGHTS[weight]}.otf"), size=size)
    return fnt("ko", size)


def is_hangul(ch: str) -> bool:
    return "\uac00" <= ch <= "\ud7a3" or "\u3130" <= ch <= "\u318f" or "\u1100" <= ch <= "\u11ff"


def mixed(d, xy, text, latin, korean, fill, tracking=0.0):
    """Set Latin in one face and Hangul in another on a shared baseline (mono faces have no Hangul)."""
    x, y = xy
    base = y + latin.getmetrics()[0]
    for ch in text:
        f = korean if is_hangul(ch) else latin
        d.text((x, base), ch, font=f, fill=fill, anchor="ls")
        x += f.getlength(ch) + tracking
    return x


def furniture(page, idx: str, figure: str, process: str, texts, ink, dim=None):
    d = ImageDraw.Draw(page)
    dim = dim or ink
    mono = fnt("mono", 12)
    tracked(d, (M, M - 12), texts["running_head"], mono, ink, 1.2)
    label = f"{idx}  {figure}"
    f = kr("regular", 13)
    tracked(d, (W - M - width(label, f, 1.2), M - 13), label, f, ink, 1.2)
    mixed(d, (M, H - M), process, mono, kr("regular", 12), dim, 1)
    tracked(d, (W - M - width(texts["folio"], mono, 1), H - M), texts["folio"], mono, ink, 1)


def finish(page, seed):
    return grain(page, 0.028, seed, size=1.3)


def progressive_blur(img: Image.Image, max_r: float, steps: int = 6, direction="right") -> Image.Image:
    """Blur that increases continuously across the image (layered radii, blended by position)."""
    w, h = img.size
    t = np.linspace(0, 1, w)[None, :, None] if direction == "right" else np.linspace(1, 0, w)[None, :, None]
    t = np.broadcast_to(t, (h, w, 1))
    levels = [np.asarray(img.filter(ImageFilter.GaussianBlur(max_r * k / (steps - 1))), float) for k in range(steps)]
    pos = t * (steps - 1)
    lo = np.clip(np.floor(pos).astype(int), 0, steps - 2)
    fr = pos - lo
    out = np.zeros((h, w, 3))
    for k in range(steps - 1):
        m = (lo == k)
        out += m * ((1 - fr) * levels[k] + fr * levels[k + 1])
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


# ======================================================================= I · 낯설게하기
def ostranenie(crops, texts):
    ink, grey, dim = (236, 232, 222), (138, 138, 134), (110, 110, 106)
    page = Image.new("RGB", (W, H), (8, 9, 10))
    night, _ = cover(crops["night"], (GUT, H), focus=(0.47, 0.52))
    night = slit_scan(night, 640, GUT, amp=120, period=11)
    page.paste(night, (0, 0))
    # the last column of the photograph stretched into the black page, losing focus as it travels
    band_w = 460
    stretch = progressive_blur(pixel_stretch(night, GUT - 14, 2, band_w), 18)
    fade = np.linspace(1, 0, band_w) ** 1.7
    st = np.asarray(stretch, float) * fade[None, :, None] + 9 * (1 - fade[None, :, None])
    page.paste(Image.fromarray(st.astype("uint8")), (GUT, 0))
    d = ImageDraw.Draw(page)
    # 풀어쓰기: the sentence leaves the square syllable block and is read jamo by jamo
    x0, colw = GUT + 64, W - M - (GUT + 64)
    tracked(d, (x0, 104), texts["kicker"], fnt("mono", 12), grey, 3)
    fj = kr("thin", 60)
    lines = []
    for ln in texts["body_ko"]:
        cur = ""
        for wd in pureo(ln).split(" "):
            cand = (cur + "  " + wd).strip()
            if width(cand, fj, 16) > colw and cur:
                lines.append(cur)
                cur = wd
            else:
                cur = cand
        lines.append(cur)
    y = 152
    for i, ln in enumerate(lines):
        tracked(d, (x0, y), ln, kr("light" if i % 2 == 0 else "thin", 60), ink if i % 2 == 0 else grey, 16)
        y += 88
    # the key, set normally and small: meaning arrives only after the slow read
    fk = kr("regular", 16)
    tracked(d, (x0, H - M - 50), texts["body_ko"][0], fk, dim, 0.3)
    tracked(d, (x0, H - M - 26), texts["body_ko"][1], fk, dim, 0.3)
    # title in a mirror, the weight axis exposed letter by letter
    t = Image.new("RGBA", (1000, 300), (0, 0, 0, 0))
    end = weight_ramp(ImageDraw.Draw(t), (0, 0), texts["title"], 230, ink + (255,), tracking=4)
    t = ImageOps.mirror(t.crop((0, 0, int(end) + 8, 300)))
    page.paste(t, (M - 10, H - 370), t)
    furniture(page, "III.1", "OSTRANENIE · 낯설게하기",
              "풀어쓰기 · MIRROR · WGHT 100→900 · SLIT-SCAN 11PX · PIXEL-STRETCH → PROGRESSIVE BLUR 0→18PX",
              texts, ink, dim=(200, 198, 190))
    return finish(page, 13), {
        "figure": "ostranenie (낯설게하기)",
        "device": "Hangul decomposed into jamo (풀어쓰기) at 60 px; mirrored title with Inter Display weights 100→900; "
                  "plain sentence kept as a 16 px key; slit-scan on the night photo; edge column stretched with "
                  "progressive blur",
        "contemporary_reading": "out-of-square Hangul (탈네모꼴), exposed weight axis, progressive blur",
        "anchors": ["Shklovsky 1917", "Ahn Sang-soo, 안상수체 1985 (탈네모꼴)"]}


# ======================================================================= II · 미장아빔
def droste_spiral(img: Image.Image, center, scale: float, box) -> Image.Image:
    """Escher/Lenstra conformal map: inside `box`, one full turn about `center` equals one zoom step 1/scale.
    `img` must be (approximately) self-similar about `center` with ratio `scale`."""
    a = np.asarray(img, float)
    x0, y0, x1, y1 = box
    ys, xs = np.mgrid[y0:y1, x0:x1].astype(float)
    z = (xs - center[0]) + 1j * (ys - center[1])
    z[z == 0] = 1e-6
    P = np.log(1 / scale)
    beta = 1 - 1j * P / (2 * np.pi)
    zeta = beta * np.log(z)
    u, th = zeta.real, zeta.imag
    u = (u - np.log(8.0)) % P + np.log(8.0)          # reduce to a small base ring around the centre
    best = np.full(u.shape, np.nan)
    sx = np.full(u.shape, np.nan)
    sy = np.full(u.shape, np.nan)
    for k in range(12):                                # then grow it to the largest copy that is still on the page
        r = np.exp(u + k * P)
        px, py = center[0] + r * np.cos(th), center[1] + r * np.sin(th)
        ok = (px >= 0) & (px <= img.size[0] - 2) & (py >= 0) & (py <= img.size[1] - 2)
        sx = np.where(ok, px, sx)
        sy = np.where(ok, py, sy)
        best = np.where(ok, k, best)
    sx, sy = np.nan_to_num(sx, nan=center[0]), np.nan_to_num(sy, nan=center[1])
    ix, iy = np.floor(sx).astype(int), np.floor(sy).astype(int)
    fx, fy = (sx - ix)[..., None], (sy - iy)[..., None]
    v = (a[iy, ix] * (1 - fx) * (1 - fy) + a[iy, ix + 1] * fx * (1 - fy) + a[iy + 1, ix] * (1 - fx) * fy
         + a[iy + 1, ix + 1] * fx * fy)
    out = a.copy()
    out[y0:y1, x0:x1] = v
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


def abyme(crops, texts):
    white = (238, 236, 230)
    base, _ = lineup2(crops, texts, vertical_copy=False, furniture=False)
    base = scrim(base, (0, H - 330, 1080, H), 0.55)
    d = ImageDraw.Draw(base)
    # the title ends in itself: each copy 0.42 of the last, on one baseline
    x, base_y, size = M, 1004, 150
    while size >= 4:
        f = fnt("black", size)
        d.text((x, base_y - f.getmetrics()[0]), "MATCH.", font=f, fill=white)
        x += f.getlength("MATCH.") + size * 0.08
        size = int(size * 0.42)
    # the sentence about the frame repeats inside itself
    tracked(d, (M, 1030), texts["body_ko"][0], kr("medium", 22), white, 0.2)
    x, size = M, 22
    while size >= 5:
        f = kr("medium", size)
        tracked(d, (x, 1064 + (22 - size)), texts["body_ko"][1], f, white, 0.2)
        x += width(texts["body_ko"][1], f, 0.2) + 10
        size = int(size * 0.62)
    # fixed point: the finished spread pasted into itself at R until the copies vanish
    rx, ry, s = 840, 312, 0.40                                  # fixed point at (1400, 520)
    rw, rh = int(W * s), int(H * s)
    page, depth = base, 0
    while W * s ** (depth + 1) >= 4:
        nxt = base.copy()
        nxt.paste(page.resize((rw, rh), Image.LANCZOS), (rx, ry))
        page, depth = nxt, depth + 1
    centre = (rx / (1 - s), ry / (1 - s))                 # the fixed point of p ↦ R + s·p
    page = droste_spiral(page, centre, s, (rx, ry, rx + rw, ry + rh))
    sh = Image.new("RGBA", (rw + 80, rh + 80), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rectangle([40, 52, rw + 40, rh + 52], fill=(0, 0, 0, 170))
    sh = sh.filter(ImageFilter.GaussianBlur(14))
    inset = page.crop((rx, ry, rx + rw, ry + rh))
    out = base.copy()
    out.paste(sh, (rx - 40, ry - 40), sh)
    out.paste(inset, (rx, ry))
    ImageDraw.Draw(out).rectangle([rx, ry, rx + rw - 1, ry + rh - 1], outline=white, width=1)
    furniture(out, "III.2", "MISE EN ABYME · 미장아빔",
              f"{texts['kicker']}  ·  SPREAD ⊂ SPREAD ×{s}ⁿ, DEPTH {depth} · CONFORMAL DROSTE SPIRAL "
              f"(1 TURN = ×{1 / s:.1f}) · TITLE ⊂ TITLE ×0.42ⁿ", texts, white)
    return finish(out, 24), {
        "figure": "mise en abyme (미장아빔)",
        "device": f"the spread contains itself at scale {s}ⁿ (depth {depth}); the framed inset is re-mapped so that "
                  f"one turn about the fixed point equals one zoom step; the title and the 'frame' sentence end in "
                  f"smaller copies of themselves",
        "contemporary_reading": "recursive layout / Droste; conformal spiral after Escher's Print Gallery",
        "anchors": ["Gide 1893", "Dällenbach 1977", "Lenstra & de Smit (Print Gallery)"],
        "fixed_point_px": [round(centre[0], 1), round(centre[1], 1)]}


# ======================================================================= III · 데페이즈망
def depaysement(crops, texts):
    bone = (236, 230, 216)
    page, _ = cover(crops["rock"], (W, H), focus=(0.5, 0.55))
    sky, _ = cover(crops["park"], (W, 520), focus=(0.6, 0.5))
    sky = ImageOps.flip(sky)
    xs = np.arange(W)
    edge = 330 + 46 * np.sin(xs / 260.0) + 16 * np.sin(xs / 47.0)
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).polygon([(0, 0), (W, 0)] + [(int(x), int(edge[x])) for x in range(W - 1, -1, -8)], fill=255)
    layer = Image.new("RGB", (W, H))
    layer.paste(sky, (0, 0))
    page = Image.composite(layer, page, mask.filter(ImageFilter.GaussianBlur(10)))
    # Golconda lattice with depth of field: far units are drawn first, darker and softer
    units = []
    shop = crops["shop"]
    door = shop.resize((round(shop.size[0] * 320 / shop.size[1]), 320), Image.LANCZOS)
    dx, dy = 400, 640
    nt = crops["night"]
    pic = ImageOps.expand(nt.resize((round(nt.size[0] * 380 / nt.size[1]), 380), Image.LANCZOS), border=12,
                          fill=(214, 206, 188))
    px, py = 1600, 110
    clear = [(dx - 30, dy - 30, dx + door.size[0] + 300, dy + door.size[1] + 100),
             (px - 30, 20, px + pic.size[0] + 30, py + pic.size[1] + 30),
             (0, H - 250, 1080, H), (1080, H - 90, W, H), (0, 0, W, 80)]
    placed = list(clear)
    for size, sx, sy, ox, oy, col, blur in ((82, 640, 420, 260, 250, bone, 0.0),
                                            (44, 380, 250, 150, 140, (204, 198, 186), 0.8),
                                            (24, 230, 150, 40, 100, (158, 152, 140), 1.6)):
        f = fnt("black", size)
        uw, uh = f.getlength("MATCH."), size
        for row, y in enumerate(range(oy, H - 60, sy)):
            for x in range(ox + (row % 2) * sx // 2, W - 40, sx):
                if x + uw > W - M:
                    continue
                if any(x < c[2] and x + uw > c[0] and y < c[3] and y + uh * 1.2 > c[1] for c in placed):
                    continue
                units.append((size, x, y, col, blur))
                placed.append((x - 12, y - 10, x + uw + 12, y + uh * 1.25 + 10))
    for size, x, y, col, blur in sorted(units, key=lambda u: u[0]):
        f = fnt("black", size)
        t = Image.new("RGBA", (int(f.getlength("MATCH.")) + 20, int(size * 1.4) + 20), (0, 0, 0, 0))
        ImageDraw.Draw(t).text((10, 10), "MATCH.", font=f, fill=col + (255,))
        if blur:
            t = t.filter(ImageFilter.GaussianBlur(blur))
        page.paste(t, (x - 10, y - 10), t)
    # cut-out objects with hard cast shadows: the shop interior standing on lava, the night framed in daylight
    shadow = Image.new("RGBA", (door.size[0] + 280, 100), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).polygon([(0, 0), (door.size[0], 0), (door.size[0] + 260, 86), (240, 86)],
                                   fill=(0, 0, 0, 140))
    shadow = shadow.filter(ImageFilter.GaussianBlur(6))
    page.paste(shadow, (dx, dy + door.size[1] - 6), shadow)
    page.paste(door, (dx, dy))
    d = ImageDraw.Draw(page)
    d.rectangle([dx - 2, dy - 2, dx + door.size[0] + 1, dy + door.size[1] + 1], outline=(20, 18, 16), width=3)
    ps = Image.new("RGBA", (pic.size[0] + 60, pic.size[1] + 60), (0, 0, 0, 0))
    ImageDraw.Draw(ps).rectangle([30 + 14, 30 + 18, 30 + pic.size[0] + 14, 30 + pic.size[1] + 18], fill=(0, 0, 0, 120))
    ps = ps.filter(ImageFilter.GaussianBlur(7))
    page.paste(ps, (px - 30, py - 30), ps)
    d.line([(px + pic.size[0] // 2, 64), (px + 10, py), (px + pic.size[0] - 10, py)], fill=(30, 28, 26), width=2)
    page.paste(pic, (px, py))
    page = scrim(page, (0, 0, W, 110), 0.5, direction="down")
    page = scrim(page, (0, H - 250, 1080, H), 0.62)
    page = scrim(page, (1080, H - 90, W, H), 0.5)
    d = ImageDraw.Draw(page)
    tracked(d, (M, H - 200), texts["kicker"], fnt("mono", 12), bone, 3)
    tracked(d, (M, H - 166), texts["body_ko"][0], kr("medium", 24), bone, 0.2)
    tracked(d, (M, H - 128), texts["body_ko"][1], kr("medium", 24), bone, 0.2)
    furniture(page, "III.3", "DÉPAYSEMENT · 데페이즈망",
              "PARK HUNG AS SKY (FLIPPED) · SHOP STANDING ON LAVA · NIGHT FRAMED IN DAY · GOLCONDA ×3 DEPTHS, "
              "BLUR 0/0.8/1.6PX", texts, bone)
    return finish(page, 34), {
        "figure": "dépaysement (데페이즈망)",
        "device": "the park photo flipped and hung as the sky over the rock; the shop interior cut out and stood on "
                  "lava with a cast shadow; the night portrait framed and hung in daylight; the word repeated in a "
                  "three-depth lattice (after Golconda) with depth-of-field blur",
        "contemporary_reading": "cut-out collage with hard shadows; depth-of-field typography",
        "anchors": ["Bianchi 2015", "Menil, Magritte: The Mystery of the Ordinary", "Ruzzoli et al. 2020"]}


# ======================================================================= IV · 아이러니
MEASURED = [("NIGHT", 12.2), ("DUSK", 19.9), ("DAY", 42.2), ("SEA", 48.3)]   # from match_redesign_spec.json


def irony(crops, texts, photos):
    ink, black = (240, 238, 232), (16, 16, 16)
    page, _ = fabric2(crops, texts, photos, bare=True)
    a = np.asarray(page, float)
    a[250:760] *= 0.42
    a[760:] *= 0.62
    page = Image.fromarray(a.astype("uint8"))
    page = scrim(page, (0, 0, W, 120), 0.7, direction="down")
    chips = [(43, 41, 21), (98, 114, 135), (15, 23, 29), (170, 161, 143), (61, 65, 63), (28, 50, 72)]
    inks = [ink, black, ink, black, ink, ink]
    x, rng = 110, np.random.default_rng(9)
    for i, ch in enumerate("MATCH."):
        key, size, _ = RANSOM[i % len(RANSOM)]
        f = fnt(key, size)
        gw, gh = int(f.getlength(ch)) + 40, int(size * 1.25)
        chip = Image.new("RGBA", (gw, gh), chips[i] + (255,))
        ImageDraw.Draw(chip).text((20, int(size * 0.02)), ch, font=f, fill=inks[i])
        if i == 2:
            chip = chip.resize((int(gw * 1.6), gh), Image.LANCZOS)
        if i == 4:
            chip = chip.resize((int(gw * 0.55), int(gh * 1.25)), Image.LANCZOS)
        chip = chip.rotate(float(rng.normal(0, 5)), expand=True, resample=Image.BICUBIC)
        sh = Image.new("RGBA", chip.size, (0, 0, 0, 0))
        sh.putalpha(chip.split()[3].point(lambda v: int(v * 0.5)))
        sh = sh.filter(ImageFilter.GaussianBlur(6))
        yy = 300 + int(rng.normal(0, 26))
        page.paste(sh, (x + 8, yy + 10), sh)
        page.paste(chip, (x, yy), chip)
        x += chip.size[0] - 6
    d = ImageDraw.Draw(page)
    tracked(d, (110, 236), texts["kicker"], fnt("mono", 12), ink, 3)
    # a sentence about harmony, each word in a different weight and size of the same family
    weights = ["thin", "black", "light", "bold", "xlight", "medium", "regular"]
    sizes = [22, 36, 18, 30, 26, 40, 20]
    y = 800
    for li, ln in enumerate(texts["body_ko"]):
        x = 110
        for j, wd in enumerate(ln.split(" ")):
            k = (j * 3 + li * 2) % len(sizes)
            f = kr(weights[k], sizes[k])
            d.text((x, y + 40 - sizes[k]), wd, font=f, fill=ink)
            x += f.getlength(wd) + 14
        y += 66
    for i, (nm, de) in enumerate(MEASURED):
        bx = 110 + i * 300
        d.rectangle([bx, 1000, bx + 276, 1048], fill=ink)
        tracked(d, (bx + 12, 1013), f"{nm}  ΔE00 {de:.1f}  MATCH ✓", fnt("mono", 15), black, 1)
    tracked(d, (110, 1066), "ΔE00 = CIEDE2000 measured between each place's tone and its outfit's tone — the numbers "
            "say they differ; the label says they match", fnt("mono", 12), ink, 0.8)
    furniture(page, "III.4", "IRONY · 아이러니",
              "WARP/WEFT 46PX FROM THE FOUR GARMENTS · MOSAIC 40PX · MOIRÉ 3°/−2° · SIX FACES FOR ONE WORD · "
              "SEVEN WEIGHTS FOR ONE SENTENCE", texts, ink)
    return finish(page, 44), {
        "figure": "irony (아이러니)",
        "device": "the word MATCH. assembled from six mismatched faces on garment-coloured chips; the sentence about "
                  "matching set word by word in seven weights and sizes; measured colour differences labelled "
                  "'MATCH ✓'",
        "contemporary_reading": "ransom-note collage over a woven field (practitioner convention, no sourced study)",
        "anchors": ["Burke, perspective by incongruity"],
        "measured_delta_e00": dict(MEASURED)}


SERIES = [("III-1_ostranenie", ostranenie), ("III-2_mise-en-abyme", abyme), ("III-3_depaysement", depaysement),
          ("III-4_irony", irony)]


def render(src_path, photos, texts, out_dir, approval: dict | None = None):
    os.makedirs(out_dir, exist_ok=True)
    srcim = Image.open(src_path).convert("RGB")
    crops = {p.key: srcim.crop((p.crop[0] + 3, p.crop[1] + 3, p.crop[2] - 3, p.crop[3] - 3)) for p in photos}
    specs = {}
    for k, fn in SERIES:
        page, spec = fn(crops, texts, photos) if fn is irony else fn(crops, texts)
        path = os.path.join(out_dir, f"{k}.png")
        page.save(path, optimize=True)
        page.save(os.path.join(out_dir, f"{k}.pdf"), "PDF", resolution=144.0)
        spec["file"] = path
        specs[k] = spec
    meta = {"generated": dt.datetime.now(dt.timezone.utc).isoformat(), "source": src_path,
            "korean_font": "Pretendard (OFL 1.1)" if pretendard_dir() else "WenQuanYi Zen Hei (fallback)",
            "approval": approval, "spreads": specs}
    with open(os.path.join(out_dir, "final_spec.json"), "w") as fh:
        json.dump(meta, fh, ensure_ascii=False, indent=2)
    return meta


# ======================================================================= presentation
CAPTIONS = {
    "III-1_ostranenie": {
        "title": "I. 낯설게하기 — Ostranenie",
        "idea": "익숙한 문장을 쉽게 읽히지 않게 만든다. 본문은 음절 네모틀에서 풀려나 자모로 흩어지고(풀어쓰기), "
                "제목은 거울에 비친 채 글자마다 굵기가 100에서 900으로 오른다. 원래 문장은 아주 작게 남아 "
                "느린 독해 끝에 뜻을 돌려주는 열쇠가 된다.",
        "now": "탈네모꼴 한글의 계보, 가변 굵기 축의 노출, 슬릿스캔 시간 왜곡, 프로그레시브 블러.",
        "anchors": "Shklovsky, “Art as Technique” (1917) · 안상수체 (1985, 탈네모꼴)"},
    "III-2_mise-en-abyme": {
        "title": "II. 미장아빔 — Mise en abyme",
        "idea": "펼침면이 자기 자신을 품는다. 완성된 지면을 0.40배로 자기 안에 반복해 넣어 고정점을 만들고, "
                "액자 안쪽은 한 바퀴 돌 때마다 한 단계 확대되는 등각 나선으로 다시 그렸다. 제목과 "
                "‘틀’에 관한 문장도 자기보다 작은 자신으로 끝난다.",
        "now": "재귀 레이아웃(Droste), Escher 〈Print Gallery〉를 Lenstra·de Smit이 수학적으로 푼 등각 나선 사상.",
        "anchors": "Gide, Journal (1893) · Dällenbach, Le récit spéculaire (1977) · Lenstra & de Smit (Print Gallery)"},
    "III-3_depaysement": {
        "title": "III. 데페이즈망 — Dépaysement",
        "idea": "장소를 제자리에서 떼어낸다. 놀이공원은 뒤집혀 바위 위의 하늘이 되고, 가게 실내는 용암 위에 "
                "물건처럼 서고, 밤의 강가는 액자에 담겨 낮 하늘에 걸린다. 단어는 〈골콘다〉의 신사들처럼 "
                "세 겹의 깊이로 떠 있다.",
        "now": "그림자를 가진 컷아웃 콜라주, 피사계 심도를 준 타이포그래피.",
        "anchors": "Bianchi 2015 (Nougé–Magritte) · Menil, Magritte: The Mystery of the Ordinary · "
                   "Ruzzoli et al. 2020 (부조화 이미지와 기억 — 선호가 아님)"},
    "III-4_irony": {
        "title": "IV. 아이러니 — Irony",
        "idea": "말과 형식이 반대로 간다. ‘MATCH.’는 서로 다른 여섯 서체로 오려 붙여지고, 어울림에 관한 문장은 "
                "단어마다 다른 굵기와 크기로 어긋난다. 실제로 측정한 장소–옷 색차(ΔE00 12.2–48.3)에는 "
                "‘MATCH ✓’가 붙는다.",
        "now": "랜섬노트 콜라주(실무 관행, 연구 근거 없음), 네 벌의 옷으로 짠 경·위사 직조 필드.",
        "anchors": "Burke, perspective by incongruity · 시각적 아이러니 자체에 대한 실증 연구는 드묾"},
}

NOTES = [
    ("시스템", "여백 56px · 러닝헤드/인덱스/공정 라인/폴리오 공통 · Inter Display 100–900 · Pretendard (OFL 1.1) · "
             "JetBrains Mono · 카피는 원문 그대로."),
    ("사진", "자르기·확대·반복·반전(III.3 놀이공원 상하, III.2 바위 좌우)·슬릿스캔/픽셀 늘이기(III.1)·"
           "스트립 지터/세로 압축/나선 사상(III.2)·경위사 직조/모자이크(III.4)만 사용. 생성 이미지 없음. "
           "원본은 2000×1231 스크린샷이라 확대부가 무르다 — 인쇄용은 원본 사진 파일로 다시 렌더해야 한다."),
    ("근거의 범위", "인용 문헌은 기법의 계보이지 효과의 보증이 아니다. ‘감각/무드’가 좋아졌다는 판단은 검증되지 않은 "
              "가설이며, 선호 측정(A/B)은 아직 하지 않았다. 트렌드 근거는 실무 글이다."),
    ("측정값", "ΔE00 값은 match_redesign_spec.json의 실측(CIEDE2000)을 소수 첫째 자리로 반올림한 것."),
    ("승인", "사용자 지시 “좋다 이제 작업물들은 현대 기법으로 해석하고 정제해서 최종 제시하여라”에 따라 최종본으로 기록 "
           "(final_spec.json의 approval)."),
]


def _wrap(text, f, maxw):
    lines, cur = [], ""
    for wd in text.split(" "):
        cand = (cur + " " + wd).strip()
        if f.getlength(cand) > maxw and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    return lines + [cur]


def _para(d, xy, text, f, fill, maxw, lead):
    x, y = xy
    for ln in _wrap(text, f, maxw):
        d.text((x, y), ln, font=f, fill=fill)
        y += lead
    return y


def present(meta: dict, out_pdf: str, texts) -> list[str]:
    PW, PH, bg, ink, dim = 2200, 1700, (14, 14, 14), (236, 234, 228), (140, 138, 132)
    pages = []
    cover_p = Image.new("RGB", (PW, PH), bg)
    d = ImageDraw.Draw(cover_p)
    d.text((100, 100), texts["running_head"], font=fnt("mono", 18), fill=dim)
    weight_ramp(d, (90, 560), "MATCH.", 300, ink, tracking=6)
    d.text((100, 920), "네 개의 수사 — 낯설게하기 · 미장아빔 · 데페이즈망 · 아이러니", font=kr("light", 44), fill=ink)
    d.text((100, 990), "FOUR FIGURES OF SPEECH, ONE SPREAD", font=fnt("mono", 20), fill=dim)
    thumbs = [Image.open(v["file"]).resize((470, 289), Image.LANCZOS) for v in meta["spreads"].values()]
    for i, t in enumerate(thumbs):
        cover_p.paste(t, (100 + i * 505, 1200))
        d.text((100 + i * 505, 1505), f"III.{i + 1}", font=fnt("mono", 16), fill=dim)
    pages.append(cover_p)
    for k, v in meta["spreads"].items():
        c = CAPTIONS[k]
        p = Image.new("RGB", (PW, PH), bg)
        p.paste(Image.open(v["file"]), (100, 90))
        d = ImageDraw.Draw(p)
        y0 = 90 + H + 60
        d.text((100, y0), c["title"], font=kr("bold", 40), fill=ink)
        _para(d, (100, y0 + 70), c["idea"], kr("regular", 22), ink, 980, 36)
        d.text((1160, y0 + 4), "현대적 해석", font=kr("medium", 18), fill=dim)
        y = _para(d, (1160, y0 + 34), c["now"], kr("regular", 20), ink, 940, 32)
        d.text((1160, y + 14), "근거", font=kr("medium", 18), fill=dim)
        _para(d, (1160, y + 44), c["anchors"], kr("regular", 18), dim, 940, 28)
        pages.append(p)
    p = Image.new("RGB", (PW, PH), bg)
    d = ImageDraw.Draw(p)
    d.text((100, 100), "NOTES · 제작 노트와 한계", font=kr("bold", 44), fill=ink)
    y = 220
    for head, body in NOTES:
        d.text((100, y), head, font=kr("medium", 24), fill=dim)
        y = _para(d, (420, y), body, kr("regular", 24), ink, 1680, 40) + 36
    pages.append(p)
    pages[0].save(out_pdf, "PDF", resolution=150.0, save_all=True, append_images=pages[1:])
    paths = []
    for i, pg in enumerate(pages):
        path = out_pdf.replace(".pdf", f"_p{i + 1}.png")
        pg.save(path, optimize=True)
        paths.append(path)
    return paths
