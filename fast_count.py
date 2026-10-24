#!/usr/bin/env python3
"""
fast_count.py - exact game and layout counts for bigger tile sets (e.g. six 3-dot tiles).

It compiles and runs fast/growth.cpp (needs g++ or clang++), then combines the results with
the standard "count orbits of a symmetry group" argument (Burnside's lemma):

    labelled boards      = (connected bar sets) x k! x 2^(tiles that can be turned round)
    layouts, rotations   = labelled boards / 4
    layouts, + mirrors   = (labelled boards + 2 x mirror-symmetric boards) / 8

and likewise for games (ordered growth sequences, per play order).  It only handles sets in
which every tile is a different type (true of the 2:1 and 3:1 sets, not of the real 4:1 box,
which contains two of each tile).

    python fast_count.py                  # six 3-dot tiles
    python fast_count.py --dots 2         # the 2:1 set; instant, prints 1,044 games / 249 layouts
    python fast_count.py --tiles bbb,bbw,www
"""
from __future__ import annotations

import argparse
import itertools
import math
import shutil
import subprocess
import sys
from pathlib import Path

from shuffledot import canonical_tile, is_palindrome, tile_types

HERE = Path(__file__).resolve().parent
SRC, BIN = HERE / "fast" / "growth.cpp", HERE / "fast" / "growth"


def build() -> None:
    if BIN.exists() and BIN.stat().st_mtime >= SRC.stat().st_mtime:
        return
    cxx = shutil.which("g++") or shutil.which("clang++")
    if not cxx:
        sys.exit("fast_count.py needs a C++ compiler (g++ or clang++) to build fast/growth.cpp")
    subprocess.run([cxx, "-O2", "-o", str(BIN), str(SRC)], check=True)


def run_growth(length: int, k: int):
    out = subprocess.run([str(BIN), str(length), str(k)], capture_output=True, text=True, check=True).stdout
    G = F = 0
    S = {0: {}, 1: {}}
    for line in out.splitlines():
        p = line.split()
        if p[0] == "G":
            G = int(p[1])
        elif p[0] == "F":
            F = int(p[1])
        else:
            S[int(p[0][1])][int(p[1])] = int(p[2])
    return G, F, S


def mirror_symmetric_sets(length: int, k: int):
    """Connected sets of k bars unchanged by flipping left-right: vertical bars on the axis
    and (odd lengths only) horizontal bars centred on it.  Yields the number of horizontal bars of each."""
    half = (length - 1) // 2

    def cells_of(bar):
        kind, y = bar
        return frozenset((0, y + j) for j in range(length)) if kind == "V" else \
            frozenset((x, y) for x in range(-half, half + 1))

    kinds = ("V", "H") if length % 2 == 1 else ("V",)
    span = k * length + 2
    bars = [(kind, y) for kind in kinds for y in range(-span, span + 1)]
    cells = {b: cells_of(b) for b in bars}

    def touching(a, b):
        return any(abs(p[0] - q[0]) + abs(p[1] - q[1]) == 1 for p in a for q in b)

    def normalise(s):
        lo = min(y for _, y in s)
        return frozenset((kind, y - lo) for kind, y in s)

    current = {normalise([b]) for b in bars}
    for _ in range(k - 1):
        nxt = set()
        for s in current:
            occ = frozenset().union(*[cells_of(b) for b in s])
            for b in bars:
                if cells[b] & occ:
                    continue
                if any(touching(cells[b], cells_of(o)) for o in s):
                    nxt.add(normalise(list(s) + [b]))
        current = nxt
    for s in current:
        yield sum(1 for kind, _ in s if kind == "H")


def count(tiles: list[str]):
    k, length = len(tiles), len(tiles[0])
    assert k >= 2 and all(len(t) == length for t in tiles), "need >= 2 tiles of the same length"
    assert len(set(tiles)) == k, "every tile must be a different type"
    pal = [is_palindrome(t) for t in tiles]
    n_pal, n_non = sum(pal), k - sum(pal)
    m = 2 ** n_non                                   # ways to turn the reversible-looking tiles round
    G, F, S = run_growth(length, k)

    # ---- games: one count per play order
    def fixed_sequences(mode, order):
        return sum(c for mask, c in S[mode].items() if all(pal[order[i]] for i in range(k) if mask >> i & 1))
    mirrored_per_order, rotation_per_order = [], m * G // 2
    for order in itertools.permutations(range(k)):
        total = m * G + m * fixed_sequences(0, order) + m * fixed_sequences(1, order)
        assert total % 4 == 0
        mirrored_per_order.append(total // 4)
    # ---- layouts
    labelled = F * math.factorial(k) * m
    sym_labelled = sum(
        math.perm(n_pal, h) * math.factorial(k - h) * m for h in mirror_symmetric_sets(length, k))
    assert (labelled + 2 * sym_labelled) % 8 == 0
    return {
        "k": k, "length": length, "fixed_sets": F, "growth_sequences": G,
        "games_per_order_mirrors": sorted(set(mirrored_per_order)),
        "games_mirrors": sum(mirrored_per_order),
        "games_per_order_rotations": rotation_per_order,
        "games_rotations": rotation_per_order * math.factorial(k),
        "layouts_mirrors": (labelled + 2 * sym_labelled) // 8,
        "layouts_rotations": labelled // 4,
        "self_mirror_layouts": 2 * ((labelled + 2 * sym_labelled) // 8) - labelled // 4,
    }


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dots", type=int, default=3, help="use every distinct tile with this many dots")
    p.add_argument("--tiles", help="comma separated tile list instead, e.g. bbb,bbw,www")
    args = p.parse_args(argv)
    tiles = [canonical_tile(t) for t in args.tiles.split(",")] if args.tiles else tile_types(args.dots)
    build()
    r = count(tiles)
    print(f"{r['k']} tiles of {r['length']} dots: {', '.join(tiles)}")
    print(f"connected sets of bars (translation only):   {r['fixed_sets']:,}")
    print(f"ordered growth sequences (first bar upright): {r['growth_sequences']:,}")
    print()
    print("                               mirrors merged       rotations only")
    print(f"games per play order      {r['games_per_order_mirrors'][0]:>18,} {r['games_per_order_rotations']:>18,}"
          + ("" if len(r['games_per_order_mirrors']) == 1 else "   (orders differ slightly)"))
    print(f"games, all {math.factorial(r['k']):,} orders {r['games_mirrors']:>18,} {r['games_rotations']:>18,}")
    print(f"distinct final layouts    {r['layouts_mirrors']:>18,} {r['layouts_rotations']:>18,}")
    print(f"(layouts that are their own mirror image: {r['self_mirror_layouts']:,})")


if __name__ == "__main__":
    main()
