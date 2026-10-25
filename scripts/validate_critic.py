"""Validate the canon critic before trusting it: does the ensemble pass canonical pages and the approved spreads,
and reject the drafts the user rejected?

    python3 scripts/validate_critic.py --build [--out DIR]    write one critic packet per labelled page
    python3 scripts/validate_critic.py --report [--out DIR]   aggregate critique_*.json and print the metrics

Labelled set: every canonical design (its first image, left out of its own references: leave-one-out) and the
three approved spreads are positives; drafts the user rejected (docs/canon/validation_set.json) are negatives.
Report: true positive and true negative rates, balanced accuracy, ROC AUC of the median key-axis grade, mean
pairwise quadratic weighted kappa between critics.  Written to docs/canon/validation_report.json.
"""
import argparse
import glob
import json
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from edas.mood.canon import aggregate, board, validation_report, write_packet  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--out", default="/mnt/project-files/critic-validation")
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--build", action="store_true")
g.add_argument("--report", action="store_true")
args = ap.parse_args()


def labelled():
    for it in board():
        if it["images"]:
            yield {"id": f"canon_{it['index']:02d}", "file": it["images"][0]["file"], "label": 1,
                   "exclude": it["index"]}
    for r in json.load(open("docs/canon/validation_set.json")):
        yield dict(r, exclude=None)


if args.build:
    for r in labelled():
        folder = os.path.join(args.out, r["id"])
        write_packet(Image.open(r["file"]), folder, None, exclude=r["exclude"])
        json.dump({"label": r["label"], "file": r["file"]}, open(os.path.join(folder, "label.json"), "w"))
    print("packets:", len(list(labelled())), "->", args.out)
else:
    results = []
    for r in labelled():
        crit = {os.path.basename(f)[9:-5]: json.load(open(f))
                for f in glob.glob(os.path.join(args.out, r["id"], "critic", "critique_*.json"))}
        if crit:
            results.append((r["label"], aggregate(crit)))
    rep = validation_report(results)
    json.dump(rep, open("docs/canon/validation_report.json", "w"), indent=1)
    print(json.dumps(rep, ensure_ascii=False))
