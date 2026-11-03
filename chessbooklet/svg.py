"""Offline SVG rendering: boards, diagrams, and printable booklet pages.

Pure-Python string building, no third-party libraries. Pages are sized for
US Letter (816x1056 at 96dpi) or A4 (794x1123).
"""

from __future__ import annotations

from typing import Iterable, List, Optional, Tuple
from xml.sax.saxutils import escape

from .chess import FILES, Position, sq_name

# Lichess-style palette.
LIGHT_SQ = "#f0d9b5"
DARK_SQ = "#b58863"
INK = "#222222"
SOFT_INK = "#666666"
ACCENT = "#1f6f43"

LETTER = (816, 1056)
A4 = (794, 1123)
PAPERS = {"letter": LETTER, "a4": A4}

GLYPHS = {
    "K": "\u2654", "Q": "\u2655", "R": "\u2656", "B": "\u2657",
    "N": "\u2658", "P": "\u2659", "k": "\u265A", "q": "\u265B",
    "r": "\u265C", "b": "\u265D", "n": "\u265E", "p": "\u265F",
}
LABELS = {" K": "K", " Q": "Q", " R": "R", " B": "B", " N": "N", " P": "P",
          "k": "K", "q": "Q", "r": "R", "b": "B", "n": "N", "p": "P"}


def esc(text: str) -> str:
    return escape(text)


class SvgBuilder:
    def __init__(self) -> None:
        self.parts: List[str] = []

    def add(self, chunk: str) -> None:
        self.parts.append(chunk)

    def rect(self, x, y, w, h, fill, rx=0, stroke="", stroke_width=0):
        attrs = (f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" '
                 f'fill="{fill}"')
        if rx:
            attrs += f' rx="{rx:g}"'
        if stroke:
            attrs += f' stroke="{stroke}" stroke-width="{stroke_width:g}"'
        self.parts.append(attrs + " />")

    def circle(self, cx, cy, r, fill, stroke="", stroke_width=0):
        attrs = f'<circle cx="{cx:g}" cy="{cy:g}" r="{r:g}" fill="{fill}"'
        if stroke:
            attrs += f' stroke="{stroke}" stroke-width="{stroke_width:g}"'
        self.parts.append(attrs + " />")

    def text(self, x, y, s, size, fill=INK, anchor="middle", weight="normal",
             style="normal"):
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" fill="{fill}" '
            f'text-anchor="{anchor}" font-weight="{weight}" '
            f'font-style="{style}" '
            f'font-family="Georgia, \'Times New Roman\', serif">{esc(s)}</text>'
        )

    def text_mono(self, x, y, s, size, fill=INK, anchor="middle"):
        self.parts.append(
            f'<text x="{x:g}" y="{y:g}" font-size="{size:g}" fill="{fill}" '
            f'text-anchor="{anchor}" font-family="\'DejaVu Sans Mono\', Consolas, monospace">'
            f'{esc(s)}</text>'
        )

    def piece(self, cx, cy, square: str, size: float, piece_style: str) -> None:
        """Draw one chess piece centred on (cx, cy); square = FEN char."""
        if square not in GLYPHS:
            return
        if piece_style == "glyphs":
            white = square.isupper()
            fill = "#ffffff" if white else "#1a1a1a"
            self.parts.append(
                f'<text x="{cx:g}" y="{cy:g}" text-anchor="middle" '
                f'font-size="{round(size * 0.92, 1):g}" '
                f'fill="{fill}" stroke="{INK}" stroke-width="{round(size * 0.055, 2):g}" '
                f'font-family="\'DejaVu Sans\', \'Arial Unicode MS\', \'Apple Symbols\', '
                f'\'Segoe UI Symbol\', sans-serif" dominant-baseline="central">'
                f'{GLYPHS[square]}</text>'
            )
        else:  # labels: colored disc with piece letter
            white = square.isupper()
            letter = square.upper()
            r = size * 0.42
            self.circle(cx, cy, r, "#ffffff" if white else "#1a1a1a",
                        stroke=INK, stroke_width=max(1.5, r * 0.12))
            self.parts.append(
                f'<text x="{cx:g}" y="{cy:g}" text-anchor="middle" '
                f'dominant-baseline="central" font-size="{round(size * 0.5, 1):g}" '
                f'fill="{SOFT_INK if white else "#ffffff"}" '
                f'font-family="Georgia, serif">{letter}</text>'
            )


def draw_board(svg: SvgBuilder, pos: Position, x: float, y: float, size: float,
               piece_style: str = "glyphs", flip: bool = False,
               coords: bool = True) -> None:
    """Draw a full chess board with pieces. `flip` shows black's view."""
    board = pos.board
    cell = size / 8.0
    svg.rect(x - 3, y - 3, size + 6, size + 6, "none", stroke=INK, stroke_width=2)
    for rank in range(8):
        for file in range(8):
            piece = board[rank * 8 + file]
            bx = x + file * cell
            by = y + (7 - rank) * cell if not flip else y + rank * cell
            dark = (rank + file) % 2 == 0
            svg.rect(bx, by, cell, cell, DARK_SQ if dark else LIGHT_SQ)
            if piece != ".":
                svg.piece(bx + cell / 2, by + cell / 2, piece, cell, piece_style)
    if coords:
        fudge = max(2.0, cell * 0.28)
        for i in range(8):
            svg.text(x + i * cell + cell / 2, y + size + fudge, FILES[i],
                     max(7, cell * 0.24), fill=SOFT_INK, anchor="middle")
            rank_lbl = str(8 - i) if not flip else str(i + 1)
            svg.text(x - fudge, y + i * cell + cell / 2 + cell * 0.09, rank_lbl,
                     max(7, cell * 0.24), fill=SOFT_INK, anchor="middle")


def svg_document(width: float, height: float, title: str, content: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{width:g}" height="{height:g}" viewBox="0 0 {width:g} {height:g}">\n'
        f'<title>{esc(title)}</title>\n{content}\n</svg>\n'
    )


def start_page(width: float, height: float) -> SvgBuilder:
    svg = SvgBuilder()
    svg.rect(0, 0, width, height, "#fdfcf9")
    return svg


def page_masthead(svg: SvgBuilder, width: float, y: float, title: str,
                  subtitle: str, rule_x0: float, rule_x1: float,
                  font_scale: float = 1.0) -> None:
    svg.text(width / 2, y + 26 * font_scale, title, 22 * font_scale,
             weight="bold")
    if subtitle:
        svg.text(width / 2, y + 46 * font_scale, subtitle, 12.5 * font_scale,
                 fill=SOFT_INK)
    rule_y = y + (58 if subtitle else 38) * font_scale
    svg.rect(rule_x0, rule_y, rule_x1 - rule_x0, 1.6, INK)
