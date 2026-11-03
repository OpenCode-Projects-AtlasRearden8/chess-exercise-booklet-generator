"""Puzzle-set parsing.

Supported line format (fields separated by ``|`` or ``;``)::

    # comment lines start with '#'
    <FEN> | <solution moves (SAN or UCI, space/comma separated)> | [difficulty] | [note]

Examples::

    4r3/8/8/8/8/8/4kK3/8 w - - 0 1 | Ra8# | easy | back-rank mate
    rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1 | e4 e5 Nf3

Difficulty is optional; when missing, a heuristic tags it automatically.
"""

from __future__ import annotations

from typing import List, Tuple

from .chess import Position
from .exercises import DIFFICULTY_LEVELS, Exercise, auto_tag_difficulty


class PuzzleError(ValueError):
    pass


def _split_fields(line: str) -> List[str]:
    return [f.strip() for f in line.replace("|", "\x00").replace(";", "\x00").split("\x00")]


def parse_puzzle_line(raw: str, lineno: int = 0, filename: str = ""
                      ) -> Tuple[str, List[str], str, str, str]:
    """Parses one puzzle line -> (fen, sans, difficulty, note, auto_difficulty)."""
    line = raw.strip()
    fields = _split_fields(line)
    if len(fields) < 2 or not fields[0]:
        raise PuzzleError(
            f"{filename}:{lineno}: expected '<FEN> | <moves>' line, got: {line!r}"
        )
    fen, moves_text = fields[:2]
    difficulty = ""
    note = ""
    if len(fields) >= 3 and fields[2]:
        word = fields[2].lower()
        if word in DIFFICULTY_LEVELS:
            difficulty = word
            if len(fields) >= 4:
                note = fields[3].strip()
        else:
            # Third field is a free-text note, not a difficulty.
            note = fields[2].strip()
            if len(fields) >= 4:
                note = (note + " " + fields[3].strip()).strip()

    pos = Position.from_fen(fen)
    sans: List[str] = []
    tokens = [t for t in moves_text.replace(",", " ").split() if t]
    if not tokens:
        raise PuzzleError(
            f"{filename}:{lineno}: puzzle has no solution moves: {line!r}"
        )
    for token in tokens:
        try:
            move = pos.parse_uci(token)
        except ValueError:
            try:
                move = pos.parse_san(token)
            except ValueError:
                raise PuzzleError(
                    f"{filename}:{lineno}: move {token!r} is illegal in position {fen!r}"
                ) from None
        sans.append(pos.san(move))
        pos = pos.make(move)

    auto = auto_tag_difficulty(fen, sans)
    if not difficulty:
        difficulty = auto
    return fen, sans, difficulty, note, auto


def parse_puzzle_text(text: str, filename: str = "") -> List[Exercise]:
    exercises: List[Exercise] = []
    n = 0
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fen, sans, difficulty, note, auto = parse_puzzle_line(line, lineno, filename)
        n += 1
        exercises.append(Exercise(
            fen=fen,
            solution_sans=sans,
            difficulty=difficulty,
            note=note,
            source=filename or "puzzle set",
            last_move_text="puzzle",
            auto_difficulty=auto,
        ))
        exercises[-1].id = f"P{n}"
    if not exercises:
        raise PuzzleError(
            f"{filename or 'puzzle set'}: no puzzle lines found "
            "(expected 'FEN | moves | difficulty | note' lines)"
        )
    return exercises
