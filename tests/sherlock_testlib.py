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


def nlm_quiz(prefix, count, correct_index=1):
    """Build a quiz in `nlm download quiz --format json` shape with distinct questions."""
    return {
        "title": f"{prefix} quiz",
        "questions": [
            {
                "question": f"{prefix} question {n}?",
                "answerOptions": [
                    {"text": f"{prefix} {n} option {i}", "isCorrect": i == correct_index}
                    for i in range(4)
                ],
            }
            for n in range(1, count + 1)
        ],
    }


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

    def add_ready_quiz(self, concept="photosynthesis", difficulty=3, quiz=None, today=None):
        """Request, submit, and import one quiz. quiz: nlm-format dict; default is the sample fixture."""
        slot = self.ok("bank", "request", "--dir", self.pkg, "--concept", concept,
                       "--difficulty", difficulty, "--today", today or self.TODAY)["slot"]
        self.ok("bank", "submitted", "--dir", self.pkg, "--quiz", slot,
                "--artifact-id", f"artifact-{slot}")
        source = FIXTURES / "quiz-sample.json"
        if quiz is not None:
            source = self.pkg / f"download-{slot}.json"
            source.write_text(json.dumps(quiz), encoding="utf-8")
        self.ok("bank", "import", "--dir", self.pkg, "--quiz", slot, "--file", source)
        return slot

    def new_student(self, nickname="test-kid"):
        return self.ok("student", "new", "--dir", self.pkg, "--nickname", nickname,
                       "--today", self.TODAY)["student_id"]

    def answer_key(self):
        """question id -> answer_index, read from every imported quiz file."""
        key = {}
        for path in (self.pkg / "quiz-bank").glob("*.json"):
            if path.name != "bank.json":
                for question in json.loads(path.read_text())["questions"]:
                    key[question["id"]] = question["answer_index"]
        return key

    def play_round(self, student, concept, mode, count, n_correct, today=None):
        """Ask `count` questions, answer the first `n_correct` correctly, close the round."""
        today = today or self.TODAY
        picked = self.ok("next", "--dir", self.pkg, "--student", student, "--concept", concept,
                         "--count", count, "--mode", mode, "--today", today)
        self.assertEqual(count, len(picked["questions"]), picked)
        key = self.answer_key()
        for index, question in enumerate(picked["questions"]):
            right = key[question["id"]]
            choice = right if index < n_correct else (right + 1) % len(question["options"])
            self.ok("record", "--dir", self.pkg, "--student", student, "--concept", concept,
                    "--mode", mode, "--question", question["id"], "--choice", choice,
                    "--today", today)
        return self.ok("close-round", "--dir", self.pkg, "--student", student,
                       "--concept", concept, "--mode", mode, "--today", today)

    def student_data(self, student):
        return json.loads((self.pkg / "students" / f"{student}.json").read_text())

    def write_student_data(self, student, data):
        (self.pkg / "students" / f"{student}.json").write_text(json.dumps(data))
