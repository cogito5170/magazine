"""splice -- John Stezaker's Marriage series: two portraits cut on one vertical line and joined, so one body
wears two places.  The structure: one spliced figure, full height, standing on the fold, so the cut is the
gutter; the title runs up the left edge, itself cut on a seam (two weights joined at its centre line) and filled
with a Richter strip taken from the splice's own seam column; the second splice is a print on the right page.
Recipe: halation + matte on the big splice, matte + soft JPEG shadow on the print, size notes, final frame."""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import Layer
from ..variants import fnt
from ._common import W, set_copy
from .recipe import Recipe, finish


def splice(A, B, pa, pb, ph, cap=360):
    """Left of A's person centre + right of B's person centre, people scaled to height ph, heads on one line."""
    sa, sb = ph / (pa[3] - pa[1]), ph / (pb[3] - pb[1])
    A2 = A.resize((round(A.size[0] * sa), round(A.size[1] * sa)), Image.LANCZOS)
    B2 = B.resize((round(B.size[0] * sb), round(B.size[1] * sb)), Image.LANCZOS)
    ta, tb = pa[1] * sa, pb[1] * sb
    m = min(ta, tb, 60)
    ya, yb = round(ta - m), round(tb - m)
    ch = min(A2.size[1] - ya, B2.size[1] - yb)
    ca, cb = round((pa[0] + pa[2]) / 2 * sa), round((pb[0] + pb[2]) / 2 * sb)
    hw = min(cap, ca, B2.size[0] - cb)
    out = Image.new("RGB", (2 * hw, ch))
    out.paste(A2.crop((ca - hw, ya, ca, ya + ch)), (0, 0))
    out.paste(B2.crop((cb, yb, cb + hw, yb + ch)), (hw, 0))
    return out, {"scales": (round(sa, 2), round(sb, 2)), "size": out.size}


def render(crops, texts, L: Layer, persons, H=1231):
    st = texts.get("structure") or {}
    pairs = st.get("pairs") or [["night", "rock"], ["park", "shop"]]
    changed = None
    if not texts.get("cover") and ["night", "rock"] in pairs:
        # a Marriage splice joins two heads on one line; the rock figure crouches, so the standing night and
        # park figures make the big splice and the rock goes with the shop on the print
        pairs, changed = [["night", "park"], ["shop", "rock"]], "night|park and shop|rock (the rock figure crouches)"
    if texts.get("cover"):          # the cover has two whole figures only: the model and the dress form
        pairs = [["night", "shop"]]
    R = Recipe()
    page = Image.new("RGB", (W, H), L.paper)
    light = tuple(min(255, int(v * 1.55)) for v in L.paper)
    # 1. the big splice: heads on one line, tall enough to stand from the top edge to the foot of the page
    a, b = pairs[0]
    ph = H
    while True:
        big, info = splice(crops[a], crops[b], persons[a], persons[b], ph)
        if big.size[1] >= H or ph > 3 * H:
            break
        ph += 20
    big = big.crop((0, 0, big.size[0], H))
    hw = big.size[0] // 2
    seam_col = big.crop((hw - 1, 0, hw + 1, H))
    big = R.hero(big, glow=True)
    x0 = 1000 - hw
    page.paste(big, (x0, 0))
    photos = [(x0, 0, x0 + big.size[0], H)]
    d = ImageDraw.Draw(page)
    rx = x0 + big.size[0] + 90
    R.note(d, (rx, H - 120), crops[a].size, info["scales"][0], L.camel, extra=f"  |  {crops[b].size[0]} × "
           f"{crops[b].size[1]}, ×{info['scales'][1]:.2f}: the big splice, cut on the fold")
    # 2. the title up the left edge: cut on a seam (Thin | Black), filled with the seam column's strip
    size = 236
    m = R.seam_mask(texts["title"], fnt("thin", size), fnt("black", size)).rotate(90, expand=True)
    m = m.crop(m.getbbox())
    tbox = R.strip_title(page, texts["title"], fnt("black", size), (64, H - 120 - m.size[1]), seam_col,
                         (0.5, 0.05, 0.95), L.paper, mask=m, toward=L.ink, mix=0.5)
    tboxes = [tbox]
    done = [texts["title"]]
    # 3. the second splice as a print on the right page, over its soft JPEG shadow
    y_copy = 130
    if len(pairs) > 1:
        c, e = pairs[1]
        pr, info2 = splice(crops[c], crops[e], persons[c], persons[e], 470, cap=220)
        pr = R.print_(pr)
        R.shadow(page, pr, (rx + 30, 110), L.paper, L.taupe)
        page.paste(pr, (rx + 30, 110))
        photos.append((rx + 30, 110, rx + 30 + pr.size[0], 110 + pr.size[1]))
        d = ImageDraw.Draw(page)
        R.note(d, (rx, 110 + pr.size[1] + 24 + 40), crops[c].size, info2["scales"][0], L.camel,
               extra=f" | {crops[e].size[0]} × {crops[e].size[1]}, ×{info2['scales'][1]:.2f}")
        y_copy = 110 + pr.size[1] + 150
    if texts.get("cover"):          # the cover sets its quote at display size
        box, s = set_copy(d, (rx, y_copy + 40), texts, L, W - 56 - rx, size=34, head_size=26, lead=56, weight="Light")
    else:
        box, s = set_copy(d, (rx, y_copy), texts, L, W - 56 - rx, size=19, head_size=26)
    tboxes.append(box)
    done += s
    R.frame(page, H, L.ink, L.taupe, ["Two photographs cut on one line and joined (after Stezaker).",
                                      "Halation · matte · seam-cut striped title · JPEG shadow"],
            px=rx)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done, "splice": info,
                            "pairs": pairs, "pairs_changed": changed}, R)
