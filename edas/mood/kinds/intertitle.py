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
    side = st.get("still", "left")                  # which page holds the still
    PX = 0 if side == "left" else G                 # still page x
    CX0 = G if side == "left" else 0                # card page x
    page.paste(R.hero(hero, slit=(int(G * 0.82), G), bold=False, glow=False), (PX, 0))
    d = ImageDraw.Draw(page)
    photos, tboxes, done = [(PX, 0, PX + G, H)], [], []
    t = texts["title"]
    cut = (len(t.rstrip(".")) + 1) // 2
    parts = [t[:cut], t[cut:]]
    f = fnt("black", int(st.get("card_size", 220)))
    cx = CX0 + G // 2

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
    ih, gap = int(st.get("frame_h", 190)), 26
    ims = []
    for k in [k for k in ("night", "shop", "rock", "park") if k != key][:3]:
        im, s = bordered(R, crops[k], L, ih, (12, 12, 12), border=0)
        ims.append(im)
    tot = sum(i.size[0] for i in ims) + gap * (len(ims) - 1)
    while tot > G - 120 and ims:
        ims.pop()
        tot = sum(i.size[0] for i in ims) + gap * (len(ims) - 1)
    x, yi = int(cx - tot / 2), b1[3] + 36
    for im in ims:
        page.paste(R.misreg(im, 3), (x, yi))
        photos.append((x, yi, x + im.size[0], yi + im.size[1]))
        x += im.size[0] + gap
    b2 = card(parts[1], yi + ih + 16, red, f)
    tboxes += [b1, b2]
    R.title_boxes += [b1, b2]
    done.append(t)
    R.defamiliar = f"the title broken across two intertitle cards: '{parts[0]}' blue, '{parts[1]}' red"
    y = b2[3] + 44
    for k, ln, fl in copy_lines(texts, L, int(st.get("copy_size", 24)), G - 200):
        w = width(ln, fl)
        d.text((int(cx - w / 2), y), ln, font=fl, fill=tuple(L.ink))
        bb = d.textbbox((int(cx - w / 2), y), ln, font=fl)
        tboxes.append(bb)
        y = bb[3] + (14 if k == "body" else 22)
        if texts[k] not in done:
            done.append(texts[k])
    lum = sum(page.crop((PX + 40, H - 112, PX + 560, H - 26)).convert("L").getdata()) / (520 * 86)
    ink = (16, 16, 16) if lum > 128 else WHITE
    R.note(d, (PX + 40, H - 110), img.size, info["scale"], ink, face="mono", extra=f" · {key}, black and white")
    R.frame(page, H, ink, None, ["Blue and red title cards on the leader (after Godard's intertitles).",
                                   "Slit-scan amp 40 · matte · misregister 3 px · the title broken in two"],
            face="mono", proc_fill=ink, px=PX + 40)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done, "hero": key}, R)
