"""Replay every MATCH round of the previous session, in order, with the code it ran, on any copy.

    python3 scripts/replay_match_flow.py            # original copy  -> output/flow/original
    python3 scripts/replay_match_flow.py new        # new copy (match_pages) -> output/flow/new
The functions are called unchanged.  Rounds (git): photo_led fb35b4a · variants 1cb3461 · artdirect 85cdf0b ·
defamiliar ea1bde2 · defamiliar2 2074360 · final (III refined) 85fd71c · contemporary/dandy 3ac3998 (approved).
"""
import os
import sys
import traceback

from PIL import Image

from edas.mood.spreads.match import PHOTOS, TEXTS

SRC = "sources/match_spread.png"
which = sys.argv[1] if len(sys.argv) > 1 else "original"
texts = dict(TEXTS)
if which == "new":
    from edas.mood.spreads.match_pages import SPREAD_TEXTS as N
    s = N["body"].split(". ")
    texts.update(body_ko=[s[0] + ". " + s[1] + ".", s[2]], kicker="", running_head="", folio="")
out = f"output/flow/{which}"
os.makedirs(out, exist_ok=True)
src = Image.open(SRC).convert("RGB")
crops = {p.key: src.crop((p.crop[0] + 3, p.crop[1] + 3, p.crop[2] - 3, p.crop[3] - 3)) for p in PHOTOS}


def run(name, fn):
    try:
        fn(os.path.join(out, name))
        print("ok  ", name)
    except Exception as e:
        print("FAIL", name, type(e).__name__, e)
        traceback.print_exc(limit=1)


from edas.mood import artdirect, contemporary, defamiliar, defamiliar2, final, photo_led, variants  # noqa: E402

run("0_photo_led", lambda d: photo_led.compose(SRC, PHOTOS, texts, d))
run("1_variants", lambda d: variants.render_all(SRC, PHOTOS, texts, d))
run("2_artdirect", lambda d: artdirect.render(SRC, PHOTOS, texts, d))
run("3_defamiliar", lambda d: defamiliar.render(SRC, PHOTOS, texts, d))
run("4_defamiliar2", lambda d: defamiliar2.render(SRC, PHOTOS, texts, d))
run("5_final", lambda d: final.render(SRC, PHOTOS, texts, d))


def approved(d):
    os.makedirs(d, exist_ok=True)
    contemporary.nocturne_contemporary(crops, texts)[0].save(f"{d}/MATCH_contemporary.png")
    contemporary.nocturne_dandy(crops, texts)[0].save(f"{d}/MATCH_dandy.png")


run("6_approved", approved)
