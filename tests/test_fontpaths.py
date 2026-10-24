import os
import unittest

from edas import fontpaths, synth
from edas.mood import final, fonts, stillness, variants


class TestBundledFonts(unittest.TestCase):
    """Every font the spreads use resolves to the bundled copy, so no system font folder is needed (macOS)."""

    def test_paths_are_bundled(self):
        paths = list(variants.F.values()) + list(stillness.FONTS.values()) + [
            synth.KOREAN_FONT[0], synth.LATIN_FONT, synth.LATIN_BOLD,
            fontpaths.find("NotoSerifKR-Regular.otf", "notoserifkr")]
        for p in paths:
            self.assertTrue(p.startswith(fontpaths.BUNDLED), p)
            self.assertTrue(os.path.exists(p), p)
        self.assertEqual(final.pretendard_dir(), os.path.join(fontpaths.BUNDLED, "pretendard"))
        self.assertTrue(all(fonts.status().values()))


if __name__ == "__main__":
    unittest.main()
