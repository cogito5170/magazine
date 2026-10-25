"""monochrome -- after Yves Klein's IKB: one page is nothing but a field of ultramarine, the other a
black-and-white photograph to the edge.  The title is cut by the gutter: white on the blue, blue on a white
panel over the photograph.  The three prints sit on the blue, unframed.  (Mood writer, round 3.)"""
from __future__ import annotations

from PIL import Image, ImageDraw

from ..moodmachine import _face
from ._common import W, wrap
from ._declare import strip_paste, bordered, bw_hero, copy_lines, mask_paste
from .recipe import Recipe, finish

IKB = (0, 47, 167)


def render(crops, texts, L, persons, H=1231):
    st = texts.get("structure") or {}
    blue = tuple(st.get("field", IKB))
    white = (246, 246, 244)
    R = Recipe()
    G = W // 2
    key, img, bw, hero, info = bw_hero(crops, persons, L, (W - G, H))
    page = Image.new("RGB", (W, H), blue)
    page.paste(R.hero(hero, slit=(int((W - G) * 0.78), W - G), bold=False, glow=False), (G, 0))
    photos, panels, tboxes, done = [(G, 0, W, H)], [], [], []
    m = R.ramp_mask(texts["title"], 250, tracking=6)
    m = m.crop(m.getbbox())
    x0, y0 = G - int(m.size[0] * 0.56), 120
    left, right = m.crop((0, 0, G - x0, m.size[1])), m.crop((G - x0, 0, m.size[0], m.size[1]))
    d = ImageDraw.Draw(page)
    pb = (G, y0 - 26, G + right.size[0] + 40, y0 + m.size[1] + 26)
    d.rectangle(pb, fill=white)
    b1 = strip_paste(R, page, left, (x0, y0), bw, white)
    b2 = strip_paste(R, page, right, (G, y0), bw, blue)
    panels += [{"box": (x0 - 10, y0 - 26, G, pb[3]), "fill": blue, "text": white},
               {"box": pb, "fill": white, "text": blue}]
    tb = (b1[0], b1[1], b2[2], b2[3])
    tboxes += [b1, b2]                      # each half lies on its own solid ground (blue field | white panel)
    R.title_boxes.append(tb)
    done.append(texts["title"])
    R.defamiliar = "the title cut by the gutter: white on the blue field, blue on white over the photograph " \
                   "(weight 100→900)"
    # prints on the field, unframed
    ih, x, yi = 210, 64, pb[3] + 70
    for k in [k for k in ("night", "shop", "rock", "park") if k != key][:3]:
        im, s = bordered(R, crops[k], L, ih, blue, border=0)
        if x + im.size[0] > G - 60:
            break
        page.paste(im, (x, yi))
        photos.append((x, yi, x + im.size[0], yi + im.size[1]))
        x += im.size[0] + 36
    y = yi + ih + 70
    for k, ln, f in copy_lines(texts, L, 26, G - 140):
        d.text((64, y), ln, font=f, fill=white)
        bb = d.textbbox((64, y), ln, font=f)
        tboxes.append(bb)
        y = bb[3] + (16 if k == "body" else 22)
        if texts[k] not in done:
            done.append(texts[k])
    R.note(d, (G + 40, H - 110), img.size, info["scale"], white, face="mono", extra=f" · {key}, black and white")
    R.frame(page, H, white, None, ["One page of ultramarine, one of the photograph (after Yves Klein's IKB).",
                                   "Slit-scan amp 40 · matte · title cut by the gutter, 100→900"],
            face="mono", head_fill=white, proc_fill=white)
    return finish(page, L, {"text_boxes": tboxes, "photo_boxes": photos, "texts_set": done,
                            "panels": panels, "hero": key}, R)
