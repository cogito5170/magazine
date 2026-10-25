"""jogakbo -- Korean patchwork wrapping cloth: the spread is cut, edge to edge, into rectangles (a seeded
guillotine split) and each rectangle is filled with a piece cut from one of the photographs, joined by light
double seams.  A piece that holds a person holds the whole person box; filler pieces are cut only from parts
of the photos that contain no person.  Where no rectangle fits a person, the photo is sewn into the rectangle
as a smaller patch on plain ramie.  Two plain ramie pieces carry the title and the copy."""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from ..moodmachine import Layer, _face
from ._common import KEYS, W, finish, prep, set_copy, text_at


def split(H, n, rng):
    pieces = [(0, 0, W, H)]
    while len(pieces) < n:
        pieces.sort(key=lambda p: (p[2] - p[0]) * (p[3] - p[1]))
        x0, y0, x1, y1 = pieces.pop()
        f = rng.uniform(0.3, 0.7)
        if x1 - x0 >= y1 - y0:
            c = int(round((x0 + f * (x1 - x0)) / 10) * 10)
            pieces += [(x0, y0, c, y1), (c, y0, x1, y1)]
        else:
            c = int(round((y0 + f * (y1 - y0)) / 10) * 10)
            pieces += [(x0, y0, x1, c), (x0, c, x1, y1)]
    return pieces


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
    big = sorted(pieces, key=lambda p: -(p[2] - p[0]) * (p[3] - p[1]))
    text = [p for p in big if p[2] - p[0] >= 420 and 160 <= p[3] - p[1] and (p[2] - p[0]) * (p[3] - p[1]) < 400000]
    if len(text) < 2:
        return None
    title_p = min(text[:4], key=lambda p: (p[3] - p[1]))
    body_p = max([p for p in text if p != title_p], key=lambda p: (p[3] - p[1]) * min(p[2] - p[0], 700))
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
    seam = tuple((st.get("seam") or {}).get("color", (248, 244, 232)))
    best = None
    for seed in range(400):
        p = plan(H, crops, persons, np.random.default_rng(seed))
        if p and (best is None or p["fit"] > best[0]["fit"]):
            best = (p, seed)
        if best and best[0]["fit"] == 4:
            break
    P, seed = best
    page = Image.new("RGB", (W, H), seam)
    d = ImageDraw.Draw(page)
    rng = np.random.default_rng(seed + 1000)
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
            page.paste(prep(im.crop((wx, wy, wx + pw, wy + ph)), L, hero=(k == "night")), (x0, y0))
            rec.append({"piece": pc, "photo": k, "scale": round(s, 2), "person": "whole"})
        elif patches and pw >= 150 and ph >= 150:
            k = patches.pop(0)
            d.rectangle((x0, y0, x1 - 1, y1 - 1), fill=L.paper)
            from ._common import fit
            im, s = fit(crops[k], pw - 40, ph - 40)
            ox, oy = x0 + (pw - im.size[0]) // 2, y0 + (ph - im.size[1]) // 2
            d.rectangle((ox - inset, oy - inset, ox + im.size[0] + inset, oy + im.size[1] + inset), fill=seam)
            page.paste(prep(im, L), (ox, oy))
            rec.append({"piece": pc, "photo": k, "scale": round(s, 2), "person": "whole, sewn in as a patch"})
        else:
            k, r = sources[int(rng.integers(len(sources)))]
            rw, rh = r[2] - r[0], r[3] - r[1]
            s = max(pw / rw, ph / rh, float(rng.uniform(1.0, 1.8)))
            ww, wh = pw / s, ph / s
            sx = r[0] + float(rng.uniform(0, rw - ww))
            sy = r[1] + float(rng.uniform(0, rh - wh))
            piece = crops[k].crop((round(sx), round(sy), round(sx + ww), round(sy + wh))).resize((pw, ph), Image.LANCZOS)
            if rng.random() < 0.3:
                piece = piece.transpose(Image.FLIP_LEFT_RIGHT)
            page.paste(prep(piece, L), (x0, y0))
            rec.append({"piece": pc, "photo": k, "scale": round(s, 2), "person": "none"})
        photos.append((x0, y0, x1, y1))
        if (st.get("seam") or {}).get("double", True):
            d.rectangle((x0 + 6, y0 + 6, x1 - 7, y1 - 7), outline=seam, width=1)
    tb, bb = P["title"], P["body"]
    ft = _face(L.title_face, L.title_weight, min(96, (tb[3] - tb[1]) - 50))
    tbox = text_at(d, (tb[0] + 36, tb[1] + 20), texts["title"], ft, L.title_color or L.ink, 6)
    box, done = set_copy(d, (bb[0] + 36, bb[1] + 32), texts, L, min(bb[2] - bb[0] - 72, 640), size=19, head_size=24)
    return finish(page, L, {"text_boxes": [tbox, box], "photo_boxes": photos, "texts_set": [texts["title"]] + done,
                            "pieces": rec, "seed": seed, "persons_fitted": P["fit"]})
