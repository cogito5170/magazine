"""Render the final MATCH series and its presentation PDF.

    sh scripts/fetch_fonts.sh          # Pretendard, once per machine
    PYTHONPATH=.:examples python3 examples/match_final.py
"""
from match_spread_data import PHOTOS, TEXTS
from edas.mood.final import present, render

APPROVAL = {"approver": "user", "decision": "approved", "scope": "MATCH spread, round III series",
            "instruction": "좋다 이제 작업물들은 현대 기법으로 해석하고 정제해서 최종 제시하여라"}

if __name__ == "__main__":
    meta = render("output/match/original_spread.png", PHOTOS, TEXTS, "output/match/final", approval=APPROVAL)
    for p in present(meta, "output/match/final/MATCH_final_presentation.pdf", TEXTS):
        print(p)
