#!/usr/bin/env python3
"""
make_figures.py - redraws the numbered figures from the article (2:1 tile set, bb played first).

Writes SVG files to ./figures (and PNGs too if the optional `cairosvg` package is installed):
    1_bb_then_bw_9_layouts      the nine ways to play bw after bb
    2_bb_then_ww_5_layouts      the five ways to play ww after bb
    3_ww_added_to_layout_1      the 13 ways to add ww to bb + bw layout 1
    4_ww_added_to_layout_2      the 22 ways to add ww to bb + bw layout 2
It also prints the third-turn tables from the article.

Boards that differ only by rotation or mirroring are drawn once, using the version that sits
furthest up and left.  bb is kept in the same spot in every panel.
"""
from __future__ import annotations

from pathlib import Path

from shuffledot import canonical, placements

BB = (((0, 0), (0, 1)), ("b", "b"))            # player 1's bb tile, upright at the origin
OUT = Path(__file__).resolve().parent / "figures"


def rep_key(p):
    cells, dots = p
    return (min(c[1] for c in cells), min(c[0] for c in cells), cells[0][1] == cells[1][1], dots)


def distinct_placements(board, tile):
    """One representative per distinct result of adding `tile` to `board` (up to rotation/mirror)."""
    groups = {}
    for p in placements(board, tile):
        groups.setdefault(canonical(board + [p]), []).append(p)
    return sorted((min(g, key=rep_key) for g in groups.values()), key=rep_key)


def kind(cells):
    """Where a 2-dot tile sits against the upright bb:
    A end to end, B horizontal over/under an end, C upright and offset by one square,
    D upright and flush alongside, E horizontal beside."""
    horizontal = cells[0][1] == cells[1][1]
    xs = [c[0] for c in cells]
    if not horizontal:
        return "A" if xs[0] == 0 else ("D" if min(c[1] for c in cells) == 0 else "C")
    return "B" if 0 in xs else "E"


def article_order_bw(second):
    """bw layouts numbered as in the article: black dot first (A..E), then white dot first."""
    black_first = sorted((p for p in second if p[1] == ("b", "w")), key=lambda p: "ABCDE".index(kind(p[0])))
    white_first = sorted((p for p in second if p[1] == ("w", "b")), key=lambda p: "ABCDE".index(kind(p[0])))
    return black_first + white_first


# ------------------------------------------------------------------ drawing
U, R, GAP = 26, 26 * 0.34, 11
FILL = ["#eeeeee", "#d6e1f3", "#d8e7d6"]       # first, second and third tile played


def render(panels, name, per_row=None):
    per_row = per_row or len(panels)
    rows = [panels[i:i + per_row] for i in range(0, len(panels), per_row)]
    parts, y, width, number = [], 6, 0, 0
    for row in rows:
        top = min(c[1] for p in row for cells, _ in p for c in cells)
        bottom = max(c[1] for p in row for cells, _ in p for c in cells) + 1
        x = 6
        for p in row:
            left = min(c[0] for cells, _ in p for c in cells)
            right = max(c[0] for cells, _ in p for c in cells) + 1
            for i, (cells, dots) in enumerate(p):
                x0, y0 = min(c[0] for c in cells), min(c[1] for c in cells)
                x1, y1 = max(c[0] for c in cells) + 1, max(c[1] for c in cells) + 1
                parts.append(f'<rect x="{x + (x0 - left) * U:.1f}" y="{y + (y0 - top) * U:.1f}" '
                             f'width="{(x1 - x0) * U}" height="{(y1 - y0) * U}" fill="{FILL[i]}" stroke="#555555"/>')
                for (cx, cy), d in zip(cells, dots):
                    parts.append(f'<circle cx="{x + (cx - left) * U + U / 2:.1f}" cy="{y + (cy - top) * U + U / 2:.1f}" '
                                 f'r="{R:.1f}" fill="{"#000000" if d == "b" else "#ffffff"}" stroke="#555555"/>')
            number += 1
            low = max(c[1] for cells, _ in p for c in cells) + 1
            parts.append(f'<text x="{x + (right - left) * U / 2:.1f}" y="{y + (low - top) * U + 13}" font-size="11" '
                         f'fill="#777" text-anchor="middle" font-family="Helvetica, Arial, sans-serif">{number}</text>')
            x += (right - left) * U + GAP
        width = max(width, x - GAP + 6)
        y += (bottom - top) * U + 22
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:.0f} {y:.0f}" width="{width:.0f}" '
           f'height="{y:.0f}"><rect width="{width:.0f}" height="{y:.0f}" fill="#ffffff"/>' + "".join(parts) + "</svg>")
    OUT.mkdir(exist_ok=True)
    (OUT / f"{name}.svg").write_text(svg)
    try:
        import cairosvg
        cairosvg.svg2png(bytestring=svg.encode(), write_to=str(OUT / f"{name}.png"), scale=2)
    except ImportError:
        pass
    print(f"wrote figures/{name}.svg  ({len(panels)} panels)")


def main():
    nine = article_order_bw(distinct_placements([BB], "bw"))
    five = sorted(distinct_placements([BB], "ww"), key=lambda p: "ABCDE".index(kind(p[0])))
    third_after_bw = [distinct_placements([BB, p], "ww") for p in nine]
    third_after_ww = [distinct_placements([BB, p], "bw") for p in five]

    render([[BB, p] for p in nine], "1_bb_then_bw_9_layouts")
    render([[BB, p] for p in five], "2_bb_then_ww_5_layouts")
    render([[BB, nine[0], q] for q in third_after_bw[0]], "3_ww_added_to_layout_1")
    render([[BB, nine[1], q] for q in third_after_bw[1]], "4_ww_added_to_layout_2", per_row=11)

    counts = [len(t) for t in third_after_bw]
    print("\nbb -> bw -> ww : ww placements for second-turn layouts 1-9:", counts, "total", sum(counts))
    counts = [len(t) for t in third_after_ww]
    print("bb -> ww -> bw : bw placements for second-turn layouts 1-5:", counts, "total", sum(counts))


if __name__ == "__main__":
    main()
