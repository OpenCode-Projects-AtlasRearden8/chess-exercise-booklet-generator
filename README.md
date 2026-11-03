# Chess Exercise Booklet Generator

Turn your `.pgn` games or puzzle sets into printable chess exercise booklets —
offline, in plain Python, with zero dependencies.

Each booklet gives you **diagram positions to solve**, a **solutions section**
(the moves and how hard each puzzle is), and an **answer key** at the back, so
students can self-check without flipping back mid-tilt. Diagrams render as SVG
pages sized for standard paper, with large-print mode for club handouts and
per-puzzle difficulty tags (easy / medium / hard).

Great for chess club nights, chess-in-the-schools teachers, and anyone who
prints scoresheets for fun. Built by [Asdale Dynamics, LLC](https://dylanasdale.github.io)
as part of a set of beginner-friendly, local-first tools.

## Requirements

- Python 3.9+ (nothing else — no pip installs, no network, no engines)

## Getting started

```sh
# optional, but makes the CLI runnable as "chessbooklet"
pip install .

# write sample input files to try right now
chessbooklet sample

# build a booklet from real PGN games
chessbooklet build sample_games.pgn -o club-night

# or from a puzzle set
chessbooklet build sample_puzzles.txt -o puzzle-night --paper a4
```

Open `club-night/index.html` in any browser and hit print — the pages are
already laid out to print one SVG per sheet. A plain-text `answer-key.txt`
lands in the same folder for coaches on the go.

## Input formats

**Games (`.pgn`)** — standard PGN with comments and variations tolerated.
Carve a bunch of exercises straight out of played games: every `--every`
plies (default 6, skipping the first `--skip` plies, default 4) you get a
"what was played here?" exercise; the answer key shows the moves that actually
followed in the game. A game carrying an `[FEN "..."]` header (a set-up board)
treated its start position as a puzzle.

**Puzzle sets (any text file)** — one puzzle per line:

```
# FEN | moves (SAN or UCI, space or comma separated) | [difficulty] | [note]
6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1 | Ra8# | easy | back-rank mate
r1b2k1r/ppp1bppp/8/1B1Q4/5q2/2P5/PPP2PPP/R3R1K1 w - - 1 0 | Qd8+ Bxd8 Re8 | hard | queen sac, rook finishes
```

The tools are opinionated in your favor: every move is validated against the
actual rules, and any difficulty you declare wins over the automatic tag.

## Difficulty tags

Every exercise gets an `EASY` / `MEDIUM` / `HARD` badge:

- a line that **starts with check** and ends in mate is tagged **easy**
- **deeper lines** or **quiet queen moves** push the tag up
- a puzzle may **declare its own difficulty** in the puzzle file (or via a
  `[Difficulty "..."]` PGN header) and that declared value always wins

Filter the whole booklet to one level with `--difficulty hard`.

## Everything the CLI can do

```
chessbooklet build INPUT [-o OUT] [options]
```

| Option | Meaning | Default |
| --- | --- | --- |
| `-o, --out DIR` | output folder | `./booklet` |
| `--type games|puzzles` | force input type | auto from `.pgn` |
| `--every N` | games: position every N plies | 6 |
| `--skip N` | games: skip first N plies | 4 |
| `--solution-moves N` | games: answered moves | 1 |
| `--difficulty X` | filter `easy` / `medium` / `hard` / `all` | all |
| `--per-page N` | diagrams per page (1-4) | 4 |
| `--large-print` | huge fonts, one giant diagram per page | off |
| `--paper letter\|a4` | page size | letter |
| `--piece-style glyphs\|labels` | chess glyphs or letter-token discs | glyphs |
| `--view auto\|white\|black` | board orientation | auto = side to move |
| `--no-coords` | drop file/rank letters on boards | coords on |
| `--no-cover` / `--no-howto` | skip cover / how-to pages | both on |
| `--title`, `--subtitle`, `--footer` | booklet text | friendly defaults |

```
chessbooklet sample [--dir DIR]
```

Outputs `sample_games.pgn` and `sample_puzzles.txt`, both ready to build.

## A suggested flow for club nights

1. `chessbooklet sample`
2. Swap in your own games from the club archive — keep every meaningful move
   number as-is — then `chessbooklet build games.pgn -o club-handout --per-page 2`
3. For instruction sheets for the beginners' table, `--large-print` is the
   default-size option with the biggest boards and fonts.
4. File the extras: `--difficulty hard` builds a "graduation" booklet for
   strong members only.

## How it works

Everything is offline and pure Python:

- `chessbooklet/chess.py` — FEN parsing, full legal move generation under the
  classical rules (castling, en passant, promotion), SAN parsing and
  generation. Verified with perft counts against the standard test positions.
- `chessbooklet/pgn.py` — tolerant PGN reader: skips comments and variations,
  handles move numbers, NAGs, and results; extracts diagram exercises.
- `chessbooklet/puzzles.py` — the line format parser, with strict validation.
- `chessbooklet/exercises.py` — the difficulty heuristic.
- `chessbooklet/svg.py` + `chessbooklet/booklet.py` — SVG page rendering and
  pagination (cover, exercise grids, answer key, how-to page).

Piece glyphs use the DejaVu Sans family (present on most Linux systems; the
`labels` style is a fallback for systems that can't honor chess glyphs).

## Tests

```
python3 -m unittest discover tests -v
```

61 tests cover the engine (perft positions), the PGN and puzzle parsers, the
difficulty heuristic, SVG output validity, and the CLI end to end.

## License

MIT — see `LICENSE`. Copyright (c) 2026 Asdale Dynamics, LLC.
