import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_skill", ROOT / "scripts" / "validate_skill.py"
)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)


class SkillRepositoryTests(unittest.TestCase):
    def test_repository_validator_passes(self):
        self.assertEqual([], validator.validate())

    def test_skill_frontmatter_identity(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        frontmatter = validator.parse_frontmatter(text)
        self.assertEqual("sherlock-study-boy", frontmatter["name"])
        self.assertEqual("1.0.0", frontmatter["version"])
        self.assertEqual("MIT", frontmatter["license"])

    def test_workflow_steps_are_contiguous(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        numbers = [
            int(line.split(".", 1)[0].removeprefix("### "))
            for line in text.splitlines()
            if line.startswith("### ") and line[4:5].isdigit()
        ]
        self.assertEqual(list(range(1, 10)), numbers)

    def test_documented_download_formats_are_current(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        expected = {
            "study-guide.md",
            "video.mp4",
            "slides.pdf",
            "flashcards.json",
            "quiz.json",
            "audio-overview.m4a",
            "mind-map.json",
            "infographic.png",
        }
        for filename in expected:
            self.assertIn(filename, text)


if __name__ == "__main__":
    unittest.main()
