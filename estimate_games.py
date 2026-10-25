#!/usr/bin/env python3
"""
estimate_games.py - estimate the number of games for a full Shuffledot box (self-contained).

The exact counters in this repo need every tile to be a different type.  The real box has
two of each of ten 4-dot tiles (twenty tiles), far too many to count exactly.  This script
estimates that number.  It uses only the Python standard library and imports nothing else
from this repo, so it can be copied and run on its own.

How the estimate is built
-------------------------
For a set of K tiles of n dots, with `copies` of each distinct tile:

    games  ~  tile orders  x  placement sequences  x  dot orientations  /  4

  tile orders          K! / (copies!)^(distinct tiles).  Swapping two identical tiles changes
                       nothing you can see, so it is not a different order.
  placement sequences  G = the number of ways to put K bars down one at a time, each touching
                       the cluster along an edge without overlapping, with the first bar upright.
                       Every tile order has the same G, because the shapes do not depend on
                       which tile fills them.  G is far too big to count, so it is ESTIMATED
                       by Knuth's random-path method (below).
  dot orientations    2 for every tile that looks different turned round (bbw / wbb), so
                       2^(number of such tiles).  Each is independent.
  / 4                 Rotations and mirror images are the same game.  Fixing the first bar
                       upright leaves 4 symmetries (identity, two flips, half turn), and none
                       of them leaves a sequence of two or more different placements unchanged,
                       apart from a few mirror-symmetric sequences that are negligible at this
                       size (about 1 part in 10^5 even for six tiles; see the README).

Knuth's method: walk down the game tree choosing one legal placement uniformly at random each
turn, and multiply together the number of options you had at every turn.  Averaged over many
walks that product is an unbiased estimate of the number of leaves, i.e. of G.  The numbers
produced here come from walks, so they vary a little between runs; the script reports how much.

Examples
--------
    python estimate_games.py                       # the real box: ten 4-dot tiles x 2 (about 2 minutes)
    python estimate_games.py --workers 4           # use 4 processes
    python estimate_games.py --dots 3 --copies 1   # six 3-dot tiles (exact answer: 53,224,047,360)
    python estimate_games.py --selftest            # compare with exact counts, takes seconds
"""
from __future__ import annotations

import argparse
import itertools
import math
import random
import sys
from multiprocessing import Pool

# ---------------------------------------------------------------- tile bookkeeping


