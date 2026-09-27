import json
import os
import subprocess
import sys
import unittest
from unittest import mock

from sherlock_testlib import ROOT, PackageTestCase, run, sherlock


class StorageTests(PackageTestCase):
    def test_save_json_leaves_original_intact_when_replace_fails(self):
        path = self.pkg / "data.json"
        sherlock.save_json(path, {"schema_version": 1, "value": "original"})
        with mock.patch.object(sherlock.os, "replace", side_effect=OSError("disk full")):
            with self.assertRaises(OSError):
                sherlock.save_json(path, {"schema_version": 1, "value": "new"})
        self.assertEqual("original", json.loads(path.read_text())["value"])
        self.assertEqual(["data.json"], sorted(os.listdir(self.pkg)))

    def test_unknown_schema_version_exits_2(self):
        self.make_bank()
        bank_path = self.pkg / "quiz-bank" / "bank.json"
        bank = json.loads(bank_path.read_text())
        bank["schema_version"] = 99
        bank_path.write_text(json.dumps(bank))
        self.fails(2, "bank", "quota", "--dir", self.pkg)

    def test_corrupt_json_exits_2(self):
        (self.pkg / "quiz-bank").mkdir()
        (self.pkg / "quiz-bank" / "bank.json").write_text("{not json")
        self.fails(2, "bank", "quota", "--dir", self.pkg)

    def test_missing_package_directory_exits_1(self):
        self.fails(1, "bank", "init", "--dir", self.pkg / "missing", "--notebook-id", "nb-test")

    def test_usage_error_exits_1(self):
        with self.assertRaises(SystemExit) as caught:
            run("bank", "init", "--dir", self.pkg)  # missing --notebook-id
        self.assertEqual(1, caught.exception.code)

    def test_bad_today_exits_1(self):
        self.make_bank()
        self.fails(1, "bank", "quota", "--dir", self.pkg, "--today", "26/09/2026")


class BankSetupTests(PackageTestCase):
    def test_init_creates_bank(self):
        out = self.ok("bank", "init", "--dir", self.pkg, "--notebook-id", "nb-test")
        self.assertEqual({"notebook_id": "nb-test", "daily_cap": 20}, {
            k: out[k] for k in ("notebook_id", "daily_cap")})
        bank = json.loads((self.pkg / "quiz-bank" / "bank.json").read_text())
        self.assertEqual(
            {"schema_version": 1, "notebook_id": "nb-test", "daily_cap": 20,
             "concepts": {}, "quizzes": []},
            bank,
        )

    def test_init_twice_is_refused(self):
        self.make_bank()
        self.fails(1, "bank", "init", "--dir", self.pkg, "--notebook-id", "nb-test")

    def test_init_rejects_zero_cap(self):
        self.fails(1, "bank", "init", "--dir", self.pkg, "--notebook-id", "nb-test",
                   "--daily-cap", 0)

    def test_add_concept_stores_focus(self):
        self.make_bank(("organ-systems", "Organ Systems", 9))
        bank = json.loads((self.pkg / "quiz-bank" / "bank.json").read_text())
        self.assertEqual(
            {"rank": 9, "name": "Organ Systems", "focus": "Organ Systems"},
            bank["concepts"]["organ-systems"],
        )

    def test_add_concept_rejects_long_focus(self):
        self.make_bank()
        err = self.fails(1, "bank", "add-concept", "--dir", self.pkg, "--slug", "organs",
                         "--name", "Organs", "--rank", 2,
                         "--focus", "Human Organ Systems Coordination And Excretion")
        self.assertIn("1-5 words", err)

    def test_add_concept_rejects_duplicate_and_bad_slug(self):
        self.make_bank()
        self.fails(1, "bank", "add-concept", "--dir", self.pkg, "--slug", "photosynthesis",
                   "--name", "Again", "--focus", "Again", "--rank", 2)
        self.fails(1, "bank", "add-concept", "--dir", self.pkg, "--slug", "Photo Synthesis",
                   "--name", "Bad", "--focus", "Bad", "--rank", 2)

    def test_quota_starts_empty(self):
        self.make_bank()
        out = self.ok("bank", "quota", "--dir", self.pkg, "--today", self.TODAY)
        self.assertEqual(
            {"today": self.TODAY, "used_today": 0, "cap": 20, "remaining": 20}, out
        )


class EntryPointTests(PackageTestCase):
    def test_script_runs_as_a_program(self):
        result = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "sherlock.py"), "bank", "init",
             "--dir", str(self.pkg), "--notebook-id", "nb-test"],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("nb-test", json.loads(result.stdout)["notebook_id"])


if __name__ == "__main__":
    unittest.main()
