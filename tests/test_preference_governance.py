import os
import unittest

import numpy as np
from reportlab.pdfgen import canvas

from edas.config import load_config
from edas.governance.evidence import (Approval, ChangeProposal, ClaimType, Evidence, Purpose, Verification,
                                      is_actionable)
from edas.governance.gate import GateError, assert_finalizable, compare_documents, record_decision
from edas.pdf.extract import open_document
from edas.preference.bt import BradleyTerry, InsufficientData
from edas.preference.schema import Judgment
from edas.preference.validate import grouped_folds, original_vs_alternatives

from .helpers import TMP


def simulate(n=600, seed=0):
    rng = np.random.default_rng(seed)
    true = {"F0": 0.0, "F1": 1.0, "F2": -1.0}
    comps, js = [], []
    for i in range(n):
        a, b = rng.choice(list(true), 2, replace=False)
        p = 1 / (1 + np.exp(-(true[a] - true[b])))
        ch = "A" if rng.random() < p else "B"
        comps.append((a, b, ch, f"r{i % 4}"))
        js.append(Judgment(rater_id=f"r{i % 4}", experiment="A_typeface", criterion="glyph_beauty",
                           stimulus_a=a, stimulus_b=b, choice=ch, font_a=a, font_b=b, page_id=f"p{i % 6}"))
    return true, comps, js


class TestPreference(unittest.TestCase):
    def test_bt_recovers_scores(self):
        true, comps, _ = simulate()
        m = BradleyTerry().fit(comps)
        self.assertAlmostEqual(m.score("F1") - m.score("F0"), 1.0, delta=0.25)
        self.assertAlmostEqual(m.score("F2") - m.score("F0"), -1.0, delta=0.25)

    def test_refuses_small_data(self):
        _, comps, _ = simulate(10)
        with self.assertRaises(InsufficientData):
            BradleyTerry(min_decisive=20).fit(comps)

    def test_grouped_folds_do_not_leak(self):
        _, _, js = simulate()
        for tr, te, _ in grouped_folds(js, lambda j: j.page_id, k=3):
            self.assertFalse({j.page_id for j in tr} & {j.page_id for j in te})

    def test_original_vs_alternatives_ci(self):
        _, _, js = simulate()
        r = original_vs_alternatives(js, "F0", n_boot=60)
        self.assertEqual(r["status"], "ok")
        lo, hi = r["alternatives"]["F1"]["ci95"]
        self.assertGreater(lo, 0)

    def test_unknown_criterion_rejected(self):
        with self.assertRaises(Exception):
            Judgment(rater_id="r", experiment="A_typeface", criterion="beauty_overall", stimulus_a="a",
                     stimulus_b="b", choice="A")


class TestGovernance(unittest.TestCase):
    def test_no_invented_sources(self):
        e = Evidence(claim_type=ClaimType.OFFICIAL_STANDARD, source_id="iso_9999_made_up")
        with self.assertRaises(ValueError):
            e.source()

    def test_aesthetic_claim_needs_preference_test(self):
        p = ChangeProposal(page=3, element="title font", original_state="A", proposed_change="B",
                           purpose=Purpose.AESTHETIC,
                           evidence=[Evidence(claim_type=ClaimType.EMPIRICAL_STUDY, source_id="choi_hyun_2024")])
        self.assertEqual(p.verification_status, Verification.UNVERIFIED)
        self.assertFalse(is_actionable(Evidence and ChangeProposal(
            page=3, element="x", original_state=1, proposed_change=2, purpose=Purpose.FUNCTIONAL,
            evidence=[Evidence(claim_type=ClaimType.SUBJECTIVE_HYPOTHESIS)]))[0])
        flat = p.flat()
        for k in ("page", "element", "original_state", "proposed_change", "claim_type", "source_title",
                  "source_url", "publisher", "publication_date", "exact_section_or_page", "source_scope",
                  "applicability", "measurement_method", "result", "uncertainty", "preserved_strengths",
                  "expected_tradeoffs", "user_approval_status", "verification_status"):
            self.assertIn(k, flat)

    def test_gate(self):
        p = ChangeProposal(page=2, element="margin", original_state=1, proposed_change=2,
                           purpose=Purpose.FUNCTIONAL, evidence=[])
        with self.assertRaises(GateError):
            assert_finalizable([p], protected_pages=set())
        record_decision(p, "approved", "user")
        with self.assertRaises(GateError):
            assert_finalizable([p], protected_pages={2})          # protected page
        assert_finalizable([p], protected_pages={2}, page_unlocks={2: "user"})
        with self.assertRaises(GateError):
            record_decision(p, "approved", "")

    def test_page2_regression(self):
        def make(path, change_page2):
            c = canvas.Canvas(path, pagesize=(300, 300))
            for i in range(3):
                c.setFont("Helvetica", 12)
                txt = f"page {i + 1} content"
                if i == 1 and change_page2:
                    c.setFillColorRGB(0.8, 0.1, 0.1)
                    txt = "page 2 contant"
                c.drawString(40, 200, txt)
                c.rect(40, 40, 80, 60, fill=1, stroke=0)
                c.showPage()
            c.save()
        a, b = os.path.join(TMP, "orig3.pdf"), os.path.join(TMP, "cand3.pdf")
        make(a, False)
        make(b, True)
        cfg = load_config()
        same = compare_documents(open_document(a, cfg), open_document(a, cfg), {2})
        self.assertTrue(same["passed"])
        diff = compare_documents(open_document(a, cfg), open_document(b, cfg), {2})
        self.assertFalse(diff["passed"])
        self.assertEqual(diff["protected_page_failures"], [2])
        self.assertIn("text", diff["pages"][2])
        self.assertEqual(diff["pages"][1], {})

    def test_protected_page_gets_no_proposal(self):
        from edas.pipeline import RunOptions, analyze
        from .helpers import synthetic
        res, _, _ = analyze(synthetic()[0], load_config(), RunOptions(with_candidates=False, protected_pages={2}))
        pages = [r["page"] for r in res.recommendations + res.evaluation["observations_without_verified_basis"]]
        self.assertNotIn(2, pages)


if __name__ == "__main__":
    unittest.main()
