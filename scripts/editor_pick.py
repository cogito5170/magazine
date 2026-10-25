"""Editor-in-chief: record which page the user picked from a round (or that none was good enough).

Each pick becomes one winner/loser row per page not picked in docs/judgement_ledger.jsonl; "none" is recorded
too.  These rows are the human ground truth: the canon critic is checked against them, and the Bradley-Terry
model in edas/preference/bt.py can be fitted once enough rows exist.

    python3 scripts/editor_pick.py <round> --shown 031 032 033 034 --chosen 032 --reason "제목 분절이 사진과 운율"
    python3 scripts/editor_pick.py <round> --shown 031 032 033 034 --none --reason "전부 잡지 같지 않다"
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from edas.mood.canon import editor_pick  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("round")
ap.add_argument("--shown", nargs="+", required=True)
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--chosen")
g.add_argument("--none", action="store_true")
ap.add_argument("--reason", default="")
args = ap.parse_args()
rows = editor_pick(args.round, args.shown, None if args.none else args.chosen, args.reason)
print(f"{len(rows)} row(s) -> docs/judgement_ledger.jsonl")
