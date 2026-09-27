import json
import unittest

from sherlock_testlib import PackageTestCase, run


class StudentNewTests(PackageTestCase):
    def test_random_id_and_untested_concepts(self):
        self.make_bank(("a-one", "One", 1), ("b-two", "Two", 2))
        out = self.ok("student", "new", "--dir", self.pkg)
        self.assertRegex(out["student_id"], r"^s-[0-9a-f]{6}$")
        self.assertEqual(["a-one", "b-two"], out["concepts"])
        data = self.student_data(out["student_id"])
        self.assertEqual("nb-test", data["notebook_id"])
        self.assertEqual({"untested"}, {c["status"] for c in data["concepts"].values()})

    def test_nickname_rules(self):
        self.make_bank()
        self.assertEqual("sky-walker-7", self.new_student("sky-walker-7"))
        for bad in ("Alice Smith", "al", "has_underscore", "UPPER", "a" * 33):
            self.fails(1, "student", "new", "--dir", self.pkg, "--nickname", bad)
        self.fails(1, "student", "new", "--dir", self.pkg, "--nickname", "sky-walker-7")

    def test_invalid_student_id_is_refused_before_touching_files(self):
        self.make_bank()
        self.fails(1, "next", "--dir", self.pkg, "--student", "../../etc/passwd",
                   "--concept", "photosynthesis", "--count", 1, "--mode", "diagnose")

    def test_unknown_schema_in_student_file_exits_2(self):
        self.make_bank()
        student = self.new_student()
        data = self.student_data(student)
        data["schema_version"] = 2
        self.write_student_data(student, data)
        self.fails(2, "next", "--dir", self.pkg, "--student", student,
                   "--concept", "photosynthesis", "--count", 1, "--mode", "diagnose")


