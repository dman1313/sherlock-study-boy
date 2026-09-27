import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_skill", ROOT / "scripts" / "validate_skill.py"
)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)

# Built at runtime so this test file never contains the pattern it checks for.
MACHINE_PATH = "/" + "home" + "/ci-runner/work/sherlock/"


class WalkFilesTests(unittest.TestCase):
    def test_walk_files_skips_cache_and_vcs_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep").mkdir()
            (root / "keep" / "notes.md").write_text("ok", encoding="utf-8")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "x.pyc").write_text(MACHINE_PATH, encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text(MACHINE_PATH, encoding="utf-8")
            found = [p.relative_to(root).as_posix() for p in validator.walk_files(root)]
            self.assertEqual(["keep/notes.md"], found)

    def test_read_text_or_none_skips_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "image.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")
            self.assertIsNone(validator.read_text_or_none(path))


@unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "needs a git checkout")
class CandidateFilesTests(unittest.TestCase):
    def test_ignored_pycache_is_not_scanned(self):
        cache_dir = ROOT / "scripts" / "__pycache__"
        cache_dir.mkdir(exist_ok=True)
        probe = cache_dir / "regression-probe.pyc"
        probe.write_text(MACHINE_PATH, encoding="utf-8")
        try:
            self.assertNotIn(probe, validator.candidate_files(ROOT))
            self.assertFalse(
                [e for e in validator.validate() if "__pycache__" in e],
                "validator scanned an ignored __pycache__ file",
            )
        finally:
            probe.unlink()

    def test_new_untracked_file_is_scanned(self):
        probe = ROOT / "untracked-probe.md"
        probe.write_text(MACHINE_PATH, encoding="utf-8")
        try:
            self.assertIn(probe, validator.candidate_files(ROOT))
            self.assertTrue(
                [e for e in validator.validate() if "untracked-probe.md" in e],
                "validator missed forbidden content in a new, unstaged file",
            )
        finally:
            probe.unlink()


if __name__ == "__main__":
    unittest.main()
