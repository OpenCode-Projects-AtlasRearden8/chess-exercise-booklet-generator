"""SVG + booklet rendering tests."""

import xml.etree.ElementTree as ET
import unittest

from chessbooklet.chess import Position, start_position
from chessbooklet.exercises import Exercise
from chessbooklet.booklet import (BookletOptions, answer_key_page, cover_page,
                                  exercise_grid_page, howto_page,
                                  solution_text_for)
from chessbooklet.svg import svg_document
from chessbooklet.svg import SvgBuilder


def wellformed(svg_text: str) -> ET.Element:
    return ET.fromstring(svg_text)


def make_exercise(i: int = 1, fen: str = None, sans=("Ra8#",), diff="easy",
                  note="back rank", flip=None):
    return Exercise(fen=fen or "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1",
                    solution_sans=list(sans), difficulty=diff, note=note,
                    source="sample", last_move_text="after g6",
                    auto_difficulty=diff)


class SvgTest(unittest.TestCase):
    def test_document_wellformed(self):
        svg = SvgBuilder()
        svg.rect(0, 0, 10, 10, "#fff")
        svg.circle(5, 5, 2, "#000")
        svg.text(5, 5, "héllo <&>", 8)
        doc = svg_document(100, 200, "tést <x>", "\n".join(svg.parts))
        root = wellformed(doc)
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertEqual(root.get("width"), "100")

    def test_escaping(self):
        svg = SvgBuilder()
        svg.text(0, 0, "Sam & Co <bold>", 10)
        doc = svg_document(10, 10, "t", "\n".join(svg.parts))
        self.assertIn("&amp;", doc)
        self.assertIn("&lt;", doc)
        wellformed(doc)

    def test_board_pieces_drawn(self):
        p = start_position()
        svg = SvgBuilder()
        for i, piece in enumerate(p.board):
            pass
        from chessbooklet.svg import draw_board
        draw_board(svg, p, 0, 0, 400, "glyphs")
        content = "".join(svg.parts)
        self.assertEqual(content.count("#b58863"), 32)
        for glyph in ("\u2654", "\u2655", "\u2656", "\u2658"):
            self.assertIn(glyph, content)


class BookletTest(unittest.TestCase):
    def _exercises(self, n=8):
        fen = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"
        out = []
        for i in range(n):
            ex = Exercise(fen=fen, solution_sans=["Ra8#"],
                          difficulty=["easy", "medium", "hard"][i % 3],
                          note=f"note {i}", source="s", last_move_text="",
                          auto_difficulty="easy")
            ex.id = f"P{i + 1}"
            out.append(ex)
        return out

    def test_ids_assigned(self):
        exs = self._exercises(8)
        opts = BookletOptions()
        page = exercise_grid_page(exs[:4], opts, 2, 4, "Exercises", ("P1", "P4"))
        wellformed(page)
        self.assertIn("P2", page)

    def test_per_page_variants(self):
        exs = self._exercises(4)
        for pp in (1, 2, 3, 4):
            opts = BookletOptions(per_page=pp)
            chunk = exs[:pp]
            wellformed(exercise_grid_page(chunk, opts, 2, 3, "Exercises",
                                          (chunk[0].id, chunk[-1].id)))

    def test_large_print_one_per_page(self):
        opts = BookletOptions(large_print=True)
        self.assertEqual(opts.per_page, 1)
        self.assertEqual(opts.font_scale, 1.5)
        chunk = self._exercises(2)
        wellformed(exercise_grid_page(chunk, opts, 2, 3, "Exercises", ("P1", "P2")))

    def test_paper_sizes(self):
        self.assertEqual(BookletOptions().page_size(), (816, 1056))
        self.assertEqual(BookletOptions(paper="a4").page_size(), (794, 1123))
        w, h = BookletOptions(paper="a4").page_size()
        opts = BookletOptions(paper="a4")
        wellformed(exercise_grid_page(self._exercises(2), opts, 2, 1,
                                      "Exercises", ("P1", "P2")))

    def test_cover_and_key(self):
        opts = BookletOptions(subtitle="Test run")
        exs = self._exercises(6)
        wellformed(cover_page(exs, opts))
        items = [(e, solution_text_for(e)) for e in exs]
        wellformed(answer_key_page(items, opts, 7, 9, ("P1", "P6")))
        wellformed(howto_page(opts, "built from sample.pgn"))

    def test_flip_modes(self):
        for mode, ex_fen in (("auto", None), ("white", None), ("black", None)):
            opts = BookletOptions(flip=mode)
            ex = make_exercise(fen=None)
            from chessbooklet.booklet import _resolve_flip
            expected = {"auto": ex.side_to_move == "b",
                        "white": False, "black": True}[mode]
            self.assertEqual(_resolve_flip(opts, ex), expected)

    def test_solution_text(self):
        ex = make_exercise(sans=["Ra8#"])
        self.assertEqual(solution_text_for(ex), "1. Ra8#")


if __name__ == "__main__":
    unittest.main()
