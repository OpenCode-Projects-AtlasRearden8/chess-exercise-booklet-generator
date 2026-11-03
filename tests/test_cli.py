"""CLI end-to-end tests (invoke via subprocess)."""

import glob
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_cli(*args, cwd=ROOT):
    env = dict(os.environ, PYTHONPATH=ROOT)
    return subprocess.run(
        [sys.executable, "-m", "chessbooklet", *args],
        capture_output=True, text=True, env=env, cwd=cwd,
    )


class CliTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.mkdtemp(prefix="chessbooklet-test-")

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_sample_command(self):
        out = os.path.join(self.tmp, "samples")
        r = run_cli("sample", "--dir", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(os.path.isfile(os.path.join(out, "sample_games.pgn")))
        self.assertTrue(os.path.isfile(os.path.join(out, "sample_puzzles.txt")))

    def _build_and_check(self, src, extra_args=(), outname="out"):
        out = os.path.join(self.tmp, outname)
        r = run_cli("build", src, "-o", out, *extra_args)
        self.assertEqual(r.returncode, 0, r.stderr)
        pages = sorted(glob.glob(os.path.join(out, "page-*.svg")))
        self.assertTrue(pages)
        for page in pages:
            ET.parse(page)
        with open(os.path.join(out, "answer-key.txt")) as fh:
            key = fh.read()
        self.assertIn("P1", key)
        self.assertIn("1. Ra8#", key)  # sample back-rank mate is in both samples
        with open(os.path.join(out, "index.html")) as fh:
            html = fh.read()
        self.assertIn(os.path.basename(pages[0]), html)
        return pages, key

    def test_build_puzzles(self):
        run_cli("sample", "--dir", os.path.join(self.tmp, "s2"))
        src = os.path.join(self.tmp, "s2", "sample_puzzles.txt")
        pages, _ = self._build_and_check(src, outname="puzzles")
        self.assertGreaterEqual(len(pages), 4)

    def test_build_games(self):
        run_cli("sample", "--dir", os.path.join(self.tmp, "s3"))
        src = os.path.join(self.tmp, "s3", "sample_games.pgn")
        pages, key = self._build_and_check(src, outname="games")
        self.assertGreaterEqual(len(pages), 4)

    def test_difficulty_filter(self):
        run_cli("sample", "--dir", os.path.join(self.tmp, "s4"))
        src = os.path.join(self.tmp, "s4", "sample_puzzles.txt")
        out = os.path.join(self.tmp, "filtered")
        r = run_cli("build", src, "-o", out, "--difficulty", "hard")
        self.assertEqual(r.returncode, 0, r.stderr)
        with open(os.path.join(out, "answer-key.txt")) as fh:
            key = fh.read()
        self.assertIn("hard", key)
        self.assertNotIn("[easy]", key)

    def test_large_print(self):
        run_cli("sample", "--dir", os.path.join(self.tmp, "s5"))
        src = os.path.join(self.tmp, "s5", "sample_puzzles.txt")
        out = os.path.join(self.tmp, "large")
        r = run_cli("build", src, "-o", out, "--large-print", "--paper", "a4")
        self.assertEqual(r.returncode, 0, r.stderr)
        page2 = os.path.join(out, "page-002.svg")
        xml = ET.parse(page2).getroot()
        self.assertEqual(xml.get("width"), "794")

    def test_bad_input(self):
        out = os.path.join(self.tmp, "bad")
        r = run_cli("build", "/nonexistent/file.pgn", "-o", out)
        self.assertEqual(r.returncode, 2)

    def test_bad_puzzle_move(self):
        src = os.path.join(self.tmp, "bad_moves.txt")
        with open(src, "w") as fh:
            fh.write("6k1/5ppp/8/8/8/8/8/R5K1 w - - 0 1 | Qe9+\n")
        out = os.path.join(self.tmp, "bad_out")
        r = run_cli("build", src, "-o", out)
        self.assertEqual(r.returncode, 1)
        self.assertIn("illegal", r.stderr)


if __name__ == "__main__":
    unittest.main()
