#!/usr/bin/env python3
"""
shuffledot.py - brute-force combinatorics for Shuffledot-style tile sets.

A tile is a straight 1 x n bar of n dots, each black ('b') or white ('w').  Tiles are
laid on a square grid (one dot per grid square) so tile edges always line up.  Every new
tile must touch the tiles already played along at least part of an edge (corner contact
does not count) and may not overlap.

This file is the slow, simple, readable reference implementation.  It is exact, and is
fine for small sets (the 2:1 set takes a second; four 3-dot tiles takes minutes).  For six 3-dot tiles use fast_count.py.

Symmetry
--------
Two boards count as the same if one can be turned into the other by rotating and/or
flipping it over ("mirrors=True", the default - this is what the article uses), or by
rotating only ("mirrors=False").

Vocabulary used throughout
--------------------------
layout  - a finished arrangement of all the tiles, ignoring rotations/mirrors.
order   - the order in which the tile types are played (k! of them for k tiles).
game    - an order plus where each tile went; two games are the same only if every
          step is the same up to one overall rotation/mirror.  The same layout reached
          by a different order of play is a different game.

Usage
-----
    python shuffledot.py tiles 3              # the six distinct 3-dot tiles
    python shuffledot.py report 2             # all headline numbers for the 2:1 tile set
    python shuffledot.py report --tiles bb,ww,bw --rotations-only
    python shuffledot.py outcomes 2           # win/draw table for the 2:1 tile set
"""
from __future__ import annotations

import argparse
import itertools
import math
from collections import Counter

# --------------------------------------------------------------------------- tile types


def canonical_tile(s: str) -> str:
    """A tile can be turned round, so 'bbw' and 'wbb' are the same tile."""
    return min(s, s[::-1])


def tile_types(n: int) -> list[str]:
    """All distinct n-dot tiles."""
    return sorted({canonical_tile("".join(p)) for p in itertools.product("bw", repeat=n)})


