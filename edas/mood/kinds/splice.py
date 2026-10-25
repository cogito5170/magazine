"""splice -- John Stezaker's Marriage series: two portraits cut on one vertical line and joined, so one body
wears two places.  Each pair is scaled so both people stand the same height with their heads on one line, then
the left half comes from the first photo and the right half from the second.  One collage per page on a wide
mat; small serif title under the left collage, copy under the right."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import Layer, _face
from ._common import W, caption, finish, prep, set_copy, text_at


def _lift(c, t):
    return tuple(int(round(v + (255 - v) * t)) for v in c)


def splice(A, B, pa, pb, ph):
    """Left of A's person centre + right of B's person centre, people scaled to height ph, tops aligned."""
    sa, sb = ph / (pa[3] - pa[1]), ph / (pb[3] - pb[1])
    A2 = A.resize((round(A.size[0] * sa), round(A.size[1] * sa)), Image.LANCZOS)
    B2 = B.resize((round(B.size[0] * sb), round(B.size[1] * sb)), Image.LANCZOS)
    ta, tb = pa[1] * sa, pb[1] * sb
    m = min(ta, tb, 60)
    ya, yb = round(ta - m), round(tb - m)
    ch = min(A2.size[1] - ya, B2.size[1] - yb)
    ca, cb = round((pa[0] + pa[2]) / 2 * sa), round((pb[0] + pb[2]) / 2 * sb)
    hw = min(330, ca, B2.size[0] - cb)
    out = Image.new("RGB", (2 * hw, ch))
    out.paste(A2.crop((ca - hw, ya, ca, ya + ch)), (0, 0))
    out.paste(B2.crop((cb, yb, cb + hw, yb + ch)), (hw, 0))
    return out, {"scales": (round(sa, 2), round(sb, 2)), "size": out.size}


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    pairs = st.get("pairs") or [["night", "rock"], ["park", "shop"]]
    if texts.get("cover"):          # the cover has two whole figures only: the model and the dress form
        pairs = [["night", "shop"]]
    page = Image.new("RGB", (W, H), L.paper)
    d = ImageDraw.Draw(page)
    mat_c = _lift(L.paper, 0.55)
    photos, tboxes, done, rec = [], [], [], {}
    ph = int(H * 0.52)
    bottoms = []
    for i, (a, b) in enumerate(pairs[:2]):
        col, info = splice(prep(crops[a], L), prep(crops[b], L), persons[a], persons[b], ph)
        cx = 1500 if len(pairs) == 1 else 500 + 1000 * i
        x0, y0 = cx - col.size[0] // 2, 120
        mat = 70
        d.rectangle((x0 - mat, y0 - mat, x0 + col.size[0] + mat, y0 + col.size[1] + mat), fill=mat_c)
        page.paste(col, (x0, y0))
        photos.append((x0, y0, x0 + col.size[0], y0 + col.size[1]))
        bottoms.append(y0 + col.size[1] + mat)
        caption(d, (x0 - mat, y0 + col.size[1] + mat + 14),
                f"{a} | {b}, cut at the centre line, ×{info['scales'][0]} / ×{info['scales'][1]}", L)
        rec[f"{a}|{b}"] = info
    y = max(bottoms) + 70
    tx, bx, by = (170, 170, y - 300) if len(pairs) == 1 else (170, 1170, y)
    ft = _face(L.title_face, L.title_weight, 44)
    tboxes.append(text_at(d, (tx, y if len(pairs) > 1 else by - 120), texts["title"], ft, L.title_color or L.ink, 14))
    done.append(texts["title"])
    box, s = set_copy(d, (bx, by), texts, L, 660, size=19, head_size=24)
    tboxes.append(box)
    done += s
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done, "splices": rec,
                            "collage_width_frac": [round((p[2] - p[0]) / W, 3) for p in photos]})
