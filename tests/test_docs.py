import contextlib
import io
import re
import unittest

from sherlock_testlib import ROOT, sherlock

COMMANDS = {
    "bank init", "bank add-concept", "bank quota", "bank request", "bank submitted",
    "bank pending", "bank import", "bank fail", "student new",
    "next", "record", "close-round", "note", "status", "due",
}
DOCS = ["SKILL.md", "references/adaptive-learning.md", "README.md"]
MENTION = re.compile(r"\bsherlock (bank [a-z-]+|student [a-z-]+|[a-z][a-z-]*)")


class DocsMatchScriptTests(unittest.TestCase):
    def test_every_listed_command_exists(self):
        for command in sorted(COMMANDS):
            with self.subTest(command=command), contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as caught:
                    sherlock.main(command.split() + ["--help"])
                self.assertEqual(0, caught.exception.code)

    def test_docs_only_mention_real_commands(self):
        for name in DOCS:
            text = (ROOT / name).read_text(encoding="utf-8")
            for command in MENTION.findall(text):
                with self.subTest(doc=name, command=command):
                    self.assertIn(command, COMMANDS)

    def test_skill_documents_every_mode(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for heading in ("## Adaptive Modes", "### Diagnose mode", "### Teach mode",
                        "### Tutor mode", "### Review mode"):
            self.assertIn(heading, text)


if __name__ == "__main__":
    unittest.main()
