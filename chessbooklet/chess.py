"""Pure-Python chess rules engine.

Positions, FEN parsing, legal move generation, SAN parsing and
generation. No third-party dependencies, fully offline.

Square indexing: 0..63 with a1 = 0, h1 = 7, a8 = 56, h8 = 63.
"""

from __future__ import annotations

import re
from typing import Iterable, List, Optional, Tuple

FILES = "abcdefgh"
WHITE = "w"
BLACK = "b"

PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 0}

KNIGHT_OFFSETS = (
    (1, 2), (2, 1), (2, -1), (1, -2),
    (-1, -2), (-2, -1), (-2, 1), (-1, 2),
)
KING_OFFSETS = ((1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1))
BISHOP_DIRS = ((1, 1), (1, -1), (-1, 1), (-1, -1))
ROOK_DIRS = ((1, 0), (0, 1), (-1, 0), (0, -1))


def sq_name(sq: int) -> str:
    """0-based square index -> algebraic name like ``e4``."""
    return FILES[sq % 8] + str(sq // 8 + 1)


def parse_sq(name: str) -> int:
    """Algebraic name like ``e4`` -> 0-based square index."""
    if len(name) != 2:
        raise ValueError(f"bad square: {name!r}")
    file_c, rank_c = name[0].lower(), name[1]
    if file_c not in FILES or not rank_c.isdigit() or not 1 <= int(rank_c) <= 8:
        raise ValueError(f"bad square: {name!r}")
    return (int(rank_c) - 1) * 8 + FILES.index(file_c)


class Move:
    """A chess move: from-square, to-square, optional promotion piece."""

    __slots__ = ("frm", "to", "promo")

    def __init__(self, frm: int, to: int, promo: str = "") -> None:
        self.frm = frm
        self.to = to
        self.promo = promo.upper()

    def uci(self) -> str:
        return sq_name(self.frm) + sq_name(self.to) + (self.promo.lower() if self.promo else "")

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, Move)
            and self.frm == other.frm
            and self.to == other.to
            and self.promo == other.promo
        )

    def __hash__(self) -> int:
        return hash((self.frm, self.to, self.promo))

    def __repr__(self) -> str:
        return f"Move({self.uci()})"


