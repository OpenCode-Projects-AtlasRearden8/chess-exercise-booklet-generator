"""PGN parsing and exercise extraction from games."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple

from .chess import Position, START_FEN, Move
from .exercises import Exercise, auto_tag_difficulty, short_shift

RESULT_RE = re.compile(r"^(1-0|0-1|1/2-1/2|\*)$")
MOVE_NUMBER_RE = re.compile(r"^\d+\.*$")
NAG_RE = re.compile(r"^\$\d+$")


def _strip_comments(movetext: str) -> str:
    # Rest comments can contain braces, brace comments can nest nothing.
    movetext = re.sub(r"\{[^}]*\}", " ", movetext)
    movetext = re.sub(r";[^\n]*", " ", movetext)
    # Variations, innermost first.
    while "(" in movetext:
        new = re.sub(r"\([^()]*\)", " ", movetext)
        if new == movetext:
            break
        movetext = new
    return movetext


def _split_games(text: str) -> List[Tuple[Dict[str, str], str]]:
    """Split PGN text into (headers, movetext) pairs."""
    games: List[Tuple[Dict[str, str], str]] = []
    headers: List[str] = []
    moves: List[str] = []
    in_moves = False

    def flush() -> None:
        nonlocal headers, moves, in_moves
        if headers or moves:
            games.append((headers, moves))
        headers, moves, in_moves = [], [], False

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("[") and re.match(r"^\[\w+\s+\".*\"\]\s*$", stripped):
            if in_moves:
                flush()
            headers.append(stripped)
        else:
            in_moves = True
            moves.append(stripped)
    flush()
    return games


class PgnError(ValueError):
    pass


GamePlay = Tuple[List["Move"], List[str]]  # playable prefix (list of moves), all sans


def _play_movetext(movetext: str, start_fen: str) -> Tuple[List[Move], List[str]]:
    """Play mainline moves; returns (played_moves, sans).

    Tolerant of bad/extra tokens: tokens that fail to parse are skipped
    with a warning kept out of output (robustness over strictness).
    """
    clean = _strip_comments(movetext)
    played: List[Move] = []
    sans: List[str] = []
    pos = Position.from_fen(start_fen)
    tokens = clean.split()
    for tok in tokens:
        tok = re.sub(r"^\d+\.+", "", tok)
        if not tok or RESULT_RE.match(tok) or MOVE_NUMBER_RE.match(tok) or NAG_RE.match(tok):
            if RESULT_RE.match(tok):
                break
            continue
        try:
            move = pos.parse_san(tok)
        except (ValueError, IndexError):
            continue  # variation leftovers, garbage, or exotic annotations
        sans.append(pos.san(move))
        played.append(move)
        pos = pos.make(move)
    return played, sans


class PgnGame:
    def __init__(self, headers: Dict[str, str], moves: List[Move],
                 sans: List[str], headers_text: List[str]) -> None:
        self.headers = headers
        self.moves = moves
        self.sans = sans
        self.headers_text = headers_text

    @property
    def title(self) -> str:
        white = self.headers.get("White", "?")
        black = self.headers.get("Black", "?")
        if white == "?" and black == "?":
            return "Untitled game"
        return f"{white} vs {black}"

    def ply_count(self) -> int:
        return len(self.moves)


HEADER_RE = re.compile(r'^\[(\w+)\s+"(.*)"\]$')


def parse_pgn(text: str) -> List[PgnGame]:
    games = []
    for headers_lines, move_lines in _split_games(text):
        headers: Dict[str, str] = {}
        for line in headers_lines:
            m = HEADER_RE.match(line)
            if m:
                headers[m.group(1)] = m.group(2).strip()
        movetext = "\n".join(move_lines)
        start_fen = headers.get("FEN", START_FEN)
        try:
            moves, sans = _play_movetext(movetext, start_fen)
        except ValueError as exc:
            raise PgnError(f"bad FEN in game: {exc}") from exc
        games.append(PgnGame(headers, moves, sans, headers_lines))
    return games


def exercises_from_game(game: PgnGame, every: int = 6, skip: int = 0,
                        solution_plies: int = 1,
                        source_name: str = "") -> List[Exercise]:
    """Carve a played game into diagram exercises.

    Exercise at ply p = position before move ``p+1`` (0-indexed ply);
    the answer key shows the next ``solution_plies`` mainline moves.
    """
    out: List[Exercise] = []
    start_fen = game.headers.get("FEN", START_FEN)
    base = Position.from_fen(start_fen)
    positions: List[str] = [base.to_fen()]
    pos = base
    for move in game.moves:
        pos = pos.make(move)
        positions.append(pos.to_fen())

    last_move_sans = game.sans
    total_plies = len(game.moves)
    # Games that start from a custom FEN are deliberate setups: treat the
    # starting position itself as the first exercise regardless of `skip`.
    effective_skip = 0 if game.headers.get("FEN") else skip
    ply = effective_skip
    n = 0
    while ply < min(total_plies, 60):
        fen = positions[ply]
        cur = Position.from_fen(fen)
        if cur.is_checkmate() or cur.is_stalemate() or not cur.legal_moves():
            ply += every
            continue
        solution_end = min(ply + solution_plies, total_plies)
        solution_sans = last_move_sans[ply:solution_end]
        if not solution_sans:
            ply += every
            continue
        last_move_text = f"after {last_move_sans[ply - 1]}" if ply > 0 else "start of game"
        # Author-declared difficulty header wins over the heuristic.
        tag = (game.headers.get("Difficulty") or "").strip().lower()
        auto = auto_tag_difficulty(fen, solution_sans)
        if tag not in ("easy", "medium", "hard"):
            tag = auto
        note = ""
        event = game.headers.get("Event", "")
        who = game.title
        note = who + (f" ({event})" if event and event != "?" else "")
        out.append(Exercise(
            fen=fen,
            solution_sans=solution_sans,
            difficulty=tag,
            note=note,
            source=source_name or short_shift(game.title),
            last_move_text=last_move_text,
            auto_difficulty=auto,
        ))
        out[-1].id = f"P{n + 1}"
        n += 1
        ply += every
    return out


def exercises_from_pgn_text(text: str, every: int = 6, skip: int = 0,
                            solution_plies: int = 1,
                            source_name: str = "") -> List[Exercise]:
    out: List[Exercise] = []
    counter = [0]
    for game in parse_pgn(text):
        exs = exercises_from_game(
            game, every=every, skip=skip, solution_plies=solution_plies,
            source_name=source_name,
        )
        for ex in exs:
            counter[0] += 1
            ex.id = f"P{counter[0]}"
        out.extend(exs)
    # Renumber sequentially across games.
    for i, ex in enumerate(out, start=1):
        ex.id = f"P{i}"
    return out
