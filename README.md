# Shuffledot combinatorics

Code behind the "Shuffledot geekery" article: how many layouts, and how many different games, can you make from a Shuffledot-style tile set as the tiles get longer?

[Shuffledot](https://shuffledot.com) is a physical tile game. Each tile is a row of black and white dots. This repo counts what happens with 1-dot, 2-dot and 3-dot tiles, where one of every distinct tile is played once.

## Headline numbers

Rotations and mirror images are treated as the same board.

| Dots per tile | Distinct tiles | Final layouts | Games (all play orders) |
| --- | --- | --- | --- |
| 1 | 2 | 1 | 2 |
| 2 | 3 | 249 | 1,044 |
| 3 | 6 | 781,937,280 | 53,224,047,360 |

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

## Quick start

You need Python 3 (developed on 3.13; it uses only the standard library). The fast counter also needs `g++` or `clang++`.

```bash
python shuffledot.py tiles 3          # the six distinct 3-dot tiles
python shuffledot.py report 2         # games, layouts, turn-by-turn counts for the 2:1 set
python shuffledot.py outcomes 2       # win/draw table for the 2:1 set
python fast_count.py --dots 2         # same 2:1 numbers via the fast counter (instant)
python fast_count.py                  # six 3-dot tiles: the billions (about 2 seconds)
python make_figures.py                # redraws the numbered figures into ./figures
python -m unittest discover -s tests -v
```

Useful options: `--rotations-only` (do not merge mirror images), `--tiles bb,ww,bw` (choose your own tiles), `outcomes --straight` (only straight lines of dots count: 30 / 30 / 5 / 184 layouts).

## Files

| File | What it is |
| --- | --- |
| `shuffledot.py` | Readable brute-force reference. Plays every game turn by turn and merges symmetric boards. Fine for small sets, far too slow for six 3-dot tiles. |
| `fast_count.py`, `fast/growth.cpp` | Exact fast counter for sets where every tile is different. Reproduces the brute-force numbers on every small set tried, then scales to six tiles. |
| `make_figures.py` | Draws the numbered layout figures as SVG (PNG too if `cairosvg` is installed). |
| `tests/test_known_values.py` | Checks every number quoted in the article, and cross-checks the fast counter against brute force. |

## How the fast counter works

Brute force cannot visit billions of games, so `fast_count.py` counts instead of listing.

1. `growth.cpp` counts **ordered growth sequences**: every way to place k bars one at a time so each touches the ones already down. It also counts connected sets of k bars (Redelmeier's algorithm), and the sequences that survive a mirror flip.
2. Every tile order uses the same shapes, only with different tiles dropped in, so the geometric count is shared by all `k!` orders. Multiply in the ways to assign tiles and turn the lopsided ones (`bbw`, `bww`) round.
3. Divide out the symmetries with Burnside's lemma: with all tiles different, rotations never leave a board unchanged, so rotation-only counts divide by 4, and the mirror-merged counts divide by 8 after adding back the small number of boards that are their own mirror image (23,040 layouts for six 3-dot tiles).

## Checks

* `python -m unittest discover -s tests -v` (a few seconds) compares the fast counter with brute force on the 2-dot set and on two sets of three 3-dot tiles, for both symmetry conventions, and checks the six-tile headline numbers.
* `SLOW=1 python -m unittest discover -s tests -v` also cross-checks four 3-dot tiles against brute force (about seven minutes).
* The six-tile results themselves are not brute-forced, since that is not feasible. They rely on the method above, validated on every smaller case.

## Limits

* Every tile must be a different type. The real box has two of each of ten 4-dot tiles, and real games add slides, so those numbers are not covered here.
* "Games" means sequences of tile placements. It says nothing about who is winning part-way through or which games a sensible player would reach.

## Credits

The counting code and calculations were developed with help from Claude (Anthropic), then checked against brute-force enumeration as described above.

## Licence

MIT, see `LICENSE`.
