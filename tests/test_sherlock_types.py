import json
import unittest

from sherlock_testlib import FIXTURES, PackageTestCase, run, sherlock


class MixedTypeNormalizeTests(unittest.TestCase):
    def setUp(self):
        raw = json.loads((FIXTURES / "quiz-mixed.json").read_text())
        self.quiz = sherlock.normalize_quiz(raw, "respiration-d3-1", "artifact-test-1")
        self.by_type = {}
        for question in self.quiz["questions"]:
            self.by_type.setdefault(question["type"], []).append(question)

    def test_keeps_supported_types_and_skips_the_rest(self):
        self.assertEqual(
            {"multiple_choice": 1, "multiple_select": 1, "fill_in_the_blank": 2, "short_answer": 1},
            {kind: len(questions) for kind, questions in self.by_type.items()},
        )
        self.assertEqual(2, len(self.quiz["skipped"]))
        self.assertTrue(any("image" in reason for reason in self.quiz["skipped"]))
        self.assertTrue(
            any("exactly one correct option" in reason for reason in self.quiz["skipped"])
        )

    def test_multiple_select_keeps_every_correct_index(self):
        question = self.by_type["multiple_select"][0]
        self.assertEqual([0, 1, 3], question["answer_indexes"])
        self.assertIsNone(question["answer_index"])

    def test_fill_in_the_blank_keeps_best_and_acceptable_answers(self):
        question = self.by_type["fill_in_the_blank"][0]
        self.assertEqual(
            ["oxygen debt", "EPOC", "excess post-exercise oxygen consumption"], question["answers"]
        )
        self.assertEqual([], question["options"])

    def test_short_answer_keeps_model_answer(self):
        question = self.by_type["short_answer"][0]
        self.assertIn("completely broken down", question["model_answer"])

    def test_quiz_without_auto_marked_questions_is_rejected(self):
        raw = {"questions": [{"type": "short_answer", "question": "Explain respiration.",
                              "grading": {"modelAnswer": "It releases energy."}}]}
        with self.assertRaisesRegex(sherlock.SherlockError,
                                    "no questions that can be marked automatically"):
            sherlock.normalize_quiz(raw, "slot", "artifact")

    def test_answer_text_normalization(self):
        norm = sherlock.normalize_answer_text
        self.assertEqual(norm("O2"), norm("$O_2$"))
        self.assertEqual(norm("oxygen-debt"), norm("Oxygen Debt"))
        self.assertEqual(norm("CO2"), norm(r"$\text{CO}_2$"))
        self.assertNotEqual(norm("oxygen"), norm("oxygen debt"))


