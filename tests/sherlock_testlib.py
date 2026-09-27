"""Shared helpers for the sherlock.py tests. Not a test module itself."""

import contextlib
import importlib.util
import io
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


def load_sherlock():
    spec = importlib.util.spec_from_file_location("sherlock", ROOT / "scripts" / "sherlock.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


sherlock = load_sherlock()


def run(*argv):
    """Run sherlock.main(argv). Returns (exit_code, parsed_stdout_or_None, stderr_text)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = sherlock.main([str(arg) for arg in argv])
    text = out.getvalue().strip()
    return code, (json.loads(text) if text else None), err.getvalue()


class PackageTestCase(unittest.TestCase):
    """Each test gets an empty study package directory at self.pkg."""

    TODAY = "2026-09-26"

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.pkg = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def ok(self, *argv):
        code, out, err = run(*argv)
        self.assertEqual(0, code, f"expected success, got exit {code}: {err}")
        return out

    def fails(self, expected_code, *argv):
        code, out, err = run(*argv)
        self.assertEqual(expected_code, code, f"stdout={out!r} stderr={err!r}")
        self.assertTrue(err.startswith("sherlock: "), err)
        return err

    def make_bank(self, *concepts, daily_cap=20):
        """concepts: (slug, focus, rank) tuples. Defaults to one 'photosynthesis' concept."""
        self.ok("bank", "init", "--dir", self.pkg, "--notebook-id", "nb-test",
                "--daily-cap", daily_cap)
        for slug, focus, rank in concepts or (("photosynthesis", "Photosynthesis", 1),):
            self.ok("bank", "add-concept", "--dir", self.pkg, "--slug", slug,
                    "--name", focus, "--focus", focus, "--rank", rank)