class RoundTests(PackageTestCase):
    def setUp(self):
        super().setUp()
        self.make_bank()
        self.student = self.new_student()

    def next(self, count, mode, today=None):
        return self.ok("next", "--dir", self.pkg, "--student", self.student,
                       "--concept", "photosynthesis", "--count", count, "--mode", mode,
                       "--today", today or self.TODAY)

    def record(self, question_id, choice, mode="diagnose"):
        return run("record", "--dir", self.pkg, "--student", self.student,
                   "--concept", "photosynthesis", "--mode", mode,
                   "--question", question_id, "--choice", choice, "--today", self.TODAY)

    def test_next_reports_shortfall_when_bank_is_empty(self):
        out = self.next(3, "diagnose")
        self.assertEqual(([], 3, 0),
                         (out["questions"], out["shortfall"], out["unseen_remaining"]))

    def test_next_never_reveals_answers(self):
        self.add_ready_quiz()
        out = self.next(3, "diagnose")
        self.assertEqual(3, len(out["questions"]))
        self.assertEqual(5, out["unseen_remaining"])
        self.assertEqual(3, out["target_difficulty"])
        for question in out["questions"]:
            self.assertEqual({"id", "type", "question", "options", "hint"}, set(question))

    def test_record_grades_and_refuses_bad_input(self):
        self.add_ready_quiz()
        first = self.next(1, "diagnose")["questions"][0]
        right = self.answer_key()[first["id"]]
        code, out, err = self.record(first["id"], (right + 1) % 4)
        self.assertEqual(0, code, err)
        self.assertFalse(out["correct"])
        self.assertEqual(right, out["correct_index"])
        self.assertEqual(first["options"][right], out["correct_option"])
        self.assertEqual(1, out["answered_this_round"])
        self.assertEqual(1, self.record(first["id"], right)[0])  # already answered this round
        self.assertEqual(1, self.record("000000000000", 0)[0])  # not in the bank
        second = self.next(1, "diagnose")["questions"][0]
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual(1, self.record(second["id"], 4)[0])  # choice out of range

    def test_diagnose_scores(self):
        self.add_ready_quiz()
        out = self.play_round(self.student, "photosynthesis", "diagnose", 3, 3)
        self.assertEqual(
            {"concept": "photosynthesis", "mode": "diagnose", "correct": 3, "asked": 3,
             "score": 1.0, "status": "mastered", "step": 2, "next_review": "2026-09-30"},
            out,
        )
        record = self.student_data(self.student)["concepts"]["photosynthesis"]
        self.assertEqual([], record["open_answers"])
        self.assertEqual(3, len(record["seen"]))

    def test_questions_shared_by_two_quizzes_count_once(self):
        self.add_ready_quiz()
        self.add_ready_quiz()  # NotebookLM can repeat questions across quizzes
        out = self.next(20, "diagnose")
        self.assertEqual((8, 12), (len(out["questions"]), out["shortfall"]))

    def test_close_round_needs_answers(self):
        self.fails(1, "close-round", "--dir", self.pkg, "--student", self.student,
                   "--concept", "photosynthesis", "--mode", "teach")

    def test_teach_uses_only_unseen_questions(self):
        self.add_ready_quiz()
        self.play_round(self.student, "photosynthesis", "diagnose", 3, 1)
        first_ids = set(self.student_data(self.student)["concepts"]["photosynthesis"]["seen"])
        teach = self.next(5, "teach")
        self.assertEqual(2, teach["target_difficulty"])  # weak -> easier quizzes preferred
        self.assertFalse(first_ids & {q["id"] for q in teach["questions"]})
        self.play_round(self.student, "photosynthesis", "teach", 5, 2)
        exhausted = self.next(5, "teach")
        self.assertEqual(([], 5, 0), (exhausted["questions"], exhausted["shortfall"],
                                      exhausted["unseen_remaining"]))

    def test_review_reuses_seen_questions(self):
        self.add_ready_quiz()
        self.play_round(self.student, "photosynthesis", "diagnose", 3, 3)
        self.play_round(self.student, "photosynthesis", "teach", 5, 5)
        review = self.next(5, "review", today="2026-09-30")
        self.assertEqual(5, len(review["questions"]))
        self.assertEqual(0, review["shortfall"])

    def test_full_journey(self):
        self.add_ready_quiz()
        self.assertEqual("partial", self.play_round(
            self.student, "photosynthesis", "diagnose", 3, 2)["status"])
        taught = self.play_round(self.student, "photosynthesis", "teach", 5, 4)
        self.assertEqual(("mastered", 0, "2026-09-27"),
                         (taught["status"], taught["step"], taught["next_review"]))
        passed = self.play_round(self.student, "photosynthesis", "review", 5, 5,
                                 today="2026-09-27")
        self.assertEqual((1, "2026-09-29"), (passed["step"], passed["next_review"]))
        failed = self.play_round(self.student, "photosynthesis", "review", 5, 3,
                                 today="2026-09-29")
        self.assertEqual(("partial", 0, None),
                         (failed["status"], failed["step"], failed["next_review"]))
        rounds = self.student_data(self.student)["concepts"]["photosynthesis"]["rounds"]
        self.assertEqual(["diagnose", "teach", "review", "review"], [r["mode"] for r in rounds])


class NoteTests(PackageTestCase):
    def setUp(self):
        super().setUp()
        self.make_bank()
        self.student = self.new_student()

    def note(self, flag, value):
        return run("note", "--dir", self.pkg, "--student", self.student,
                   "--concept", "photosynthesis", flag, value)

    def test_misconceptions_are_single_line_and_deduplicated(self):
        self.assertEqual(0, self.note("--misconception", "thinks CO2\nis the energy source")[0])
        code, out, _ = self.note("--misconception", "thinks CO2 is the energy source")
        self.assertEqual(0, code)
        self.assertEqual(["thinks CO2 is the energy source"], out["misconceptions"])
        self.assertEqual(1, self.note("--misconception", "x" * 121)[0])

    def test_explanation_tags(self):
        code, out, _ = self.note("--explanation", "factory-analogy")
        self.assertEqual((0, ["factory-analogy"]), (code, out["explanations_tried"]))
        self.assertEqual(1, self.note("--explanation", "Factory Analogy")[0])

    def test_one_of_misconception_or_explanation_is_required(self):
        with self.assertRaises(SystemExit) as caught:
            run("note", "--dir", self.pkg, "--student", self.student,
                "--concept", "photosynthesis")
        self.assertEqual(1, caught.exception.code)


if __name__ == "__main__":
    unittest.main()
