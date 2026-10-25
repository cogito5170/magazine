"""MATCH pages (new copy), round I of the previous session's flow: art direction from the copy.

Same rules as `artdirect` (round I, the intensity the user called right):
* the supplied photographs are the only imagery; they are cropped, enlarged, extended at their edges, toned
  down and covered by a film grain (recorded per page); no retouching, no generated imagery;
* nothing analytic on the page (no swatches, codes, labels); copy verbatim;
* one structural idea per page, taken from what the copy says.

Spread copy: "원색보다 한 톤 낮은 색을 좋아한다. 가라앉은 색은 혼자 드러나지 않고 주변과 어우러진다. ..."
    SINK    한 톤 낮은 / 가라앉은 -- four places as bands, each one tone darker and lower than the last
    BLEND   주변과 어우러진다 -- four places stretched at their edges until they run into one another
    AMONG   혼자 드러나지 않고 -- the crowded park as the whole spread, the person one of many
    TONE    JAJU의 톤에 녹아들어 -- each photo set in a field of its own colour, one tone lower
Cover copy: "옷의 색감, 원단, 디자인을 맞춘다. 그날 갈 장소에 옷의 무드를 맞춘다."
    PAIR    the dress form and the model, one page each, scaled to one height: clothes matched to a body
    FABRIC  the quilted vest enlarged until the fabric is the page; form and model as small prints
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance

from .artdirect import cover, grain, scrim
from .final import kr
from .photo_led import tracked
from .variants import fnt, width

W = 2000


def _tone(img, k):
    """One step lower: brightness × k (a tone treatment)."""
    return ImageEnhance.Brightness(img).enhance(k)


def _wrap(text, f, maxw):
    lines, cur = [], ""
    for wd in text.split(" "):
        cand = (cur + " " + wd).strip()
        if f.getlength(cand) > maxw and cur:
            lines.append(cur)
            cur = wd
        else:
            cur = cand
    lines.append(cur)
    assert " ".join(lines) == text
    return lines


def _copy(d, xy, texts, maxw, fill, size=20, head=28):
    x, y = xy
    if texts.get("head"):
        d.text((x, y), texts["head"], font=kr("medium", head), fill=fill)
        y += int(head * 1.9)
    for ln in _wrap(texts["body"], kr("light", size), maxw):
        d.text((x, y), ln, font=kr("light", size), fill=fill)
        y += int(size * 1.75)
    return y


def _person_crop(img, pb, w, h, scale_to_h=True):
    """Fill w×h from the photo, centred on the person."""
    fx = ((pb[0] + pb[2]) / 2) / img.size[0]
    fy = ((pb[1] + pb[3]) / 2) / img.size[1]
    return cover(img, (w, h), focus=(fx, fy))


# ------------------------------------------------------------------ spread A. SINK
def sink(crops, texts, persons, H=1231):
    bg = (22, 21, 20)
    page = Image.new("RGB", (W, H), (226, 220, 210))
    rec = {}
    tops = (230, 330, 430, 530)
    tones = (1.0, 0.9, 0.8, 0.7)
    for i, k in enumerate(("park", "shop", "night", "rock")):
        x0 = i * 500
        band, info = _person_crop(crops[k], persons[k], 496, H)
        band = _tone(band, tones[i])
        page.paste(band.crop((0, 0, 496, H - tops[i])), (x0 + 2, tops[i]))
        rec[k] = dict(info, top=tops[i], brightness=tones[i])
    d = ImageDraw.Draw(page)
    _copy(d, (60, 50), texts, 1500, bg, size=23, head=32)
    # the title sinks: only its upper part stays above the foot of the page
    ft = fnt("black", 430)
    tw = width(texts["title"], ft, -10)
    tracked(d, ((W - tw) / 2, H - 330), texts["title"], ft, (236, 232, 224), -10)
    page = grain(page, 0.035, 11, size=1.4)
    return page, {"name": "SINK / 가라앉음", "idea": "한 톤 낮은 색, 가라앉은 색: four places as bands, each a step "
                  "darker and lower than the last; the title sinks below the foot of the page, still readable",
                  "photos": rec, "treatment": "person-centred crops, brightness 1.0/0.9/0.8/0.7, film grain"}


# ------------------------------------------------------------------ spread B. BLEND
def _extend(img, w):
    """Widen a photo to w by stretching its outermost columns (the photo itself is untouched)."""
    if img.size[0] >= w:
        x0 = (img.size[0] - w) // 2
        return img.crop((x0, 0, x0 + w, img.size[1]))
    pad = w - img.size[0]
    l, r = pad // 2, pad - pad // 2
    out = Image.new("RGB", (w, img.size[1]))
    out.paste(img.crop((0, 0, 4, img.size[1])).resize((l, img.size[1]), Image.NEAREST), (0, 0))
    out.paste(img, (l, 0))
    out.paste(img.crop((img.size[0] - 4, 0, img.size[0], img.size[1])).resize((r, img.size[1]), Image.NEAREST),
              (l + img.size[0], 0))
    return out


def blend(crops, texts, persons, H=1231):
    seg, ov = 560, 80
    order = ("night", "shop", "park", "rock")
    page = np.zeros((H, W, 3), float)
    weight = np.zeros((H, W, 1), float)
    rec = {}
    for i, k in enumerate(order):
        img, pb = crops[k], persons[k]
        s = H / img.size[1]
        im = img.resize((round(img.size[0] * s), H), Image.LANCZOS)
        cx = int((pb[0] + pb[2]) / 2 * s)
        w_ = seg + ov
        x_src = int(np.clip(cx - w_ // 2, 0, max(0, im.size[0] - w_)))
        im = _extend(im.crop((x_src, 0, min(im.size[0], x_src + w_), H)), w_)
        x0 = int(i * (W - w_) / 3)
        a = np.ones((1, w_, 1))
        ramp = np.linspace(0, 1, ov)[None, :, None]
        if i > 0:
            a[:, :ov] = ramp
        if i < 3:
            a[:, -ov:] = ramp[:, ::-1]
        page[:, x0:x0 + w_] += np.asarray(im, float) * a
        weight[:, x0:x0 + w_] += a
        rec[k] = {"scale": round(s, 2), "x": x0, "stretched_px": max(0, w_ - (im.size[0]))}
    page = Image.fromarray(np.clip(page / np.maximum(weight, 1e-6), 0, 255).astype("uint8"))
    page = scrim(page, (0, H - 330, 1100, H), 0.6)
    d = ImageDraw.Draw(page)
    ft = fnt("thin", 300)
    tw = width(texts["title"], ft, 30)
    tracked(d, ((W - tw) / 2, 380), texts["title"], ft, (240, 236, 228), 30)
    _copy(d, (60, H - 270), texts, 1000, (240, 236, 228), size=20, head=28)
    page = grain(page, 0.04, 21, size=1.6)
    return page, {"name": "BLEND / 어우러짐", "idea": "주변과 어우러진다: the four places stretched at their edges and "
                  "cross-faded until they run into one another; one thin word holds them", "photos": rec,
                  "treatment": "height-fitted crops, edge columns stretched to meet, 80 px cross-fades, scrim, grain"}


# ------------------------------------------------------------------ spread C. AMONG
def among(crops, texts, persons, H=1231):
    img, pb = crops["park"], persons["park"]
    page, info = cover(img, (W, H), focus=(0.62, 0.5))
    page = scrim(page, (0, H - 470, 1150, H), 0.66)
    d = ImageDraw.Draw(page)
    bone = (238, 234, 226)
    x, y = 60, H - 430
    rec = {"park": dict(info, placement="full bleed; the person stays one of the crowd")}
    for k in ("night", "shop", "rock"):
        im = crops[k]
        s = 150 / im.size[1]
        im2 = im.resize((max(1, round(im.size[0] * s)), 150), Image.LANCZOS)
        page.paste(im2, (x, y))
        rec[k] = {"scale": round(s, 2), "box": (x, y, x + im2.size[0], y + 150)}
        x += im2.size[0] + 10
    tracked(d, (W - 60 - width(texts["title"], fnt("bold", 120), 4), 60), texts["title"], fnt("bold", 120), bone, 4)
    _copy(d, (60, H - 250), texts, 1050, bone, size=20, head=28)
    page = grain(page, 0.045, 31, size=1.6)
    return page, {"name": "AMONG / 혼자 드러나지 않고", "idea": "the crowded park is the whole spread; the subject is "
                  "neither centred nor marked, one of the crowd; the other places as a small contact strip",
                  "photos": rec, "treatment": "enlargement, scrim under the copy, grain"}


# ------------------------------------------------------------------ spread D. TONE
def tone(crops, texts, persons, H=1231):
    page = Image.new("RGB", (W, H))
    rec = {}
    fields = []
    for i, k in enumerate(("night", "park", "shop", "rock")):
        img, pb = crops[k], persons[k]
        mean = np.asarray(img, float).reshape(-1, 3).mean(0)
        field = tuple(int(v * 0.85) for v in mean)                       # one tone lower than the photo
        fields.append(field)
        x0 = i * 500
        ImageDraw.Draw(page).rectangle((x0, 0, x0 + 500, H), fill=field)
        im, info = _person_crop(img, pb, 340, 520)
        page.paste(im, (x0 + 80, 300))
        rec[k] = dict(info, field=field)
    d = ImageDraw.Draw(page)
    ft = fnt("black", 220)
    x = 80
    for i, ch in enumerate(texts["title"]):
        c = tuple(min(255, int(v * 1.9) + 20) for v in fields[min(3, i * 4 // len(texts["title"]))])
        tracked(d, (x, 40), ch, ft, c, 0)
        x += ft.getlength(ch) + 4
    _copy(d, (80, 880), texts, 1700, (240, 236, 228), size=20, head=28)
    page = grain(page, 0.03, 41, size=1.4)
    return page, {"name": "TONE / 한 톤 낮은", "idea": "each place sits in a field of its own colour, one tone lower; "
                  "the person melts into the field; the title letters take the four tones", "photos": rec,
                  "treatment": "photo mean colour × 0.85 as the field; crops; grain"}


# ------------------------------------------------------------------ cover E. PAIR
def pair(cv, texts, boxes, H=1233):
    paper = tuple(int(v) for v in np.asarray(cv.crop((660, 20, 740, 80)), float).reshape(-1, 3).mean(0))  # the wall
    page = Image.new("RGB", (W, H), paper)
    rec = {}
    top, ph = 120, 940                       # both figures stand the same height, heads on one line
    floor_src = 488                          # where the floor starts in the cover source
    floor = tuple(int(v) for v in np.asarray(cv.crop((600, 560, 700, 620)), float).reshape(-1, 3).mean(0))
    b0 = boxes["form"]
    s = ph / (b0[3] - b0[1])
    fy = top + int((floor_src - b0[1]) * s)
    ImageDraw.Draw(page).rectangle((0, fy, W, H), fill=floor)
    for i, k in enumerate(("form", "model")):
        b = boxes[k]
        im = cv.crop(b)
        im2 = im.resize((round(im.size[0] * s), ph), Image.LANCZOS)
        x = 500 + 1000 * i - im2.size[0] // 2
        page.paste(im2, (x, top))
        rec[k] = {"scale": round(s, 2), "box": (x, top, x + im2.size[0], top + ph)}
    d = ImageDraw.Draw(page)
    ft = fnt("black", 300)
    tw = width(texts["title"], ft, 20)
    tracked(d, ((W - tw) / 2, fy - 300), texts["title"], ft, (36, 34, 32), 20)
    fq = kr("regular", 30)
    y = fy + 60
    tracked(d, (60, y + 6), texts["kicker"], fnt("bold", 16), (36, 34, 32), 5)
    for ln in texts["quote"]:
        d.text((W - 60 - 470, y), ln, font=fq, fill=(36, 34, 32))
        y += 46
    page = grain(page, 0.03, 51, size=1.4)
    return page, {"name": "PAIR / 맞춘다", "idea": "the dress form and the model, one page each, scaled to one height "
                  "with heads on one line; the word sits across both bodies at the waist", "photos": rec,
                  "treatment": "crops from the cover, enlargement ×1.7, grain"}


# ------------------------------------------------------------------ cover F. FABRIC
def fabric(cv, texts, boxes, H=1233):
    vest = (800, 160, 905, 330)                       # the quilted vest on the model, in the cover source
    page, info = cover(cv.crop(vest), (W, H), focus=(0.5, 0.5))
    page = scrim(page, (0, H - 420, 1200, H), 0.6)
    d = ImageDraw.Draw(page)
    bone = (240, 236, 228)
    rec = {"vest": dict(info, source_box=vest)}
    x, y = W - 60, 60
    for k in ("model", "form"):
        im = cv.crop(boxes[k])
        s = 300 / im.size[1]
        im2 = im.resize((round(im.size[0] * s), 300), Image.LANCZOS)
        x -= im2.size[0]
        page.paste(im2, (x, y))
        rec[k] = {"scale": round(s, 2)}
        x -= 16
    ft = fnt("black", 260)
    tracked(d, (56, 40), texts["title"], ft, bone, 6)
    tracked(d, (60, H - 330), texts["kicker"], fnt("bold", 16), bone, 5)
    y = H - 280
    for ln in texts["quote"]:
        d.text((60, y), ln, font=kr("regular", 34), fill=bone)
        y += 56
    page = grain(page, 0.05, 61, size=1.8)
    return page, {"name": "FABRIC / 원단", "idea": "the vest's quilting enlarged until the fabric is the cover; the "
                  "form and the model as two small prints", "photos": rec,
                  "treatment": f"vest enlarged ×{info['scale']:.1f} (very soft: a poor image), scrim, grain"}


SPREADS = {"A_sink": sink, "B_blend": blend, "C_among": among, "D_tone": tone}
COVERS = {"E_pair": pair, "F_fabric": fabric}