def tile_counts(dots: int):
    """(distinct tiles, tiles that read the same turned round)."""
    pal = 2 ** ((dots + 1) // 2)
    return (2 ** dots + pal) // 2, pal


# ---------------------------------------------------------------- Knuth random-path walk


def one_walk(length: int, k: int, rng: random.Random) -> float:
    """log10 of the product of option counts along one random game of k bars."""
    occupied = {(0, j) for j in range(length)}          # first bar: upright at the origin
    frontier = set()

    def add_to_frontier(cells):
        for x, y in cells:
            for q in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if q not in occupied:
                    frontier.add(q)

    add_to_frontier(occupied)
    total = 0.0
    for _ in range(k - 1):
        options = set()
        for fx, fy in frontier:
            for t in range(length):
                for horizontal in (True, False):
                    sx, sy = (fx - t, fy) if horizontal else (fx, fy - t)
                    key = (sx, sy, horizontal)
                    if key in options:
                        continue
                    if horizontal:
                        free = all((sx + j, sy) not in occupied for j in range(length))
                    else:
                        free = all((sx, sy + j) not in occupied for j in range(length))
                    if free:
                        options.add(key)
        total += math.log10(len(options))
        sx, sy, horizontal = rng.choice(sorted(options))
        cells = [(sx + j, sy) if horizontal else (sx, sy + j) for j in range(length)]
        occupied.update(cells)
        frontier.difference_update(cells)
        add_to_frontier(cells)
    return total


def _worker(args):
    length, k, samples, seed = args
    rng = random.Random(seed)
    return [one_walk(length, k, rng) for _ in range(samples)]


def sample_logs(length: int, k: int, samples: int, seed: int, workers: int):
    if workers <= 1:
        return _worker((length, k, samples, seed))
    per = [samples // workers + (1 if i < samples % workers else 0) for i in range(workers)]
    with Pool(workers) as pool:
        parts = pool.map(_worker, [(length, k, n, seed + 7919 * i) for i, n in enumerate(per)])
    return [x for part in parts for x in part]


def log10_mean(logs) -> float:
    """log10 of the mean of 10^x, computed without overflow."""
    top = max(logs)
    return top + math.log10(sum(10 ** (x - top) for x in logs) / len(logs))


def estimate_g(length: int, k: int, samples: int, seed: int = 1, workers: int = 1):
    """(log10 of the estimate of G, standard error in log10 units, per-batch estimates)."""
    logs = sample_logs(length, k, samples, seed, workers)
    batches = 10
    size = len(logs) // batches
    per_batch = [log10_mean(logs[i * size:(i + 1) * size]) for i in range(batches)]
    mean_b = sum(per_batch) / batches
    sd = math.sqrt(sum((b - mean_b) ** 2 for b in per_batch) / (batches - 1))
    return log10_mean(logs), sd / math.sqrt(batches), per_batch


# ---------------------------------------------------------------- the calculation


def games_estimate(dots: int, copies: int, samples: int, seed: int = 1, workers: int = 1,
                   rotations_only: bool = False):
    distinct, pal = tile_counts(dots)
    k = distinct * copies
    non_pal_tiles = (distinct - pal) * copies
    orders = math.factorial(k) // math.factorial(copies) ** distinct
    orientations = 2 ** non_pal_tiles
    log_g, err, _ = estimate_g(dots, k, samples, seed, workers)
    # Per play order, mirrors merged:  orientations x G / 4   (first bar upright, 4 symmetries fix it)
    # Per play order, rotations only:  orientations x 2G / 4  (the first bar may also lie flat)
    divisor = 2 if rotations_only else 4
    log_games = math.log10(orders) + math.log10(orientations) + log_g - math.log10(divisor)
    return {"tiles": k, "distinct": distinct, "copies": copies, "orders": orders,
            "orientations": orientations, "log10_g": log_g, "log10_err": err,
            "log10_games": log_games}


def selftest() -> bool:
    """Estimates of G for small cases whose exact values come from fast/growth.cpp."""
    exact = {(2, 3): 344, (3, 3): 768, (3, 4): 30_240, (3, 6): 73_921_776}
    ok = True
    for (length, k), value in exact.items():
        log_g, err, _ = estimate_g(length, k, 20_000, seed=3)
        off = 10 ** (log_g - math.log10(value)) - 1
        good = abs(off) < 0.03
        ok &= good
        print(f"  {length}-dot bars, {k} tiles: exact G = {value:>12,}   estimate = {10 ** log_g:>14,.0f}"
              f"   ({off:+.1%})  {'ok' if good else 'TOO FAR OFF'}")
    return ok


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dots", type=int, default=4, help="dots per tile (default 4)")
    p.add_argument("--copies", type=int, default=2, help="copies of each distinct tile (default 2)")
    p.add_argument("--samples", type=int, default=20_000, help="random walks (default 20000)")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--workers", type=int, default=1, help="processes to use")
    p.add_argument("--rotations-only", action="store_true", help="do not merge mirror images")
    p.add_argument("--selftest", action="store_true", help="check the method against exact counts and exit")
    args = p.parse_args(argv)
    if args.selftest:
        print("Self-test: random-walk estimate of G against exact counts")
        sys.exit(0 if selftest() else 1)

    r = games_estimate(args.dots, args.copies, args.samples, args.seed, args.workers, args.rotations_only)
    sym = "rotations only" if args.rotations_only else "rotations and mirror images merged"
    print(f"{r['tiles']} tiles: {r['distinct']} distinct {args.dots}-dot tiles x {r['copies']} copies   ({sym})")
    print(f"tile orders       {math.factorial(r['tiles']):,} / {r['copies']}!^{r['distinct']}"
          f" = {r['orders']:,}")
    print(f"dot orientations  {r['orientations']:,}")
    print(f"placement seqs G  ~ 10^{r['log10_g']:.2f}  (+/- {r['log10_err']:.2f} in the exponent, from {args.samples:,} walks)")
    print(f"games             ~ 10^{r['log10_games']:.2f}  =  {10 ** (r['log10_games'] % 1):.1f} x 10^{int(r['log10_games'])}")


if __name__ == "__main__":
    main()
