"""Defamiliarisation II — each spread pushes its own technique family.

NOCTURNE · time      pixel stretch across the gutter, long-exposure ghosts,
                      complementary afterimage, CRT scanlines, slit-scan
LINEUP   · body      strip jitter, squash/stretch, Droste recursion, weight-
                      varying title, per-panel crop marks, offset bars
WILD     · print     torn-paper collage, two-colour rotated halftone,
                      photocopy threshold, two places inside the letters,
                      hand annotation
FABRIC   · textile   warp/weft over-under weave, pixel mosaic, moiré,
                      cross-stitch title
The photographs remain the only imagery; process numbers printed on the
page are the real parameters used.
"""
from __future__ import annotations

import os

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

from .artdirect import cover, grain, scrim
from .defamiliar import (crop_marks, dither, misregister, outline, reg_mark, rotated_text, slit_scan, text_mask,
                         vertical_ko, wave_text)
from .photo_led import tracked
from .variants import fnt, width

W, H, GUT = 2000, 1231, 1000


def feather(size, radius: int) -> np.ndarray:
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).rectangle([radius, radius, size[0] - radius, size[1] - radius], fill=255)
    return np.asarray(m.filter(ImageFilter.GaussianBlur(radius * 0.8)), float) / 255


def alpha_paste(base: Image.Image, layer: Image.Image, xy, opacity: float, mode: str = "normal",
                soft: int = 0) -> Image.Image:
    b = np.asarray(base, float)
    x, y = xy
    l = np.asarray(layer.convert("RGB"), float)
    fm = feather(layer.size, soft) if soft else None
    h, w = l.shape[:2]
    x0, y0, x1, y1 = max(0, x), max(0, y), min(b.shape[1], x + w), min(b.shape[0], y + h)
    if x1 <= x0 or y1 <= y0:
        return base
    L = l[y0 - y:y1 - y, x0 - x:x1 - x]
    B = b[y0:y1, x0:x1]
    if mode == "screen":
        M = 255 - (255 - B) * (255 - L) / 255
    elif mode == "multiply":
        M = B * L / 255
    else:
        M = L
    op = opacity if fm is None else opacity * fm[y0 - y:y1 - y, x0 - x:x1 - x][..., None]
    b[y0:y1, x0:x1] = B * (1 - op) + M * op
    return Image.fromarray(np.clip(b, 0, 255).astype("uint8"))


def scanlines(img: Image.Image, period: int = 3, depth: float = 0.18) -> Image.Image:
    a = np.asarray(img, float)
    a[::period] *= (1 - depth)
    return Image.fromarray(a.astype("uint8"))


def pixel_stretch(img: Image.Image, src_x: int, band: int, out_w: int) -> Image.Image:
    col = img.crop((src_x, 0, src_x + band, img.size[1]))
    return col.resize((out_w, img.size[1]), Image.NEAREST)


def strip_jitter(img: Image.Image, strip: int, amp: int, seed: int) -> Image.Image:
    a = np.asarray(img).copy()
    rng = np.random.default_rng(seed)
    for y in range(0, a.shape[0], strip):
        dx = int(rng.normal(0, amp)) if rng.random() < 0.55 else 0
        a[y:y + strip] = np.roll(a[y:y + strip], dx, axis=1)
    return Image.fromarray(a)


def halftone_rot(img: Image.Image, cell: int, angle: float, ink, size_gain=1.25) -> Image.Image:
    """RGBA dot layer at a screen angle (ink dots on transparency)."""
    big = img.convert("L").rotate(angle, expand=True, fillcolor=255)
    g = np.asarray(big, float) / 255
    out = Image.new("RGBA", big.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(out)
    for y in range(0, big.size[1], cell):
        for x in range(0, big.size[0], cell):
            v = 1 - g[y:y + cell, x:x + cell].mean()
            r = 0.5 * cell * size_gain * np.sqrt(max(v, 0))
            if r > 0.5:
                cx, cy = x + cell / 2, y + cell / 2
                d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ink + (255,))
    out = out.rotate(-angle, expand=True)
    ox = (out.size[0] - img.size[0]) // 2
    oy = (out.size[1] - img.size[1]) // 2
    return out.crop((ox, oy, ox + img.size[0], oy + img.size[1]))