class MixedTypeRoundTests(PackageTestCase):
    def setUp(self):
        super().setUp()
        self.make_bank(("respiration", "Respiration", 1))
        slot = self.ok("bank", "request", "--dir", self.pkg, "--concept", "respiration",
                       "--difficulty", 3, "--today", self.TODAY)["slot"]
        self.ok("bank", "submitted", "--dir", self.pkg, "--quiz", slot,
                "--artifact-id", "artifact-test-1")
        self.imported = self.ok("bank", "import", "--dir", self.pkg, "--quiz", slot,
                                "--file", FIXTURES / "quiz-mixed.json")

    def serve(self, student):
        return self.ok("next", "--dir", self.pkg, "--student", student,
                       "--concept", "respiration", "--count", 10, "--mode", "diagnose",
                       "--today", self.TODAY)["questions"]

    def find(self, questions, fragment):
        return next(q for q in questions if fragment in q["question"])

    def record(self, student, question, *answer):
        return run("record", "--dir", self.pkg, "--student", student,
                   "--concept", "respiration", "--mode", "diagnose",
                   "--question", question["id"], *answer, "--today", self.TODAY)

    def test_import_reports_gradable_and_skipped_counts(self):
        self.assertEqual(
            {"status": "ready", "question_count": 5, "gradable_count": 4, "skipped": 2},
            {k: self.imported[k] for k in ("status", "question_count", "gradable_count", "skipped")},
        )

    def test_next_serves_only_auto_marked_types(self):
        served = self.serve(self.new_student())
        self.assertEqual(4, len(served))
        self.assertNotIn("short_answer", {q["type"] for q in served})
        for question in served:
            self.assertEqual({"id", "type", "question", "options", "hint"}, set(question))

    def test_multiple_choice_still_reports_correct_option(self):
        student = self.new_student()
        question = self.find(self.serve(student), "product of aerobic")
        code, out, err = self.record(student, question, "--choice", 1)
        self.assertEqual(0, code, err)
        self.assertEqual((True, 1, "Carbon dioxide"),
                         (out["correct"], out["correct_index"], out["correct_option"]))

    def test_multiple_select_requires_the_exact_set(self):
        right, wrong, bad = (self.new_student(n) for n in ("kid-right", "kid-wrong", "kid-bad"))
        question = self.find(self.serve(right), "yeast")
        code, out, _ = self.record(right, question, "--choices", "3,0,1")
        self.assertEqual((0, True), (code, out["correct"]))
        code, out, _ = self.record(wrong, question, "--choices", "0,1")
        self.assertEqual((0, False, [0, 1, 3]), (code, out["correct"], out["correct_indexes"]))
        self.assertEqual(1, self.record(bad, question, "--choices", "0,0,1")[0])  # duplicate
        self.assertEqual(1, self.record(bad, question, "--choices", "0,9")[0])    # out of range

    def test_fill_in_matches_normalized_answers(self):
        right, wrong = self.new_student("kid-right"), self.new_student("kid-wrong")
        question = self.find(self.serve(right), "requires glucose")
        code, out, _ = self.record(right, question, "--text", "O2")
        self.assertEqual((0, True), (code, out["correct"]))
        code, out, _ = self.record(wrong, question, "--text", "carbon dioxide")
        self.assertEqual((0, False, ["oxygen", "$O_2$"]),
                         (code, out["correct"], out["accepted_answers"]))

    def test_answer_form_must_match_question_type(self):
        student = self.new_student()
        served = self.serve(student)
        err = self.fails(1, "record", "--dir", self.pkg, "--student", student,
                         "--concept", "respiration", "--mode", "diagnose",
                         "--question", self.find(served, "product of aerobic")["id"],
                         "--text", "carbon dioxide")
        self.assertIn("--choice", err)
        err = self.fails(1, "record", "--dir", self.pkg, "--student", student,
                         "--concept", "respiration", "--mode", "diagnose",
                         "--question", self.find(served, "requires glucose")["id"],
                         "--choice", 0)
        self.assertIn("--text", err)

    def test_fill_in_text_is_never_stored(self):
        student = self.new_student()
        question = self.find(self.serve(student), "requires glucose")
        self.record(student, question, "--text", "Oxygen gas")
        raw = (self.pkg / "students" / f"{student}.json").read_text()
        self.assertNotIn("Oxygen gas", raw)
        self.assertIsNone(self.student_data(student)["concepts"]["respiration"]
                          ["open_answers"][0]["choice"])


class ReimportTests(PackageTestCase):
    def pending_slot(self):
        self.make_bank()
        slot = self.ok("bank", "request", "--dir", self.pkg, "--concept", "photosynthesis",
                       "--difficulty", 3, "--today", self.TODAY)["slot"]
        self.ok("bank", "submitted", "--dir", self.pkg, "--quiz", slot,
                "--artifact-id", "artifact-test-1")
        return slot

    def test_failed_import_can_be_retried_without_a_new_generation(self):
        slot = self.pending_slot()
        self.fails(1, "bank", "import", "--dir", self.pkg, "--quiz", slot,
                   "--file", FIXTURES / "quiz-broken.json")
        out = self.ok("bank", "import", "--dir", self.pkg, "--quiz", slot,
                      "--file", FIXTURES / "quiz-sample.json")
        self.assertEqual("ready", out["status"])

    def test_slot_that_never_got_an_artifact_cannot_import(self):
        self.make_bank()
        slot = self.ok("bank", "request", "--dir", self.pkg, "--concept", "photosynthesis",
                       "--difficulty", 3, "--today", self.TODAY)["slot"]
        self.ok("bank", "fail", "--dir", self.pkg, "--quiz", slot, "--reason", "rate limited")
        self.fails(1, "bank", "import", "--dir", self.pkg, "--quiz", slot,
                   "--file", FIXTURES / "quiz-sample.json")


if __name__ == "__main__":
    unittest.main()
