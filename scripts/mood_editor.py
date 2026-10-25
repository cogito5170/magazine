"""Editor: take mood specs written by the mood writer, render them in the approved structure, judge, reply.

Mailbox (shared project folder, one folder per proposal; the writer only writes spec.json):
    /mnt/project-files/mood-relay/<NNN-name>/spec.json      {"name", "mood", "sources": [...], "layer": {...}}
    /mnt/project-files/mood-relay/<NNN-name>/response.json  written here: verdict, why, V, J
    /mnt/project-files/mood-relay/<NNN-name>/preview.jpg    the spread (and cover) as rendered
Every decision, rejections included, is appended to docs/mood_ledger.jsonl.

    python3 scripts/mood_editor.py [--relay DIR] [--all]     (--all re-judges folders that already have a response)
"""
import argparse
import datetime as dt
import glob
import json
import os
from dataclasses import fields, replace

from PIL import Image

from edas.mood.judge import judge, machine_check
from edas.mood.moodmachine import DANDY, Layer, nocturne_mood
from edas.mood.spreads import match_pages as mp
from edas.mood.spreads.match import TEXTS

ap = argparse.ArgumentParser()
ap.add_argument("--relay", default="/mnt/project-files/mood-relay")
ap.add_argument("--all", action="store_true")
args = ap.parse_args()

ALLOWED = {f.name for f in fields(Layer)} - {"name"}


def tup(v):
    return tuple(tup(x) for x in v) if isinstance(v, list) else v


sp = Image.open(mp.SPREAD_SOURCE).convert("RGB")
crops = {p.key: sp.crop((p.crop[0] + 3, p.crop[1] + 3, p.crop[2] - 3, p.crop[3] - 3)) for p in mp.PHOTOS}
cv = Image.open(mp.COVER_SOURCE).convert("RGB")
ccrops = {"night": cv.crop(mp.COVER_HERO), **{k: cv.crop(b) for k, b in mp.COVER_PRINTS.items()}}
t = mp.SPREAD_TEXTS
stext = {"title": t["title"], "head": t["head"], "body": t["body"]}
c = mp.COVER_TEXTS
ctext = {"title": c["title"], "kicker": c["kicker"], "body": " ".join(c["quote"])}
machine_ok = machine_check(crops, TEXTS)
print("machine (DANDY == approved):", machine_ok)
for d in sorted(glob.glob(os.path.join(args.relay, "*", "spec.json"))):
    folder = os.path.dirname(d)
    if os.path.exists(os.path.join(folder, "response.json")) and not args.all:
        continue
    spec = json.load(open(d))
    bad = sorted(set(spec.get("layer", {})) - ALLOWED)
    if bad:
        res = {"verdict": "REJECT", "why": f"unknown layer keys: {bad}"}
    else:
        L = replace(DANDY, name=spec.get("name", os.path.basename(folder)),
                    **{k: tup(v) for k, v in spec.get("layer", {}).items()})
        note = (f"Mood layer: {L.name} · structure and methods as approved (slit-scan, divided/mirrored/repeated "
                "title, shadow copies)",)
        stext["notes"] = ctext["notes"] = note
        try:
            page, s = nocturne_mood(crops, stext, L)
            res = judge(page, s, L, machine_ok)
            cover_page, _ = nocturne_mood(ccrops, ctext, replace(L, strip_key="park", strip_col=(0.5, 0.1, 0.95)), H=1233)
            prev = Image.new("RGB", (1200, 1500), (245, 243, 238))
            prev.paste(cover_page.resize((1200, 740)), (0, 0))
            prev.paste(page.resize((1200, 739)), (0, 760))
            prev.save(os.path.join(folder, "preview.jpg"), quality=88)
        except Exception as e:                                   # a spec that cannot render is a rejection
            res = {"verdict": "REJECT", "why": f"render failed: {type(e).__name__}: {e}"}
    res["at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    json.dump(res, open(os.path.join(folder, "response.json"), "w"), ensure_ascii=False, indent=1)
    with open("docs/mood_ledger.jsonl", "a") as fh:
        fh.write(json.dumps({"proposal": os.path.basename(folder), "name": spec.get("name"), **res},
                            ensure_ascii=False) + "\n")
    print(res["verdict"], os.path.basename(folder), "-", res["why"])