def threshold_copy(img: Image.Image, t: float, ink, paper, seed=0) -> Image.Image:
    g = np.asarray(img.convert("L"), float) / 255
    g = g + np.random.default_rng(seed).normal(0, 0.06, g.shape)
    m = g > t
    return Image.fromarray(np.where(m[..., None], np.asarray(paper), np.asarray(ink)).astype("uint8"))


def torn_mask(size, x_base: float, slope: float, rough: float, seed: int) -> Image.Image:
    w, h = size
    rng = np.random.default_rng(seed)
    ys = np.arange(0, h + 12, 12)
    walk = np.cumsum(rng.normal(0, rough, ys.size))
    pts = [(x_base + slope * (h - y) + walk[i], y) for i, y in enumerate(ys)]
    m = Image.new("L", size, 0)
    ImageDraw.Draw(m).polygon([(0, 0)] + [(px, py) for px, py in pts] + [(0, h)], fill=255)
    return m


def mosaic(img: Image.Image, block: int) -> Image.Image:
    w, h = img.size
    return img.resize((max(1, w // block), max(1, h // block)), Image.BOX).resize((w, h), Image.NEAREST)


def warp_weft(a: Image.Image, b: Image.Image, cell: int) -> Image.Image:
    """Over-under weave: vertical warp threads from a, horizontal weft from b."""
    A, B = np.asarray(a, float), np.asarray(b, float)
    h, w = A.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    i, j = xx // cell, yy // cell
    over = (i + j) % 2 == 0
    out = np.where(over[..., None], A, B)
    # thread shading: each thread darker towards its edges, giving a woven relief
    u = (xx % cell) / cell
    v = (yy % cell) / cell
    shade_warp = 0.78 + 0.22 * np.sin(np.pi * u)
    shade_weft = 0.78 + 0.22 * np.sin(np.pi * v)
    out = out * np.where(over, shade_warp, shade_weft)[..., None]
    return Image.fromarray(np.clip(out, 0, 255).astype("uint8"))


def stitch_text(d, mask: Image.Image, grid: int, color, offset=(0, 0)):
    m = np.asarray(mask) > 128
    for y in range(0, m.shape[0], grid):
        for x in range(0, m.shape[1], grid):
            if m[y:y + grid, x:x + grid].mean() > 0.45:
                ox, oy = x + offset[0], y + offset[1]
                q = grid * 0.36
                cx, cy = ox + grid / 2, oy + grid / 2
                d.line([(cx - q, cy - q), (cx + q, cy + q)], fill=color, width=3)
                d.line([(cx - q, cy + q), (cx + q, cy - q)], fill=color, width=3)


# ------------------------------------------------------------------ NOCTURNE · time
def nocturne2(crops, texts):
    ink = (236, 232, 222)
    dim = (78, 80, 80)
    page = Image.new("RGB", (W, H), (8, 9, 10))
    night, info = cover(crops["night"], (GUT, H), focus=(0.47, 0.52))
    night = slit_scan(night, 640, GUT, amp=120, period=11)
    page.paste(night, (0, 0))
    # pixel stretch: the last columns of the night are dragged across the gutter for 520 px
    stretch = pixel_stretch(night, GUT - 14, 2, 520)
    fade = np.linspace(1, 0, 520) ** 1.6
    st = np.asarray(stretch, float) * fade[None, :, None] + np.asarray([8, 9, 10], float) * (1 - fade[None, :, None])
    page.paste(Image.fromarray(st.astype("uint8")), (GUT, 0))
    # long-exposure ghosts of the figure, drifting right, fading
    fig = night.crop((60, 140, 640, H))
    for k, op in enumerate([0.22, 0.14, 0.08]):
        page = alpha_paste(page, fig, (60 + 230 * (k + 1), 140), op, mode="screen", soft=110)
    # complementary afterimage: the inverted figure, cyan-shifted, burned in after the eye moves
    after = ImageOps.invert(fig).filter(ImageFilter.GaussianBlur(6))
    page = alpha_paste(page, after, (1240, 140 - 40), 0.13, mode="screen", soft=140)
    d = ImageDraw.Draw(page)
    # the other places as tiny long-exposure trails
    for key, w_, (x, y) in (("park", 260, (1560, 90)), ("shop", 92, (1680, 520)), ("rock", 210, (1520, 900))):
        im = crops[key]
        s = w_ / im.size[0]
        im2 = im.resize((w_, round(im.size[1] * s)), Image.LANCZOS)
        for t in range(6, 0, -1):
            page = alpha_paste(page, im2, (x - t * 22, y), 0.05 * (7 - t), mode="screen", soft=12)
        page.paste(misregister(im2, 3, 0), (x, y))
        d = ImageDraw.Draw(page)
        crop_marks(d, (x, y, x + im2.size[0], y + im2.size[1]), dim)
        tracked(d, (x, y + im2.size[1] + 12), f"t-{6 * 22}PX  x{s:.2f}", fnt("mono", 11), dim, 1)
    # title as afterimage: three outline copies stepping back in time
    for k, col in enumerate([(30, 32, 33), (44, 46, 47), (70, 72, 72)]):
        rot = Image.new("RGBA", (1300, 260), (0, 0, 0, 0))
        outline(ImageDraw.Draw(rot), (0, 0), texts["title"], fnt("black", 220), col, stroke=2, tracking=6,
                bg=(8, 9, 10))
        rot = rot.rotate(90, expand=True)
        page.paste(rot, (GUT + 10 + k * 26, -20 + k * 34), rot)
    d = ImageDraw.Draw(page)
    fk = fnt("ko", 22)
    vertical_ko(d, 1905, 330, texts["body_ko"][0], fk, ink)
    vertical_ko(d, 1866, 330, texts["body_ko"][1], fk, ink)
    rotated_text(page, (1330, 760), texts["kicker"], fnt("light", 14), ink + (255,), angle=90, tracking=6)
    d = ImageDraw.Draw(page)
    tracked(d, (40, H - 44), f"00:00:{info['scale']:05.2f}  SLIT-SCAN 640–1000  STRETCH 2PX→520PX  GHOSTS 3",
            fnt("mono", 12), ink, 1)
    reg_mark(d, 1960, 40, 10, dim)
    tracked(d, (W - 80, H - 44), texts["folio"], fnt("mono", 12), dim, 1)
    page = scanlines(page, 3, 0.16)
    return grain(page, 0.03, 13, size=1.4), {"name": "NOCTURNE II — 시간", "techniques": [
        "slit-scan", "pixel stretch across the gutter", "long-exposure ghosts (screen blend)",
        "complementary afterimage", "light trails on thumbnails", "time-stepped outline title", "scanlines",
        "세로쓰기", "process timecode"]}


# ------------------------------------------------------------------ LINEUP · body
def lineup2(crops, texts, vertical_copy=True):
    ink = (238, 236, 230)
    page = Image.new("RGB", (W, H), (6, 6, 6))
    pw = W // 4
    focus = {"night": (0.43, 0.55), "park": (0.73, 0.5), "shop": (0.42, 0.5), "rock": (0.56, 0.45)}
    offs = [0, -80, 60, -30]
    order = ["night", "park", "shop", "rock"]
    for i, k in enumerate(order):
        im, _ = cover(crops[k], (pw - 6, H), focus=focus[k])
        if k == "night":
            im = strip_jitter(im, 18, 22, 3)                     # the body shivers in slices
        if k == "park":                                          # squash: the body compressed to 72 %
            sq = im.resize((im.size[0], int(H * 0.72)), Image.LANCZOS)
            im = Image.new("RGB", im.size, (6, 6, 6))
            im.paste(sq, (0, H - sq.size[1]))
            top = sq.crop((0, 0, sq.size[0], 6)).resize((sq.size[0], H - sq.size[1]), Image.NEAREST)
            im.paste(top, (0, 0))
        if k == "shop":                                          # Droste: the panel contains itself
            inner = im.resize((im.size[0] // 3, H // 3), Image.LANCZOS)
            im.paste(inner, (im.size[0] - inner.size[0] - 30, 300))
            inner2 = inner.resize((inner.size[0] // 3, inner.size[1] // 3), Image.LANCZOS)
            im.paste(inner2, (im.size[0] - inner.size[0] - 30 + inner.size[0] - inner2.size[0] - 10, 300 + 100))
        if k == "rock":
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
            im = misregister(im, -5, 0)
        page.paste(im, (i * pw + 3, offs[i]))
    d = ImageDraw.Draw(page)
    # title: each letter a different weight, each displaced with its panel
    weights = ["thin", "xlight", "light", "regular", "bold", "black"]
    x = 360
    for n, ch in enumerate(texts["title"]):
        f = fnt(weights[n % len(weights)], 250)
        cx = x + f.getlength(ch) / 2
        panel = min(3, int(cx // pw))
        tracked(d, (x, 470 + offs[panel]), ch, f, ink, 0)
        x += f.getlength(ch) + 22
    for i in range(4):
        outline(d, (i * pw + 24, -60 + offs[i]), f"0{i + 1}", fnt("black", 200), ink, stroke=1, bg=(0, 0, 0))
        crop_marks(d, (i * pw + 3, max(0, offs[i]), (i + 1) * pw - 3, min(H, H + offs[i])), ink)
        # offset bar: a measurement drawn as rhythm
        bh = abs(offs[i]) * 2 + 4
        d.rectangle([i * pw + pw - 26, 600 - bh // 2, i * pw + pw - 18, 600 + bh // 2], fill=ink)
    if vertical_copy:
        rotated_text(page, (pw - 44, 700), texts["body_ko"][0], fnt("ko", 17), ink + (255,), angle=90, tracking=0.6)
        rotated_text(page, (3 * pw - 44, 640), texts["body_ko"][1], fnt("ko", 17), ink + (255,), angle=90, tracking=0.6)
    page = scrim(page, (0, H - 120, W, H), 0.5)
    d = ImageDraw.Draw(page)
    tracked(d, (26, H - 44), f"{texts['kicker']}   JITTER 18PX · SQUASH 0.72 · DROSTE 1/3, 1/9 · MIRROR · "
            f"OFFSETS {offs[0]}/{offs[1]}/{offs[2]}/{offs[3]}", fnt("mono", 12), ink, 1)
    tracked(d, (W - 60, H - 44), texts["folio"], fnt("mono", 12), ink, 1)
    return grain(page, 0.04, 23, size=1.6), {"name": "LINEUP II — 몸", "techniques": [
        "strip jitter", "squash 0.72", "Droste recursion", "mirror + misregistration", "weight-varying broken title",
        "per-panel crop marks", "offset bars", "rotated copy"]}


# ------------------------------------------------------------------ WILD · print
def wild2(crops, texts):
    bone = (232, 226, 212)
    blue = (23, 48, 72)               # measured deep blue of the rock photo
    rock, info = cover(crops["rock"], (W, H), focus=(0.5, 0.48))
    # layer 1: two-colour rotated halftone of the rock on bone paper
    paper = Image.new("RGB", (W, H), bone)
    ht_blue = halftone_rot(rock, 13, 15, blue)
    ht_dark = halftone_rot(rock.point(lambda v: min(255, v + 40)), 13, 75, (40, 36, 30), size_gain=0.9)
    paper.paste(ht_dark, (3, 2), ht_dark)
    paper.paste(ht_blue, (0, 0), ht_blue)
    # layer 2: photocopy threshold torn strip; layer 3: the photograph, torn on top
    copy_ = threshold_copy(rock, 0.42, (14, 14, 14), bone, seed=5)
    m_copy = torn_mask((W, H), 760, 0.32, 9, 11)
    m_photo = torn_mask((W, H), 920, 0.32, 9, 17)
    page = Image.composite(copy_, paper, m_copy)
    inv = ImageOps.invert(m_photo)
    shadow = inv.filter(ImageFilter.GaussianBlur(10))
    page = Image.composite(Image.new("RGB", (W, H), (40, 36, 30)), page, shadow.point(lambda v: int(v * 0.35)))
    page = Image.composite(rock, page, inv)
    # two places inside the letters: night in MAT, park in CH
    ft = fnt("black", 520)
    m1 = text_mask((W, H), "MAT", ft, (-48, -150), -14)
    x2 = -48 + width("MAT", ft, -14) - 14
    m2 = text_mask((W, H), "CH", ft, (x2, -150), -14)
    nb, _ = cover(crops["night"], (W, 420), focus=(0.5, 0.64))
    pb, _ = cover(crops["park"], (W, 420), focus=(0.5, 0.55))
    nl, pl = Image.new("RGB", (W, H)), Image.new("RGB", (W, H))
    nl.paste(nb, (0, 0))
    pl.paste(pb, (0, 0))
    page = Image.composite(nl, page, m1)
    page = Image.composite(pl, page, m2)
    d = ImageDraw.Draw(page)
    # hand annotation: circle the hand, lead a line to a note
    cx, cy, r = 1145, 640, 70
    d.ellipse([cx - r, cy - r * 0.8, cx + r, cy + r * 0.8], outline=bone, width=3)
    d.line([(cx + r - 6, cy - 30), (1420, 470)], fill=bone, width=2)
    xe = tracked(d, (1430, 450), "HAND / ", fnt("mono", 14), bone, 1)
    xe = tracked(d, (xe, 447), "손", fnt("ko", 15), bone, 0)
    tracked(d, (xe + 8, 450), "— x" + f"{info['scale']:.2f}", fnt("mono", 14), bone, 1)
    # shop as a small taped print
    sh = crops["shop"]
    s = 170 / sh.size[0]
    sh2 = sh.resize((170, round(sh.size[1] * s)), Image.LANCZOS)
    page.paste(sh2.rotate(-4, expand=True, fillcolor=bone), (1700, 700))
    d = ImageDraw.Draw(page)
    d.rectangle([1740, 688, 1830, 712], fill=(220, 212, 190))
    page = scrim(page, (0, H - 220, 1000, H), 0.55)
    d = ImageDraw.Draw(page)
    fk = fnt("ko", 20)
    for (yy, txt, f_, tr) in ((H - 160, texts["kicker"], fnt("bold", 14), 4), (H - 120, texts["body_ko"][0], fk, 0.6),
                              (H - 86, texts["body_ko"][1], fk, 0.6)):
        d.rectangle([62, yy - 5, 70 + width(txt, f_, tr) + 8, yy + f_.size + 7], fill=(14, 14, 14))   # label strips
        tracked(d, (70, yy), txt, f_, bone, tr)
    tracked(d, (1000, H - 44), "SCREENS 15° BLUE / 75° UMBER · 13PX · THRESHOLD 0.42 · NIGHT ∈ MAT · DUSK ∈ CH",
            fnt("mono", 12), bone, 1)
    tracked(d, (W - 66, H - 44), texts["folio"], fnt("mono", 12), bone, 1)
    return grain(page, 0.04, 33, size=1.6), {"name": "WILD II — 인쇄", "techniques": [
        "two-colour rotated halftone (measured rock blue + umber)", "photocopy threshold strip", "torn-paper layers "
        "with shadow", "two places clipped into the letters", "hand annotation", "taped print"]}


# ------------------------------------------------------------------ FABRIC · textile
def fabric2(crops, texts, photos):
    ink = (240, 238, 232)
    byk = {p.key: p for p in photos}
    fields = {}
    for k in ["night", "park", "shop", "rock"]:
        p = byk[k]
        cx0, cy0 = p.crop[0], p.crop[1]
        px0, _, px1, _ = p.person
        win = (max(0, max(px0, cx0) - cx0), max(0, p.outfit[1] - 40 - cy0), min(crops[k].size[0], px1 - cx0),
               crops[k].size[1])
        fields[k], _ = cover(crops[k].crop(win), (GUT, H))
    # left page: night (warp) woven with sea knit (weft); right page: dusk coat (warp) with day coat (weft)
    left = warp_weft(fields["night"], fields["rock"], 46)
    right = warp_weft(fields["park"], fields["shop"], 46)
    page = Image.new("RGB", (W, H))
    page.paste(left, (0, 0))
    page.paste(right, (GUT, 0))
    # pixel mosaic band: the original block motif, rebuilt from the garments themselves
    band = page.crop((0, 760, W, 1000))
    page.paste(mosaic(band, 40), (0, 760))
    # moiré: two fine line screens a few degrees apart
    mo = Image.new("RGBA", (W + 600, H + 600), (0, 0, 0, 0))
    dm = ImageDraw.Draw(mo)
    for x in range(0, W + 600, 7):
        dm.line([(x, 0), (x, H + 600)], fill=(255, 255, 255, 90), width=2)
    mo1 = mo.rotate(3, center=(W / 2 + 300, H / 2 + 300)).crop((300, 300, 300 + W, 300 + H))
    mo2 = mo.rotate(-2, center=(W / 2 + 300, H / 2 + 300)).crop((300, 300, 300 + W, 300 + H))
    region = Image.new("L", (W, H), 0)
    ImageDraw.Draw(region).ellipse([520, 120, 1480, 760], fill=255)
    region = region.filter(ImageFilter.GaussianBlur(40))
    for mo_ in (mo1, mo2):
        a = mo_.split()[3]
        a = ImageChops.multiply(a, region)
        mo_.putalpha(a)
        page.paste(mo_, (0, 0), mo_)
    a = np.asarray(page, float)
    a[360:690, :W - 160] *= 0.38                                         # dark ground cloth for the stitches
    page = Image.fromarray(a.astype("uint8"))
    d = ImageDraw.Draw(page)
    # cross-stitch title over the weave
    m = text_mask((W, H), texts["title"], fnt("black", 300), (140, 330), 10)
    stitch_text(d, m, 12, ink)
    a = np.asarray(page, float)
    a[:, W - 150:W - 40] *= 0.42
    page = Image.fromarray(a.astype("uint8"))
    d = ImageDraw.Draw(page)
    fk = fnt("ko", 20)
    vertical_ko(d, W - 70, 120, texts["body_ko"][0], fk, ink)
    vertical_ko(d, W - 110, 120, texts["body_ko"][1], fk, ink)
    tracked(d, (26, 26), "WARP NIGHT × WEFT SEA  |  WARP DUSK × WEFT DAY  ·  THREAD 46PX  ·  MOSAIC 40PX  ·  "
            "MORE 3° / −2°  ·  STITCH 12PX", fnt("mono", 12), ink, 1)
    for i, wd in enumerate(["NIGHT × SEA", "", "DUSK × DAY", ""]):
        if wd:
            tracked(d, (i * 500 + 26, H - 60), wd, fnt("light", 14), ink, 5)
    tracked(d, (W - 200, H - 60), texts["folio"], fnt("mono", 12), ink, 1)
    return grain(page, 0.04, 43, size=2.0), {"name": "FABRIC II — 직물", "techniques": [
        "warp/weft over-under weave with thread relief", "pixel mosaic band (original block motif rebuilt from the "
        "garments)", "moiré from two line screens", "cross-stitch title", "세로쓰기"]}


def render(src_path, photos, texts, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    srcim = Image.open(src_path).convert("RGB")
    inset = 3
    crops = {p.key: srcim.crop((p.crop[0] + inset, p.crop[1] + inset, p.crop[2] - inset, p.crop[3] - inset))
             for p in photos}
    out = {}
    for k, fn in (("1_nocturne_II", nocturne2), ("2_lineup_II", lineup2), ("3_wild_II", wild2), ("4_fabric_II", fabric2)):
        page, spec = fn(crops, texts, photos) if k == "4_fabric_II" else fn(crops, texts)
        path = os.path.join(out_dir, f"{k}.png")
        page.save(path, optimize=True)
        page.save(os.path.join(out_dir, f"{k}.pdf"), "PDF", resolution=144.0)
        spec["file"] = path
        out[k] = spec
    return out
