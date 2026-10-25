"""Canon critic: record a vision-language critic's reading of a page the code judge passed.

The editor (scripts/mood_editor.py) writes <proposal>/critic/: candidate.jpg, the nearest canonical pages
(canon_1..3.jpg), aesthetic_criteria.md and prompt.md.  A Claude session opens prompt.md and the images, judges the
page beside the canon, and writes critique.json there.  This script validates it and records the result in the
proposal's response.json and in docs/mood_ledger.jsonl, turning the editor's PENDING into the judge's final
ACCEPT or REJECT.  The user follows that verdict; only ACCEPT pages are shown.

    python3 scripts/mood_critic.py [--relay DIR]            list packets still waiting for a critique
    python3 scripts/mood_critic.py --record <proposal>      aggregate and record <proposal>/critic/critique_*.json

Critics are independent (a Claude session, GPT through the effiency relay); each writes critique_<name>.json.
The ensemble rule (edas/mood/canon.py aggregate): at least two valid critiques, majority pass, an agreed dominant
device, key axes at 보통 or better by the median, and no key axis where the critics differ by more than one step.
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from edas.mood.canon import aggregate, validate_critique  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--relay", default="/mnt/project-files/mood-relay")
ap.add_argument("--record")
args = ap.parse_args()

if not args.record:
    for d in sorted(glob.glob(os.path.join(args.relay, "*", "critic", "prompt.md"))):
        folder = os.path.dirname(os.path.dirname(d))
        have = [os.path.basename(f) for f in glob.glob(os.path.join(folder, "critic", "critique_*.json"))]
        if len(have) < 2:
            print("waiting:", os.path.basename(folder), "->", os.path.dirname(d), "has", have or "none")
    sys.exit(0)

folder = os.path.join(args.relay, args.record)
crits = {os.path.basename(f)[len("critique_"):-len(".json")]: json.load(open(f))
         for f in sorted(glob.glob(os.path.join(folder, "critic", "critique_*.json")))}
for name, c in crits.items():
    errs = validate_critique(c)
    if errs:
        print(f"critique_{name}.json ignored: " + "; ".join(errs))
agg = aggregate(crits)
res = json.load(open(os.path.join(folder, "response.json")))
ok = agg["verdict"] == "pass"
res["critic"] = dict(res.get("critic", {}), status=agg["verdict"], ensemble=agg, critiques=crits,
                     at=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
if res.get("verdict") == "PENDING":                  # the judge's final word: invariants + canon critic
    res["verdict"] = "ACCEPT" if ok else "REJECT"
    res["why"] = f"canon critics ({agg['n']}): {agg['why']}; device {agg.get('device')}"
json.dump(res, open(os.path.join(folder, "response.json"), "w"), ensure_ascii=False, indent=1)
with open("docs/mood_ledger.jsonl", "a") as fh:
    fh.write(json.dumps({"proposal": args.record, "stage": "critic", "verdict": res["verdict"], "why": res["why"],
                         **res["critic"]}, ensure_ascii=False) + "\n")
print(res["verdict"], args.record, "-", res["why"])
