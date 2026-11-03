# STATUS

**Project:** Chess Exercise Booklet Generator
**Date:** 2026-11-03
**Author:** Asdale Dynamics, LLC

## What was built

A fully offline, dependency-free, pure-Python CLI (`chessbooklet`) that turns
`.pgn` games or plain-text puzzle sets into printable chess exercise
booklets:

- **Positions to solve**: batch-extracted diagram pages (1, 2, 3, or 4
  diagrams per page) with prompts ("White to move in 1"), difficulty badges,
  notes, and writing space under each diagram.
- **Solutions**: answer-key pages at the back plus a plain-text
  `answer-key.txt` for coaches.
- **Difficulty tagging**: an auto heuristic (solution length, checks,
  captures, quiet-queen moves) or an author-declared tag in the input file
  (puzzle field or `[Difficulty "..."]` PGN header, which always wins).
- **Large-print mode**: `--large-print` gives one giant diagram per page with
  1.5x-scaled fonts.
- **SVG rendering**: every page is a self-contained SVG sized for US Letter
  (816x1056) or A4 (794x1123), plus an `index.html` browser page that stacks
  the pages for quick printing.
- **Two input modes**:
  - games mode: exercises carved from played PGN games every `--every` plies
    (default 6, first `--skip` 4 plies skipped; FEN-set-up games start at ply 0);
  - puzzles mode: `FEN | moves | [difficulty] | [note]` lines, moves given in
    SAN or UCI, all validated against the real rules.
- **A real chess engine** (`chessbooklet/chess.py`): FEN, full legality
  (castling with through-check rules, en passant pins included,
  promotions), SAN generation with disambiguation and +/# suffixes, SAN and
  UCI parsing, checkmate/stalemate detection.
- **`chessbooklet sample`**: writes ready-to-build sample files.
- Installable as a console command via `pyproject.toml`
  (`pip install .` provides `chessbooklet` and `python -m chessbooklet`).

## Repository layout

```
chessbooklet/           package (chess, pgn, puzzles, exercises, svg, booklet, cli)
tests/                  61 unittest tests
examples/               sample_games.pgn, sample_puzzles.txt
README.md, LICENSE (MIT), pyproject.toml, STATUS.md
```

## How to run it

```sh
python3 -m chessbooklet sample --dir samples       # optional: get input files
python3 -m chessbooklet build samples/sample_games.pgn -o club-handout
python3 -m chessbooklet build samples/sample_puzzles.txt -o puzzle-night \
    --paper a4 --subtitle "Puzzle Night"
python3 -m chessbooklet build INPUT --large-print --difficulty easy
```

Then open `OUTPUT/index.html` in a browser and print, or hand out the
individual `page-NNN.svg` files. `OUTPUT/answer-key.txt` holds the plain-text
answer key.

## Verification performed

- `python3 -m unittest discover tests` -> **61 tests, all pass**.
- Engine verified against known **perft** counts: start position (20 / 400 /
  8,902 / 197,281), Talkchess "Kiwipete" (48 / 2,039 / 97,862), position 3
  with the en-passant edge case (14 / 191 / 2,812 / 43,238), the promotion
  maze (6 / 264 / 9,467), plus castling rights probes (26 / 568).
- Engine + SAN round-trips **cross-checked against python-chess on 1,800
  randomized game positions** (dev-time check only; the released package has
  zero dependencies).
- End-to-end CLI runs verified against both example inputs and sample output;
  every produced SVG parses as well-formed XML; `index.html` links every page;
  footers show correct "page N of M" numbering (fixed during verification).
- The wheel builds (`pip wheel .`) and the installed `chessbooklet` command
  runs a real build (verified, then uninstalled).
- Rendered pages were visually inspected as PNGs (cover, exercise grid,
  large-print) - diagrams, badges, notes, and glyphs all draw correctly.

## Known gaps / notes

- The difficulty tag is a heuristic page-layout aid, not a rating: trust
  declared tags over the auto tag for anything subtle.
- The PGN reader plays the **main line** of each game and ignores embedded
  variations (standard booklet behavior, but no per-variation drills).
- Piece rendering uses DejaVu-family chess glyphs; on systems without them,
  use `--piece-style labels` (letter-token discs) which needs no special fonts.
- No PDF writer of its own (browser "print to PDF" from `index.html` is the
  intended path); pages-per-sheet imposition is left to the print dialog.
- Dark-board contrast for the glyph style is tuned for print margins rather
  than projector use; labels style reads better if a projector is involved.
- The auto difficulty has no notion of "position asymmetry"; everything is
  derived from the solution line only.
