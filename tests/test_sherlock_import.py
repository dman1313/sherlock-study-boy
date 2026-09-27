import json
import unittest

from sherlock_testlib import FIXTURES, PackageTestCase, nlm_quiz, sherlock


class QuestionIdTests(unittest.TestCase):
    def test_id_ignores_case_and_whitespace(self):
        a = sherlock.question_id("What is  the main SOURCE\nof energy?")
        b = sherlock.question_id("what is the main source of energy?")
        self.assertEqual(a, b)
        self.assertRegex(a, r"^[0-9a-f]{12}$")

    def test_different_text_gives_different_id(self):
        self.assertNotEqual(sherlock.question_id("Question A?"), sherlock.question_id("Question B?"))


class NormalizeQuizTests(unittest.TestCase):
    def test_normalizes_real_format_fixture(self):
        raw = json.loads((FIXTURES / "quiz-sample.json").read_text())
        quiz = sherlock.normalize_quiz(raw, "photosynthesis-d3-1", "artifact-test-1")
        self.assertEqual(8, len(quiz["questions"]))
        first = quiz["questions"][0]
        self.assertEqual(
            {
                "id": sherlock.question_id("What is the main source of energy for photosynthesis?"),
                "type": "multiple_choice",
                "question": "What is the main source of energy for photosynthesis?",
                "options": ["Carbon dioxide", "Sunlight", "Water", "Soil nutrients"],
                "answer_index": 1,
                "answer_indexes": [1],
                "answers": [],
                "model_answer": None,
                "rationale": "Chlorophyll captures light energy, which drives the reaction.",
                "hint": "Think about what a plant needs to be placed near.",
            },
            first,
        )
        self.assertIsNone(quiz["questions"][2]["hint"])
        self.assertIsNone(quiz["questions"][2]["rationale"])

    def test_rejects_two_correct_options(self):
        raw = json.loads((FIXTURES / "quiz-broken.json").read_text())
        with self.assertRaisesRegex(sherlock.SherlockError, "exactly one correct option"):
            sherlock.normalize_quiz(raw, "slot", "artifact")

    def test_rejects_empty_and_malformed_quizzes(self):
        for raw in ({"questions": []}, {"cards": []}, [], {"questions": [{"question": "Q?"}]}):
            with self.assertRaises(sherlock.SherlockError):
                sherlock.normalize_quiz(raw, "slot", "artifact")

    def test_drops_duplicate_questions(self):
        raw = nlm_quiz("dup", 2)
        raw["questions"][1]["question"] = "  DUP question 1?  "
        quiz = sherlock.normalize_quiz(raw, "slot", "artifact")
        self.assertEqual(1, len(quiz["questions"]))


class ImportCommandTests(PackageTestCase):
    def pending_slot(self):
        self.make_bank()
        slot = self.ok("bank", "request", "--dir", self.pkg, "--concept", "photosynthesis",
                       "--difficulty", 3, "--today", self.TODAY)["slot"]
        self.ok("bank", "submitted", "--dir", self.pkg, "--quiz", slot,
                "--artifact-id", "artifact-test-1")
        return slot

    def bank_quiz(self, slot):
        bank = json.loads((self.pkg / "quiz-bank" / "bank.json").read_text())
        return next(q for q in bank["quizzes"] if q["slot"] == slot)

    def test_import_marks_ready_and_writes_normalized_file(self):
        slot = self.pending_slot()
        out = self.ok("bank", "import", "--dir", self.pkg, "--quiz", slot,
                      "--file", FIXTURES / "quiz-sample.json")
        self.assertEqual({"slot": slot, "status": "ready", "question_count": 8,
                          "gradable_count": 8, "skipped": 0}, out)
        stored = json.loads((self.pkg / "quiz-bank" / f"{slot}.json").read_text())
        self.assertEqual("artifact-test-1", stored["artifact_id"])
        self.assertEqual("ready", self.bank_quiz(slot)["status"])

    def test_invalid_quiz_marks_failed(self):
        slot = self.pending_slot()
        err = self.fails(1, "bank", "import", "--dir", self.pkg, "--quiz", slot,
                         "--file", FIXTURES / "quiz-broken.json")
        self.assertIn("failed validation", err)
        quiz = self.bank_quiz(slot)
        self.assertEqual("failed", quiz["status"])
        self.assertIn("exactly one correct option", quiz["reason"])
        self.assertFalse((self.pkg / "quiz-bank" / f"{slot}.json").exists())

    def test_unparseable_file_marks_failed(self):
        slot = self.pending_slot()
        bad = self.pkg / "download.json"
        bad.write_text("<html>not json</html>")
        self.fails(1, "bank", "import", "--dir", self.pkg, "--quiz", slot, "--file", bad)
        self.assertEqual("failed", self.bank_quiz(slot)["status"])

    def test_missing_file_leaves_quiz_pending(self):
        slot = self.pending_slot()
        self.fails(1, "bank", "import", "--dir", self.pkg, "--quiz", slot,
                   "--file", self.pkg / "not-downloaded.json")
        self.assertEqual("pending", self.bank_quiz(slot)["status"])

    def test_import_requires_pending(self):
        self.make_bank()
        slot = self.ok("bank", "request", "--dir", self.pkg, "--concept", "photosynthesis",
                       "--difficulty", 3)["slot"]
        self.fails(1, "bank", "import", "--dir", self.pkg, "--quiz", slot,
                   "--file", FIXTURES / "quiz-sample.json")


if __name__ == "__main__":
    unittest.main()
