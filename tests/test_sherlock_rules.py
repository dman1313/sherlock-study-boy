import datetime as dt
import unittest

from sherlock_testlib import sherlock

TODAY = dt.date(2026, 9, 26)


def fresh(step=0):
    record = sherlock.new_concept_record()
    record["step"] = step
    return record


def question(qid):
    return {"id": qid, "question": qid, "options": ["x", "y"], "answer_index": 0,
            "rationale": None, "hint": None}


class ClassifyTests(unittest.TestCase):
    def test_boundaries(self):
        cases = {0.0: "weak", 0.49: "weak", 0.5: "partial", 0.79: "partial",
                 0.8: "mastered", 1.0: "mastered", 4 / 5: "mastered", 2 / 3: "partial",
                 1 / 3: "weak"}
        for score, expected in cases.items():
            self.assertEqual(expected, sherlock.classify(score), score)


class ApplyRoundTests(unittest.TestCase):
    def test_diagnose_mastered_reviews_after_4_days(self):
        record = sherlock.apply_round(fresh(), "diagnose", 3, 3, TODAY)
        self.assertEqual(("mastered", 2, "2026-09-30"),
                         (record["status"], record["step"], record["next_review"]))

    def test_diagnose_not_mastered_has_no_review(self):
        record = sherlock.apply_round(fresh(), "diagnose", 2, 3, TODAY)
        self.assertEqual(("partial", 0, None),
                         (record["status"], record["step"], record["next_review"]))
        record = sherlock.apply_round(fresh(), "diagnose", 1, 3, TODAY)
        self.assertEqual("weak", record["status"])

    def test_teach_mastered_reviews_after_1_day(self):
        record = sherlock.apply_round(fresh(), "teach", 4, 5, TODAY)
        self.assertEqual(("mastered", 0, "2026-09-27"),
                         (record["status"], record["step"], record["next_review"]))

    def test_review_pass_climbs_one_step_up_to_60_days(self):
        expected = {0: (1, "2026-09-28"), 3: (4, "2026-10-12"), 5: (6, "2026-11-25"),
                    6: (6, "2026-11-25")}
        for start, (step, due) in expected.items():
            record = sherlock.apply_round(fresh(step=start), "review", 5, 5, TODAY)
            self.assertEqual(("mastered", step, due),
                             (record["status"], record["step"], record["next_review"]), start)

    def test_review_fail_resets_and_clears_review(self):
        record = sherlock.apply_round(fresh(step=4), "review", 3, 5, TODAY)
        self.assertEqual(("partial", 0, None),
                         (record["status"], record["step"], record["next_review"]))
        record = sherlock.apply_round(fresh(step=4), "review", 2, 5, TODAY)
        self.assertEqual("weak", record["status"])

    def test_round_is_logged_and_score_rounded(self):
        record = sherlock.apply_round(fresh(), "diagnose", 2, 3, TODAY)
        self.assertEqual(0.6667, record["score"])
        self.assertEqual(
            [{"date": "2026-09-26", "mode": "diagnose", "correct": 2, "asked": 3}],
            record["rounds"],
        )

    def test_empty_round_is_refused(self):
        with self.assertRaises(sherlock.SherlockError):
            sherlock.apply_round(fresh(), "teach", 0, 0, TODAY)


class SelectQuestionsTests(unittest.TestCase):
    CANDIDATES = [(3, question("a")), (2, question("b")), (4, question("c")), (3, question("d"))]

    def test_unseen_first_closest_difficulty_first(self):
        picked, remaining = sherlock.select_questions(self.CANDIDATES, {}, 2, 2, False)
        self.assertEqual(["b", "a"], [q["id"] for q in picked])
        self.assertEqual(2, remaining)

    def test_seen_questions_excluded_without_allow_seen(self):
        seen = {qid: {"last_seen": "2026-09-01", "times": 1, "last_correct": True}
                for qid in ("a", "b", "c")}
        picked, remaining = sherlock.select_questions(self.CANDIDATES, seen, 3, 3, False)
        self.assertEqual(["d"], [q["id"] for q in picked])
        self.assertEqual(0, remaining)

    def test_allow_seen_adds_oldest_seen_first(self):
        seen = {
            "a": {"last_seen": "2026-09-20", "times": 1, "last_correct": True},
            "b": {"last_seen": "2026-09-01", "times": 1, "last_correct": True},
            "c": {"last_seen": "2026-09-10", "times": 1, "last_correct": False},
        }
        picked, _ = sherlock.select_questions(self.CANDIDATES, seen, 3, 3, True)
        self.assertEqual(["d", "b", "c"], [q["id"] for q in picked])


if __name__ == "__main__":
    unittest.main()
