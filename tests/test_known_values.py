"""Checks every number quoted in the article.  Run from the repository root:

    python -m unittest discover -s tests -v          # quick (a few seconds)
    SLOW=1 python -m unittest discover -s tests -v   # also cross-checks 4 three-dot tiles (about seven minutes)
"""
import os
import shutil
import sys
import unittest
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import shuffledot as sd  # noqa: E402

HAVE_CXX = bool(shutil.which("g++") or shutil.which("clang++"))
if HAVE_CXX:
    import fast_count  # noqa: E402


class TileTypes(unittest.TestCase):
    def test_counts(self):
        self.assertEqual([sd.count_tile_types(n) for n in range(1, 6)], [2, 3, 6, 10, 20])
        for n in range(1, 8):
            self.assertEqual(len(sd.tile_types(n)), sd.count_tile_types(n))


class TwoDotTiles(unittest.TestCase):
    tiles = ["bb", "ww", "bw"]

    def test_games_and_layouts(self):
        per_order = sd.games_by_order(self.tiles)
        self.assertEqual(set(per_order.values()), {174})
        self.assertEqual(sum(per_order.values()), 1044)
        lay = sd.layouts(self.tiles)
        self.assertEqual(len(lay), 249)
        self.assertEqual(Counter(lay.values()), Counter({4: 225, 6: 24}))

    def test_rotations_only(self):
        self.assertEqual(sum(sd.games_by_order(self.tiles, mirrors=False).values()), 2064)
        self.assertEqual(len(sd.layouts(self.tiles, mirrors=False)), 492)

    def test_turn_counts(self):
        levels = sd.grow(("bb", "bw", "ww"))
        self.assertEqual([len(x) for x in levels], [1, 9, 174])
        self.assertEqual([len(x) for x in sd.grow(("bb", "ww", "bw"))], [1, 5, 174])
        self.assertEqual(sum(len(sd.grow(o)[1]) for o in __import__("itertools").permutations(self.tiles)), 46)

    def test_outcomes(self):
        lay = sd.layouts(self.tiles)
        layouts, games = Counter(), Counter()
        for key, n in lay.items():
            o = sd.outcome(key)
            layouts[o] += 1
            games[o] += n
        self.assertEqual(dict(layouts), {"B wins": 61, "W wins": 61, "draw 3:3": 36, "draw 2:2": 91})
        self.assertEqual(dict(games), {"B wins": 258, "W wins": 258, "draw 3:3": 156, "draw 2:2": 372})

    def test_outcomes_straight_lines_only(self):
        c = Counter(sd.outcome(k, straight_only=True) for k in sd.layouts(self.tiles))
        self.assertEqual(dict(c), {"B wins": 30, "W wins": 30, "draw 3:3": 5, "draw 2:2": 184})


class OneDotTiles(unittest.TestCase):
    def test_trivial_game(self):
        self.assertEqual(sum(sd.games_by_order(["b", "w"]).values()), 2)
        self.assertEqual(len(sd.layouts(["b", "w"])), 1)


@unittest.skipUnless(HAVE_CXX, "no C++ compiler available")
class FastCounter(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fast_count.build()

    def check_against_brute_force(self, tiles):
        r = fast_count.count(tiles)
        for mirrors, g, l in ((True, "games_mirrors", "layouts_mirrors"), (False, "games_rotations", "layouts_rotations")):
            self.assertEqual(r[g], sum(sd.games_by_order(tiles, mirrors).values()), (tiles, mirrors, "games"))
            self.assertEqual(r[l], len(sd.layouts(tiles, mirrors)), (tiles, mirrors, "layouts"))

    def test_two_dot_set(self):
        self.check_against_brute_force(["bb", "ww", "bw"])

    def test_three_dot_triples(self):
        self.check_against_brute_force(["bbb", "bbw", "www"])
        self.check_against_brute_force(["bwb", "bww", "wbw"])

    @unittest.skipUnless(os.environ.get("SLOW"), "set SLOW=1 for the four-tile cross-check")
    def test_four_three_dot_tiles(self):
        self.check_against_brute_force(["bbb", "bbw", "bwb", "bww"])

    def test_six_three_dot_tiles(self):
        r = fast_count.count(sd.tile_types(3))
        self.assertEqual(r["fixed_sets"], 2_172_016)
        self.assertEqual(r["games_per_order_mirrors"], [73_922_288])
        self.assertEqual(r["games_mirrors"], 53_224_047_360)
        self.assertEqual(r["games_rotations"], 106_447_357_440)
        self.assertEqual(r["layouts_mirrors"], 781_937_280)
        self.assertEqual(r["layouts_rotations"], 1_563_851_520)


if __name__ == "__main__":
    unittest.main()
