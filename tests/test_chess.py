"""Chess engine tests: FEN, movegen perft, SAN, UCI, legality."""

import unittest

from chessbooklet.chess import (
    Move, Position, parse_sq, sq_name, start_position, START_FEN,
)


class FenTest(unittest.TestCase):
    START = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def test_start_roundtrip(self):
        p = Position.from_fen(self.START)
        self.assertEqual(p.to_fen(), self.START)

    def test_roundtrip_arbitrary(self):
        for fen in [
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
            "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1",
            "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1",
            "8/8/8/8/8/8/8/K1k5 w - - 0 1",
        ]:
            self.assertEqual(Position.from_fen(fen).to_fen(), fen, fen)

    def test_bad_fen(self):
        for fen in ["", "8/8/8/8/8/8/8/8 x KQkq e4 0 1",
                    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBN w KQkq - 0 1",
                    "8/8/8/8/8/8/8/9 w KQkq - 0 1"]:
            with self.assertRaises(ValueError):
                Position.from_fen(fen)

    def test_short_fen_allowed(self):
        p = Position.from_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -")
        self.assertEqual(p.halfmove, 0)
        self.assertEqual(p.fullmove, 1)

    def test_squares(self):
        self.assertEqual(sq_name(parse_sq("a1")), "a1")
        self.assertEqual(sq_name(parse_sq("h8")), "h8")
        self.assertEqual(parse_sq("e4"), 28)
        with self.assertRaises(ValueError):
            parse_sq("i4")


class PerftTest(unittest.TestCase):
    def perft(self, fen, depth):
        pos = Position.from_fen(fen)
        if depth == 0:
            return 1
        return sum(self.perft(pos.make(m).to_fen(), depth - 1)
                   for m in pos.legal_moves())

    def check(self, fen, depth, want):
        self.assertEqual(self.perft(fen, depth), want, fen)

    def test_start(self):
        self.check(START_FEN, 1, 20)
        self.check(START_FEN, 2, 400)
        self.check(START_FEN, 3, 8902)

    def test_kiwipete(self):
        fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
        self.check(fen, 1, 48)
        self.check(fen, 2, 2039)

    def test_promotions(self):
        fen = "r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1"
        self.check(fen, 1, 6)
        self.check(fen, 2, 264)
        self.check(fen, 3, 9467)

    def test_ep_pins(self):
        fen = "8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1"
        self.check(fen, 2, 191)
        self.check(fen, 3, 2812)

    def test_castling_rights_drop(self):
        fen = "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1"
        self.check(fen, 1, 26)
        self.check(fen, 2, 568)


class MovegameTest(unittest.TestCase):
    def test_make_pawns(self):
        p = start_position()
        e4 = p.parse_san("e4")
        self.assertEqual(e4.uci(), "e2e4")
        nxt = p.make(e4)
        self.assertEqual(nxt.to_fen(),
                         "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1")
        self.assertEqual(nxt.fullmove, 1)
        e5 = nxt.parse_san("e5")
        after = nxt.make(e5)
        self.assertEqual(after.to_fen(),
                         "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6 0 2")
        self.assertEqual(after.fullmove, 2)

    def test_castling_san(self):
        p = Position.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        self.assertIn("e1g1", [m.uci() for m in p.legal_moves()])
        self.assertIn("e1c1", [m.uci() for m in p.legal_moves()])
        self.assertEqual(p.san(p.parse_san("O-O-O")), "O-O-O")
        b = p.make(p.parse_san("O-O"))
        self.assertEqual(b.to_fen(),
                         "r3k2r/8/8/8/8/8/8/R4RK1 b kq - 1 1")
        qb = p.make(p.parse_san("O-O-O"))
        self.assertEqual(qb.castling, "kq")
        self.assertEqual(qb.san(qb.parse_san("O-O")), "O-O")

    def test_castling_right_lost_by_rook_move(self):
        p = Position.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        nxt = p.make(p.match_uci("a1b1"))
        self.assertEqual(nxt.castling, "Kkq")
        nxt = p.make(p.match_uci("h1h2"))
        self.assertEqual(nxt.castling, "Qkq")

    def test_castling_right_lost_by_rook_capture(self):
        p2 = Position.from_fen("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1")
        nxt = p2.make(p2.parse_san("Rxa8"))
        self.assertEqual(nxt.castling, "Kk")  # a-rook moved; black lost queenside

    def test_en_passant(self):
        p = Position.from_fen("8/8/8/8/4p3/8/3P4/8 w - - 0 1")
        nxt = p.make(p.parse_san("d4"))
        self.assertEqual(nxt.ep, parse_sq("d3"))
        b = nxt.make(nxt.parse_san("exd3"))
        self.assertEqual(b.board[parse_sq("d4")], ".")
        self.assertEqual(b.board[parse_sq("d3")], "p")

    def test_en_passant_pin_illegal(self):
        # classic ep-pin: capturing en passant exposes the white king on a5
        p = Position.from_fen("3k4/8/8/KPp4r/8/8/8/8 w - c6 0 1")
        self.assertNotIn("b5c6", [m.uci() for m in p.legal_moves()])
        self.assertIn("b5b6", [m.uci() for m in p.legal_moves()])

    def test_promotion(self):
        p = Position.from_fen("8/5P2/8/8/8/8/8/K6k w - - 0 1")
        promos = [m.promo for m in p.legal_moves() if m.promo]
        self.assertEqual(sorted(promos), ["B", "N", "Q", "R"])
        self.assertEqual(p.san(p.parse_san("f8=Q")), "f8=Q")

    def test_mate_and_stalemate(self):
        # fool's mate
        p = Position.from_fen("rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3")
        self.assertTrue(p.is_checkmate())
        # stalemate: black king h8, white queen f7 and king g6
        s2 = Position.from_fen("7k/5Q2/6K1/8/8/8/8/8 b - - 0 1")
        self.assertTrue(s2.is_stalemate())

    def test_disambiguation(self):
        p = Position.from_fen("7k/8/R7/8/8/8/R5KP/8 w - - 0 1")
        move = p.parse_san("R6a4")
        self.assertEqual(move.frm, parse_sq("a6"))
        self.assertEqual(p.san(move), "R6a4")
        p2 = Position.from_fen("8/7k/8/R7/8/8/R7/8 w - - 0 1")
        move = p2.parse_san("R5a3")
        self.assertEqual(move.frm, parse_sq("a5"))
        self.assertEqual(p2.san(move), "R5a3")

    def test_sans_with_suffixes(self):
        p = Position.from_fen("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1")
        move = p.parse_san("Ra8#!")
        self.assertEqual(p.san(move), "Ra8#")
        self.assertEqual(p.parse_san("Ra8+"), move)

    def test_uci(self):
        p = start_position()
        self.assertEqual(p.parse_uci("e2e4").uci(), "e2e4")
        with self.assertRaises(ValueError):
            p.parse_uci("e2e5")

    def test_illegal_san(self):
        p = start_position()
        with self.assertRaises(ValueError):
            p.parse_san("Ke4")


if __name__ == "__main__":
    unittest.main()
