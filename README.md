# Shuffledot combinatorics

Code behind the "Shuffledot geekery" article: how many layouts, and how many different games, can you make from a Shuffledot-style tile set as the tiles get longer?

[Shuffledot](https://shuffledot.com) is a physical tile game. Each tile is a row of black and white dots. This repo counts what happens with 1-dot, 2-dot and 3-dot tiles exactly, and estimates the full box of twenty 4-dot tiles.

## Headline numbers

Rotations and mirror images are treated as the same board.

| Dots per tile | Tiles played | Final layouts | Games (all play orders) |
| --- | --- | --- | --- |
| 1 | 2 | 1 | 2 |
| 2 | 3 | 249 | 1,044 |
| 3 | 6 | 781,937,280 | 53,224,047,360 |
| 4 (real box, two of each of ten tiles) | 20 | not computed | about 2 x 10^56 (estimate) |

If mirror images count as different (rotations only), the 2-dot and 3-dot rows become 492 and 1,563,851,520 layouts, and 2,064 and 106,447,357,440 games.

Win/draw split for the 2-dot set (largest group of same-coloured dots wins; groups join sideways or up and down):

| | B wins | W wins | 3:3 draw | 2:2 draw |
| --- | --- | --- | --- | --- |
| 249 layouts | 61 | 61 | 36 | 91 |
| 1,044 games | 258 | 258 | 156 | 372 |

## What is being counted

* A **tile** is a straight row of n dots, each black or white. A tile can be turned round, so `bbw` and `wbb` are the same tile. The number of distinct n-dot tiles is `(2^n + 2^ceil(n/2)) / 2`, giving 2, 3, 6, 10, 20, ...
* Tiles sit on a square grid, one dot per square, so edges always line up.
* Each tile is used exactly once. Every new tile must not overlap and must share part of an edge with a tile already played. Touching at a corner does not count.
* A **layout** is a finished arrangement of all the tiles. A **game** is the order of play plus where each tile went, so the same layout built in a different order is a different game. Two games are the same only if every step matches after one overall rotation or mirror.
* Slides, and any other rule not listed here, are not modelled.

## Quick start

You need Python 3 (developed on 3.13; standard library only). The fast exact counter also needs `g++` or `clang++`.

```bash
python shuffledot.py tiles 3          # the six distinct 3-dot tiles
python shuffledot.py report 2         # games, layouts, turn-by-turn counts for the 2:1 set
python shuffledot.py outcomes 2       # win/draw table for the 2:1 set
python fast_count.py --dots 2         # same 2:1 numbers via the fast counter (instant)
python fast_count.py                  # six 3-dot tiles: the billions (about 2 seconds)
python estimate_games.py              # the real box, twenty 4-dot tiles (about 2 minutes)
python estimate_games.py --selftest   # check the estimator against exact counts
python make_figures.py                # redraws the numbered figures into ./figures
python -m unittest discover -s tests -v
```

Useful options: `--rotations-only` (do not merge mirror images), `--tiles bb,ww,bw` (choose your own tiles), `outcomes --straight` (only straight lines of dots count: 30 / 30 / 5 / 184 layouts), `estimate_games.py --workers 4 --samples 100000` (more precision, faster).

## Files

| File | What it is |
| --- | --- |
| `shuffledot.py` | Readable brute-force reference. Plays every game turn by turn and merges symmetric boards. Fine for small sets, far too slow for six 3-dot tiles. |
| `fast_count.py`, `fast/growth.cpp` | Exact fast counter for sets where every tile is a different type. Reproduces the brute-force numbers on every small set tried, then scales to six tiles. |
| `estimate_games.py` | Self-contained estimator (standard library only) for sets with duplicate tiles, such as the real box. Copy it on its own if you like. |
| `make_figures.py` | Draws the numbered layout figures as SVG (PNG too if `cairosvg` is installed). |
| `tests/test_known_values.py` | Checks every number quoted in the article, and cross-checks the fast counter and the estimator. |

## How the fast exact counter works

Brute force cannot visit billions of games, so `fast_count.py` counts instead of listing.

1. `growth.cpp` counts **ordered growth sequences**: every way to place k bars one at a time so each touches the ones already down. It also counts connected sets of k bars (Redelmeier's algorithm), and the sequences that survive a mirror flip.
2. Every tile order uses the same shapes, only with different tiles dropped in, so the geometric count is shared by all `k!` orders. Multiply in the ways to assign tiles and turn the lopsided ones (`bbw`, `bww`) round.
3. Divide out the symmetries with Burnside's lemma: with all tiles different, rotations never leave a board unchanged, so rotation-only counts divide by 4, and the mirror-merged counts divide by 8 after adding back the small number of boards that are their own mirror image (23,040 layouts for six 3-dot tiles).

## Estimating the full box (twenty 4-dot tiles)

The real box holds two of each of ten 4-dot tiles, and a game uses all twenty. That is far beyond exact counting, so `estimate_games.py` multiplies three pieces:

```
games  ~  tile orders  x  placement sequences  x  dot orientations  /  4
```

| Piece | Value for the real box | How |
| --- | --- | --- |
| Tile orders | 2,375,880,867,360,000 (2.4 quadrillion) | Exact: `20! / (2!)^10`. Twenty tiles can be ordered 20! ways, but swapping the two copies of a tile changes nothing you can see, and there are ten pairs, so each distinct order is counted 2^10 = 1,024 times and is divided out. |
| Placement sequences (G) | about 9 x 10^37 | Estimated. Every tile order has the same G, because the shapes do not depend on which tile fills them. |
| Dot orientations | 4,096 | Exact: 2 for each of the twelve tiles that look different turned round (6 types x 2 copies), so 2^12. |
| Divide by 4 | | Rotations and mirror images are the same game. With the first tile upright, 4 symmetries remain, and none leaves a sequence unchanged except a negligible number of mirror-symmetric ones. |

Result: about **2 x 10^56** games (`10^56.3`). For scale, six 3-dot tiles give 5 x 10^10, and everyone on Earth playing one game a second since the Big Bang would reach about 3.5 x 10^27.

**How G is estimated.** G is the number of leaves of the game tree: place 20 bars, each touching the cluster. It is too big to count, so the script uses Knuth's random-path method. It walks down the tree choosing one legal placement at random each turn, and multiplies together the number of options it had at every turn (from about 32 on turn 2 to about 160 on turn 20). Averaged over many walks, that product is an unbiased estimate of the number of leaves.

**How far to trust it.**
* The method is checked, not assumed. `--selftest` runs the same walks on cases whose exact G is known from `fast/growth.cpp` and compares them. At 20,000 walks the estimates are within 0.1% for 3, 4 and 6 tiles. For six 3-dot tiles the games estimate is 10^10.73, against an exact 10^10.726.
* The 20-tile run reports its own spread across ten batches (about +/-0.01 in the exponent at 20,000 walks), and a faster independent C++ sampler (not included) gave the same 10^37.94 at both 100,000 and 1,500,000 walks. The error from the extremely rare, extremely large branches of the tree that random walks can miss is harder to bound, so quote the answer as "around 10^56", not to three figures.
* The tile-order and orientation pieces are exact. The "divide by 4" ignores mirror-symmetric sequences. For six 3-dot tiles they change the per-order count from 73,921,776 x 4 / 4 to 73,922,288, about 7 parts per million, and the effect shrinks as tile counts grow.
* Everything is under the counting rules above. Slides and any other rule of the real game are not modelled, so this is the number of tile-laying games under these rules, not of real games of Shuffledot.

## Checks

* `python -m unittest discover -s tests -v` (about 15 seconds) compares the fast counter with brute force on the 2-dot set and on two sets of three 3-dot tiles, for both symmetry conventions, checks the six-tile headline numbers, and tests the estimator against exact values.
* `SLOW=1 python -m unittest discover -s tests -v` also cross-checks four 3-dot tiles against brute force (about seven minutes).
* The six-tile exact results are not brute-forced, since that is not feasible. They rely on the method above, validated on every smaller case. The 20-tile figure is an estimate.

## Limits

* The exact counters (`shuffledot.py`, `fast_count.py`) need every tile to be a different type. Duplicate tiles are only handled by the estimator.
* "Games" means sequences of tile placements. It says nothing about who is winning part-way through or which games a sensible player would reach.
* The number of final layouts for the real box has not been computed.

## Credits

The counting code and calculations were developed with help from Claude (Anthropic), then checked against brute-force enumeration as described above.

## Licence

MIT, see `LICENSE`.