class Position:
    """An immutable-ish chess position; :meth:`make` returns a new one."""

    __slots__ = ("board", "turn", "castling", "ep", "halfmove", "fullmove")

    def __init__(self, board, turn, castling, ep, halfmove, fullmove) -> None:
        self.board = board          # list of 64 one-char strings, "." = empty
        self.turn = turn            # "w" or "b"
        self.castling = castling    # subset of "KQkq", in FEN order
        self.ep = ep                # square index or None
        self.halfmove = halfmove
        self.fullmove = fullmove

    # ------------------------------------------------------------------ FEN

    @classmethod
    def from_fen(cls, fen: str) -> "Position":
        """Parse a FEN string (fields 5 and 6 may be omitted)."""
        parts = fen.split()
        if len(parts) < 4:
            raise ValueError(f"bad FEN (need at least 4 fields): {fen!r}")
        placement, turn, castling, ep = parts[0], parts[1], parts[2], parts[3]
        halfmove = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 0
        fullmove = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 1

        rows = placement.split("/")
        if len(rows) != 8:
            raise ValueError(f"bad FEN placement: {placement!r}")
        board = ["."] * 64
        for r, row in enumerate(rows):
            file_idx = 0
            for ch in row:
                if ch.isdigit():
                    file_idx += int(ch)
                elif ch in "PNBRQKpnbrqk":
                    if file_idx > 7:
                        raise ValueError(f"bad FEN row: {row!r}")
                    board[(7 - r) * 8 + file_idx] = ch
                    file_idx += 1
                else:
                    raise ValueError(f"bad FEN character: {ch!r}")
            if file_idx != 8:
                raise ValueError(f"bad FEN row: {row!r}")

        if turn not in ("w", "b"):
            raise ValueError(f"bad FEN turn: {turn!r}")
        if castling == "-":
            castling = ""
        else:
            if not re.fullmatch(r"K?Q?k?q?", castling) or castling == "":
                raise ValueError(f"bad FEN castling: {castling!r}")
        ep_sq = None if ep == "-" else parse_sq(ep)
        return cls(board, turn, castling, ep_sq, halfmove, fullmove)

    def to_fen(self) -> str:
        row_strs = []
        for rank in range(7, -1, -1):
            row = ""
            empty = 0
            for f in range(8):
                piece = self.board[rank * 8 + f]
                if piece == ".":
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += piece
            if empty:
                row += str(empty)
            row_strs.append(row)
        castling = self.castling or "-"
        ep = sq_name(self.ep) if self.ep is not None else "-"
        return f"{'/'.join(row_strs)} {self.turn} {castling} {ep} {self.halfmove} {self.fullmove}"

    # ----------------------------------------------------------- basic info

    def copy(self) -> "Position":
        return Position(
            self.board[:], self.turn, self.castling, self.ep, self.halfmove, self.fullmove
        )

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Position) and self.to_fen() == other.to_fen()

    def key(self) -> tuple:
        return (tuple(self.board), self.turn, self.castling, self.ep)

    def piece_at(self, sq: int) -> str:
        return self.board[sq]

    def color_of(self, piece: str) -> str:
        """'w' for uppercase pieces, 'b' for lowercase."""
        return WHITE if piece.isupper() else BLACK

    def king_square(self, color: str) -> Optional[int]:
        target = "K" if color == WHITE else "k"
        try:
            return self.board.index(target)
        except ValueError:
            return None

    def material(self, color: str) -> int:
        """Total material value (excluding pawns is NOT applied; pawns count 1)."""
        total = 0
        for piece in self.board:
            if piece != "." and self.color_of(piece) == color:
                total += PIECE_VALUES[piece.upper()]
        return total

    def occupied(self, color: str) -> List[int]:
        return [i for i, p in enumerate(self.board) if p != "." and self.color_of(p) == color]

    # ------------------------------------------------------------ attacks

    def attacked(self, sq: int, by: str) -> bool:
        """Is ``sq`` attacked by any piece of color ``by``?"""
        file_c, rank = sq % 8, sq // 8

        # Pawns: a pawn of color `by` on (sq - pawn_dir) attacks sq.
        pawn = "P" if by == WHITE else "p"
        fwd = 1 if by == WHITE else -1
        for df in (-1, 1):
            f, r = file_c - df, rank - fwd
            if 0 <= f < 8 and 0 <= r < 8 and self.board[r * 8 + f] == pawn:
                return True

        knight = "N" if by == WHITE else "n"
        for df, dr in KNIGHT_OFFSETS:
            f, r = file_c + df, rank + dr
            if 0 <= f < 8 and 0 <= r < 8 and self.board[r * 8 + f] == knight:
                return True

        king = "K" if by == WHITE else "k"
        for df, dr in KING_OFFSETS:
            f, r = file_c + df, rank + dr
            if 0 <= f < 8 and 0 <= r < 8 and self.board[r * 8 + f] == king:
                return True

        for dirs, sliders in (
            (BISHOP_DIRS, "BQ" if by == WHITE else "bq"),
            (ROOK_DIRS, "RQ" if by == WHITE else "rq"),
        ):
            for df, dr in dirs:
                f, r = file_c + df, rank + dr
                while 0 <= f < 8 and 0 <= r < 8:
                    piece = self.board[r * 8 + f]
                    if piece != ".":
                        if piece in sliders:
                            return True
                        break
                    f += df
                    r += dr
        return False

    def in_check(self, color: Optional[str] = None) -> bool:
        color = color or self.turn
        ksq = self.king_square(color)
        if ksq is None:
            return False
        return self.attacked(ksq, BLACK if color == WHITE else WHITE)

    # -------------------------------------------------------- move making

    def _disambiguation_targets(self) -> None:  # pragma: no cover - helper placeholder
        pass

    def make(self, move: Move) -> "Position":
        """Apply a move and return the resulting position.

        Validation is lenient here (movegen callers construct legal moves);
        this assumes ``move`` came from :meth:`legal_moves` or is at least
        structurally sensible for this position.
        """
        board = self.board[:]
        frm, to, promo = move.frm, move.to, move.promo
        piece = board[frm]
        if piece == ".":
            raise ValueError(f"no piece on {sq_name(frm)} to move")
        mover = self.color_of(piece)
        captured = board[to]
        new_castling = self.castling

        board[frm] = "."
        board[to] = (
            (promo if mover == WHITE else promo.lower()) if promo else piece
        )

        # En passant capture: the captured pawn is not on `to`.
        if piece in ("P", "p") and to == self.ep and captured == ".":
            behind = to - 8 if piece == "P" else to + 8
            board[behind] = "."

        # Castling: move the rook as well.
        if piece in ("K", "k") and abs((to % 8) - (frm % 8)) == 2:
            rank = frm // 8
            if to % 8 == 6:  # king side
                board[rank * 8 + 5] = board[rank * 8 + 7]
                board[rank * 8 + 7] = "."
            else:            # queen side
                board[rank * 8 + 3] = board[rank * 8 + 0]
                board[rank * 8 + 0] = "."

        # Castling rights updates.
        rights = set(new_castling)
        drop = set()
        if piece in ("K", "k"):
            drop |= {"K", "Q"} if mover == WHITE else {"k", "q"}
        if piece in ("R", "r") or captured in ("R", "r"):
            for color_upper, pair in ((WHITE, ("K", "Q")), (BLACK, ("k", "q"))):
                home_rank = 0 if color_upper == WHITE else 7
                for i, sq in enumerate((home_rank * 8, home_rank * 8 + 7)):
                    if sq in (frm, to):
                        # i == 0 is the queenside rook square, i == 1 kingside.
                        drop.add(pair[1] if i == 0 else pair[0])
        if drop:
            rights -= drop
            new_castling = "".join(c for c in "KQkq" if c in rights)

        new_ep = None
        if piece in ("P", "p") and abs(to - frm) == 16:
            new_ep = (frm + to) // 2
        halfmove = 0 if (piece in ("P", "p") or captured != ".") else self.halfmove + 1
        fullmove = self.fullmove + (1 if self.turn == BLACK else 0)
        return Position(board, BLACK if self.turn == WHITE else WHITE,
                        new_castling, new_ep, halfmove, fullmove)

    # ------------------------------------------------------- move gen

    def _pawn_moves(self, sq: int, out: List[Move]) -> None:
        piece = self.board[sq]
        white = piece == "P"
        fwd = 1 if white else -1
        start_rank = 1 if white else 6
        promo_rank = 7 if white else 0
        file_c, rank = sq % 8, sq // 8
        promos = ("Q", "N", "R", "B")

        one = sq + fwd * 8
        if 0 <= one < 64 and self.board[one] == ".":
            if (one // 8) == promo_rank:
                for p in promos:
                    out.append(Move(sq, one, p))
            else:
                out.append(Move(sq, one))
                if rank == start_rank:
                    two = one + fwd * 8
                    if self.board[two] == ".":
                        out.append(Move(sq, two))
        for df in (-1, 1):
            f, r = file_c + df, rank + fwd
            if not (0 <= f < 8 and 0 <= r < 8):
                continue
            target = r * 8 + f
            tp = self.board[target]
            if (piece == "P" and tp.islower()) or (piece == "p" and tp.isupper()):
                    if r == promo_rank:
                        for p in promos:
                            out.append(Move(sq, target, p))
                    else:
                        out.append(Move(sq, target))
            elif tp == "." and self.ep is not None and target == self.ep:
                out.append(Move(sq, target))

    def _piece_moves(self, sq: int, out: List[Move]) -> None:
        piece = self.board[sq]
        pt = piece.upper()
        me = self.color_of(piece)
        file_c, rank = sq % 8, sq // 8

        def try_target(f: int, r: int) -> bool:
            """Returns True if the ray may continue."""
            if not (0 <= f < 8 and 0 <= r < 8):
                return False
            target = r * 8 + f
            tp = self.board[target]
            if tp == ".":
                out.append(Move(sq, target))
                return True
            if self.color_of(tp) != me:
                out.append(Move(sq, target))
            return False

        if pt == "N":
            for df, dr in KNIGHT_OFFSETS:
                try_target(file_c + df, rank + dr)
        elif pt in ("B", "R", "Q"):
            dirs = BISHOP_DIRS if pt == "B" else ROOK_DIRS if pt == "R" else BISHOP_DIRS + ROOK_DIRS
            for df, dr in dirs:
                f, r = file_c + df, rank + dr
                while try_target(f, r):
                    f += df
                    r += dr
        elif pt == "K":
            for df, dr in KING_OFFSETS:
                try_target(file_c + df, rank + dr)

        # Castling.
        home = 0 if me == WHITE else 7
        if sq == home * 8 + 4:
            rights = self.castling
            own_r = "R" if me == WHITE else "r"
            ks_right = "K" if me == WHITE else "k"
            qs_right = "Q" if me == WHITE else "q"
            enemy = BLACK if me == WHITE else WHITE
            if ks_right in rights:
                if (self.board[home * 8 + 5] == "." and self.board[home * 8 + 6] == "."
                        and self.board[home * 8 + 7] == own_r
                        and not self.attacked(home * 8 + 4, enemy)
                        and not self.attacked(home * 8 + 5, enemy)
                        and not self.attacked(home * 8 + 6, enemy)):
                    out.append(Move(sq, home * 8 + 6))
            if qs_right in rights:
                if (self.board[home * 8 + 3] == "." and self.board[home * 8 + 2] == "."
                        and self.board[home * 8 + 1] == "."
                        and self.board[home * 8 + 0] == own_r
                        and not self.attacked(home * 8 + 4, enemy)
                        and not self.attacked(home * 8 + 3, enemy)
                        and not self.attacked(home * 8 + 2, enemy)):
                    out.append(Move(sq, home * 8 + 2))

    def pseudo_moves(self) -> List[Move]:
        out: List[Move] = []
        for sq, piece in enumerate(self.board):
            if piece == "." or self.color_of(piece) != self.turn:
                continue
            if piece in ("P", "p"):
                self._pawn_moves(sq, out)
            else:
                self._piece_moves(sq, out)
        return out

    def legal_moves(self) -> List[Move]:
        legal = []
        for move in self.pseudo_moves():
            nxt = self.make(move)
            if not nxt.in_check(self.turn):
                legal.append(move)
        return legal

    # -------------------------------------------------------------- SAN

    def san(self, move: Move) -> str:
        """Standard Algebraic Notation, including +/# suffixes."""
        piece = self.board[move.frm]
        if piece == ".":
            raise ValueError(f"no piece on {sq_name(move.frm)}")
        pt = piece.upper()
        me = self.color_of(piece)
        is_capture = self.board[move.to] != "." or (
            piece in ("P", "p") and move.to == self.ep
        )

        if pt == "K" and abs((move.to % 8) - (move.frm % 8)) == 2:
            core = "O-O" if move.to % 8 == 6 else "O-O-O"
        elif pt == "P":
            if is_capture:
                core = FILES[move.frm % 8] + "x" + sq_name(move.to)
            else:
                core = sq_name(move.to)
            if move.promo:
                core += "=" + move.promo
        else:
            # Disambiguation: other legal moves by the same piece type to the
            # same target square from a different origin.
            rivals = [
                m for m in self.legal_moves()
                if m.to == move.to and m.frm != move.frm
                and self.board[m.frm].upper() == pt
            ]
            disamb = ""
            if rivals:
                same_file = any(m.frm % 8 == move.frm % 8 for m in rivals)
                same_rank = any(m.frm // 8 == move.frm // 8 for m in rivals)
                if not same_file:
                    disamb = FILES[move.frm % 8]
                elif not same_rank:
                    disamb = str(move.frm // 8 + 1)
                else:
                    disamb = sq_name(move.frm)
            core = pt.upper() + disamb + ("x" if is_capture else "") + sq_name(move.to)

        nxt = self.make(move)
        if nxt.in_check(nxt.turn):
            core += "#" if not nxt.legal_moves() else "+"
        return core

    def san_list(self, moves: Iterable[Move]) -> List[str]:
        pos = self
        sans = []
        for m in moves:
            sans.append(pos.san(m))
            pos = pos.make(m)
        return sans

    SAN_STRIP = re.compile(r"[+#!?]|e\.p\.")

    def parse_san(self, san: str) -> Move:
        """Parse a SAN move for *this* position (``+#!?!`` suffixes ignored)."""
        cleaned = self.SAN_STRIP.sub("", san.strip())
        cleaned = re.sub(r"^\d+\.+", "", cleaned)
        if not cleaned:
            raise ValueError(f"empty SAN: {san!r}")
        if cleaned.startswith("0"):
            cleaned = cleaned.replace("0", "O")
        elif cleaned[:1].lower() == "o" and cleaned[1:2] == "-":
            cleaned = "O" + cleaned[1:]

        candidates = {}
        for move in self.legal_moves():
            core = self.SAN_STRIP.sub("", self.san(move))
            candidates[core] = move

        if cleaned in candidates:
            return candidates[cleaned]

        # Tolerate leading lowercase piece letters ("nf3").
        if len(cleaned) > 1 and cleaned[0].isalpha() and cleaned[0].islower() and cleaned[0] in "pnbrqk":
            alt = cleaned[0].upper() + cleaned[1:]
            if alt in candidates:
                return candidates[alt]
        raise ValueError(f"illegal or unrecognized move {san!r}; legal: "
                         f"{', '.join(sorted(candidates)) or '(none)'}")

    def parse_uci(self, uci: str) -> Move:
        """Parse a UCI move like ``e2e4`` or ``g7g8q`` for this position."""
        return self.match_uci(uci)

    def match_uci(self, uci: str) -> Move:
        uci = uci.strip().lower()
        frm, rest = parse_sq(uci[0:2]), uci[2:]
        to = parse_sq(rest[:2])
        promo = rest[2:3].upper()
        for move in self.legal_moves():
            if move.frm == frm and move.to == to and move.promo == promo:
                return move
        raise ValueError(f"illegal UCI move {uci!r} in position {self.to_fen()!r}")

    # -------------------------------------------------------- game state

    def is_checkmate(self) -> bool:
        return self.in_check() and not self.legal_moves()

    def is_stalemate(self) -> bool:
        return not self.in_check() and not self.legal_moves()

    def has_material_related_to_mate(self, color: str) -> bool:
        """Rough check that `color` is not down to a bare king (at least one
        non-king piece remains)."""
        pieces = [p for p in self.occupied(color) if self.board[p].upper() != "K"]
        return bool(pieces)


START_FEN = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


def start_position() -> Position:
    return Position.from_fen(START_FEN)
