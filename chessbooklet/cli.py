"""Command-line entry point.

Usage:
    chessbooklet build INPUT [-o OUTPUT_DIR] [options]
    chessbooklet sample [--dir DIR]

``build`` accepts a .pgn file (games become diagram exercises) or a puzzle
set text file (``FEN | moves | difficulty | note`` lines).
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import List, Optional

from .chess import Position
from .exercises import DIFFICULTY_LEVELS, Exercise
from .booklet import (BookletOptions, answer_key_page, cover_page,
                      exercise_grid_page, howto_page, solution_text_for)
from .pgn import PgnError, exercises_from_pgn_text
from .puzzles import PuzzleError, parse_puzzle_text
from .svg import svg_document

SAMPLE_PGN = """[Event "Booklet Sample Club Night"]
[Site "Local chess club"]
[Date "2026.10.15"]
[White "Riley P."]
[Black "Sam K."]
[Result "0-1"]

1. e4 e5 2. Nf3 {A friendly Italian.} 2... Nc6 3. Bc4 Nf6 4. Ng5 Nxe4?!
5. Nxf7 Qe7 {Ponyfork: flashy, tricky.} 6. Nd5+ {Blink and it's gone.}
Qxe4+ 7. Qe2 {Forces the issue.} Bxf2+ 8. Kd1 Nxg5 0-1

[Event "Booklet Sample Club Night"]
[Site "Local chess club"]
[Date "2026.10.15"]
[White "Marisol T."]
[Black "Avery L."]
[Result "1-0"]

1. d4 d5 2. c4 e6 3. Nf3 Nf6 4. Nc3 Be7 5. Bg5 O-O 6. e3 h6 7. Bh4 c6
8. Qc2 g5 9. Bg3 Ne4 {Simple plan: knight lands in the middle.} 10. Bb5 cxd5
11. Nxd5 exd5 12. Bxd5 Nb8?? {Ouch.} 13. Qb3+ 1-0

[Event "Mate queue drill"]
[Site "Local club handout"]
[Date "2026.10.15"]
[White "Puzzle Board #1"]
[Black "Practice partner"]
[Result "*"]

[FEN "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"]
1. Ra8#{Simple back-rank finish.}
"""

SAMPLE_PUZZLES = """# Chessbooklet sample puzzle set.
# Format: FEN | moves (SAN or UCI, space/comma separated) | [difficulty] | [note]
# Difficulty is optional - leave it off and the tool tags it for you.
# Declared difficulties (easy / medium / hard) override the heuristic.

6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1 | Ra8# | easy | back-rank mate: the second row is all your own pawns
6k1/R7/1Q6/8/8/8/8/6K1 w - - 0 1 | Qb8# | easy | queen lands on the empty back rank; rook guards the 7th
8/3r4/8/8/4k3/3N4/6K1/8 w - - 0 1 | Nc5+ Kd4 Nxd7 | medium | fork the king, then scoop the rook
r1b2k1r/ppp1bppp/8/1B1Q4/5q2/2P5/PPP2PPP/R3R1K1 w - - 1 0 | Qd8+ Bxd8 Re8 | hard | classic queen sac, rook finishes
"""


def guess_input_kind(path: str, explicit: Optional[str]) -> str:
    if explicit:
        if explicit not in ("games", "puzzles"):
            raise SystemExit(f"error: --type must be 'games' or 'puzzles', got {explicit!r}")
        return explicit
    if path.lower().endswith(".pgn"):
        return "games"
    return "puzzles"


def load_exercises(path: str, kind: str, args) -> List[Exercise]:
    with open(path, "r", encoding="utf-8-sig") as fh:
        text = fh.read()
    if kind == "games":
        exercises = exercises_from_pgn_text(
            text, every=args.every, skip=args.skip,
            solution_plies=args.solution_moves, source_name=os.path.basename(path),
        )
    else:
        exercises = parse_puzzle_text(text, filename=os.path.basename(path))
    return exercises


def apply_filters(exercises: List[Exercise], args) -> List[Exercise]:
    out = []
    for ex in exercises:
        if args.difficulty in DIFFICULTY_LEVELS and ex.difficulty != args.difficulty:
            continue
        out.append(ex)
    for i, ex in enumerate(out, start=1):
        ex.id = f"P{i}"
    return out


def paginate(items: List[Exercise], per_page: int) -> List[List[Exercise]]:
    return [items[i:i + per_page] for i in range(0, len(items), per_page)]


def cmd_build(args) -> int:
    kind = guess_input_kind(args.input, args.type)
    if not os.path.isfile(args.input):
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2
    exercises = load_exercises(args.input, kind, args)
    exercises = apply_filters(exercises, args)
    if not exercises:
        print("error: no exercises survived the filters - nothing to paginate.",
              file=sys.stderr)
        return 1

    opts = BookletOptions(
        title=args.title, subtitle=args.subtitle, paper=args.paper,
        per_page=args.per_page, large_print=args.large_print,
        piece_style=args.piece_style, coords=not args.no_coords,
        flip=args.view, cover=not args.no_cover, howto=not args.no_howto,
        footer=args.footer,
    )

    os.makedirs(args.out, exist_ok=True)
    width, height = opts.page_size()  # page size for the print CSS

    pages: List[Tuple[str, str]] = []
    page_no = [0]

    def make(svg_text: str, doc_title: str) -> None:
        page_no[0] += 1
        fname = f"page-{page_no[0]:03d}.svg"
        with open(os.path.join(args.out, fname), "w", encoding="utf-8") as fh:
            fh.write(svg_text)
        pages.append((fname, doc_title))

    inputs_desc = (
        f"Built from: {os.path.basename(args.input)} ({'game annotations' if kind == 'games' else 'puzzle set'})"
    )

    # Plan the full booklet first so footers show correct page numbers.
    chunks = paginate(exercises, opts.per_page)
    key_items = [(ex, solution_text_for(ex)) for ex in exercises]
    key_chunks = [key_items[i:i + args.key_per_page]
                  for i in range(0, len(key_items), args.key_per_page)]
    total_pages = ((1 if opts.cover else 0) + len(chunks) + len(key_chunks)
                   + (1 if opts.howto else 0))
    cover_offset = 1 if opts.cover else 0
    section = "Exercises"

    if opts.cover:
        make(cover_page(exercises, opts), "Cover")
    for i, chunk in enumerate(chunks, start=1):
        first, last = chunk[0].id, chunk[-1].id
        make(exercise_grid_page(chunk, opts, i + cover_offset, total_pages,
                                section, (first, last)),
             f"{section} {first}-{last}")
    key_start = cover_offset + len(chunks)
    for i, chunk_k in enumerate(key_chunks, start=1):
        make(answer_key_page(chunk_k, opts, key_start + i, total_pages,
                             (chunk_k[0][0].id, chunk_k[-1][0].id)),
             f"Answer key {chunk_k[0][0].id}-{chunk_k[-1][0].id}")
    if opts.howto:
        make(howto_page(opts, inputs_desc), "How to use")

    # Plain-text answer key, handy for itinerant coaches.
    key_path = os.path.join(args.out, "answer-key.txt")
    with open(key_path, "w", encoding="utf-8") as fh:
        fh.write(f"{opts.title}\n")
        if opts.subtitle:
            fh.write(f"{opts.subtitle}\n")
        fh.write("=" * 40 + "\n\n")
        for ex, solution in key_items:
            fh.write(f"{ex.id}  [{ex.difficulty}]  {ex.prompt}\n")
            fh.write(f"    {solution}\n")
            if ex.note:
                fh.write(f"    note: {ex.note}\n")
            if ex.auto_difficulty and ex.auto_difficulty != ex.difficulty:
                fh.write(f"    heuristic tag: {ex.auto_difficulty}\n")
            fh.write("\n")

    # Browser-printable index (works offline with just this folder).
    imgs = "\n".join(
        f'<div class="sheet"><h2>{title}</h2><img src="{name}" alt="{title}"></div>'
        for name, title in pages
    )
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  body {{ font-family: Georgia, serif; margin: 0; background: #eee; }}
  .sheet {{ background: #fff; margin: 12px auto; padding: 8px; width: {w}px; }}
  .sheet img {{ width: 100%; height: auto; }}
  h2 {{ font-size: 14px; margin: 0 0 4px; font-weight: normal; color: #555; }}
  @media print {{
    body {{ background: none; }}
    h2 {{ display: none; }}
    .sheet {{ margin: 0; padding: 0; width: 100%; page-break-after: always; }}
  }}
</style>
</head>
<body>
{imgs}
</body>
</html>
""".format(title=opts.title, imgs=imgs, w=int(width))
    with open(os.path.join(args.out, "index.html"), "w", encoding="utf-8") as fh:
        fh.write(html)

    print(f"Wrote {len(pages)} SVG pages to {args.out}/")
    print(f"- open {os.path.join(args.out, 'index.html')} in a browser and print")
    print(f"- plain-text answers: {key_path}")
    return 0


def cmd_sample(args) -> int:
    os.makedirs(args.dir, exist_ok=True)
    pgn_path = os.path.join(args.dir, "sample_games.pgn")
    puzzle_path = os.path.join(args.dir, "sample_puzzles.txt")
    with open(pgn_path, "w", encoding="utf-8") as fh:
        fh.write(SAMPLE_PGN)
    with open(puzzle_path, "w", encoding="utf-8") as fh:
        fh.write(SAMPLE_PUZZLES)
    print(f"Wrote {pgn_path} and {puzzle_path}.")
    print("Try:  chessbooklet build " + pgn_path + " -o sample-game-booklet")
    print("  or: chessbooklet build " + puzzle_path + " -o sample-puzzle-booklet")
    return 0


def add_common_build_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("-o", "--out", default="booklet",
                        help="output directory (default: ./booklet)")
    parser.add_argument("--title", default="Chess Exercise Booklet")
    parser.add_argument("--subtitle", default="Solve, commit, and check.")
    parser.add_argument("--paper", choices=["letter", "a4", "Letter", "A4"],
                        default="letter")
    parser.add_argument("--per-page", type=int, default=4, choices=(1, 2, 3, 4),
                        help="exercise diagrams per page (default 4)")
    parser.add_argument("--key-per-page", type=int, default=16,
                        help="answer-key entries per page (default 16)")
    parser.add_argument("--large-print", action="store_true",
                        help="big fonts and one giant diagram per page")
    parser.add_argument("--piece-style", choices=["glyphs", "labels"],
                        default="glyphs",
                        help="glyph chess symbols or letter-token discs")
    parser.add_argument("--no-coords", action="store_true",
                        help="omit board file/rank letters")
    parser.add_argument("--view", default="auto",
                        choices=["auto", "white", "black"],
                        help="board orientation: auto=side to move, white, black")
    parser.add_argument("--no-cover", action="store_true")
    parser.add_argument("--no-howto", action="store_true")
    parser.add_argument("--footer", default="",
                        help="footer text (default credits this generator)")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="chessbooklet",
        description="Turn .pgn games or puzzle sets into printable chess "
                    "exercise booklets (SVG pages, offline, no dependencies).",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="build a booklet from an input file")
    build.add_argument("input", help="a .pgn file or a puzzle-set text file")
    build.add_argument("--type", choices=["games", "puzzles"], default=None,
                       help="force input type (default: .pgn=games else puzzles)")
    build.add_argument("--every", type=int, default=6,
                       help="games mode: take a position every N plies (default 6)")
    build.add_argument("--skip", type=int, default=4,
                       help="games mode: skip first N plies of each game (default 4)")
    build.add_argument("--solution-moves", type=int, default=1,
                       help="games mode: how many played moves form the answer (default 1)")
    build.add_argument("--difficulty", default="all",
                       choices=["all"] + sorted(DIFFICULTY_LEVELS),
                       help="keep only this difficulty (default: all)")
    add_common_build_args(build)
    build.set_defaults(func=cmd_build)

    sample = sub.add_parser("sample", help="write sample .pgn and puzzle files")
    sample.add_argument("--dir", default=".", help="directory for sample files")
    sample.set_defaults(func=cmd_sample)

    args = parser.parse_args(argv)
    args.large_print = bool(getattr(args, "large_print", False))
    try:
        return args.func(args)
    except (PgnError, PuzzleError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
