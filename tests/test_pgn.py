"""PGN parsing and game-exercise extraction tests."""

import unittest

from chessbooklet.pgn import parse_pgn, exercises_from_pgn_text
from chessbooklet.puzzles import parse_puzzle_text

SAMPLE = """[Event "Club Blitz"]
[White "Ana"]
[Black "Bo"]
[Result "1-0"]

1. e4 c5 2. Nf3 {solid choice; the main line} d6 (2... Nc6 3. Bb5)
3. d4 cxd4 4. Nxd4 Nf6 5. $1 Nc3 a6 *"""

MASTERS = """[Event "Booklet sample"]
[White "Riley P."]
[Black "Sam K."]
[Result "0-1"]

1. e4 e5 2. Nf3 {A friendly Italian.} 2... Nc6 3. Bc4 Nf6 4. Ng5 Nxe4?!
5. Nxf7 Qe7 {Ponyfork: flashy, tricky.} 6. Nd5+ {Blink and it's gone.}
Qxe4+ 7. Qe2 {Forces the issue.} Bxf2+ 8. Kd1 Nxg5 0-1"""


class PgnParseTest(unittest.TestCase):
    def test_basic_parse(self):
        games = parse_pgn(SAMPLE)
        self.assertEqual(len(games), 1)
        g = games[0]
        self.assertEqual(g.headers["White"], "Ana")
        self.assertEqual(g.headers["Event"], "Club Blitz")
        self.assertEqual(len(g.moves), 10)  # e4 c5 Nf3 d6 d4 cxd4 Nxd4 Nf6 Nc3 a6
        self.assertEqual(g.sans[0], "e4")
        self.assertEqual(g.sans[3], "d6")

    def test_comments_variations_nags_stripped(self):
        g = parse_pgn(SAMPLE)[0]
        joined = " ".join(g.sans)
        self.assertNotIn("solid", joined)
        self.assertNotIn("$1", joined)
        self.assertNotIn("Bb5", joined)
        self.assertEqual(g.sans[4], "d4")

    def test_fen_header_start(self):
        text = '[FEN "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"]\n\n1. Ra8# 1-0\n'
        g = parse_pgn(text)[0]
        self.assertEqual(g.sans, ["Ra8#"])
        self.assertEqual(g.ply_count(), 1)

    def test_multiple_games(self):
        games = parse_pgn(MASTERS + "\n" + SAMPLE)
        self.assertEqual(len(games), 2)
        self.assertEqual(games[0].headers["Black"], "Sam K.")

    def test_zero_moves_ok(self):
        games = parse_pgn('[Result "*"]\n\n*\n')
        self.assertEqual(len(games), 1)
        self.assertEqual(games[0].ply_count(), 0)


class ExtractionTest(unittest.TestCase):
    def test_every_and_skip(self):
        exs = exercises_from_pgn_text(MASTERS, every=4, skip=0, solution_plies=2)
        # plies 0, 4, 8 within 17 total plies
        self.assertEqual(len(exs), 3)
        self.assertEqual([e.id for e in exs], ["P1", "P2", "P3"])

    def test_solution_sans_follow_mainline(self):
        exs = exercises_from_pgn_text(MASTERS, every=6, skip=0, solution_plies=2)
        first = exs[0]
        self.assertEqual(first.solution_sans[:2], ["e4", "e5"])

    def test_difficulty_header_wins(self):
        text = (MASTERS.replace('[White "Riley P."]',
                                '[White "Riley P."]\n[Difficulty "hard"]'))
        exs = exercises_from_pgn_text(text)
        self.assertTrue(all(e.difficulty == "hard" for e in exs))

    def test_renumbered_across_games(self):
        exs = exercises_from_pgn_text(MASTERS + "\n" + MASTERS, every=6, skip=4)
        self.assertEqual(exs[-1].id, f"P{len(exs)}")
        self.assertTrue(len(exs) >= 2)

    def test_pgn_with_uci_puzzles_via_pgn_start(self):
        text = '[FEN "6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1"]\n\n1. Ra8# 1-0\n'
        exs = exercises_from_pgn_text(text, every=1, skip=0)
        self.assertEqual(len(exs), 1)
        self.assertEqual(exs[0].solution_sans, ["Ra8#"])


if __name__ == "__main__":
    unittest.main()