def count_tile_types(n: int) -> int:
    """(2^n + 2^ceil(n/2)) / 2 : all patterns plus palindromes, halved."""
    return (2 ** n + 2 ** ((n + 1) // 2)) // 2


def is_palindrome(tile: str) -> bool:
    return tile == tile[::-1]


def orientations(tile: str) -> list[str]:
    """The distinct ways round the tile can be read along a fixed direction."""
    return [tile] if is_palindrome(tile) else [tile, tile[::-1]]


# --------------------------------------------------------------------------- geometry
# A tile on the board is (cells, dots): cells = ((x, y), ...) and dots = ('b', 'w', ...)
# both listed in reading order (top to bottom, then left to right).  x grows right, y down.

ROTATIONS = [lambda x, y: (x, y), lambda x, y: (-y, x), lambda x, y: (-x, -y), lambda x, y: (y, -x)]
ALL_SYMMETRIES = ROTATIONS + [
    lambda x, y: (-x, y), lambda x, y: (x, -y), lambda x, y: (y, x), lambda x, y: (-y, -x)]


def _reading(cells, dots):
    pairs = sorted(zip(cells, dots), key=lambda p: (p[0][1], p[0][0]))
    return tuple(p[0] for p in pairs), tuple(p[1] for p in pairs)


def canonical(board, mirrors: bool = True):
    """Canonical form of a board: identical for boards that differ by a symmetry/translation."""
    best = None
    for f in (ALL_SYMMETRIES if mirrors else ROTATIONS):
        tiles = [_reading([f(*c) for c in cells], dots) for cells, dots in board]
        mx = min(c[0] for cells, _ in tiles for c in cells)
        my = min(c[1] for cells, _ in tiles for c in cells)
        key = tuple(sorted((tuple((x - mx, y - my) for x, y in cells), dots) for cells, dots in tiles))
        if best is None or key < best:
            best = key
    return best


def first_board(tile: str):
    """Player 1's tile, placed vertically at the origin (any other placement is a rotation of it)."""
    n = len(tile)
    return [(tuple((0, j) for j in range(n)), tuple(orientations(tile)[0]))]


def placements(board, tile: str):
    """Every legal way to add `tile` to `board`: (cells, dots) pairs, no overlap, edge contact."""
    n = len(tile)
    occupied = {c for cells, _ in board for c in cells}
    frontier = set()
    for x, y in occupied:
        for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if q not in occupied:
                frontier.add(q)
    seen = set()
    for fx, fy in sorted(frontier):
        for horizontal in (True, False):
            for offset in range(n):
                sx, sy = (fx - offset, fy) if horizontal else (fx, fy - offset)
                if (sx, sy, horizontal) in seen:
                    continue
                seen.add((sx, sy, horizontal))
                cells = tuple((sx + j, sy) if horizontal else (sx, sy + j) for j in range(n))
                if any(c in occupied for c in cells):
                    continue
                for dots in orientations(tile):
                    yield cells, tuple(dots)


# --------------------------------------------------------------------------- growing games


def grow(order, mirrors: bool = True):
    """Play the tiles in `order`; return the list of {canonical board: board} after each turn."""
    start = first_board(order[0])
    levels = [{canonical(start, mirrors): start}]
    for tile in order[1:]:
        nxt = {}
        for board in levels[-1].values():
            for cells, dots in placements(board, tile):
                new = board + [(cells, dots)]
                nxt.setdefault(canonical(new, mirrors), new)
        levels.append(nxt)
    return levels


def games_by_order(tiles, mirrors: bool = True):
    """{order: number of distinct games}.  With one tile of each type, fixing the order makes
    the final board determine the whole game, so this is the number of distinct final boards."""
    return {order: len(grow(order, mirrors)[-1]) for order in itertools.permutations(tiles)}


def layouts(tiles, mirrors: bool = True):
    """{canonical final board: number of play orders that can build it}."""
    reach = Counter()
    for order in itertools.permutations(tiles):
        for key in grow(order, mirrors)[-1]:
            reach[key] += 1
    return reach


# --------------------------------------------------------------------------- scoring


def _dot_map(board):
    return {c: d for cells, dots in board for c, d in zip(cells, dots)}


def largest_group(board, colour: str, straight_only: bool = False) -> int:
    """Largest set of `colour` dots joined sideways/up-down (or longest straight run if asked)."""
    dots = _dot_map(board)
    cells = {c for c, d in dots.items() if d == colour}
    if straight_only:
        best = 0
        for (x, y) in cells:
            for dx, dy in ((1, 0), (0, 1)):
                if (x - dx, y - dy) in cells:
                    continue
                run, cx, cy = 0, x, y
                while (cx, cy) in cells:
                    run += 1
                    cx, cy = cx + dx, cy + dy
                best = max(best, run)
        return best
    seen, best = set(), 0
    for start in cells:
        if start in seen:
            continue
        stack, size = [start], 0
        seen.add(start)
        while stack:
            x, y = stack.pop()
            size += 1
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q in cells and q not in seen:
                    seen.add(q)
                    stack.append(q)
        best = max(best, size)
    return best


def outcome(board, straight_only: bool = False) -> str:
    """'B wins' / 'W wins' / 'draw b:w' - the bigger group wins, equal groups draw."""
    b, w = largest_group(board, "b", straight_only), largest_group(board, "w", straight_only)
    if b > w:
        return "B wins"
    if w > b:
        return "W wins"
    return f"draw {b}:{w}"


# --------------------------------------------------------------------------- command line


def _tiles_from_args(args) -> list[str]:
    if args.tiles:
        return [canonical_tile(t) for t in args.tiles.split(",")]
    return tile_types(args.dots)


def cmd_tiles(args):
    print(f"{count_tile_types(args.dots)} distinct {args.dots}-dot tiles (formula: "
          f"(2^{args.dots} + 2^ceil({args.dots}/2)) / 2):")
    print("  " + ", ".join(tile_types(args.dots)))


def cmd_report(args):
    tiles = _tiles_from_args(args)
    mirrors = not args.rotations_only
    sym = "rotations and mirror images merged" if mirrors else "rotations only"
    print(f"Tiles: {', '.join(tiles)}   ({sym})")
    per_order = games_by_order(tiles, mirrors)
    lay = layouts(tiles, mirrors)
    print(f"Orders of play:                {len(per_order)}")
    for order, n in list(per_order.items())[: (len(per_order) if len(per_order) <= 6 else 3)]:
        print(f"  {'-'.join(order):<24}{n} games")
    print(f"Total games (sum over orders): {sum(per_order.values()):,}")
    print(f"Distinct final layouts:        {len(lay):,}")
    spread = Counter(lay.values())
    print("Layouts by number of orders that can build them:",
          ", ".join(f"{n} layouts in {k} orders" for k, n in sorted(spread.items())))
    print("Distinct boards after each turn, first order:")
    for turn, level in enumerate(grow(tuple(tiles), mirrors), 1):
        print(f"  after turn {turn}: {len(level)}")


def cmd_outcomes(args):
    tiles = _tiles_from_args(args)
    lay = layouts(tiles, not args.rotations_only)
    layout_counts, game_counts = Counter(), Counter()
    for key, n_orders in lay.items():
        o = outcome(key, args.straight)
        layout_counts[o] += 1
        game_counts[o] += n_orders
    print(f"{'outcome':<12}{'layouts':>10}{'games':>10}")
    for o in sorted(layout_counts):
        print(f"{o:<12}{layout_counts[o]:>10}{game_counts[o]:>10}")
    print(f"{'total':<12}{sum(layout_counts.values()):>10}{sum(game_counts.values()):>10}")


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("tiles", help="list the distinct n-dot tiles"); s.add_argument("dots", type=int); s.set_defaults(fn=cmd_tiles)
    for name, fn in (("report", cmd_report), ("outcomes", cmd_outcomes)):
        s = sub.add_parser(name)
        s.add_argument("dots", type=int, nargs="?", default=2, help="use all distinct tiles with this many dots")
        s.add_argument("--tiles", help="comma separated tile list instead, e.g. bb,ww,bw")
        s.add_argument("--rotations-only", action="store_true", help="do not merge mirror images")
        if name == "outcomes":
            s.add_argument("--straight", action="store_true", help="only straight lines of dots count")
        s.set_defaults(fn=fn)
    args = p.parse_args(argv)
    args.fn(args)


if __name__ == "__main__":
    main()
