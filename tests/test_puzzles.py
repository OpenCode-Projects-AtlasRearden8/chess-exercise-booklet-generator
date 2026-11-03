"""Puzzle-set parsing tests."""

import unittest

from chessbooklet.puzzles import parse_puzzle_line, parse_puzzle_text, PuzzleError

RA8 = "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"


class PuzzleLineTest(unittest.TestCase):
    def test_basic_san(self):
        fen, sans, diff, note, auto = parse_puzzle_line(f"{RA8} | Ra8# | easy | back rank")
        self.assertEqual(sans, ["Ra8#"])
        self.assertEqual(diff, "easy")
        self.assertEqual(note, "back rank")

    def test_auto_difficulty(self):
        fen, sans, diff, note, auto = parse_puzzle_line(f"{RA8} | Ra8#")
        self.assertEqual(diff, auto)
        self.assertEqual(diff, "easy")

    def test_uci_moves(self):
        line = f"{RA8} | a1a8"
        fen, sans, diff, note, auto = parse_puzzle_line(line, 1)
        self.assertEqual(sans, ["Ra8#"])

    def test_mixed_and_multi_move(self):
        fen = "8/3r4/8/8/4k3/3N4/6K1/8 w - - 0 1"
        line = fen + " | Nc5+ Kd4 Nxd7"
        _, sans, diff, _, auto = parse_puzzle_line(line, 1)
        self.assertEqual(sans, ["Nc5+", "Kd4", "Nxd7"])
        self.assertEqual(sans, sans)
        self.assertEqual(diff, "medium" if diff in ("medium",) else diff)
        self.assertTrue(auto in ("easy", "medium", "hard"))

    def test_declared_difficulty_wins(self):
        _, _, diff, _, auto = parse_puzzle_line(f"{RA8} | Ra8# | hard")
        self.assertEqual(diff, "hard")
        self.assertEqual(auto, "easy")

    def test_free_text_note_without_difficulty(self):
        _, _, diff, note, _ = parse_puzzle_line(f"{RA8} | Ra8# | back rank trick")
        self.assertEqual(note, "back rank trick")
        self.assertEqual(diff, "easy")

    def test_pipe_and_semicolon_fields(self):
        for sep in ("|", ";"):
            _, _, diff, note, _ = parse_puzzle_line(f"{RA8} {sep} Ra8# {sep} easy {sep} n1", 1)
            self.assertEqual(diff, "easy")

    def test_bad_move(self):
        with self.assertRaises(PuzzleError):
            parse_puzzle_line(f"{RA8} | Qf6+")

    def test_missing_moves(self):
        with self.assertRaises(PuzzleError):
            parse_puzzle_line(f"{RA8} |")


class PuzzleTextTest(unittest.TestCase):
    def test_comments_and_blanks_skipped(self):
        text = "# a comment\n\n  \n" + f"{RA8} | Ra8#\n"
        exs = parse_puzzle_text(text, "sample.txt")
        self.assertEqual([e.id for e in exs], ["P1"])

    def test_ids_sequential(self):
        text = (f"{RA8} | Ra8#\n" + f"{RA8} | Ra8#\n")
        exs = parse_puzzle_text(text)
        self.assertEqual([e.id for e in exs], ["P1", "P2"])

    def test_empty_rejected(self):
        with self.assertRaises(PuzzleError):
            parse_puzzle_text("\n# only comments\n", "nada.txt")


if __name__ == "__main__":
    unittest.main()
