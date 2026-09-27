import unittest

from sherlock_testlib import PackageTestCase, nlm_quiz


class StatusTests(PackageTestCase):
    def setUp(self):
        super().setUp()
        self.make_bank(("alpha", "Alpha", 1), ("beta", "Beta", 2), ("gamma", "Gamma", 3))
        for slug in ("alpha", "beta", "gamma"):
            self.add_ready_quiz(slug, quiz=nlm_quiz(slug, 8))
        self.student = self.new_student()

    def status(self, today=None):
        return self.ok("status", "--dir", self.pkg, "--student", self.student,
                       "--today", today or self.TODAY)

    def test_rows_follow_rank_and_count_unseen(self):
        self.play_round(self.student, "beta", "diagnose", 3, 3)
        rows = self.status()["concepts"]
        self.assertEqual(["alpha", "beta", "gamma"], [r["concept"] for r in rows])
        self.assertEqual([8, 5, 8], [r["unseen_questions"] for r in rows])
        self.assertEqual(["untested", "mastered", "untested"], [r["status"] for r in rows])

    def test_teach_queue_weak_first_then_lowest_score(self):
        self.play_round(self.student, "alpha", "diagnose", 3, 2)  # partial 0.67
        self.play_round(self.student, "beta", "diagnose", 3, 1)   # weak 0.33
        self.play_round(self.student, "gamma", "diagnose", 3, 0)  # weak 0.0
        self.assertEqual(["gamma", "beta", "alpha"], self.status()["teach_queue"])

    def test_teach_queue_skips_concepts_taught_three_times_today(self):
        self.play_round(self.student, "alpha", "diagnose", 3, 0)
        data = self.student_data(self.student)
        data["concepts"]["alpha"]["rounds"] += [
            {"date": self.TODAY, "mode": "teach", "correct": 1, "asked": 5}] * 3
        self.write_student_data(self.student, data)
        self.assertEqual([], self.status()["teach_queue"])
        self.assertEqual(["alpha"], self.status(today="2026-09-27")["teach_queue"])

    def test_due_and_quota(self):
        self.play_round(self.student, "alpha", "diagnose", 3, 3)  # review on 2026-09-30
        self.assertEqual([], self.status()["due"])
        self.assertEqual(["alpha"], self.status(today="2026-09-30")["due"])
        self.assertEqual({"used_today": 3, "cap": 20, "remaining": 17}, self.status()["quota"])

    def test_pending_quizzes_are_counted(self):
        self.ok("bank", "request", "--dir", self.pkg, "--concept", "gamma",
                "--difficulty", 2, "--today", self.TODAY)
        rows = {r["concept"]: r for r in self.status()["concepts"]}
        self.assertEqual(1, rows["gamma"]["quizzes_pending"])
        self.assertEqual(0, rows["alpha"]["quizzes_pending"])


class DueTests(PackageTestCase):
    def test_due_lists_concepts_in_review_order(self):
        self.make_bank(("alpha", "Alpha", 1), ("beta", "Beta", 2))
        for slug in ("alpha", "beta"):
            self.add_ready_quiz(slug, quiz=nlm_quiz(slug, 8))
        student = self.new_student()
        self.play_round(student, "beta", "diagnose", 3, 3)          # due 2026-09-30
        self.play_round(student, "alpha", "diagnose", 3, 0)
        self.play_round(student, "alpha", "teach", 5, 5)            # due 2026-09-27
        out = self.ok("due", "--dir", self.pkg, "--student", student, "--today", "2026-09-30")
        self.assertEqual(
            [{"concept": "alpha", "name": "Alpha", "next_review": "2026-09-27", "step": 0},
             {"concept": "beta", "name": "Beta", "next_review": "2026-09-30", "step": 2}],
            out["due"],
        )
        none_due = self.ok("due", "--dir", self.pkg, "--student", student,
                           "--today", "2026-09-26")
        self.assertEqual([], none_due["due"])


if __name__ == "__main__":
    unittest.main()
