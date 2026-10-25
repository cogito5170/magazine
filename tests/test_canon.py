import json
import os
import shutil
import tempfile
import unittest

from PIL import Image

from edas.mood import canon

from .helpers import TMP


def good_critique(**over):
    c = {"dominant_device": "syllable-stack", "grades": {a: "좋음" for a in canon.AXES}, "closest_canon": 14,
         "evidence": "음절 분절 스택이 판면 높이를 채우고 본문은 정형 단 구성이다.", "verdict": "pass"}
    c.update(over)
    return c


class TestCanonBoard(unittest.TestCase):
    def test_board_images_exist(self):
        b = canon.board()
        self.assertEqual(len(b), 37)
        self.assertEqual([x["index"] for x in b], list(range(1, 38)))
        files = [im["file"] for x in b for im in x["images"]]
        self.assertEqual(len(files), 67)
        self.assertTrue(all(os.path.exists(f) for f in files))

    def test_devices_point_at_board(self):
        for nums in canon.DEVICES.values():
            self.assertTrue(all(1 <= n <= 37 for n in nums))

    def test_nearest_returns_distinct_designs(self):
        page = Image.open(canon.board()[13]["images"][0]["file"])    # a canon page is nearest to itself
        near = canon.nearest(page, 3)
        self.assertEqual(near[0]["index"], 14)
        self.assertEqual(near[0]["distance"], 0.0)
        self.assertEqual(len({n["index"] for n in near}), 3)


class TestCritique(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(canon.validate_critique(good_critique()), [])
        self.assertTrue(canon.critic_passes(good_critique()))

    def test_invalid(self):
        self.assertTrue(canon.validate_critique(good_critique(dominant_device="glitch")))
        self.assertTrue(canon.validate_critique(good_critique(grades={"bold": "멋짐"})))
        self.assertTrue(canon.validate_critique(good_critique(closest_canon=99)))

    def test_competing_devices_fail(self):
        g = {a: "좋음" for a in canon.AXES}
        g["restraint"] = "미흡"
        self.assertFalse(canon.critic_passes(good_critique(grades=g)))
        self.assertFalse(canon.critic_passes(good_critique(dominant_device="none")))

    def test_device_check(self):
        self.assertIsNone(canon.device_check({}))
        self.assertTrue(canon.device_check({"dominant_device": "masthead-intrusion"}))
        self.assertFalse(canon.device_check({"dominant_device": "pixel sort"}))


class TestPacketAndPick(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp(dir=TMP)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_packet(self):
        out = canon.write_packet(Image.open("docs/approved/match-dandy.jpg"), self.d, "single-object")
        names = sorted(os.listdir(out["packet"]))
        self.assertEqual(names, ["aesthetic_criteria.md", "candidate.jpg", "canon_1.jpg", "canon_2.jpg",
                                 "canon_3.jpg", "prompt.md", "zoom_gutter.jpg"])
        self.assertEqual(set(out["measures"]), {"quiet", "focal", "palette"})
        self.assertIn("single-object", open(os.path.join(out["packet"], "prompt.md")).read())

    def test_pick_rows(self):
        led = os.path.join(self.d, "ledger.jsonl")
        rows = canon.editor_pick("r1", ["a", "b", "c", "d"], "b", "test", ledger=led)
        self.assertEqual([(r["winner"], r["loser"]) for r in rows], [("b", "a"), ("b", "c"), ("b", "d")])
        canon.editor_pick("r2", ["a", "b"], None, "none good", ledger=led)
        lines = [json.loads(x) for x in open(led)]
        self.assertEqual(len(lines), 4)
        self.assertIsNone(lines[-1]["winner"])
        with self.assertRaises(ValueError):
            canon.editor_pick("r3", ["a"], "z", ledger=led)


class TestEnsemble(unittest.TestCase):
    def test_needs_two_agreeing_critics(self):
        self.assertEqual(canon.aggregate({"claude": good_critique()})["verdict"], "fail")
        self.assertEqual(canon.aggregate({"claude": good_critique(), "gpt": good_critique()})["verdict"], "pass")

    def test_disagreement_rejects(self):
        g = {a: "좋음" for a in canon.AXES}
        g["stable"] = "나쁨"
        agg = canon.aggregate({"claude": good_critique(), "gpt": good_critique(grades=g, verdict="revise")})
        self.assertEqual(agg["verdict"], "fail")
        self.assertIn("stable", agg["why"])

    def test_qwk(self):
        self.assertAlmostEqual(canon.qwk([0, 1, 2, 3, 4], [0, 1, 2, 3, 4]), 1.0)
        self.assertLess(canon.qwk([0, 1, 2, 3, 4], [4, 3, 2, 1, 0]), 0)

    def test_leave_one_out(self):
        page = Image.open(canon.board()[13]["images"][0]["file"])
        self.assertNotIn(14, [n["index"] for n in canon.nearest(page, 3, exclude=14)])

    def test_validation_metrics(self):
        hi = canon.aggregate({"a": good_critique(), "b": good_critique()})
        lo = canon.aggregate({"a": good_critique(grades={x: "미흡" for x in canon.AXES}, verdict="reject"),
                              "b": good_critique(grades={x: "나쁨" for x in canon.AXES}, verdict="reject")})
        rep = canon.validation_report([(1, hi), (0, lo)])
        self.assertEqual((rep["balanced_accuracy"], rep["auc"]), (1.0, 1.0))
