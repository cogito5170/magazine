"""intertitle -- after Jean-Luc Godard's title cards: the photograph is a black-and-white still on one page,
the other page is black film leader with the title broken into two cards, blue then red, and the copy as a
white card, centred, all set like intertitles.  The three prints run between the cards like frames.
(Mood writer, round 3.)"""
from __future__ import annotations

from PIL import ImageDraw

from ..variants import fnt, width
from ._common import W
from ._declare import strip_paste, bordered, bw_hero, copy_lines
from .recipe import Recipe, finish

BLUE, WHITE, RED = (40, 86, 230), (240, 238, 232), (226, 34, 40)


def render(crops, texts, L, persons, H=1231):
    st = texts.get("structure") or {}
    blue, red = tuple(st.get("first", BLUE)), tuple(st.get("second", RED))
    R = Recipe()
    G = W // 2
    key, img, bw, hero, info = bw_hero(crops, persons, L, (G, H), prefer="night")
    page = hero.copy().resize((W, H))
    page.paste(tuple(L.paper), (0, 0, W, H))
    page.paste(R.hero(hero, slit=(int(G * 0.82), G), bold=False, glow=False), (0, 0))
    d = ImageDraw.Draw(page)
    photos, tboxes, done = [(0, 0, G, H)], [], []
    t = texts["title"]
    cut = (len(t.rstrip(".")) + 1) // 2
    parts = [t[:cut], t[cut:]]
    f = fnt("black", 220)
    cx = G + (W - G) // 2

    def card(text, y, colour, font):
        w = width(text, font, 4)
        x = int(cx - w / 2)
        from ..defamiliar import text_mask
        bb = d.textbbox((x, y), text, font=font)
        m = text_mask((bb[2] - x + 20, bb[3] - y + 20), text, font, (0, 0), 0)
        strip_paste(R, page, m, (x, y), bw, colour)
        return bb

    b1 = card(parts[0], 70, blue, f)
    # frames between the cards
    ih, gap = 190, 26
    ims = []
    for k in [k for k in ("night", "shop", "rock", "park") if k != key][:3]:
        im, s = bordered(R, crops[k], L, ih, (12, 12, 12), border=0)
        ims.append(im)
    tot = sum(i.size[0] for i in ims) + gap * (len(ims) - 1)
    while tot > W - G - 120 and ims:
        ims.pop()
        tot = sum(i.size[0] for i in ims) + gap * (len(ims) - 1)
    x, yi = int(cx - tot / 2), b1[3] + 50
    for im in ims:
        page.paste(R.misreg(im, 3), (x, yi))
        photos.append((x, yi, x + im.size[0], yi + im.size[1]))
        x += im.size[0] + gap
    b2 = card(parts[1], yi + ih + 30, red, f)
    tb = (min(b1[0], b2[0]), b1[1], max(b1[2], b2[2]), b2[3])
    tboxes += [b1, b2]
    R.title_boxes += [b1, b2]
    done.append(t)
    R.defamiliar = f"the title broken across two intertitle cards: '{parts[0]}' blue, '{parts[1]}' red"
    y = b2[3] + 60
    for k, ln, fl in copy_lines(texts, L, 24, W - G - 200):
        w = width(ln, fl)
        d.text((int(cx - w / 2), y), ln, font=fl, fill=WHITE)
        bb = d.textbbox((int(cx - w / 2), y), ln, font=fl)
        tboxes.append(bb)
        y = bb[3] + (14 if k == "body" else 22)
        if texts[k] not in done:
            done.append(texts[k])
    lum = sum(page.crop((40, H - 112, 560, H - 26)).convert("L").getdata()) / (520 * 86)
    ink = (16, 16, 16) if lum > 128 else WHITE
    R.note(d, (40, H - 110), img.size, info["scale"], ink, face="mono", extra=f" · {key}, black and white")
    R.frame(page, H, WHITE, None, ["Blue, white and red title cards on black leader (after Godard's intertitles).",
                                   "Slit-scan amp 40 · matte · misregister 3 px · the title broken in two"],
            face="mono", proc_fill=ink)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done, "hero": key}, R)
