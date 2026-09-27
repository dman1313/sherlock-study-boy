import json
import unittest

from sherlock_testlib import PackageTestCase


class QuizSlotTests(PackageTestCase):
    def request(self, concept="photosynthesis", difficulty=3, today=None, **extra):
        argv = ["bank", "request", "--dir", self.pkg, "--concept", concept,
                "--difficulty", difficulty, "--today", today or self.TODAY]
        for key, value in extra.items():
            argv += [f"--{key}", value]
        return argv

    def bank(self):
        return json.loads((self.pkg / "quiz-bank" / "bank.json").read_text())

    def test_request_prints_exact_nlm_command(self):
        self.make_bank(("organ-systems", "Organ Systems", 1))
        out = self.ok(*self.request("organ-systems", 2))
        self.assertEqual("organ-systems-d2-1", out["slot"])
        self.assertEqual(
            ["nlm", "quiz", "create", "nb-test", "--focus", "Organ Systems",
             "--count", "8", "--difficulty", "2", "--confirm", "--json"],
            out["command"],
        )
        self.assertEqual(
            "nlm quiz create nb-test --focus 'Organ Systems' --count 8 --difficulty 2 --confirm --json",
            out["command_line"],
        )
        self.assertEqual({"used_today": 1, "cap": 20, "remaining": 19}, out["quota"])
        self.assertEqual("reserved", self.bank()["quizzes"][0]["status"])

    def test_slot_numbers_increase_per_concept_and_difficulty(self):
        self.make_bank()
        slots = [self.ok(*self.request(difficulty=d))["slot"] for d in (3, 3, 2)]
        self.assertEqual(
            ["photosynthesis-d3-1", "photosynthesis-d3-2", "photosynthesis-d2-1"], slots
        )

    def test_daily_cap_is_enforced_and_resets_next_day(self):
        self.make_bank(("a-one", "One", 1), ("b-two", "Two", 2), daily_cap=2)
        self.ok(*self.request("a-one"))
        self.ok(*self.request("b-two"))
        err = self.fails(1, *self.request("a-one"))
        self.assertIn("daily quiz cap reached", err)
        self.ok(*self.request("a-one", today="2026-09-27"))

    def test_three_requests_per_concept_per_day(self):
        self.make_bank()
        for _ in range(3):
            self.ok(*self.request())
        err = self.fails(1, *self.request())
        self.assertIn("try again tomorrow", err)

    def test_request_validates_inputs(self):
        self.make_bank()
        self.fails(1, *self.request(difficulty=6))
        self.fails(1, *self.request(concept="unknown"))
        self.fails(1, *self.request(count=0))

    def test_submitted_then_pending_then_fail(self):
        self.make_bank()
        slot = self.ok(*self.request())["slot"]
        self.ok("bank", "submitted", "--dir", self.pkg, "--quiz", slot,
                "--artifact-id", "artifact-test-1")
        pending = self.ok("bank", "pending", "--dir", self.pkg)["pending"]
        self.assertEqual(1, len(pending))
        self.assertEqual(
            {"slot": slot, "concept": "photosynthesis", "artifact_id": "artifact-test-1"},
            {k: pending[0][k] for k in ("slot", "concept", "artifact_id")},
        )
        self.assertGreaterEqual(pending[0]["minutes_pending"], 0)
        out = self.ok("bank", "fail", "--dir", self.pkg, "--quiz", slot,
                      "--reason", "status failed twice")
        self.assertEqual("failed", out["status"])
        self.assertEqual([], self.ok("bank", "pending", "--dir", self.pkg)["pending"])

    def test_submitted_requires_reserved(self):
        self.make_bank()
        slot = self.ok(*self.request())["slot"]
        self.ok("bank", "submitted", "--dir", self.pkg, "--quiz", slot, "--artifact-id", "a-1")
        self.fails(1, "bank", "submitted", "--dir", self.pkg, "--quiz", slot,
                   "--artifact-id", "a-2")

    def test_fail_refuses_unknown_and_finished_slots(self):
        self.make_bank()
        self.fails(1, "bank", "fail", "--dir", self.pkg, "--quiz", "nope-d3-1", "--reason", "x")
        slot = self.ok(*self.request())["slot"]
        self.ok("bank", "fail", "--dir", self.pkg, "--quiz", slot, "--reason", "x")
        self.fails(1, "bank", "fail", "--dir", self.pkg, "--quiz", slot, "--reason", "again")

    def test_failed_requests_still_count_against_quota(self):
        self.make_bank(daily_cap=1)
        slot = self.ok(*self.request())["slot"]
        self.ok("bank", "fail", "--dir", self.pkg, "--quiz", slot, "--reason", "rate limited")
        self.fails(1, *self.request())


if __name__ == "__main__":
    unittest.main()
