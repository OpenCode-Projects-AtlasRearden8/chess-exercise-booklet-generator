"""Booklet assembly: paginate exercises into printable SVG pages.

Page plan (when enabled):
  1. Cover page: title, subtitle, contents summary, one hero diagram.
  2..N. Exercise pages: grids of diagrams with prompts and writing space.
  Then. Answer-key pages: exercise id, prompt, and the solution moves.
  Optional last page: "How to use this booklet" tips.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from .chess import Position
from .exercises import DIFFICULTY_ORDER, Exercise
from .svg import (ACCENT, INK, PAPERS, SOFT_INK, draw_board, page_masthead,
                  start_page, svg_document)

DIFF_LABEL = {"easy": "EASY", "medium": "MEDIUM", "hard": "HARD"}
DIFF_COLOR = {"easy": "#2e7d32", "medium": "#c07f00", "hard": "#b23a48"}


class BookletOptions:
    def __init__(self, title: str = "Chess Exercise Booklet",
                 subtitle: str = "", paper: str = "letter",
                 per_page: int = 4, large_print: bool = False,
                 piece_style: str = "glyphs", coords: bool = True,
                 flip: str = "auto", cover: bool = True,
                 howto: bool = True, footer: str = "") -> None:
        self.title = title
        self.subtitle = subtitle
        self.paper = paper.lower() if paper.lower() in PAPERS else "letter"
        self.large_print = large_print
        self.piece_style = piece_style if piece_style in ("glyphs", "labels") else "glyphs"
        self.coords = coords
        self.flip = flip.strip().lower()
        self.cover = cover
        self.howto = howto
        self.footer = footer or "Made with Chess Exercise Booklet Generator"
        self.font_scale = 1.5 if large_print else 1.0
        if large_print:
            per_page = 1
        self.per_page = max(1, per_page)

    def page_size(self) -> Tuple[float, float]:
        return PAPERS[self.paper]


def _resolve_flip(opts: BookletOptions, exercise: Exercise) -> bool:
    mode = opts.flip
    if mode in ("w", "white"):
        return False
    if mode in ("b", "black"):
        return True
    return exercise.side_to_move == "b"


def _difficulty_badge(svg, x, y, difficulty: str, scale: float = 1.0) -> None:
    w, h = 64 * scale, 17 * scale
    svg.rect(x, y - h, w, h, DIFF_COLOR[difficulty], rx=h / 2)
    svg.text(x + w / 2, y - h / 2 + 3.5 * scale, DIFF_LABEL[difficulty],
             10.5 * scale, fill="#ffffff", weight="bold")


def _wrap_text(text: str, max_chars: int) -> List[str]:
    words = text.split()
    lines, cur = [], ""
    for w in words:
        if not cur or len(cur) + 1 + len(w) <= max_chars:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines or [""]


def _grid_for(per_page: int) -> Tuple[int, int]:
    if per_page >= 4:
        return 2, 2
    if per_page in (2, 3):
        return 2, 1
    return 1, 1


def _page_frame_footer(svg, opts: BookletOptions, width: float,
                       height: float, page_no_text: str) -> None:
    svg.text(width / 2, height - 26, opts.footer, 10.5, fill=SOFT_INK)
    svg.text(width - 40, height - 26, page_no_text, 10.5, fill=SOFT_INK,
             anchor="end")


def cover_page(exercises: List[Exercise], opts: BookletOptions,
               hero_position: Optional[str] = None) -> str:
    width, height = opts.page_size()
    svg = start_page(width, height)
    svg.rect(6, 6, width - 12, height - 12, "none", stroke=INK, stroke_width=2.5)

    svg.text(width / 2, height * 0.13, opts.title, 40 * opts.font_scale,
             weight="bold")
    if opts.subtitle:
        svg.text(width / 2, height * 0.13 + 36 * opts.font_scale, opts.subtitle,
                 16 * opts.font_scale, fill=SOFT_INK)

    draw_width = min(width * 0.55, height * 0.48)
    board_y = height * 0.22
    if hero_position is None and exercises:
        hero_position = exercises[0].fen
    if hero_position:
        pos = Position.from_fen(hero_position)
        draw_board(svg, pos, width / 2 - draw_width / 2, board_y, draw_width,
                   opts.piece_style,
                   flip=_resolve_flip(opts, exercises[0]) if exercises else False,
                   coords=opts.coords)

    counts = {}
    for ex in exercises:
        counts[ex.difficulty] = counts.get(ex.difficulty, 0) + 1
    summary = f"{len(exercises)} exercises"
    parts = [f"{counts.get(level, 0)} {level}" for level in DIFFICULTY_ORDER
             if counts.get(level)]
    if parts:
        summary += "   |   " + "  ".join(p.capitalize() for p in parts)
    y = board_y + draw_width + 52 * opts.font_scale
    svg.rect(width * 0.28, y, width * 0.44, 1.6, INK)
    svg.text(width / 2, y + 30 * opts.font_scale, summary, 15 * opts.font_scale)

    svg.text(width / 2, height - 58 * opts.font_scale, opts.footer,
             11 * opts.font_scale, fill=SOFT_INK)
    return svg_document(width, height, "Cover", "\n".join(svg.parts))


def exercise_grid_page(exercises: List[Exercise], opts: BookletOptions,
                       page_no: int, total_pages: int, section: str,
                       label: Tuple[int, int]) -> str:
    width, height = opts.page_size()
    svg = start_page(width, height)
    scale = opts.font_scale
    margin = 40

    start_no, end_no = label
    masthead_title = section if (start_no == 1 and end_no == len(exercises)) else None
    title = f"{section} ({start_no}-{end_no})"
    page_masthead(svg, width, 18 * scale, title, opts.subtitle, margin,
                  width - margin, scale)

    top = (18 + (46 if opts.subtitle else 38)) * scale + 10
    usable_w = width - 2 * margin
    usable_h = height - top - 62

    cols, rows = _grid_for(len(exercises))
    cell_w = usable_w / cols
    cell_h = usable_h / rows
    board_max = min(cell_w - 26, cell_h - 88 * scale)
    board_max = max(board_max, 96)

    for idx, ex in enumerate(exercises):
        cx0 = margin + (idx % cols) * cell_w
        cy0 = top + (idx // cols) * cell_h
        center_x = cx0 + cell_w / 2
        flip = _resolve_flip(opts, ex)
        pos = Position.from_fen(ex.fen)

        svg.rect(cx0 + 8, cy0 + 6, cell_w - 16, cell_h - 12, "none",
                 stroke="#d8d2c4", rx=4, stroke_width=1.2)

        svg.text(cx0 + 16, cy0 + 26 * scale, ex.id, 18 * scale, fill=ACCENT,
                 anchor="start", weight="bold")
        svg.text(cx0 + 34 * scale + 18, cy0 + 26 * scale, ex.prompt,
                 15 * scale, anchor="start", weight="bold")
        _difficulty_badge(svg, cx0 + cell_w - 76 * scale, cy0 + 25 * scale,
                          ex.difficulty, 0.85 * scale)

        board_size = board_max
        bx = center_x - board_size / 2
        by = cy0 + 36 * scale
        draw_board(svg, pos, bx, by, board_size, opts.piece_style, flip=flip,
                   coords=opts.coords and board_size >= 190)

        base_y = min(by + board_size + 24 * scale, cy0 + cell_h - 16 * scale)
        svg.rect(bx + 6, base_y, board_size - 12, 1.2, "#cfc8b8")
        note_y = base_y + 19 * scale
        if ex.note:
            for line in _wrap_text(ex.note, 64)[:2]:
                svg.text(center_x, note_y, line, 11.5 * scale, fill=SOFT_INK)
                note_y += 15 * scale
        elif ex.last_move_text and ex.last_move_text not in ("puzzle", "start of game"):
            svg.text(center_x, note_y, ex.last_move_text, 11.5 * scale,
                     fill=SOFT_INK)

    _page_frame_footer(svg, opts, width, height,
                       f"page {page_no} of {total_pages}")
    return svg_document(width, height, f"{section} ({start_no}-{end_no})",
                        "\n".join(svg.parts))


def answer_key_page(items: List[Tuple[Exercise, str]], opts: BookletOptions,
                    page_no: int, total_pages: int,
                    label: Tuple[int, int]) -> str:
    width, height = opts.page_size()
    svg = start_page(width, height)
    margin = 40
    first_label, last_label = label
    page_masthead(svg, width, 18, f"Answer Key ({first_label}-{last_label}) ",
                  "", margin, width - margin, 1.0)
    y = 84
    lines_per_page = (height - 90 - y) // 41
    for ex, solution in items:
        _difficulty_badge(svg, width - margin - 55, y - 2, ex.difficulty, 0.85)
        svg.text(margin, y, ex.id, 16, fill=ACCENT, anchor="start", weight="bold")
        solution_lines = _wrap_text(solution, 72)[:3]
        svg.text(margin + 36, y, f"{ex.prompt} :", 14, anchor="start")
        for line in solution_lines:
            svg.text(margin + 150, y, line, 14, anchor="start")
            y += 15
        meta = []
        if ex.note:
            meta.append(ex.note)
        if ex.auto_difficulty and ex.auto_difficulty != ex.difficulty:
            meta.append(f"(heuristic tag: {ex.auto_difficulty})")
        if meta:
            for line in _wrap_text("; ".join(meta), 92)[:1]:
                svg.text(margin + 36, y, line, 10.5, fill=SOFT_INK,
                         anchor="start")
                y += 13
        y += 8
        if y >= height - 80:
            break
    _page_frame_footer(svg, opts, width, height,
                       f"page {page_no} of {total_pages}")
    return svg_document(width, height, f"Answer key ({first_label}-{last_label})",
                        "\n".join(svg.parts))


def howto_page(opts: BookletOptions, inputs_desc: str) -> str:
    width, height = opts.page_size()
    svg = start_page(width, height)
    margin = 40
    page_masthead(svg, width, 18, "How to Use This Booklet", "", margin,
                  width - margin, 1.0)
    lines = [
        "Each diagram shows a position with one side to move.",
        "The prompt tells you the side to move and how many moves to find.",
        "Cover the answer-key pages in the back until you have picked your",
        "move. Write your answer in the space under the diagram, then check",
        "yourself with the key. Wrong? Play the line out and see where it",
        "went sideways. That is the whole workout.",
        "",
        "Difficulty tags, in plain English:",
        "  EASY   - one move; checks, captures, or an obvious mate lead.",
        "  MEDIUM - two or three moves of calculation, or one quiet idea.",
        "  HARD   - deeper lines or a counterintuitive first move.",
        "",
        "Tags come from a simple heuristic (length of the solution line plus",
        "checks, captures, and quiet-queen moves). If your puzzle file",
        "declares a difficulty, that declared value wins over the heuristic.",
        "",
        inputs_desc,
    ]
    y = 96
    for line in lines:
        svg.text(margin, y, line, 13, anchor="start")
        y += 21
    _page_frame_footer(svg, opts, width, height, "how to use")
    return svg_document(width, height, "How to use", "\n".join(svg.parts))


def solution_text_for(ex: Exercise) -> str:
    if not ex.solution_sans:
        return "(no solution given)"
    return "   ".join(f"{i}. {san}" for i, san in enumerate(ex.solution_sans, 1))
