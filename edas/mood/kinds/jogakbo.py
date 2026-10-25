"""jogakbo -- Korean patchwork wrapping cloth: the spread is cut, edge to edge, into rectangles (a seeded
guillotine split) and each rectangle is filled with a piece cut from one of the photographs, joined by light
double seams.  A piece that holds a person holds the whole person box; filler pieces are cut only from parts
of the photos that contain no person.  Where no rectangle fits a person, the photo is sewn into the rectangle
as a smaller patch on plain ramie.  Two plain ramie pieces carry the title and the copy."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..moodmachine import Layer, _face
from ..variants import width
from ._common import KEYS, W, set_copy
from .recipe import Recipe, finish


def split(H, n, rng):
    """A title band is cut first from one corner (it stays whole), then the rest is split largest-first."""
    tw, th = int(rng.integers(105, 125)) * 10, int(rng.integers(32, 40)) * 10
    corner = int(rng.integers(4))
    left, top = corner % 2 == 0, corner < 2
    tx0 = 0 if left else W - tw
    ty0 = 0 if top else H - th
    title = (tx0, ty0, tx0 + tw, ty0 + th)
    side = (tw, 0, W, H) if left else (0, 0, W - tw, H)
    rest = (tx0, th, tx0 + tw, H) if top else (tx0, 0, tx0 + tw, H - th)
    pieces, fixed = [side, rest], [title]
    while len(pieces) + 1 < n:
        pieces.sort(key=lambda p: (p[2] - p[0]) * (p[3] - p[1]))
        x0, y0, x1, y1 = pieces.pop()
        f = rng.uniform(0.3, 0.7)
        if x1 - x0 >= y1 - y0:
            c = int(round((x0 + f * (x1 - x0)) / 10) * 10)
            pieces += [(x0, y0, c, y1), (c, y0, x1, y1)]
        else:
            c = int(round((y0 + f * (y1 - y0)) / 10) * 10)
            pieces += [(x0, y0, x1, c), (x0, c, x1, y1)]
    return fixed + pieces


def person_scale(piece, img, pb, smin=0.85):
    """Scale range that both covers the piece from the image and keeps the person box whole."""
    pw, ph = piece[2] - piece[0], piece[3] - piece[1]
    lo = max(pw / img.size[0], ph / img.size[1], smin)
    hi = min(pw / (pb[2] - pb[0]), ph / (pb[3] - pb[1]))
    return lo, hi


def free_regions(img, pb):
    """Rectangles of the crop that do not touch the person box."""
    w, h = img.size
    r = [(0, 0, w, pb[1]), (0, pb[3], w, h), (0, 0, pb[0], h), (pb[2], 0, w, h)]
    return [b for b in r if b[2] - b[0] >= 60 and b[3] - b[1] >= 60]


def plan(H, crops, persons, rng):
    n = int(rng.integers(14, 23))
    pieces = split(H, n, rng)
    big = sorted(pieces[1:], key=lambda p: -(p[2] - p[0]) * (p[3] - p[1]))
    title_p = pieces[0]
    bodies = [p for p in big if 460 <= p[2] - p[0] <= 900 and 300 <= p[3] - p[1]]
    if not bodies:
        return None
    body_p = max(bodies, key=lambda p: (p[3] - p[1]) * min(p[2] - p[0], 700))
    rest = [p for p in pieces if p not in (title_p, body_p)]
    assign, score = {}, 0
    for k in KEYS:
        best = None
        for p in rest:
            if p in assign.values():
                continue
            lo, hi = person_scale(p, crops[k], persons[k])
            area = (p[2] - p[0]) * (p[3] - p[1])
            if lo <= hi and (best is None or area > best[1]):
                best = (p, area)
        if best:
            assign[k] = best[0]
            score += 1
    return {"pieces": pieces, "title": title_p, "body": body_p, "persons": assign, "fit": score}


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    R = Recipe()
    seam = tuple((st.get("seam") or {}).get("color", (248, 244, 232)))
    best = None
    for seed in range(3000):
        p = plan(H, crops, persons, np.random.default_rng(seed))
        if p and (best is None or p["fit"] > best[0]["fit"]):
            best = (p, seed)
        if best and best[0]["fit"] == 4:
            break
    P, seed = best
    page = Image.new("RGB", (W, H), seam)
    d = ImageDraw.Draw(page)
    rng = np.random.default_rng(seed + 1000)
    mirrored = 0
    inset = 3
    photos, rec = [], []
    placed = set(P["persons"])
    patches = [k for k in KEYS if k not in placed]
    sources = [(k, r) for k in KEYS for r in free_regions(crops[k], persons[k])]
    for i, pc in enumerate(P["pieces"]):
        x0, y0, x1, y1 = pc[0] + inset, pc[1] + inset, pc[2] - inset, pc[3] - inset
        pw, ph = x1 - x0, y1 - y0
        if pc in (P["title"], P["body"]):
            d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=L.paper)
            continue
        who = [k for k, v in P["persons"].items() if v == pc]
        if who:
            k = who[0]
            img, pb = crops[k], persons[k]
            lo, hi = person_scale(pc, img, pb)
            s = lo
            cx, cy = (pb[0] + pb[2]) / 2 * s, (pb[1] + pb[3]) / 2 * s
            im = img.resize((round(img.size[0] * s), round(img.size[1] * s)), Image.LANCZOS)
            wx = int(np.clip(cx - pw / 2, 0, im.size[0] - pw))
            wy = int(np.clip(cy - ph / 2, 0, im.size[1] - ph))
            cut = im.crop((wx, wy, wx + pw, wy + ph))
            page.paste(R.hero(cut) if k == "night" else R.print_(cut), (x0, y0))
            rec.append({"piece": pc, "photo": k, "scale": round(s, 2), "person": "whole"})
        elif patches and pw >= 150 and ph >= 150:
            k = patches.pop(0)
            d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=L.paper)
            from ._common import fit
            im, s = fit(crops[k], pw - 40, ph - 40)
            ox, oy = x0 + (pw - im.size[0]) // 2, y0 + (ph - im.size[1]) // 2
            d.rectangle((ox - inset, oy - inset, ox + im.size[0] + inset, oy + im.size[1] + inset), fill=seam)
            page.paste(R.print_(im), (ox, oy))
            rec.append({"piece": pc, "photo": k, "scale": round(s, 2), "person": "whole, sewn in as a patch"})
        else:
            k, r = sources[int(rng.integers(len(sources)))]
            rw, rh = r[2] - r[0], r[3] - r[1]
            s = max(pw / rw, ph / rh, float(rng.uniform(1.0, 1.8)))
            ww, wh = pw / s, ph / s
            sx = r[0] + float(rng.uniform(0, max(0.0, rw - ww)))
            sy = r[1] + float(rng.uniform(0, max(0.0, rh - wh)))
            piece = crops[k].crop((round(sx), round(sy), round(sx + ww), round(sy + wh))).resize((pw, ph), Image.LANCZOS)
            if rng.random() < 0.4:      # mirrored pieces: Richter's divided/mirrored logic, sewn
                piece = piece.transpose(Image.FLIP_LEFT_RIGHT)
                mirrored += 1
            if rng.random() < 0.35:     # a dyed ramie piece in the photo's own mean colour
                kk = KEYS[int(rng.integers(len(KEYS)))]          # dyed in the colour of someone's clothes
                q = persons[kk]
                qh = q[3] - q[1]
                c = np.asarray(crops[kk].crop((q[0], q[1] + int(qh * 0.35), q[2], q[1] + int(qh * 0.75))),
                               float).reshape(-1, 3).mean(0)
                c = tuple(int(0.8 * a + 0.2 * b) for a, b in zip(c, L.paper))
                k = kk
                ImageDraw.Draw(page).rectangle((x0, y0, x1 - 1, y1 - 1), fill=c)
                rec.append({"piece": pc, "dyed_from": k, "colour": c})
                if (st.get("seam") or {}).get("double", True):
                    d.rectangle((x0 + 6, y0 + 6, x1 - 7, y1 - 7), outline=seam, width=1)
                continue
            page.paste(R.print_(piece), (x0, y0))
            rec.append({"piece": pc, "photo": k, "scale": round(s, 2), "person": "none"})
        photos.append((x0, y0, x1, y1))
        if (st.get("seam") or {}).get("double", True):
            d.rectangle((x0 + 6, y0 + 6, x1 - 7, y1 - 7), outline=seam, width=1)
    tb, bb = P["title"], P["body"]
    from ..variants import fnt
    size = 300
    while width(texts["title"], fnt("black", size), 8) > (tb[2] - tb[0]) - 90 or size * 0.78 > (tb[3] - tb[1]) - 70:
        size -= 6
    src = crops["night"]
    m_box = R.strip_title(page, texts["title"], fnt("black", size), (tb[0] + 40, tb[1] + 36), src, (0.55, 0.3, 0.95),
                          L.paper, tracking=8, toward=L.ink, mix=0.45)
    box, done = set_copy(d, (bb[0] + 36, bb[1] + 32), texts, L, min(bb[2] - bb[0] - 72, 640), size=19, head_size=24)
    R.defamiliar = f"pieces mirrored like Richter's strips ({mirrored} of {len(P['pieces'])})"
    pn = [r for r in rec if r.get("photo") == "night"]
    R.note(d, (bb[0] + 36, bb[3] - 40), crops["night"].size, pn[0]["scale"] if pn else 1.0, L.camel, face="mono",
           extra=f" · {len(P['pieces'])} pieces, seed {seed}")
    R.frame(page, H, L.ink, None, ["The photographs cut into pieces and sewn edge to edge (jogakbo).",
                                   "Halation · matte · mirrored pieces · title striped from the night"], face="mono")
    return finish(page, L, {"text_boxes": [m_box, box], "photo_boxes": photos, "texts_set": [texts["title"]] + done,
                            "pieces": rec, "seed": seed, "persons_fitted": P["fit"]}, R)
