"""Exercise model and difficulty tagging."""

from __future__ import annotations

import re
from typing import List, Optional

DIFFICULTY_LEVELS = {"easy": 0, "medium": 1, "hard": 2}
DIFFICULTY_ORDER = ["easy", "medium", "hard"]


class Exercise:
    """A single exercise: a diagram position plus its answer-key solution."""

    __slots__ = (
        "id", "fen", "solution_sans", "difficulty", "note", "source",
        "last_move_text", "auto_difficulty",
    )

    def __init__(self, fen: str, solution_sans: List[str], difficulty: str,
                 note: str = "", source: str = "", last_move_text: str = "",
                 auto_difficulty: Optional[str] = None) -> None:
        self.id = ""
        self.fen = fen
        self.solution_sans = solution_sans
        self.difficulty = difficulty or "medium"
        self.note = note
        self.source = source
        self.last_move_text = last_move_text
        self.auto_difficulty = auto_difficulty

    @property
    def side_to_move(self) -> str:
        from .chess import Position
        return Position.from_fen(self.fen).turn

    @property
    def prompt(self) -> str:
        side = "White" if self.side_to_move == "w" else "Black"
        if not self.solution_sans:
            return f"{side} to move"
        half = len(self.solution_sans)
        if half == 1:
            return f"{side} to move in 1"
        return f"{side} to move in {half}"

    @property
    def show_difficulty(self) -> str:
        return self.difficulty


def _move_style_points(san: str) -> int:
    """Rough 'how hard is it to notice this move' score from one SAN."""
    pts = 0
    if "#" in san:
        pts -= 20            # mating move: usually the most forcing option
    if "+" in san:
        pts -= 8             # checks narrow the search
    if "x" in san:
        pts -= 4             # material grabs are inviting
    m = re.match(r"^([QK])", san)
    if m:
        pts += 14            # quiet king/queen maneuvers take a harder look
    m = re.match(r"^([NBR])", san)
    if m:
        pts += 4
    return pts


def auto_tag_difficulty(fen: str, sans: List[str]) -> str:
    """Heuristic difficulty: easy / medium / hard.

    Longer solutions and quiet queen maneuvering push up; checks, captures,
    and mate push down. Good enough for club booklets, easily overridden in
    inputs.
    """
    if not sans:
        return "easy"
    score = 10 * (len(sans) - 1)
    for san in sans:
        score += _move_style_points(san)
    if score <= 2:
        return "easy"
    if score <= 22:
        return "medium"
    return "hard"


def short_shift(name: str) -> str:
    """Trim long game/source names for booklet captions."""
    name = re.sub(r"\s+", " ", name).strip()
    if len(name) > 28:
        name = name[:25] + "..."
    return name
