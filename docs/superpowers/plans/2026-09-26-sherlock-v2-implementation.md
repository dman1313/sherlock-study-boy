# Sherlock Study Boy v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. If you do not have those skills, follow **How to execute this plan** below; it is sufficient on its own.

**Goal:** Repair the Sherlock Study Boy skill (v2.0.1), then add working adaptive tutoring modes backed by a tested bookkeeping script (v2.1.0).

**Architecture:** The skill stays an instruction file (`SKILL.md`) that an agent follows while driving the `nlm` NotebookLM CLI. Milestone 1 restores the clean v1 instructions and fixes the validator so CI passes. Milestone 2 adds `scripts/sherlock.py`, a single standard-library Python script that owns all adaptive-mode state (quiz bank, student progress, grading, review schedule, quota); `SKILL.md` tells the agent when to call it.

**Tech Stack:** Python standard library only (`argparse`, `json`, `unittest`), `git`, GitHub Actions, the `nlm` CLI (`notebooklm-mcp-cli` 0.9.14; used only in Task 14).

**Spec:** `docs/superpowers/specs/2026-09-26-sherlock-repair-and-adaptive-modes-design.md`. Read §1–§4 before starting. When this plan and the spec disagree, this plan wins: it was written after the spec and every code block in it has been executed and tested.

## Global Constraints

- **Python compatibility:** code must run on Python 3.9 or newer. This Mac's `/usr/bin/python3` is 3.9.6; CI runs 3.10 and 3.12. Every script starts with `from __future__ import annotations`. Do not use `match`, `zip(strict=...)`, or `X | Y` outside annotations.
- **Standard library only.** Do not `pip install` anything and do not add dependency files.
- **Forbidden content, in every file git would commit (including tests and this plan):** machine-specific home paths (`/Users/<name>/` or `/home/<name>/` with a real name), real-looking UUIDs, GitHub tokens, Google API keys, private keys. Use `~` in paths and placeholders such as `<notebook-id>`, `nb-test`, `artifact-test-1`. The validator (`python3 scripts/validate_skill.py`) enforces this.
- **Notebook and artifact IDs are UUIDs.** Never paste a real one into any repository file, including the Task 14 run log.
- **`SKILL.md` frontmatter:** `description` is at most 60 characters and ends with a period. Headings that start `### ` followed by a digit are reserved for the nine procedure steps; a test requires them to be exactly 1–9.
- **No NotebookLM calls** (`nlm ... create`, `source add`, `download`, `query`) except in Task 14, and only after the human approves. The test suite never calls `nlm`.
- **Branch:** work on `sdd/v2-repair-and-adaptive-modes` until Task 5; Task 5 says what to use afterwards. Never push, open a pull request, tag, or merge without the human's explicit approval (Tasks 5 and 15 are human checkpoints).
- **Stay in the repository.** Do not change files outside it, except: the study package directory in Task 14 (after approval), and the Hermes copy of the skill in Task 5 Step 7 and Task 15 Step 6 (the human chose plain-copy updates on 2026-09-27).
- **Nothing else pushes to this repository during the build.** The human has paused the Hermes SWF (software factory) profile, which made the earlier commits. If `main` moves unexpectedly, stop and tell the human.
- **Run every command from the repository root** (`sherlock-study-boy/`).

## Before you start

- [ ] Ask the human to confirm, word for word: "Is the Hermes SWF (software factory) profile paused for sherlock-study-boy?" Do not start until they say yes.
- [ ] Check that `main` has not moved since this plan was written:

```bash
git fetch origin
git rev-parse --short origin/main
git branch --show-current
```

Expected: `61bf61d` and `sdd/v2-repair-and-adaptive-modes`. If `origin/main` is anything else, stop and tell the human that someone changed `main`.

## How to execute this plan

1. Do the tasks in order. Do not skip ahead; later tasks depend on names created earlier.
2. In each task, do the steps in order and tick each checkbox as you go.
3. Copy code **exactly**. Do not rename, reformat, reorder, or "improve" anything. Other tasks and tests depend on exact names.
4. After every command, compare the result with **Expected**. If it differs, stop and fix only the step you just did. If you cannot make it match, stop and report the command, the expected result, and the actual output. Do not change tests to make them pass.
5. "Insert above the marker line" means: find the line exactly once in the file, and paste the block immediately before it, leaving the marker line in place. Keep the block's indentation exactly as shown. In `scripts/sherlock.py`, leave two blank lines between an inserted function block and the `# --- CLI` line, and one blank line between an inserted parser block and `    return parser`.
6. Commit at the end of each task with the message given. Commit only the files the task names.

## File map

| File | Responsibility | Tasks |
|---|---|---|
| `scripts/validate_skill.py` | Offline structural and leak checks for the repository | 1, 12, 13 |
| `tests/test_validator.py` | Regression tests for the validator's file scanning | 1 |
| `SKILL.md` | The skill instructions an agent follows | 2, 13 |
| `tests/test_skill.py` | Frontmatter, step numbering, formats, version/changelog match | 2 |
| `CHANGELOG.md` | Release notes | 2, 13 |
| `references/nlm-cli-quirks.md` | `nlm` syntax, formats, and failure notes | 3 |
| `references/pipeline-patterns.md` | Per-concept generation patterns | 3 |
| `.github/workflows/validate.yml` | CI: validator and tests on Python 3.10 and 3.12 | 4 |
| `scripts/sherlock.py` | All adaptive-mode state: bank, students, grading, rules, quota | 6–11 |
| `tests/sherlock_testlib.py` | Shared test helpers (not a test module) | 6, 8, 10 |
| `tests/test_sherlock_*.py` | Tests for `sherlock.py`, one file per task | 6–11 |
| `tests/fixtures/quiz-*.json` | Quiz files in the exact `nlm download quiz --format json` shape | 8 |
| `references/adaptive-learning.md` | Reference manual for the adaptive modes and `sherlock.py` | 12 |
| `references/privacy-and-safety.md` | Privacy rules, including student data | 12 |
| `.gitignore` | Keeps student progress and quiz banks out of git | 12 |
| `tests/test_docs.py` | Docs only name commands that exist | 13 |
| `README.md` | User-facing overview | 13 |
| `docs/runs/<date>-e2e.md` | Record of the live end-to-end run | 14 |

---

# Milestone 1 — Repair (v2.0.1)

### Task 1: Validator scans only files git would commit

**Why:** CI has never passed. The validator reads every file under the repository, including `scripts/__pycache__/*.pyc` that Python creates during the test run. That bytecode contains the CI machine's absolute home path, which trips the validator's own "machine-specific path" rule. The fix scans only files git would commit: tracked files plus new files that `.gitignore` does not exclude.

**Files:**
- Modify (full replacement): `scripts/validate_skill.py`
- Create: `tests/test_validator.py`

**Interfaces:**
- Produces: `walk_files(root: Path) -> list[Path]`, `candidate_files(root: Path) -> list[Path]`, `read_text_or_none(path: Path) -> str | None` in `scripts/validate_skill.py`. Forbidden-content errors now name the file: `forbidden content found: <label> in <relative path>`.

- [ ] **Step 1: Write the failing test.** Create `tests/test_validator.py` with exactly this content:

```python
import importlib.util
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "validate_skill", ROOT / "scripts" / "validate_skill.py"
)
validator = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(validator)

# Built at runtime so this test file never contains the pattern it checks for.
MACHINE_PATH = "/" + "home" + "/ci-runner/work/sherlock/"


class WalkFilesTests(unittest.TestCase):
    def test_walk_files_skips_cache_and_vcs_directories(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "keep").mkdir()
            (root / "keep" / "notes.md").write_text("ok", encoding="utf-8")
            (root / "__pycache__").mkdir()
            (root / "__pycache__" / "x.pyc").write_text(MACHINE_PATH, encoding="utf-8")
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text(MACHINE_PATH, encoding="utf-8")
            found = [p.relative_to(root).as_posix() for p in validator.walk_files(root)]
            self.assertEqual(["keep/notes.md"], found)

    def test_read_text_or_none_skips_binary(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "image.png"
            path.write_bytes(b"\x89PNG\r\n\x1a\n\xff\xfe")
            self.assertIsNone(validator.read_text_or_none(path))


@unittest.skipUnless(shutil.which("git") and (ROOT / ".git").exists(), "needs a git checkout")
class CandidateFilesTests(unittest.TestCase):
    def test_ignored_pycache_is_not_scanned(self):
        cache_dir = ROOT / "scripts" / "__pycache__"
        cache_dir.mkdir(exist_ok=True)
        probe = cache_dir / "regression-probe.pyc"
        probe.write_text(MACHINE_PATH, encoding="utf-8")
        try:
            self.assertNotIn(probe, validator.candidate_files(ROOT))
            self.assertFalse(
                [e for e in validator.validate() if "__pycache__" in e],
                "validator scanned an ignored __pycache__ file",
            )
        finally:
            probe.unlink()

    def test_new_untracked_file_is_scanned(self):
        probe = ROOT / "untracked-probe.md"
        probe.write_text(MACHINE_PATH, encoding="utf-8")
        try:
            self.assertIn(probe, validator.candidate_files(ROOT))
            self.assertTrue(
                [e for e in validator.validate() if "untracked-probe.md" in e],
                "validator missed forbidden content in a new, unstaged file",
            )
        finally:
            probe.unlink()


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_validator.py' -v`
Expected: `FAILED (errors=4)`, with errors like `AttributeError: module 'validate_skill' has no attribute 'walk_files'` (or `... 'candidate_files'`, `... 'read_text_or_none'`).

- [ ] **Step 3: Replace the validator.** Overwrite `scripts/validate_skill.py` with exactly this content:

```python
#!/usr/bin/env python3
"""Offline structural validator for the Sherlock Study Boy skill."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "SKILL.md"

REQUIRED_FILES = [
    SKILL,
    ROOT / "README.md",
    ROOT / "LICENSE",
    ROOT / ".gitignore",
    ROOT / "references" / "privacy-and-safety.md",
    ROOT / "references" / "nlm-cli-quirks.md",
    ROOT / "references" / "pipeline-patterns.md",
]

FORBIDDEN_PATTERNS = {
    "machine-specific user path": re.compile(r"/(?:Users|home)/[A-Za-z0-9._-]+/"),
    "real UUID": re.compile(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b",
        re.IGNORECASE,
    ),
    "GitHub token": re.compile(r"\bgh[opsu]_[A-Za-z0-9]{20,}\b"),
    "Google API key": re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b"),
    "private key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
}

REQUIRED_SNIPPETS = [
    "nlm login --check",
    "nlm video create <notebook-id>",
    "nlm studio status <notebook-id>",
    "nlm download video <notebook-id> --id <artifact-id>",
    "references/privacy-and-safety.md",
    "references/nlm-cli-quirks.md",
]


def parse_frontmatter(text: str) -> dict[str, str]:
    if not text.startswith("---\n"):
        raise AssertionError("SKILL.md must start with YAML frontmatter")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise AssertionError("SKILL.md frontmatter is not closed")
    values: dict[str, str] = {}
    for line in text[4:end].splitlines():
        if line and not line.startswith((" ", "\t")) and ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    return values


SKIP_DIRS = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules"}


def walk_files(root: Path) -> list[Path]:
    """Every file under root, skipping VCS, cache, and environment directories."""
    files = []
    for path in sorted(root.rglob("*")):
        rel_parts = path.relative_to(root).parts
        if any(part in SKIP_DIRS for part in rel_parts):
            continue
        if path.is_file():
            files.append(path)
    return files


def candidate_files(root: Path) -> list[Path]:
    """Files git would commit: tracked plus untracked-but-not-ignored.

    Falls back to walk_files() when root is not inside a git work tree
    (for example, a copy installed without .git).
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--cached", "--others",
             "--exclude-standard"],
            capture_output=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return walk_files(root)
    names = [name for name in result.stdout.decode("utf-8").split("\0") if name]
    files = [root / name for name in names if (root / name).is_file()]
    return files or walk_files(root)


def read_text_or_none(path: Path) -> str | None:
    """Return the file's UTF-8 text, or None for binary/unreadable files."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def validate() -> list[str]:
    errors: list[str] = []
    for path in REQUIRED_FILES:
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"missing or empty required file: {path.relative_to(ROOT)}")

    if not SKILL.is_file():
        return errors

    text = SKILL.read_text(encoding="utf-8")
    try:
        frontmatter = parse_frontmatter(text)
    except AssertionError as exc:
        errors.append(str(exc))
        return errors

    for key in ("name", "description", "version", "author", "license", "platforms"):
        if not frontmatter.get(key):
            errors.append(f"missing frontmatter field: {key}")

    description = frontmatter.get("description", "").strip('"')
    if len(description) > 60:
        errors.append(f"frontmatter description exceeds 60 chars: {len(description)}")
    if description and not description.endswith("."):
        errors.append("frontmatter description must end with a period")

    for snippet in REQUIRED_SNIPPETS:
        if snippet not in text:
            errors.append(f"missing required instruction: {snippet}")

    for path in candidate_files(ROOT):
        text = read_text_or_none(path)
        if text is None:
            continue
        for label, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(text):
                errors.append(
                    f"forbidden content found: {label} in {path.relative_to(ROOT)}"
                )

    referenced = set(re.findall(r"references/[A-Za-z0-9._/-]+\.md", text))
    for rel in sorted(referenced):
        if not (ROOT / rel).is_file():
            errors.append(f"broken reference: {rel}")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("VALIDATION FAILED")
        for error in errors:
            print(f"- {error}")
        return 1
    print("VALIDATION PASSED")
    print(f"- skill: {SKILL}")
    print(f"- required files: {len(REQUIRED_FILES)}")
    print(f"- forbidden-pattern checks: {len(FORBIDDEN_PATTERNS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the new tests and confirm they pass.**

Run: `python3 -m unittest discover -s tests -p 'test_validator.py' -v`
Expected: `Ran 4 tests` and `OK`.

The full suite still fails at this point because `SKILL.md` is broken; Task 2 fixes that. Do not try to fix it here.

- [ ] **Step 5: Commit.**

```bash
git add scripts/validate_skill.py tests/test_validator.py
git commit -m "fix(validator): scan only files git would commit"
```

---

### Task 2: Restore the v1 `SKILL.md` as 2.0.1

**Why:** Commit `61bf61d` (2.0.0) replaced the clean v1 `SKILL.md` with an older draft (VPS-only steps, steps out of order, a real notebook ID, stale download formats, a link to a missing file) and appended K3 adaptive modes that were never implemented. Restore v1 exactly, bump the version, and withdraw the unimplemented adaptive docs until Milestone 2.

**Files:**
- Modify: `SKILL.md` (restored from git history)
- Delete: `references/adaptive-learning.md` (recreated in Task 12)
- Modify (full replacement): `tests/test_skill.py`
- Modify: `CHANGELOG.md`

**Interfaces:**
- Produces: `SKILL.md` frontmatter `version: 2.0.1`. A test that keeps the frontmatter version equal to the newest `## [x.y.z]` heading in `CHANGELOG.md`. Every later release must bump both.

- [ ] **Step 1: Write the failing test.** Overwrite `tests/test_skill.py` with exactly this content:

```python
import importlib.util
import re
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
        self.assertEqual("MIT", frontmatter["license"])

    def test_version_matches_newest_changelog_entry(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        version = validator.parse_frontmatter(text)["version"]
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        newest = re.search(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.MULTILINE)
        self.assertIsNotNone(newest, "CHANGELOG.md has no '## [x.y.z]' heading")
        self.assertEqual(newest.group(1), version)

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
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_skill.py' -v`
Expected: `FAILED`. `test_repository_validator_passes` lists validator errors, and `test_workflow_steps_are_contiguous` fails with `Lists differ: [1, 2, 3, 4, 5, 6, 7, 8, 9] != []`.

- [ ] **Step 3: Restore `SKILL.md` from v1 and set the version.**

```bash
git show c3d3033:SKILL.md > SKILL.md
sed -i.bak 's/^version: 1.0.0$/version: 2.0.1/' SKILL.md && rm SKILL.md.bak
head -7 SKILL.md
```

Expected output of `head -7`:

```text
---
name: sherlock-study-boy
description: Turn curriculum files into NotebookLM study media.
version: 2.0.1
author: Dwayne Primeau, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
```

- [ ] **Step 4: Remove the withdrawn adaptive-learning reference.**

```bash
git rm -q references/adaptive-learning.md
```

- [ ] **Step 5: Add the 2.0.1 changelog entry.** In `CHANGELOG.md`, insert the following block above the marker line `## [2.0.0] - 2026-09-13`. If today's date is not 2026-09-26, use today's date in `YYYY-MM-DD` form in the heading.

````markdown
## [2.0.1] - 2026-09-26

### Fixed
- `SKILL.md` restored from 1.0.0. The 2.0.0 release had replaced it with a pre-1.0 draft
  (VPS-only instructions, out-of-order steps, a real notebook ID, stale download formats,
  and a link to a missing reference file).
- The repository validator now scans only files git would commit, so Python's
  `__pycache__` no longer trips the machine-specific-path check. CI passes for the first time.

### Removed
- The K3/Nebius adaptive-mode descriptions from 2.0.0. They were documented but never
  implemented. Working adaptive modes arrive in 2.1.0.
````

- [ ] **Step 6: Run the validator and the full suite.**

Run: `python3 scripts/validate_skill.py`
Expected: first line `VALIDATION PASSED`.

Run: `python3 -m unittest discover -s tests -v`
Expected: `Ran 9 tests` and `OK`.

- [ ] **Step 7: Commit.**

```bash
git add SKILL.md tests/test_skill.py CHANGELOG.md
git commit -m "fix: restore v1 SKILL.md as 2.0.1"
```

(`git rm` already staged the deletion; it is included in this commit.)

---

### Task 3: Merge real-session `nlm` notes into the references

**Why:** The copy of this skill installed in Hermes (`~/.hermes/skills/research/sherlock-study-boy`) holds notes from real runs that never reached the repository: exact error messages, empty-artifact sizes, the quiz JSON format, and lessons from a 10-concept run. The merged text below keeps the repository's validated 0.9.14 guidance and adds those notes with all IDs and machine paths removed. Do not read or copy from the Hermes directory yourself; use the text below.

**Files:**
- Modify (full replacement): `references/nlm-cli-quirks.md`
- Modify (full replacement): `references/pipeline-patterns.md`

**Interfaces:**
- Produces: the "Quiz JSON format" section in `references/nlm-cli-quirks.md`, which `references/adaptive-learning.md` (Task 12) links to.

- [ ] **Step 1: Replace `references/nlm-cli-quirks.md`** with exactly this content:

````markdown
# NLM CLI Quirks

Validated against `notebooklm-mcp-cli` / `nlm` 0.9.14. NotebookLM uses unofficial endpoints, so verify questionable syntax with `nlm <group> <command> --help`. Add new quirks here as they surface in real sessions.

## Current output formats

| Artifact | Downloader | Default/required output |
|---|---|---|
| Report | `nlm download report` | Markdown (`.md`) |
| Video | `nlm download video` | MP4 (`.mp4`) |
| Slides | `nlm download slide-deck` | PDF or PPTX |
| Flashcards | `nlm download flashcards` | JSON, Markdown, or HTML |
| Quiz | `nlm download quiz` | JSON, Markdown, or HTML |
| Audio | `nlm download audio` | M4A |
| Mind map | `nlm download mind-map` | JSON |
| Infographic | `nlm download infographic` | PNG |

All specific artifact downloads use `--id <artifact-id>`. Do not pass the artifact ID positionally:

```text
nlm download report <notebook-id> --id <artifact-id> --output study-guide.md   # correct
nlm download report <notebook-id> <artifact-id> --output study-guide.md        # fails
```

The mind-map downloader is hyphenated (`mind-map`). `nlm studio status` can list a mind map with `type: "flashcards"`; if `nlm download mind-map` fails for that artifact, try `nlm download flashcards <notebook-id> --id <mind-map-artifact-id>`.

## Difficulty types differ

```text
nlm flashcards create <notebook-id> --difficulty medium --confirm
nlm quiz create <notebook-id> --difficulty 3 --confirm
```

Flashcard difficulty is `easy`, `medium`, or `hard`. Quiz difficulty is an integer from 1 to 5. The wrong type fails with messages like:

```text
Error: Invalid value for '--difficulty' / '-d': 'medium' is not a valid integer.   # quiz given a word
Error: Unknown difficulty '3'. Valid options: easy, hard, medium                     # flashcards given a number
```

## Quiz JSON format

`nlm download quiz <notebook-id> --id <artifact-id> --format json` writes (per `nlm` 0.9.14's `core/download.py`):

```json
{
  "title": "Quiz title",
  "questions": [
    {
      "question": "Question text",
      "answerOptions": [
        { "text": "Option A", "isCorrect": false },
        { "text": "Option B", "isCorrect": true }
      ],
      "hint": "Optional hint"
    }
  ]
}
```

The downloader passes NotebookLM's question objects through unchanged, so extra fields (for example a per-option `rationale`) may appear. Only `question`, `answerOptions[].text`, `answerOptions[].isCorrect`, and `hint` are confirmed. `nlm quiz create ... --json` prints `{"artifact_type": "quiz", "artifact_id": "...", "status": "in_progress", ...}`.

## Focus phrases

Use a short topic phrase (two to five words) for focused generations:

```text
--focus "Organ Systems"
```

Long prompts and parenthetical curriculum-objective text have produced empty or failed artifacts. In one real run, the focus "Human Organ Systems (Coordination & Excretion)" produced empty flashcards and videos stuck in `unknown`. Keep the full concept label and a separate short `focus` value:

```json
{ "rank": 9, "name": "Human Organ Systems (Coordination & Excretion)", "focus": "Organ Systems" }
```

## Generation status

- Poll with `nlm studio status <notebook-id> --json --full`. For one artifact, add `--artifact-id <artifact-id>`.
- Status values are `in_progress`, `completed`, `failed`, and `unknown`.
- Video may temporarily report `unknown`; wait 3–5 minutes before deciding it failed. Do not download while status is `unknown`.
- A video can move from `in_progress` to `failed` between polls. That is a real failure: resubmit, and record the new artifact ID, which differs from the old one.
- Slides can fail server-side with no CLI error and succeed on one retry.
- Audio can time out while server-side work continues; check studio status before resubmitting.

## Rate limits

Video and slides often hit:

```text
Error: Rate limited — API error (code 8): ...UserDisplayableError
```

Stop after three bounded attempts, move on to other artifacts, and come back later. On paid tiers the limit usually eases after 10–15 minutes; per-minute burst limits still apply.

## Audio

NotebookLM delivers AAC audio in an MP4 container, and the CLI refuses an `.mp3` output name:

```text
Error: NotebookLM delivers AAC audio in an MP4 container; cannot honor '.mp3' suffix.
```

Download as `.m4a`. If MP3 is required, transcode locally: `ffmpeg -i audio-overview.m4a -acodec libmp3lame -q:a 2 audio-overview.mp3`.

`httpx.ReadTimeout` on `nlm audio create` is common on the first attempt; check studio status, then retry once. Paid tiers can produce two audio overviews (two `type: "audio"` entries); both are distinct and can be downloaded.

## Empty artifacts

A successful download command does not prove useful content.

- Flashcards and quizzes must parse as JSON and contain non-empty collections. Known empty stubs: 46 bytes (`[]`) and 79 bytes (`{"cards":[]}`, seen with long focus phrases). Treat any flashcard file under 200 bytes as suspect.
- Markdown study guides should exceed 500 characters and differ from other focused guides.
- Slides should have a PDF signature and exceed 100 KB.
- Videos should have an MP4-compatible `ftyp` box and exceed 1 MB.

## Focused study guides

Use `nlm notebook query` for concept-focused guides. `nlm report create --prompt` controls custom report instructions but is not a dependable topic filter across large notebooks: in one real run, ten "focused" reports were byte-identical. Reports whose `custom_instructions` is `null` in studio status are generic and cannot be matched to a concept.

`nlm notebook query <notebook-id> --json "<prompt>"` nests the answer at `.response.answer` or `.value.answer`. Queries can take 30–90 seconds; allow a 120-second timeout.

## Authentication

Run `nlm login --check` before a batch. If it fails, the user must renew authentication interactively with `nlm login`. Never ask the user to paste cookies into chat or store them in the repository.
````

- [ ] **Step 2: Replace `references/pipeline-patterns.md`** with exactly this content:

````markdown
# Per-Concept Pipeline Patterns

Use this only after the notebook-level video or full package is complete and the user explicitly requests deep dives.

## Lessons from a real 10-concept run

| Artifact | What was tried | What happened |
|---|---|---|
| Study guide | `nlm report create --prompt "Focus on X"` | All ten guides were byte-identical. `--prompt` is a style hint, not a content filter. |
| Flashcards | `--focus "Full Concept Name (Parenthetical)"` | Every file was a 79-byte empty stub. |
| Slides | `--focus "Full Concept Name"` | Only 3 of 10 generated; the rest failed silently on the first attempt. |
| Video | `--focus "Full Concept Name"` | Mostly worked; some stuck in `unknown`. |

The fixes below come from that run.

## Generation order

1. Focused study guide via `nlm notebook query` (fastest; runs as a query, not a studio artifact)
2. Flashcards with a short `--focus`
3. Slides with the same short `--focus`
4. Video last because it is slowest (3–7 minutes) and most rate-limit prone

## Focused study guide

```text
nlm notebook query <notebook-id> --json "Focus on <topic> for <course and level>. Give me: 1. Key definitions 2. Core processes 3. Common exam questions 4. Diagrams to memorize 5. Common mistakes."
```

Save the answer from `.response.answer` or `.value.answer` as Markdown. Allow a 120-second timeout.

## Progress file

Keep operational state outside the skill repository, in the package output directory:

```json
{
  "notebook_id": "<notebook-id>",
  "concepts": [
    {
      "rank": 1,
      "name": "Human Organ Systems and Coordination",
      "focus": "Organ Systems",
      "status": "pending",
      "artifacts": {}
    }
  ]
}
```

Allowed status values: `pending`, `generating`, `completed`, `failed`, `skipped`. Always pass the `focus` value, never the `name`, to `--focus`.

## Bounded retry policy

- Poll every 60 seconds.
- Treat `unknown` as in progress for up to ten minutes.
- Retry slides once after a confirmed `failed` status.
- Retry rate-limited video generation no more than three times with increasing waits.
- Record failure and move on; never use an unbounded loop. A scheduled pipeline should mark a concept `failed` after a fixed number of runs rather than retrying forever.

## Validation

- Study guide: >500 characters and not byte-identical to another concept guide (compare hashes).
- Flashcards: valid JSON, at least one card, and at least 200 bytes.
- Slides: PDF signature and >100 KB.
- Video: MP4-compatible signature and >1 MB. Healthy focused videos are usually over 10 MB, so a small file deserves a manual look.

A concept is `completed` only when every artifact requested for that concept passes its validation. Partial success remains visible in the artifact map.
````

- [ ] **Step 3: Run the validator and the full suite.**

Run: `python3 scripts/validate_skill.py`
Expected: first line `VALIDATION PASSED`.

Run: `python3 -m unittest discover -s tests`
Expected: `OK`.

- [ ] **Step 4: Commit.**

```bash
git add references/nlm-cli-quirks.md references/pipeline-patterns.md
git commit -m "docs: merge real-session nlm notes into references"
```

---

### Task 4: CI on Python 3.10 and 3.12 with current actions

**Why:** The README promises Python 3.10+, but CI only tested 3.12. The `actions/checkout@v4` and `actions/setup-python@v5` actions trigger Node 20 deprecation warnings; v7 of both is current.

**Files:**
- Modify (full replacement): `.github/workflows/validate.yml`

- [ ] **Step 1: Replace `.github/workflows/validate.yml`** with exactly this content:

```yaml
name: Validate skill

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    strategy:
      fail-fast: false
      matrix:
        python-version: ["3.10", "3.12"]
    steps:
      - uses: actions/checkout@v7
      - uses: actions/setup-python@v7
        with:
          python-version: ${{ matrix.python-version }}
      - name: Validate skill structure and safety
        run: python3 scripts/validate_skill.py
      - name: Run tests
        run: python3 -m unittest discover -s tests -v
```

- [ ] **Step 2: Check the YAML parses.**

Run: `python3 -c "import json, yaml; print(json.dumps(yaml.safe_load(open('.github/workflows/validate.yml'))['jobs']['validate']['strategy']))"`
Expected: `{"fail-fast": false, "matrix": {"python-version": ["3.10", "3.12"]}}`. If it prints `No module named 'yaml'`, skip this step; CI checks the file in Task 5.

- [ ] **Step 3: Run the validator.**

Run: `python3 scripts/validate_skill.py`
Expected: first line `VALIDATION PASSED`.

- [ ] **Step 4: Commit.**

```bash
git add .github/workflows/validate.yml
git commit -m "ci: test on Python 3.10 and 3.12 with current actions"
```

---

### Task 5: Release checkpoint for v2.0.1 (human approval required)

**Why:** Milestone 1 is a complete, shippable repair. Publishing it is outward-facing, so the human decides.

- [ ] **Step 1: Final local check.**

```bash
python3 scripts/validate_skill.py
python3 -m unittest discover -s tests
git status --short
```

Expected: `VALIDATION PASSED`, `OK`, and no output from `git status --short`.

- [ ] **Step 2: STOP and ask the human, word for word:**

> Milestone 1 (v2.0.1 repair) is complete and passes locally. May I push branch `sdd/v2-repair-and-adaptive-modes` to GitHub and open a pull request into `main`?

Do nothing further until the human says yes.

- [ ] **Step 3: On approval, push and open the pull request.** Before pushing, confirm nobody else has changed `main`:

```bash
git fetch origin
git log --oneline HEAD..origin/main
```

Expected: no output. If it lists commits, stop and tell the human; do not push.

```bash
git push -u origin sdd/v2-repair-and-adaptive-modes
gh pr create --base main --title "v2.0.1: restore SKILL.md and fix CI" --body "Restores the v1 SKILL.md that 2.0.0 overwrote, withdraws the unimplemented K3 adaptive-mode docs, fixes the validator so CI can pass, merges real-session nlm notes into references, and runs CI on Python 3.10 and 3.12. Includes the spec and implementation plan for v2.1.0 under docs/superpowers/."
```

- [ ] **Step 4: Wait for CI.** Run `gh pr checks --watch`. Expected: both `validate (3.10)` and `validate (3.12)` pass. If either fails, read the log with `gh run view --log-failed`, report it to the human, and stop.

- [ ] **Step 5: Ask the human to merge the pull request.** Do not merge it yourself unless they tell you to.

- [ ] **Step 6: After the merge, and only with the human's approval, tag the release and start the Milestone 2 branch.**

```bash
git checkout main
git pull
git tag v2.0.1
git push origin v2.0.1
git checkout -b sdd/v2.1-adaptive-modes
```

- [ ] **Step 7: Update the Hermes copy of the skill with a plain copy (the human chose this).** Hermes on this Mac loads the skill from `~/.hermes/skills/research/sherlock-study-boy`. That folder is not a git checkout and is included in the human's hermes-brain backups, so keep it a plain folder: back it up **outside** `~/.hermes/skills/` (a backup inside it would load as a second skill with the same name), then mirror the released files into it. Run from the repository root right after Step 6; the new branch starts at the `v2.0.1` commit, so the files are the released ones:

```bash
git describe --tags --exact-match
cp -R ~/.hermes/skills/research/sherlock-study-boy ~/sherlock-study-boy-hermes-backup-$(date +%Y%m%d)-v2.0.1
rsync -a --delete --exclude .git --exclude .github --exclude __pycache__ --exclude docs --exclude tests --exclude .gitignore ./ ~/.hermes/skills/research/sherlock-study-boy/
diff -rq --exclude=.git --exclude=.github --exclude=__pycache__ --exclude=docs --exclude=tests --exclude=.gitignore . ~/.hermes/skills/research/sherlock-study-boy && echo identical
head -4 ~/.hermes/skills/research/sherlock-study-boy/SKILL.md
```

Expected: `git describe` prints `v2.0.1`; `diff` prints only `identical`; the `head` output includes `version: 2.0.1`. `--delete` removes files the release no longer has (the old `references/pipeline-v2-patterns.md` and the empty `web/` folder); the backup keeps them. If the backup folder name already exists, add a suffix such as `-2`. Tell the human where the backup is and to start a new Hermes session so the skill reloads.

---

# Milestone 2 — Adaptive modes (v2.1.0)

**Background for Tasks 6–11.** The adaptive modes are driven by one script, `scripts/sherlock.py`. It is a command-line tool with subcommands; every command takes `--dir <study package directory>`, prints one JSON object on success, and on failure prints one line starting `sherlock:` to stderr and exits 1 (bad input or refused action) or 2 (unreadable data or unknown `schema_version`). Task 6 creates the file with two marker lines that later tasks insert code above:

- `# --- CLI -----…` (the section divider above the command-line code): **insert new functions above this line.**
- `    return parser` (the last line of `build_parser()`, indented 4 spaces): **insert new parser registrations above this line.**

Each task adds one test file. Test helpers live in `tests/sherlock_testlib.py`, which is not a test module (its name does not start with `test_`). Tests load `scripts/sherlock.py` by path, the same way `tests/test_skill.py` loads the validator.

Section 6 of the spec describes the behavior. The only deliberate differences from the spec are: the command is `bank add-concept` (not `bank concept add`); `bank request` also refuses a 4th request for one concept on one day; the bank records `requested` (date) and `submitted_at` (timestamp) separately; and raw downloads go to `<pkg>/quiz-bank/downloads/`.

### Task 6: `sherlock.py` skeleton, storage, and bank setup

**Files:**
- Create: `scripts/sherlock.py`
- Create: `tests/sherlock_testlib.py`
- Test: `tests/test_sherlock_store.py`

**Interfaces:**
- Produces, in `scripts/sherlock.py`: constants `SCHEMA_VERSION = 1`, `LADDER_DAYS`, `MASTERED_AT`, `PARTIAL_AT`, `DIAGNOSE_MASTERED_STEP`, `DEFAULT_DAILY_CAP = 20`, `DEFAULT_QUIZ_COUNT = 8`, `MAX_FOCUS_WORDS = 5`, `MAX_REQUESTS_PER_CONCEPT_PER_DAY = 3`, `MAX_TEACH_ROUNDS_PER_DAY = 3`, `MAX_MISCONCEPTION_CHARS = 120`, `MODES`, `TARGET_DIFFICULTY`, `SLUG_RE`, `NICKNAME_RE`, `TAG_RE`; exceptions `SherlockError` (exit 1) and `DataError` (exit 2); `bank_file(pkg) -> Path`, `student_file(pkg, student_id) -> Path`, `load_json(path) -> dict`, `save_json(path, data) -> None`, `package_dir(args) -> Path`, `today_from(args) -> date`, `now_utc() -> datetime`, `require_concept(bank, concept) -> None`, `quota(bank, today) -> dict`; commands `bank init`, `bank add-concept`, `bank quota`; `ArgumentParser`, `build_parser()`, `main(argv) -> int`.
- Produces, in `tests/sherlock_testlib.py`: `ROOT`, `FIXTURES`, `sherlock` (the loaded module), `run(*argv) -> (exit_code, parsed_json_or_None, stderr)`, and `PackageTestCase` with `self.pkg`, `TODAY = "2026-09-26"`, `ok(*argv)`, `fails(expected_code, *argv)`, `make_bank(*concepts, daily_cap=20)`.

- [ ] **Step 1: Create the test helper module.** Create `tests/sherlock_testlib.py` with exactly this content:

```python
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
```

- [ ] **Step 2: Write the failing test.** Create `tests/test_sherlock_store.py` with exactly this content:

```python
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
```

- [ ] **Step 3: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_store.py'`
Expected: `FAILED (errors=1)` with `FileNotFoundError` naming `scripts/sherlock.py`.

- [ ] **Step 4: Create `scripts/sherlock.py`** with exactly this content, then make it executable with `chmod +x scripts/sherlock.py`:

```python
#!/usr/bin/env python3
"""Bookkeeping for Sherlock Study Boy's adaptive modes.

The agent runs the conversation; this script owns every state change: the
shared per-notebook quiz bank, per-student progress, grading, mastery, review
scheduling, question selection, and the daily quiz-generation quota.

Standard library only. Every command prints one JSON object to stdout. Errors
print one line to stderr and exit 1 (bad input or refused action) or 2
(unreadable data or unknown schema_version).
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import secrets
import shlex
import sys
import tempfile
from pathlib import Path

SCHEMA_VERSION = 1
LADDER_DAYS = [1, 2, 4, 8, 16, 30, 60]
MASTERED_AT = 0.80
PARTIAL_AT = 0.50
DIAGNOSE_MASTERED_STEP = 2
DEFAULT_DAILY_CAP = 20
DEFAULT_QUIZ_COUNT = 8
MAX_FOCUS_WORDS = 5
MAX_REQUESTS_PER_CONCEPT_PER_DAY = 3
MAX_TEACH_ROUNDS_PER_DAY = 3
MAX_MISCONCEPTION_CHARS = 120
MODES = ("diagnose", "teach", "review")
TARGET_DIFFICULTY = {"untested": 3, "weak": 2, "partial": 3, "mastered": 4}

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")
NICKNAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{2,31}$")
TAG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,39}$")


class SherlockError(Exception):
    """Bad input or a refused action (exit code 1)."""

    exit_code = 1


class DataError(SherlockError):
    """Unreadable data or an unknown schema_version (exit code 2)."""

    exit_code = 2


# --- Files -------------------------------------------------------------------


def bank_file(pkg: Path) -> Path:
    return pkg / "quiz-bank" / "bank.json"



def student_file(pkg: Path, student_id: str) -> Path:
    return pkg / "students" / f"{student_id}.json"



def load_json(path: Path) -> dict:
    if not path.is_file():
        raise SherlockError(f"file not found: {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DataError(f"cannot read {path}: {exc}") from exc
    if not isinstance(data, dict) or data.get("schema_version") != SCHEMA_VERSION:
        raise DataError(
            f"unsupported schema_version in {path} (expected {SCHEMA_VERSION})"
        )
    return data



def save_json(path: Path, data: dict) -> None:
    """Write JSON atomically: temp file in the same directory, fsync, replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_name, path)
    except BaseException:
        if os.path.exists(tmp_name):
            os.unlink(tmp_name)
        raise



def package_dir(args: argparse.Namespace) -> Path:
    pkg = Path(args.dir)
    if not pkg.is_dir():
        raise SherlockError(f"study package directory not found: {pkg}")
    return pkg



def today_from(args: argparse.Namespace) -> dt.date:
    if args.today is None:
        return dt.date.today()
    try:
        return dt.date.fromisoformat(args.today)
    except ValueError as exc:
        raise SherlockError(f"--today must be YYYY-MM-DD, got {args.today!r}") from exc



def now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)



# --- Bank setup --------------------------------------------------------------


def require_concept(bank: dict, concept: str) -> None:
    if concept not in bank["concepts"]:
        raise SherlockError(f"unknown concept: {concept}")



def quota(bank: dict, today: dt.date) -> dict:
    used = sum(1 for quiz in bank["quizzes"] if quiz["requested"] == today.isoformat())
    cap = bank["daily_cap"]
    return {"used_today": used, "cap": cap, "remaining": max(cap - used, 0)}



def cmd_bank_init(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    path = bank_file(pkg)
    if path.exists():
        raise SherlockError(f"bank already exists: {path}")
    notebook_id = args.notebook_id.strip()
    if not notebook_id:
        raise SherlockError("--notebook-id must not be empty")
    if args.daily_cap < 1:
        raise SherlockError("--daily-cap must be at least 1")
    bank = {
        "schema_version": SCHEMA_VERSION,
        "notebook_id": notebook_id,
        "daily_cap": args.daily_cap,
        "concepts": {},
        "quizzes": [],
    }
    save_json(path, bank)
    return {"bank": str(path), "notebook_id": notebook_id, "daily_cap": args.daily_cap}



def cmd_bank_add_concept(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    bank = load_json(bank_file(pkg))
    if not SLUG_RE.match(args.slug):
        raise SherlockError(
            "slug must be 1-48 lowercase letters, digits, or dashes, starting with a letter or digit"
        )
    if args.slug in bank["concepts"]:
        raise SherlockError(f"concept already exists: {args.slug}")
    name = args.name.strip()
    if not name:
        raise SherlockError("--name must not be empty")
    words = args.focus.split()
    if not 1 <= len(words) <= MAX_FOCUS_WORDS:
        raise SherlockError(
            f"--focus must be 1-{MAX_FOCUS_WORDS} words (long focus phrases fail silently); got {len(words)}"
        )
    if args.rank < 1:
        raise SherlockError("--rank must be 1 or more")
    bank["concepts"][args.slug] = {"rank": args.rank, "name": name, "focus": " ".join(words)}
    save_json(bank_file(pkg), bank)
    return {"concept": args.slug, **bank["concepts"][args.slug]}



def cmd_bank_quota(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    today = today_from(args)
    bank = load_json(bank_file(pkg))
    return {"today": today.isoformat(), **quota(bank, today)}



# --- CLI ---------------------------------------------------------------------


class ArgumentParser(argparse.ArgumentParser):
    """Exit 1 on usage errors so that exit 2 always means a data error."""

    def error(self, message: str):  # type: ignore[override]
        self.print_usage(sys.stderr)
        self.exit(1, f"sherlock: {message}\n")


def build_parser() -> ArgumentParser:
    common = ArgumentParser(add_help=False)
    common.add_argument("--dir", required=True, help="study package directory")
    common.add_argument("--today", help="override today's date (YYYY-MM-DD)")

    parser = ArgumentParser(prog="sherlock.py", description=__doc__.splitlines()[0])
    commands = parser.add_subparsers(dest="command", required=True)

    bank = commands.add_parser("bank", help="manage the shared quiz bank")
    actions = bank.add_subparsers(dest="action", required=True)

    p = actions.add_parser("init", parents=[common], help="create quiz-bank/bank.json")
    p.add_argument("--notebook-id", required=True)
    p.add_argument("--daily-cap", type=int, default=DEFAULT_DAILY_CAP)
    p.set_defaults(handler=cmd_bank_init)

    p = actions.add_parser("add-concept", parents=[common], help="register a concept")
    p.add_argument("--slug", required=True)
    p.add_argument("--name", required=True)
    p.add_argument("--focus", required=True, help=f"1-{MAX_FOCUS_WORDS} word focus phrase")
    p.add_argument("--rank", type=int, required=True)
    p.set_defaults(handler=cmd_bank_add_concept)

    p = actions.add_parser("quota", parents=[common], help="show today's quiz quota")
    p.set_defaults(handler=cmd_bank_quota)

    return parser


def main(argv: list | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        result = args.handler(args)
    except SherlockError as exc:
        print(f"sherlock: {exc}", file=sys.stderr)
        return exc.exit_code
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: Run the tests and confirm they pass.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_store.py' -v`
Expected: `Ran 14 tests` and `OK`.

Run: `python3 -m unittest discover -s tests`
Expected: `OK`.

- [ ] **Step 6: Commit.**

```bash
git add scripts/sherlock.py tests/sherlock_testlib.py tests/test_sherlock_store.py
git commit -m "feat(sherlock): add script skeleton and bank setup"
```

---

### Task 7: Quiz slot lifecycle and daily cap

A quiz slot moves `reserved` (by `bank request`) → `pending` (by `bank submitted`, after the agent ran the printed `nlm quiz create` command) → `ready` (Task 8's `bank import`) or `failed` (`bank fail`). `bank request` prints the exact `nlm` command, built from the concept's stored focus phrase, so the agent never composes those flags itself.

**Files:**
- Modify: `scripts/sherlock.py` (two insertions)
- Test: `tests/test_sherlock_bank.py`

**Interfaces:**
- Consumes: `load_json`, `save_json`, `bank_file`, `package_dir`, `today_from`, `now_utc`, `require_concept`, `quota` (Task 6).
- Produces: `find_quiz(bank, slot) -> dict`; commands `bank request --concept --difficulty [--count]` (output keys `slot`, `command`, `command_line`, `quota`), `bank submitted --quiz --artifact-id`, `bank pending` (output `{"pending": [{"slot", "concept", "artifact_id", "minutes_pending"}]}`), `bank fail --quiz --reason`. Slot names are `<concept>-d<difficulty>-<n>`. Bank quiz entries have keys `slot, concept, difficulty, count, status, artifact_id, requested, submitted_at, file, question_count, reason`; `file` is `quiz-bank/<slot>.json`.

- [ ] **Step 1: Write the failing test.** Create `tests/test_sherlock_bank.py` with exactly this content:

```python
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
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_bank.py'`
Expected: `FAILED (errors=9)` with `invalid choice: 'request'` (and one `invalid choice: 'fail'`).

- [ ] **Step 3: Insert the functions.** In `scripts/sherlock.py`, insert this block above the marker line that starts `# --- CLI`:

```python
# --- Quiz slots --------------------------------------------------------------


def find_quiz(bank: dict, slot: str) -> dict:
    for quiz in bank["quizzes"]:
        if quiz["slot"] == slot:
            return quiz
    raise SherlockError(f"unknown quiz slot: {slot}")



def cmd_bank_request(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    today = today_from(args)
    bank = load_json(bank_file(pkg))
    require_concept(bank, args.concept)
    if not 1 <= args.difficulty <= 5:
        raise SherlockError("--difficulty must be 1-5")
    if args.count < 1:
        raise SherlockError("--count must be at least 1")
    usage = quota(bank, today)
    if usage["remaining"] == 0:
        raise SherlockError(
            f"daily quiz cap reached ({usage['cap']}); use questions already in the bank"
        )
    concept_today = sum(
        1
        for quiz in bank["quizzes"]
        if quiz["concept"] == args.concept and quiz["requested"] == today.isoformat()
    )
    if concept_today >= MAX_REQUESTS_PER_CONCEPT_PER_DAY:
        raise SherlockError(
            f"already requested {concept_today} quizzes for {args.concept} today; try again tomorrow"
        )
    number = 1 + sum(
        1
        for quiz in bank["quizzes"]
        if quiz["concept"] == args.concept and quiz["difficulty"] == args.difficulty
    )
    slot = f"{args.concept}-d{args.difficulty}-{number}"
    command = [
        "nlm", "quiz", "create", bank["notebook_id"],
        "--focus", bank["concepts"][args.concept]["focus"],
        "--count", str(args.count),
        "--difficulty", str(args.difficulty),
        "--confirm", "--json",
    ]
    bank["quizzes"].append(
        {
            "slot": slot,
            "concept": args.concept,
            "difficulty": args.difficulty,
            "count": args.count,
            "status": "reserved",
            "artifact_id": None,
            "requested": today.isoformat(),
            "submitted_at": None,
            "file": f"quiz-bank/{slot}.json",
            "question_count": 0,
            "reason": None,
        }
    )
    save_json(bank_file(pkg), bank)
    return {
        "slot": slot,
        "command": command,
        "command_line": shlex.join(command),
        "quota": quota(bank, today),
    }



def cmd_bank_submitted(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    bank = load_json(bank_file(pkg))
    quiz = find_quiz(bank, args.quiz)
    if quiz["status"] != "reserved":
        raise SherlockError(f"{args.quiz} is {quiz['status']}, expected reserved")
    artifact_id = args.artifact_id.strip()
    if not artifact_id:
        raise SherlockError("--artifact-id must not be empty")
    quiz.update(status="pending", artifact_id=artifact_id, submitted_at=now_utc().isoformat())
    save_json(bank_file(pkg), bank)
    return {"slot": args.quiz, "status": "pending", "artifact_id": artifact_id}



def cmd_bank_pending(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    bank = load_json(bank_file(pkg))
    now = now_utc()
    pending = []
    for quiz in bank["quizzes"]:
        if quiz["status"] != "pending":
            continue
        submitted = dt.datetime.fromisoformat(quiz["submitted_at"])
        pending.append(
            {
                "slot": quiz["slot"],
                "concept": quiz["concept"],
                "artifact_id": quiz["artifact_id"],
                "minutes_pending": int((now - submitted).total_seconds() // 60),
            }
        )
    return {"pending": pending}



def cmd_bank_fail(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    bank = load_json(bank_file(pkg))
    quiz = find_quiz(bank, args.quiz)
    if quiz["status"] not in ("reserved", "pending"):
        raise SherlockError(f"{args.quiz} is {quiz['status']}; only reserved or pending quizzes can fail")
    reason = " ".join(args.reason.split())
    if not reason:
        raise SherlockError("--reason must not be empty")
    quiz.update(status="failed", reason=reason[:200])
    save_json(bank_file(pkg), bank)
    return {"slot": args.quiz, "status": "failed", "reason": quiz["reason"]}
```

- [ ] **Step 4: Register the commands.** In `scripts/sherlock.py`, insert this block above the marker line `    return parser` (keep the 4-space indentation):

```python
    p = actions.add_parser("request", parents=[common], help="reserve a quiz slot")
    p.add_argument("--concept", required=True)
    p.add_argument("--difficulty", type=int, required=True)
    p.add_argument("--count", type=int, default=DEFAULT_QUIZ_COUNT)
    p.set_defaults(handler=cmd_bank_request)

    p = actions.add_parser("submitted", parents=[common], help="record a submitted quiz")
    p.add_argument("--quiz", required=True)
    p.add_argument("--artifact-id", required=True)
    p.set_defaults(handler=cmd_bank_submitted)

    p = actions.add_parser("pending", parents=[common], help="list quizzes being generated")
    p.set_defaults(handler=cmd_bank_pending)

    p = actions.add_parser("fail", parents=[common], help="mark a quiz as failed")
    p.add_argument("--quiz", required=True)
    p.add_argument("--reason", required=True)
    p.set_defaults(handler=cmd_bank_fail)
```

- [ ] **Step 5: Run the tests and confirm they pass.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_bank.py' -v`
Expected: `Ran 9 tests` and `OK`.

Run: `python3 -m unittest discover -s tests`
Expected: `OK`.

- [ ] **Step 6: Commit.**

```bash
git add scripts/sherlock.py tests/test_sherlock_bank.py
git commit -m "feat(sherlock): add quiz slot lifecycle and daily cap"
```

---

### Task 8: Import and validate NotebookLM quizzes

`nlm download quiz <notebook-id> --id <artifact-id> --format json` writes `{"title": ..., "questions": [{"question": ..., "answerOptions": [{"text": ..., "isCorrect": true|false}], "hint": ...}]}`. This was confirmed by reading `notebooklm_tools/core/download.py` in `nlm` 0.9.14. `bank import` converts that into the bank's normalized format and rejects anything unusable. The fixtures below use exactly that shape.

**Files:**
- Modify: `scripts/sherlock.py` (two insertions)
- Modify: `tests/sherlock_testlib.py` (one insertion)
- Create: `tests/fixtures/quiz-sample.json`, `tests/fixtures/quiz-broken.json`
- Test: `tests/test_sherlock_import.py`

**Interfaces:**
- Consumes: `find_quiz` (Task 7), Task 6 helpers.
- Produces: `question_id(text) -> str` (12 hex chars); `normalize_quiz(raw, slot, artifact_id) -> dict` returning `{"schema_version": 1, "slot", "artifact_id", "questions": [{"id", "question", "options", "answer_index", "rationale", "hint"}]}`; command `bank import --quiz --file`. In the test helpers: `nlm_quiz(prefix, count, correct_index=1) -> dict`.

- [ ] **Step 1: Create the fixtures.** Create `tests/fixtures/quiz-sample.json` with exactly this content:

```json
{
  "title": "Photosynthesis Quiz",
  "questions": [
    {
      "question": "What is the main source of energy for photosynthesis?",
      "answerOptions": [
        { "text": "Carbon dioxide", "isCorrect": false },
        { "text": "Sunlight", "isCorrect": true, "rationale": "Chlorophyll captures light energy, which drives the reaction." },
        { "text": "Water", "isCorrect": false },
        { "text": "Soil nutrients", "isCorrect": false }
      ],
      "hint": "Think about what a plant needs to be placed near."
    },
    {
      "question": "Which pigment absorbs light in plant cells?",
      "answerOptions": [
        { "text": "Chlorophyll", "isCorrect": true },
        { "text": "Haemoglobin", "isCorrect": false },
        { "text": "Melanin", "isCorrect": false },
        { "text": "Keratin", "isCorrect": false }
      ],
      "hint": "It gives leaves their green colour."
    },
    {
      "question": "Where in the cell does photosynthesis take place?",
      "answerOptions": [
        { "text": "Mitochondria", "isCorrect": false },
        { "text": "Nucleus", "isCorrect": false },
        { "text": "Chloroplasts", "isCorrect": true },
        { "text": "Cell membrane", "isCorrect": false }
      ]
    },
    {
      "question": "Which gas is released as a by-product of photosynthesis?",
      "answerOptions": [
        { "text": "Oxygen", "isCorrect": true },
        { "text": "Carbon dioxide", "isCorrect": false },
        { "text": "Nitrogen", "isCorrect": false },
        { "text": "Hydrogen", "isCorrect": false }
      ]
    },
    {
      "question": "Which gas do plants take in for photosynthesis?",
      "answerOptions": [
        { "text": "Oxygen", "isCorrect": false },
        { "text": "Carbon dioxide", "isCorrect": true },
        { "text": "Nitrogen", "isCorrect": false },
        { "text": "Methane", "isCorrect": false }
      ]
    },
    {
      "question": "What sugar is produced by photosynthesis?",
      "answerOptions": [
        { "text": "Glucose", "isCorrect": true },
        { "text": "Sucrose", "isCorrect": false },
        { "text": "Lactose", "isCorrect": false },
        { "text": "Fructose", "isCorrect": false }
      ]
    },
    {
      "question": "Which factor would most likely increase the rate of photosynthesis?",
      "answerOptions": [
        { "text": "Lower light intensity", "isCorrect": false },
        { "text": "Higher light intensity", "isCorrect": true },
        { "text": "Removing water", "isCorrect": false },
        { "text": "Covering the leaves", "isCorrect": false }
      ]
    },
    {
      "question": "Through which structures does carbon dioxide enter a leaf?",
      "answerOptions": [
        { "text": "Roots", "isCorrect": false },
        { "text": "Stomata", "isCorrect": true },
        { "text": "Xylem", "isCorrect": false },
        { "text": "Petals", "isCorrect": false }
      ],
      "hint": "Tiny pores, mostly on the underside of the leaf."
    }
  ]
}
```

Create `tests/fixtures/quiz-broken.json` with exactly this content:

```json
{
  "title": "Broken Quiz",
  "questions": [
    {
      "question": "Which of these is a primary colour of light?",
      "answerOptions": [
        { "text": "Red", "isCorrect": true },
        { "text": "Green", "isCorrect": true },
        { "text": "Brown", "isCorrect": false }
      ]
    }
  ]
}
```

- [ ] **Step 2: Add the quiz builder to the test helpers.** In `tests/sherlock_testlib.py`, insert this block above the marker line `class PackageTestCase(unittest.TestCase):`:

```python
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
```

- [ ] **Step 3: Write the failing test.** Create `tests/test_sherlock_import.py` with exactly this content:

```python
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
                "question": "What is the main source of energy for photosynthesis?",
                "options": ["Carbon dioxide", "Sunlight", "Water", "Soil nutrients"],
                "answer_index": 1,
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
        self.assertEqual({"slot": slot, "status": "ready", "question_count": 8}, out)
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
```

- [ ] **Step 4: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_import.py'`
Expected: `FAILED`, with `AttributeError: module 'sherlock' has no attribute 'question_id'` (or `'normalize_quiz'`) and `invalid choice: 'import'`.

- [ ] **Step 5: Insert the functions.** In `scripts/sherlock.py`, insert this block above the marker line that starts `# --- CLI`:

```python
# --- Quiz import -------------------------------------------------------------


def question_id(text: str) -> str:
    """Stable ID: first 12 hex chars of SHA-256 of the lowercased, whitespace-collapsed text."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]



def normalize_quiz(raw: object, slot: str, artifact_id: str) -> dict:
    """Convert `nlm download quiz --format json` output into the bank's format.

    Raises SherlockError describing the first problem found.
    """
    if not isinstance(raw, dict) or not isinstance(raw.get("questions"), list):
        raise SherlockError("quiz JSON must be an object with a 'questions' list")
    questions = []
    seen_ids = set()
    for number, item in enumerate(raw["questions"], start=1):
        if not isinstance(item, dict):
            raise SherlockError(f"question {number} is not an object")
        text = item.get("question")
        if not isinstance(text, str) or not text.strip():
            raise SherlockError(f"question {number} has no text")
        options = item.get("answerOptions")
        if not isinstance(options, list) or len(options) < 2:
            raise SherlockError(f"question {number} needs at least two answer options")
        option_texts = []
        correct = []
        for index, option in enumerate(options):
            option_text = option.get("text") if isinstance(option, dict) else None
            if not isinstance(option_text, str) or not option_text.strip():
                raise SherlockError(f"question {number} option {index + 1} has no text")
            option_texts.append(option_text.strip())
            if option.get("isCorrect") is True:
                correct.append(index)
        if len(correct) != 1:
            raise SherlockError(
                f"question {number} must have exactly one correct option, found {len(correct)}"
            )
        qid = question_id(text)
        if qid in seen_ids:
            continue
        seen_ids.add(qid)
        rationale = options[correct[0]].get("rationale")
        hint = item.get("hint")
        questions.append(
            {
                "id": qid,
                "question": text.strip(),
                "options": option_texts,
                "answer_index": correct[0],
                "rationale": rationale.strip()
                if isinstance(rationale, str) and rationale.strip()
                else None,
                "hint": hint.strip() if isinstance(hint, str) and hint.strip() else None,
            }
        )
    if not questions:
        raise SherlockError("quiz has no questions")
    return {
        "schema_version": SCHEMA_VERSION,
        "slot": slot,
        "artifact_id": artifact_id,
        "questions": questions,
    }



def cmd_bank_import(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    bank = load_json(bank_file(pkg))
    quiz = find_quiz(bank, args.quiz)
    if quiz["status"] != "pending":
        raise SherlockError(f"{args.quiz} is {quiz['status']}, expected pending")
    source = Path(args.file)
    if not source.is_file():
        raise SherlockError(f"downloaded quiz file not found: {source}")
    try:
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise SherlockError(f"cannot parse {source}: {exc}") from exc
        normalized = normalize_quiz(raw, quiz["slot"], quiz["artifact_id"])
    except SherlockError as exc:
        quiz.update(status="failed", reason=str(exc)[:200])
        save_json(bank_file(pkg), bank)
        raise SherlockError(f"{args.quiz} failed validation: {exc}") from exc
    save_json(pkg / quiz["file"], normalized)
    quiz.update(status="ready", question_count=len(normalized["questions"]))
    save_json(bank_file(pkg), bank)
    return {"slot": args.quiz, "status": "ready", "question_count": quiz["question_count"]}
```

- [ ] **Step 6: Register the command.** In `scripts/sherlock.py`, insert this block above the marker line `    return parser`:

```python
    p = actions.add_parser("import", parents=[common], help="import a downloaded quiz")
    p.add_argument("--quiz", required=True)
    p.add_argument("--file", required=True)
    p.set_defaults(handler=cmd_bank_import)
```

- [ ] **Step 7: Run the tests and confirm they pass.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_import.py' -v`
Expected: `Ran 11 tests` and `OK`.

Run: `python3 -m unittest discover -s tests`
Expected: `OK`.

- [ ] **Step 8: Commit.**

```bash
git add scripts/sherlock.py tests/sherlock_testlib.py tests/fixtures/quiz-sample.json tests/fixtures/quiz-broken.json tests/test_sherlock_import.py
git commit -m "feat(sherlock): import and validate NotebookLM quizzes"
```

---

### Task 9: Mastery, review schedule, and question selection rules

These are pure functions with no file access. They carry the rules from spec §6.4: thresholds 0.80 and 0.50; review ladder `[1, 2, 4, 8, 16, 30, 60]` days; diagnose mastery starts at step 2 (4 days), teach mastery at step 0 (1 day), each passed review climbs one step (maximum 6), and any round below 0.80 resets to step 0 with no review date.

**Files:**
- Modify: `scripts/sherlock.py` (one insertion)
- Test: `tests/test_sherlock_rules.py`

**Interfaces:**
- Produces: `classify(score) -> "mastered" | "partial" | "weak"`; `apply_round(record, mode, correct, asked, today) -> dict` (mutates `record`: sets `status`, `score` rounded to 4 places, `step`, `next_review` as `YYYY-MM-DD` or `None`, and appends to `rounds`); `select_questions(candidates, seen, target, count, allow_seen) -> (list_of_questions, unseen_remaining)` where `candidates` is a list of `(difficulty, question)` pairs; `new_concept_record() -> dict` with keys `status, score, step, next_review, misconceptions, explanations_tried, rounds, open_answers, seen`.

- [ ] **Step 1: Write the failing test.** Create `tests/test_sherlock_rules.py` with exactly this content:

```python
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
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_rules.py'`
Expected: `FAILED (errors=11)` with `AttributeError: module 'sherlock' has no attribute 'apply_round'` (also `'classify'`, `'select_questions'`).

- [ ] **Step 3: Insert the functions.** In `scripts/sherlock.py`, insert this block above the marker line that starts `# --- CLI`:

```python
# --- Rules -------------------------------------------------------------------


def classify(score: float) -> str:
    if score >= MASTERED_AT:
        return "mastered"
    if score >= PARTIAL_AT:
        return "partial"
    return "weak"



def apply_round(
    record: dict, mode: str, correct: int, asked: int, today: dt.date
) -> dict:
    """Apply one closed round to a student's concept record. Mutates and returns it."""
    if asked <= 0:
        raise SherlockError("a round needs at least one answer")
    score = correct / asked
    status = classify(score)
    if status == "mastered":
        if mode == "diagnose":
            step = DIAGNOSE_MASTERED_STEP
        elif mode == "teach":
            step = 0
        else:
            step = min(record["step"] + 1, len(LADDER_DAYS) - 1)
        next_review = (today + dt.timedelta(days=LADDER_DAYS[step])).isoformat()
    else:
        step = 0
        next_review = None
    record.update(
        status=status, score=round(score, 4), step=step, next_review=next_review
    )
    record["rounds"].append(
        {"date": today.isoformat(), "mode": mode, "correct": correct, "asked": asked}
    )
    return record



def select_questions(
    candidates: list, seen: dict, target: int, count: int, allow_seen: bool
) -> tuple:
    """Pick questions for a round.

    candidates: list of (difficulty, question) pairs in bank order.
    Returns (selected_questions, unseen_remaining).
    Unseen questions come first, closest difficulty to target first (ties keep
    bank order). If allow_seen, top up with seen questions, oldest last_seen first.
    """
    unseen = [c for c in candidates if c[1]["id"] not in seen]
    unseen.sort(key=lambda c: abs(c[0] - target))
    selected = unseen[:count]
    if allow_seen and len(selected) < count:
        already = [c for c in candidates if c[1]["id"] in seen]
        already.sort(key=lambda c: (seen[c[1]["id"]]["last_seen"], abs(c[0] - target)))
        selected = selected + already[: count - len(selected)]
    unseen_remaining = max(len(unseen) - count, 0)
    return [question for _, question in selected], unseen_remaining



def new_concept_record() -> dict:
    return {
        "status": "untested",
        "score": None,
        "step": 0,
        "next_review": None,
        "misconceptions": [],
        "explanations_tried": [],
        "rounds": [],
        "open_answers": [],
        "seen": {},
    }
```

- [ ] **Step 4: Run the tests and confirm they pass.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_rules.py' -v`
Expected: `Ran 11 tests` and `OK`.

Run: `python3 -m unittest discover -s tests`
Expected: `OK`.

- [ ] **Step 5: Commit.**

```bash
git add scripts/sherlock.py tests/test_sherlock_rules.py
git commit -m "feat(sherlock): add mastery, review, and selection rules"
```

---

### Task 10: Students, question rounds, and notes

A round is: `next` (pick questions; never reveals answers) → one `record` per answer (grades it against the stored answer key) → `close-round` (scores the round with `apply_round`). `note` stores a one-line misconception or an explanation-strategy tag. Student IDs are a nickname matching `^[a-z0-9][a-z0-9-]{2,31}$` or a generated `s-` plus 6 hex characters; invalid IDs are refused before any file path is built.

**Files:**
- Modify: `scripts/sherlock.py` (two insertions)
- Modify: `tests/sherlock_testlib.py` (append methods)
- Test: `tests/test_sherlock_student.py`

**Interfaces:**
- Consumes: `normalize_quiz` output files (Task 8), `apply_round`, `select_questions`, `new_concept_record` (Task 9), Task 6–7 helpers.
- Produces: `ready_questions(pkg, bank, concept) -> list[(difficulty, question)]`, `load_student(pkg, student_id) -> dict`, `concept_record(student, bank, concept) -> dict`; commands `student new [--nickname]`, `next --student --concept --count --mode`, `record --student --concept --mode --question --choice`, `close-round --student --concept --mode`, `note --student --concept (--misconception | --explanation)`. Inside `build_parser()`: the local helper `student_command(name, help_text, handler)` that Task 11 uses. Test helpers gain `add_ready_quiz`, `new_student`, `answer_key`, `play_round`, `student_data`, `write_student_data`.

- [ ] **Step 1: Add the round helpers to the test helpers.** Append this block to the end of `tests/sherlock_testlib.py`. The methods belong to `PackageTestCase`, which is the last thing in the file, so keep the 4-space indentation:

```python
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
```

- [ ] **Step 2: Write the failing test.** Create `tests/test_sherlock_student.py` with exactly this content:

```python
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
            self.assertEqual({"id", "question", "options", "hint"}, set(question))

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
```

- [ ] **Step 3: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_student.py'`
Expected: `FAILED`, with errors including `invalid choice: 'student'`.

- [ ] **Step 4: Insert the functions.** In `scripts/sherlock.py`, insert this block above the marker line that starts `# --- CLI`:

```python
# --- Students and rounds -----------------------------------------------------


def ready_questions(pkg: Path, bank: dict, concept: str) -> list:
    """(difficulty, question) for every question in the concept's ready quizzes, deduplicated by ID."""
    found = {}
    for quiz in bank["quizzes"]:
        if quiz["concept"] != concept or quiz["status"] != "ready":
            continue
        for question in load_json(pkg / quiz["file"])["questions"]:
            found.setdefault(question["id"], (quiz["difficulty"], question))
    return list(found.values())



def load_student(pkg: Path, student_id: str) -> dict:
    if not NICKNAME_RE.match(student_id):
        raise SherlockError(f"invalid student id: {student_id!r}")
    return load_json(student_file(pkg, student_id))



def concept_record(student: dict, bank: dict, concept: str) -> dict:
    require_concept(bank, concept)
    return student["concepts"].setdefault(concept, new_concept_record())



def cmd_student_new(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    today = today_from(args)
    bank = load_json(bank_file(pkg))
    if args.nickname is not None:
        if not NICKNAME_RE.match(args.nickname):
            raise SherlockError(
                "nickname must be 3-32 lowercase letters, digits, or dashes, starting with a letter or digit"
            )
        student_id = args.nickname
        if student_file(pkg, student_id).exists():
            raise SherlockError(f"student already exists: {student_id}")
    else:
        for _ in range(10):
            student_id = "s-" + secrets.token_hex(3)
            if not student_file(pkg, student_id).exists():
                break
        else:
            raise SherlockError("could not generate an unused student id")
    student = {
        "schema_version": SCHEMA_VERSION,
        "student_id": student_id,
        "notebook_id": bank["notebook_id"],
        "created": today.isoformat(),
        "concepts": {slug: new_concept_record() for slug in bank["concepts"]},
    }
    save_json(student_file(pkg, student_id), student)
    return {"student_id": student_id, "concepts": sorted(student["concepts"])}



def cmd_next(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    bank = load_json(bank_file(pkg))
    student = load_student(pkg, args.student)
    record = concept_record(student, bank, args.concept)
    if args.count < 1:
        raise SherlockError("--count must be at least 1")
    target = TARGET_DIFFICULTY[record["status"]]
    in_round = {answer["question"] for answer in record["open_answers"]}
    candidates = [
        c for c in ready_questions(pkg, bank, args.concept) if c[1]["id"] not in in_round
    ]
    selected, unseen_remaining = select_questions(
        candidates, record["seen"], target, args.count, allow_seen=args.mode == "review"
    )
    return {
        "student": args.student,
        "concept": args.concept,
        "mode": args.mode,
        "target_difficulty": target,
        "questions": [
            {
                "id": q["id"],
                "question": q["question"],
                "options": q["options"],
                "hint": q["hint"],
            }
            for q in selected
        ],
        "shortfall": args.count - len(selected),
        "unseen_remaining": unseen_remaining,
    }



def cmd_record(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    today = today_from(args)
    bank = load_json(bank_file(pkg))
    student = load_student(pkg, args.student)
    record = concept_record(student, bank, args.concept)
    if any(answer["question"] == args.question for answer in record["open_answers"]):
        raise SherlockError(f"question {args.question} is already answered in this round")
    match = None
    for _, question in ready_questions(pkg, bank, args.concept):
        if question["id"] == args.question:
            match = question
            break
    if match is None:
        raise SherlockError(f"question {args.question} is not in a ready quiz for {args.concept}")
    if not 0 <= args.choice < len(match["options"]):
        raise SherlockError(f"--choice must be 0-{len(match['options']) - 1}")
    correct = args.choice == match["answer_index"]
    times = record["seen"].get(args.question, {}).get("times", 0)
    record["seen"][args.question] = {
        "last_seen": today.isoformat(),
        "times": times + 1,
        "last_correct": correct,
    }
    record["open_answers"].append(
        {"question": args.question, "mode": args.mode, "choice": args.choice, "correct": correct}
    )
    save_json(student_file(pkg, args.student), student)
    return {
        "question": args.question,
        "correct": correct,
        "correct_index": match["answer_index"],
        "correct_option": match["options"][match["answer_index"]],
        "rationale": match["rationale"],
        "answered_this_round": sum(
            1 for answer in record["open_answers"] if answer["mode"] == args.mode
        ),
    }



def cmd_close_round(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    today = today_from(args)
    bank = load_json(bank_file(pkg))
    student = load_student(pkg, args.student)
    record = concept_record(student, bank, args.concept)
    answers = [answer for answer in record["open_answers"] if answer["mode"] == args.mode]
    if not answers:
        raise SherlockError(f"no recorded {args.mode} answers for {args.concept} to close")
    correct = sum(1 for answer in answers if answer["correct"])
    apply_round(record, args.mode, correct, len(answers), today)
    record["open_answers"] = [
        answer for answer in record["open_answers"] if answer["mode"] != args.mode
    ]
    save_json(student_file(pkg, args.student), student)
    return {
        "concept": args.concept,
        "mode": args.mode,
        "correct": correct,
        "asked": len(answers),
        "score": record["score"],
        "status": record["status"],
        "step": record["step"],
        "next_review": record["next_review"],
    }



def cmd_note(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    bank = load_json(bank_file(pkg))
    student = load_student(pkg, args.student)
    record = concept_record(student, bank, args.concept)
    if args.misconception is not None:
        text = " ".join(args.misconception.split())
        if not text or len(text) > MAX_MISCONCEPTION_CHARS:
            raise SherlockError(
                f"--misconception must be 1-{MAX_MISCONCEPTION_CHARS} characters on one line"
            )
        if text not in record["misconceptions"]:
            record["misconceptions"].append(text)
    else:
        if not TAG_RE.match(args.explanation):
            raise SherlockError(
                "--explanation must be a tag of 1-40 lowercase letters, digits, or dashes"
            )
        if args.explanation not in record["explanations_tried"]:
            record["explanations_tried"].append(args.explanation)
    save_json(student_file(pkg, args.student), student)
    return {
        "concept": args.concept,
        "misconceptions": record["misconceptions"],
        "explanations_tried": record["explanations_tried"],
    }
```

- [ ] **Step 5: Register the commands.** In `scripts/sherlock.py`, insert this block above the marker line `    return parser`:

```python
    student = commands.add_parser("student", help="manage students")
    student_actions = student.add_subparsers(dest="action", required=True)
    p = student_actions.add_parser("new", parents=[common], help="create a student file")
    p.add_argument("--nickname")
    p.set_defaults(handler=cmd_student_new)

    def student_command(name: str, help_text: str, handler) -> ArgumentParser:
        sub = commands.add_parser(name, parents=[common], help=help_text)
        sub.add_argument("--student", required=True)
        sub.set_defaults(handler=handler)
        return sub

    p = student_command("next", "select questions for a round", cmd_next)
    p.add_argument("--concept", required=True)
    p.add_argument("--count", type=int, required=True)
    p.add_argument("--mode", choices=MODES, required=True)

    p = student_command("record", "grade and record one answer", cmd_record)
    p.add_argument("--concept", required=True)
    p.add_argument("--mode", choices=MODES, required=True)
    p.add_argument("--question", required=True)
    p.add_argument("--choice", type=int, required=True, help="0-based option index")

    p = student_command("close-round", "score the open round", cmd_close_round)
    p.add_argument("--concept", required=True)
    p.add_argument("--mode", choices=MODES, required=True)

    p = student_command("note", "record a misconception or explanation tag", cmd_note)
    p.add_argument("--concept", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--misconception")
    group.add_argument("--explanation")
```

- [ ] **Step 6: Run the tests and confirm they pass.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_student.py' -v`
Expected: `Ran 16 tests` and `OK`.

Run: `python3 -m unittest discover -s tests`
Expected: `OK`.

- [ ] **Step 7: Commit.**

```bash
git add scripts/sherlock.py tests/sherlock_testlib.py tests/test_sherlock_student.py
git commit -m "feat(sherlock): add students, question rounds, and notes"
```

---

### Task 11: `status` and `due`

`status` is what the agent reads at the start of every session: per-concept rows, the teach queue (weak before partial, then lowest score, then rank; concepts with three teach rounds today are excluded), concepts due for review, and the quota.

**Files:**
- Modify: `scripts/sherlock.py` (two insertions)
- Test: `tests/test_sherlock_status.py`

**Interfaces:**
- Consumes: `student_command` inside `build_parser()` (Task 10), `ready_questions`, `load_student`, `new_concept_record`, `quota`.
- Produces: `concept_rows(pkg, bank, student, today) -> list[dict]` (row keys `concept, name, rank, status, score, step, next_review, unseen_questions, teach_rounds_today, quizzes_pending, misconceptions`); commands `status --student` (output keys `student, notebook_id, today, concepts, teach_queue, due, quota`) and `due --student` (output `{"student", "today", "due": [{"concept", "name", "next_review", "step"}]}`).

- [ ] **Step 1: Write the failing test.** Create `tests/test_sherlock_status.py` with exactly this content:

```python
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
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_status.py'`
Expected: `FAILED (errors=6)` with `invalid choice: 'status'` (and one `invalid choice: 'due'`).

- [ ] **Step 3: Insert the functions.** In `scripts/sherlock.py`, insert this block above the marker line that starts `# --- CLI`:

```python
# --- Status and review -------------------------------------------------------


def concept_rows(pkg: Path, bank: dict, student: dict, today: dt.date) -> list:
    rows = []
    for slug, meta in sorted(bank["concepts"].items(), key=lambda item: item[1]["rank"]):
        record = student["concepts"].get(slug) or new_concept_record()
        unseen = sum(
            1 for _, q in ready_questions(pkg, bank, slug) if q["id"] not in record["seen"]
        )
        rows.append(
            {
                "concept": slug,
                "name": meta["name"],
                "rank": meta["rank"],
                "status": record["status"],
                "score": record["score"],
                "step": record["step"],
                "next_review": record["next_review"],
                "unseen_questions": unseen,
                "teach_rounds_today": sum(
                    1
                    for r in record["rounds"]
                    if r["mode"] == "teach" and r["date"] == today.isoformat()
                ),
                "quizzes_pending": sum(
                    1
                    for quiz in bank["quizzes"]
                    if quiz["concept"] == slug and quiz["status"] in ("reserved", "pending")
                ),
                "misconceptions": record["misconceptions"],
            }
        )
    return rows



def cmd_status(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    today = today_from(args)
    bank = load_json(bank_file(pkg))
    student = load_student(pkg, args.student)
    rows = concept_rows(pkg, bank, student, today)
    teachable = [
        r
        for r in rows
        if r["status"] in ("weak", "partial")
        and r["teach_rounds_today"] < MAX_TEACH_ROUNDS_PER_DAY
    ]
    teachable.sort(
        key=lambda r: (
            0 if r["status"] == "weak" else 1,
            r["score"] if r["score"] is not None else 0.0,
            r["rank"],
        )
    )
    return {
        "student": args.student,
        "notebook_id": bank["notebook_id"],
        "today": today.isoformat(),
        "concepts": rows,
        "teach_queue": [r["concept"] for r in teachable],
        "due": [
            r["concept"]
            for r in rows
            if r["next_review"] is not None and r["next_review"] <= today.isoformat()
        ],
        "quota": quota(bank, today),
    }



def cmd_due(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    today = today_from(args)
    bank = load_json(bank_file(pkg))
    student = load_student(pkg, args.student)
    rows = [
        r
        for r in concept_rows(pkg, bank, student, today)
        if r["next_review"] is not None and r["next_review"] <= today.isoformat()
    ]
    rows.sort(key=lambda r: (r["next_review"], r["rank"]))
    return {
        "student": args.student,
        "today": today.isoformat(),
        "due": [
            {"concept": r["concept"], "name": r["name"], "next_review": r["next_review"], "step": r["step"]}
            for r in rows
        ],
    }
```

- [ ] **Step 4: Register the commands.** In `scripts/sherlock.py`, insert this block above the marker line `    return parser`:

```python
    student_command("status", "show progress and queues", cmd_status)
    student_command("due", "list concepts due for review", cmd_due)
```

- [ ] **Step 5: Run the tests and confirm they pass, on every Python version available.**

Run: `python3 -m unittest discover -s tests -p 'test_sherlock_status.py' -v`
Expected: `Ran 6 tests` and `OK`.

Run: `python3 -m unittest discover -s tests`
Expected: `Ran 76 tests` and `OK`.

If `uv` is installed, also run these two; both must print `OK` (skip them if `uv` is missing):

```bash
uv run --no-project --python 3.10 python -m unittest discover -s tests
uv run --no-project --python 3.12 python -m unittest discover -s tests
```

- [ ] **Step 6: Smoke-test the script as a program.** Run this as one command block (it uses a throwaway directory and no NotebookLM calls):

```bash
PKG=$(mktemp -d)
python3 scripts/sherlock.py bank init --dir "$PKG" --notebook-id nb-test
python3 scripts/sherlock.py bank add-concept --dir "$PKG" --slug organ-systems --name "Human Organ Systems" --focus "Organ Systems" --rank 1
python3 scripts/sherlock.py bank request --dir "$PKG" --concept organ-systems --difficulty 3
rm -rf "$PKG"
```

Expected: three JSON objects; the last contains `"command_line": "nlm quiz create nb-test --focus 'Organ Systems' --count 8 --difficulty 3 --confirm --json"`.

- [ ] **Step 7: Commit.**

```bash
git add scripts/sherlock.py tests/test_sherlock_status.py
git commit -m "feat(sherlock): add status and due commands"
```

---

### Task 12: Adaptive-learning reference, privacy rules, and ignore rules

**Files:**
- Create: `references/adaptive-learning.md`
- Modify: `references/privacy-and-safety.md`
- Modify: `.gitignore`
- Modify: `scripts/validate_skill.py`

**Interfaces:**
- Consumes: the command names and output keys from Tasks 6–11 (the reference documents them).
- Produces: `references/adaptive-learning.md`, which Task 13's `SKILL.md` links to. The validator requires `references/adaptive-learning.md` and `scripts/sherlock.py` to exist.

- [ ] **Step 1: Create `references/adaptive-learning.md`** with exactly this content:

````markdown
# Adaptive Learning Reference

How Sherlock's diagnose, teach, tutor, and review modes store data and make decisions. `SKILL.md` has the step-by-step procedures; this file is the reference for `scripts/sherlock.py`.

## Division of labor

- **NotebookLM** writes the quiz questions: one focused quiz per concept, via `nlm quiz create --focus`.
- **The agent** runs the conversation: explanations, feedback, check-understanding questions, and tutoring.
- **`scripts/sherlock.py`** owns every state change: the quiz bank, grading, mastery, review dates, question selection, and the daily quiz quota. The agent never edits these files directly.

## Files

All adaptive data lives in the study package directory (`<pkg>`, default `./study-packages/<safe-title>/`):

```text
<pkg>/
├── quiz-bank/
│   ├── bank.json                     # shared by every student of this notebook
│   ├── <concept>-d<difficulty>-<n>.json   # one normalized quiz per NotebookLM quiz artifact
│   └── downloads/                    # raw `nlm download quiz` output before import
└── students/
    └── <student-id>.json             # one progress file per student
```

`quiz-bank/` holds curriculum-derived content only. `students/` holds student progress. Both are ignored by git.

## Command reference

Run as `python3 <skill-dir>/scripts/sherlock.py <command> --dir <pkg> [options]`. Every command also accepts `--today YYYY-MM-DD`, used by tests and for checking future review dates. Output is one JSON object on stdout. Errors are one line on stderr beginning `sherlock:`; exit code 1 means bad input or a refused action, 2 means unreadable data or an unknown `schema_version`.

| Command | Options | Does |
|---|---|---|
| `bank init` | `--notebook-id <id>` `[--daily-cap 20]` | Creates `quiz-bank/bank.json`. |
| `bank add-concept` | `--slug <slug>` `--name <name>` `--focus <1-5 words>` `--rank <n>` | Registers a concept. Slugs are lowercase letters, digits, and dashes. |
| `bank quota` | | Shows `used_today`, `cap`, `remaining`. |
| `bank request` | `--concept <slug>` `--difficulty <1-5>` `[--count 8]` | Reserves a quiz slot, counts it against today's cap, and prints the exact `nlm quiz create` command to run (`command` as a list, `command_line` as a string). |
| `bank submitted` | `--quiz <slot>` `--artifact-id <id>` | Marks a reserved slot `pending`. |
| `bank pending` | | Lists pending slots with `artifact_id` and `minutes_pending`. |
| `bank import` | `--quiz <slot>` `--file <downloaded.json>` | Validates and normalizes a downloaded quiz; marks it `ready`, or `failed` if invalid. A missing file changes nothing. |
| `bank fail` | `--quiz <slot>` `--reason <text>` | Marks a reserved or pending slot `failed`. |
| `student new` | `[--nickname <nickname>]` | Creates a student file. Without a nickname, the ID is `s-` plus six hex characters. |
| `next` | `--student <id>` `--concept <slug>` `--count <n>` `--mode <mode>` | Selects questions. Output has `questions` (`id`, `question`, `options`, `hint` — never the answer), `shortfall`, `unseen_remaining`, `target_difficulty`. |
| `record` | `--student <id>` `--concept <slug>` `--mode <mode>` `--question <id>` `--choice <0-based index>` | Grades one answer. Output has `correct`, `correct_index`, `correct_option`, `rationale`, `answered_this_round`. |
| `close-round` | `--student <id>` `--concept <slug>` `--mode <mode>` | Scores the answers recorded since the last round and applies the rules below. |
| `note` | `--student <id>` `--concept <slug>` and one of `--misconception <text>` / `--explanation <tag>` | Records a one-line misconception (max 120 characters) or an explanation-strategy tag. |
| `status` | `--student <id>` | Per-concept rows (`status`, `score`, `step`, `next_review`, `unseen_questions`, `teach_rounds_today`, `quizzes_pending`, `misconceptions`), plus `teach_queue`, `due`, and `quota`. |
| `due` | `--student <id>` | Concepts whose `next_review` is today or earlier, earliest first. |

`<mode>` is `diagnose`, `teach`, or `review`.

## Rules

### Mastery

Each closed round scores `correct ÷ asked`:

| Score | Status |
|---|---|
| 0.80 or more | `mastered` |
| 0.50–0.79 | `partial` |
| below 0.50 | `weak` |

A 3-question diagnose round gives 3/3 mastered, 2/3 partial, 0–1/3 weak. A 5-question round needs 4/5 for mastered. New concepts start `untested`.

### Review schedule

Review gaps follow the ladder `[1, 2, 4, 8, 16, 30, 60]` days, indexed by `step`.

| Round | Result | Status | `step` | Next review |
|---|---|---|---|---|
| diagnose | ≥ 0.80 | mastered | 2 | today + 4 days |
| teach | ≥ 0.80 | mastered | 0 | today + 1 day |
| review | ≥ 0.80 | mastered | one higher, at most 6 | today + ladder[step] |
| any | < 0.80 | partial or weak | 0 | none |

A failed review sends the concept back to the teach queue. When it is mastered again in teach, it returns for review the next day. Concepts that are `untested`, `weak`, or `partial` have no review date.

### Queues and limits

- **Teach queue:** `weak` before `partial`, then lower score first, then lower rank first. A concept leaves the queue for the day after three teach rounds.
- **Target difficulty:** untested 3, weak 2, partial 3, mastered 4.
- **Question selection:** unseen questions first, closest to the target difficulty first. Diagnose and teach use unseen questions only and report a `shortfall`. Review may reuse seen questions, oldest `last_seen` first.
- **Question identity:** a question's ID is the first 12 hex characters of the SHA-256 of its lowercased, whitespace-collapsed text, so a question NotebookLM repeats in another quiz counts as already seen.
- **Quota:** at most `daily_cap` quiz requests per day across all students (default 20), and at most 3 per concept per day. Failed requests still count, because they may have used NotebookLM quota.
- **Top-ups:** teach requests a new quiz when a concept has fewer than 5 unseen questions and none pending.

## Data formats

### `quiz-bank/bank.json`

```json
{
  "schema_version": 1,
  "notebook_id": "<notebook-id>",
  "daily_cap": 20,
  "concepts": {
    "photosynthesis": { "rank": 1, "name": "Photosynthesis", "focus": "Photosynthesis" }
  },
  "quizzes": [
    {
      "slot": "photosynthesis-d3-1",
      "concept": "photosynthesis",
      "difficulty": 3,
      "count": 8,
      "status": "reserved | pending | ready | failed",
      "artifact_id": "<artifact-id or null>",
      "requested": "2026-09-26",
      "submitted_at": "2026-09-26T02:02:00+00:00",
      "file": "quiz-bank/photosynthesis-d3-1.json",
      "question_count": 8,
      "reason": null
    }
  ]
}
```

### Normalized quiz (`quiz-bank/<slot>.json`)

```json
{
  "schema_version": 1,
  "slot": "photosynthesis-d3-1",
  "artifact_id": "<artifact-id>",
  "questions": [
    {
      "id": "3f9c2a1b7d4e",
      "question": "What is the main source of energy for photosynthesis?",
      "options": ["Carbon dioxide", "Sunlight", "Water", "Soil nutrients"],
      "answer_index": 1,
      "rationale": null,
      "hint": "Think about what a plant needs to be placed near."
    }
  ]
}
```

`bank import` reads the `nlm download quiz --format json` shape (`questions[].question`, `questions[].answerOptions[].text` / `.isCorrect`, optional `hint`; see `references/nlm-cli-quirks.md`). It rejects a quiz with no questions, or any question without at least two options and exactly one correct option.

### Student file (`students/<student-id>.json`)

```json
{
  "schema_version": 1,
  "student_id": "s-7f3a2c",
  "notebook_id": "<notebook-id>",
  "created": "2026-09-26",
  "concepts": {
    "photosynthesis": {
      "status": "partial",
      "score": 0.6,
      "step": 0,
      "next_review": null,
      "misconceptions": ["thinks CO2 is the energy source"],
      "explanations_tried": ["factory-analogy"],
      "rounds": [{ "date": "2026-09-26", "mode": "diagnose", "correct": 2, "asked": 3 }],
      "open_answers": [],
      "seen": {
        "3f9c2a1b7d4e": { "last_seen": "2026-09-26", "times": 1, "last_correct": false }
      }
    }
  }
}
```

`open_answers` holds answers recorded since the last `close-round` for that concept and mode.

## Privacy

See `references/privacy-and-safety.md`, section "Adaptive modes".
````

- [ ] **Step 2: Add the privacy section.** In `references/privacy-and-safety.md`, insert this block above the marker line `## Incident response`:

````markdown
## Adaptive modes

- Identify students by a random ID or a nickname they choose (3–32 lowercase letters, digits, or dashes). Never use a real name.
- Student files in `<pkg>/students/` store option indexes, scores, dates, and one-line misconception notes written by the agent. Never store the student's own free-text words.
- Nothing about students is sent to NotebookLM. Uploads stay curriculum-only.
- `students/` and `quiz-bank/` are ignored by git. Do not commit or share them.
- To delete a student's data, delete their file in `<pkg>/students/`.
````

- [ ] **Step 3: Ignore adaptive data.** In `.gitignore`, find the line `progress.json` and add two lines directly below it, so that part of the file reads:

```text
progress.json
students/
quiz-bank/
```

- [ ] **Step 4: Require the new files.** In `scripts/validate_skill.py`, find this text:

```python
    ROOT / "references" / "pipeline-patterns.md",
]
```

and replace it with:

```python
    ROOT / "references" / "pipeline-patterns.md",
    ROOT / "references" / "adaptive-learning.md",
    ROOT / "scripts" / "sherlock.py",
]
```

- [ ] **Step 5: Run the validator and the full suite.**

Run: `python3 scripts/validate_skill.py`
Expected: `VALIDATION PASSED` and `- required files: 9`.

Run: `python3 -m unittest discover -s tests`
Expected: `OK`.

- [ ] **Step 6: Commit.**

```bash
git add references/adaptive-learning.md references/privacy-and-safety.md .gitignore scripts/validate_skill.py
git commit -m "docs: add adaptive-learning reference and privacy rules"
```

---

### Task 13: Document the adaptive modes in `SKILL.md` and release notes (2.1.0)

**Files:**
- Modify: `SKILL.md` (seven replacements and one insertion)
- Modify: `scripts/validate_skill.py`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Test: `tests/test_docs.py`

**Interfaces:**
- Consumes: every command from Tasks 6–11. `tests/test_docs.py` fails if any doc names a `sherlock` command that does not exist.
- Produces: `SKILL.md` at version 2.1.0 with the section `## Adaptive Modes` and the headings `### Diagnose mode`, `### Teach mode`, `### Tutor mode`, `### Review mode`.

- [ ] **Step 1: Write the failing test.** Create `tests/test_docs.py` with exactly this content:

```python
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
```

- [ ] **Step 2: Run it and confirm it fails.**

Run: `python3 -m unittest discover -s tests -p 'test_docs.py'`
Expected: `FAILED (failures=1)`, with `'## Adaptive Modes' not found`.

- [ ] **Step 3: Edit the `SKILL.md` frontmatter and introduction.** Make each replacement below. Each "find" text occurs exactly once.

3a. Find:

```text
description: Turn curriculum files into NotebookLM study media.
version: 2.0.1
```

Replace with:

```text
description: Turn curriculum into NotebookLM study media and tutoring.
version: 2.1.0
```

3b. Find:

```text
    tags: [notebooklm, curriculum, video, study-materials]
```

Replace with:

```text
    tags: [notebooklm, curriculum, video, study-materials, tutoring]
```

3c. Find:

```text
Turn authorized curriculum documents into native NotebookLM videos or complete study packages. This skill
```

Replace with:

```text
Turn authorized curriculum documents into native NotebookLM videos or complete study packages, then tutor a student through them. This skill
```

3d. Find:

```text
- Identify frequently assessed concepts, then generate focused learning media.
```

Replace with:

```text
- Identify frequently assessed concepts, then generate focused learning media.
- Tutor a student: diagnose knowledge gaps, teach weak concepts, answer questions, and schedule reviews ("tutor me", "diagnose my knowledge", "adaptive study").
```

3e. Find:

```text
3. **Focused deep dive:** after the notebook-level package, generate explicitly requested concept-specific media using a two-to-five-word focus phrase.
```

Replace with:

```text
3. **Focused deep dive:** after the notebook-level package, generate explicitly requested concept-specific media using a two-to-five-word focus phrase.
4. **Adaptive tutoring:** diagnose, teach, tutor, and review one student at a time using NotebookLM quizzes. See Adaptive Modes.
```

- [ ] **Step 4: Insert the Adaptive Modes section.** In `SKILL.md`, insert this block above the marker line `## Output Structure`:

````markdown
## Adaptive Modes

After a notebook has a curriculum analysis (Step 3), Sherlock can tutor one student at a time in four modes: diagnose, teach, tutor, and review. NotebookLM generates the quiz questions (one focused quiz per concept). The bundled script `scripts/sherlock.py` does all grading and record keeping. Read `references/adaptive-learning.md` for the data files, rules, and full command reference.

Below, `sherlock` means `python3 <skill-dir>/scripts/sherlock.py` (the script next to this file) and `<pkg>` is the study package directory from Step 1. Every `sherlock` command takes `--dir <pkg>` and prints one JSON object. Never edit files in `<pkg>/quiz-bank/` or `<pkg>/students/` by hand.

### Adaptive rules

- The person in the chat is the student. Ask for a nickname (3–32 lowercase letters, digits, or dashes), never a real name, then run `sherlock student new --dir <pkg> --nickname <nickname>`. Without a nickname, `sherlock student new --dir <pkg>` generates an ID.
- Start every session with `nlm login --check` and `sherlock status --dir <pkg> --student <id>`. If login fails, tell the student to ask whoever set Sherlock up to run `nlm login`, and stop.
- Only quiz answers change mastery. Record each answer with `sherlock record` and end each round with `sherlock close-round`.
- `sherlock next` never includes correct answers. Do not reveal an answer before the student chooses; `sherlock record` returns the correct option afterwards for feedback.
- Pass `--choice` as the 0-based index of the option the student picked.
- If a `sherlock` command exits non-zero, read its one-line error, explain it plainly, and do not work around it by editing files.

### Diagnose mode

Use for a student's first session on a notebook.

1. If `<pkg>/quiz-bank/bank.json` does not exist, run `sherlock bank init --dir <pkg> --notebook-id <notebook-id>`. Then register each of the ten concepts from `curriculum-analysis.md` (run Step 3 first if it is missing). The focus must be 1–5 words:

   ```text
   sherlock bank add-concept --dir <pkg> --slug organ-systems --name "Human Organ Systems (Coordination & Excretion)" --focus "Organ Systems" --rank 1
   ```

2. Tell the user how many quizzes will be generated (one per concept without a ready or pending quiz) and that this uses NotebookLM quota. Obtain approval. This is the only approval prompt in the adaptive modes; later top-ups are limited by the script's daily cap.
3. For each concept by rank, one at a time:

   ```text
   sherlock bank request --dir <pkg> --concept <slug> --difficulty 3
   <run the exact "command" it printed: nlm quiz create ... --confirm --json>
   sherlock bank submitted --dir <pkg> --quiz <slot> --artifact-id <artifact_id from the nlm output>
   ```

   Submit sequentially; never background with `&`. If `nlm` errors, run `sherlock bank fail --dir <pkg> --quiz <slot> --reason "<error>"`.
4. Rolling start: run `sherlock bank pending --dir <pkg>`, then check each pending quiz with `nlm studio status <notebook-id> --json --full --artifact-id <artifact-id>`. When one is `completed`:

   ```text
   nlm download quiz <notebook-id> --id <artifact-id> --format json --output <pkg>/quiz-bank/downloads/<slot>.json
   sherlock bank import --dir <pkg> --quiz <slot> --file <pkg>/quiz-bank/downloads/<slot>.json
   ```

   Start quizzing as soon as the first concept is ready, and check the others between concepts.
5. For each ready concept: `sherlock next --dir <pkg> --student <id> --concept <slug> --count 3 --mode diagnose`. Ask each question with its options, run `sherlock record --dir <pkg> --student <id> --concept <slug> --mode diagnose --question <question-id> --choice <index>`, give brief feedback, then `sherlock close-round --dir <pkg> --student <id> --concept <slug> --mode diagnose`.
6. Finish with `sherlock status`: show each concept as mastered (green), partial (yellow), or weak (red).

### Teach mode

1. Run `sherlock status`. Take up to three concepts from `teach_queue`, in order.
2. If a concept's `unseen_questions` is below 5 and its `quizzes_pending` is 0, request a top-up at the target difficulty (weak: 2, partial: 3) and submit it as in Diagnose step 3 before explaining.
3. Explain the concept from the package files on disk (study guide, answer keys), aimed at its recorded `misconceptions` and avoiding strategies already in `explanations_tried`. Use `nlm notebook query` only when the package does not cover the concept. Record the strategy with `sherlock note --dir <pkg> --student <id> --concept <slug> --explanation <tag>` (for example `factory-analogy`). End with an unscored check-understanding question.
4. Import the top-up if it has completed. Then run `sherlock next ... --count 5 --mode teach`, ask each question, `record` each answer, and `close-round`.
5. If the concept is not mastered, try a different explanation and another round. `status` removes a concept from `teach_queue` after three teach rounds in one day; flag it for the next session.
6. End with what improved, what still needs work, and the next review dates.

### Tutor mode

1. Answer the student's question from the package files, or with `nlm notebook query` when a cited curriculum answer is needed.
2. Follow up with a check-understanding question. Never reveal answers to quiz-bank questions.
3. Tutor mode never calls `record` or `close-round`. When the student shows a misconception, record it with `sherlock note --dir <pkg> --student <id> --concept <slug> --misconception "<one line, at most 120 characters>"` and suggest teach mode.

### Review mode

1. Run `sherlock due --dir <pkg> --student <id>` to list concepts due today.
2. For each: `sherlock next ... --count 5 --mode review`, ask, `record`, then `close-round`. Review may repeat questions the student has seen before; that is intended.
3. Show what passed, what returned to the teach queue, and the next review dates.

### Adaptive failure handling

| Situation | Do this |
|---|---|
| `next` returns fewer questions than asked (`shortfall` > 0) | Use what came back. Move to another concept and return later, or request a top-up. Tell the student what is happening. |
| Studio status `unknown` | Keep polling until `minutes_pending` reaches 10; never submit a duplicate while one is pending. Then `sherlock bank fail`. |
| Studio status `failed` | `sherlock bank fail`, then request once more. After a second failure, skip the concept for today. |
| Rate limited (`code 8`) | `sherlock bank fail`, wait 5 minutes, then request again. The script allows 3 requests per concept per day. |
| `bank import` fails validation | The quiz is marked failed and its questions are never shown. Request another if needed. |
| `bank request` reports the daily cap | Continue with questions already in the bank and tell the student. |
````

- [ ] **Step 5: Update the output structure and verification list in `SKILL.md`.**

5a. Find:

```text
├── answer-keys.md
└── study-package-index.md
```

Replace with:

```text
├── answer-keys.md
├── study-package-index.md
├── quiz-bank/              # adaptive modes: shared quiz bank (bank.json + normalized quizzes)
└── students/               # adaptive modes: one progress file per student; never commit
```

5b. Find:

```text
- The final report distinguishes completed, failed, and skipped artifacts.
```

Replace with:

```text
- The final report distinguishes completed, failed, and skipped artifacts.
- Adaptive sessions changed quiz-bank and student files only through `scripts/sherlock.py`.
```

- [ ] **Step 6: Require `SKILL.md` to reference the new files.** In `scripts/validate_skill.py`, find:

```python
    "references/nlm-cli-quirks.md",
]
```

and replace it with:

```python
    "references/nlm-cli-quirks.md",
    "references/adaptive-learning.md",
    "scripts/sherlock.py",
]
```

- [ ] **Step 7: Add the README section.** In `README.md`, insert this block above the marker line `## Privacy and authentication`:

````markdown
## Adaptive study modes

Once a notebook has a curriculum analysis, Sherlock can tutor one student at a time:

- **Diagnose:** a short quiz on every concept finds what the student already knows.
- **Teach:** explains weak concepts, then quizzes until they are mastered.
- **Tutor:** answers the student's own questions from the curriculum.
- **Review:** brings mastered concepts back after 1, 2, 4, 8, 16, 30, then 60 days.

NotebookLM writes the quiz questions, one focused quiz per concept. The bundled `scripts/sherlock.py` grades answers and keeps records in the study package directory.

```text
Use sherlock-study-boy in diagnose mode.
Study package: ./study-packages/forces-review
```

The first diagnose on a notebook generates about ten quizzes and asks before doing so. After that, the script allows at most 20 quiz generations per day (set with `bank init --daily-cap`). Student progress stays in `students/` inside the study package directory; it is never uploaded or committed.
````

- [ ] **Step 8: Add the 2.1.0 changelog entry.** In `CHANGELOG.md`, insert this block above the marker line that starts `## [2.0.1]`. Use today's date in the heading if it is not 2026-09-26.

````markdown
## [2.1.0] - 2026-09-26

### Added
- Working adaptive modes: diagnose, teach, tutor, and review, for one student at a time.
- `scripts/sherlock.py`, a standard-library script that owns the shared quiz bank, student
  progress, grading, mastery thresholds, the review schedule (1, 2, 4, 8, 16, 30, 60 days),
  question selection, and a daily quiz-generation cap.
- NotebookLM native quizzes as the question source, one focused quiz per concept.
- `references/adaptive-learning.md` with the data files, rules, and command reference.
- Offline tests for the script and a check that the docs only name real commands.

### Changed
- The frontmatter description now covers tutoring.
- Privacy guidance covers student progress files.
````

- [ ] **Step 9: Run everything.**

Run: `python3 scripts/validate_skill.py`
Expected: `VALIDATION PASSED` and `- required files: 9`.

Run: `python3 -m unittest discover -s tests -v`
Expected: `Ran 79 tests` and `OK`. In particular `test_version_matches_newest_changelog_entry`, `test_workflow_steps_are_contiguous`, and all `test_docs` tests pass.

Run: `grep -c '^### [0-9]' SKILL.md`
Expected: `9`.

- [ ] **Step 10: Commit.**

```bash
git add SKILL.md scripts/validate_skill.py README.md CHANGELOG.md tests/test_docs.py
git commit -m "feat: document adaptive modes in SKILL.md (2.1.0)"
```

---

### Task 14: Live end-to-end run (human approval required; uses NotebookLM quota)

**Why:** The offline tests prove the rules. This run proves the real loop: a real quiz from NotebookLM imports cleanly, and diagnose → teach → review behave as specified. It uses one quiz generation, or two if the optional top-up step is approved.

**Files:**
- Create: `docs/runs/<YYYY-MM-DD>-e2e.md`

- [ ] **Step 1: STOP and ask the human, word for word:**

> Task 14 is a live test against NotebookLM. It generates one quiz (two if you also approve the optional top-up check) on a notebook you choose. Please give me: (1) the notebook ID of a notebook with curriculum-only sources, (2) one concept from it and a 1–5 word focus phrase for that concept, and (3) permission to proceed, with or without the top-up check.

Do nothing further until you have all three answers.

- [ ] **Step 2: Preflight.**

```bash
nlm --version
nlm login --check
```

Expected: a version line (0.9.14 was tested) and a successful login check. If the login check fails, ask the human to run `nlm login`, then stop until they confirm.

**Conventions for Steps 3–10.** Shell variables may not survive between commands in your environment, so every command below is written out in full. Before running each one, replace these placeholders with literal values: `<notebook-id>` (from the human), `<artifact-id>` (from Step 4), `<tomorrow>` (tomorrow's date as `YYYY-MM-DD`). The package directory is always `~/study-packages/sherlock-e2e`, and the concept slug is always `concept-1`. Run everything from the repository root.

- [ ] **Step 3: Set up a package directory outside the repository.** If `~/study-packages/sherlock-e2e` already exists, ask the human whether to delete it before continuing. Replace `<concept-name>` and `<focus>` with the human's answers.

```bash
mkdir -p ~/study-packages/sherlock-e2e/quiz-bank/downloads
python3 scripts/sherlock.py bank init --dir ~/study-packages/sherlock-e2e --notebook-id <notebook-id>
python3 scripts/sherlock.py bank add-concept --dir ~/study-packages/sherlock-e2e --slug concept-1 --name "<concept-name>" --focus "<focus>" --rank 1
python3 scripts/sherlock.py bank request --dir ~/study-packages/sherlock-e2e --concept concept-1 --difficulty 3
```

Expected: the last command prints `"slot": "concept-1-d3-1"` and a `command_line`.

- [ ] **Step 4: Generate the quiz.** Run the exact `command_line` printed in Step 3. Expected: JSON containing `"artifact_id"`. That value is `<artifact-id>` from now on; never write it into a repository file. Then:

```bash
python3 scripts/sherlock.py bank submitted --dir ~/study-packages/sherlock-e2e --quiz concept-1-d3-1 --artifact-id <artifact-id>
```

If `nlm` returned an error instead of an artifact ID, run `python3 scripts/sherlock.py bank fail --dir ~/study-packages/sherlock-e2e --quiz concept-1-d3-1 --reason "<error text>"`, report the error to the human, and stop.

- [ ] **Step 5: Poll until complete (at most 10 minutes).** Every 60 seconds run:

```bash
nlm studio status <notebook-id> --json --full --artifact-id <artifact-id>
```

Continue while the status is `in_progress` or `unknown`. On `completed`, go to Step 6. On `failed`, or after 10 minutes, run the `bank fail` command from Step 4 with the reason, report it to the human, and stop.

- [ ] **Step 6: Download and import.**

```bash
nlm download quiz <notebook-id> --id <artifact-id> --format json --output ~/study-packages/sherlock-e2e/quiz-bank/downloads/concept-1-d3-1.json
python3 scripts/sherlock.py bank import --dir ~/study-packages/sherlock-e2e --quiz concept-1-d3-1 --file ~/study-packages/sherlock-e2e/quiz-bank/downloads/concept-1-d3-1.json
```

Expected: `"status": "ready"` and a `question_count` of 8 or close to it. **If import fails validation, stop.** The real format has changed from what `nlm` 0.9.14's source produces. Report the exact error and the file's keys to the human:

```bash
python3 -c "import json, os; d = json.load(open(os.path.expanduser('~/study-packages/sherlock-e2e/quiz-bank/downloads/concept-1-d3-1.json'))); print(list(d)); print(list(d['questions'][0]))"
```

Do not change `normalize_quiz` without the human's approval.

- [ ] **Step 7: Diagnose round: aim for partial (2 of 3 correct).** For this test only, read the answer key from the normalized quiz file so you can answer deliberately:

```bash
python3 scripts/sherlock.py student new --dir ~/study-packages/sherlock-e2e --nickname e2e-tester
python3 scripts/sherlock.py next --dir ~/study-packages/sherlock-e2e --student e2e-tester --concept concept-1 --count 3 --mode diagnose
python3 -c "import json, os; [print(q['id'], q['answer_index']) for q in json.load(open(os.path.expanduser('~/study-packages/sherlock-e2e/quiz-bank/concept-1-d3-1.json')))['questions']]"
```

For the 3 question IDs that `next` returned: record the first two using their `answer_index` as the choice, and the third with a wrong choice (`answer_index` + 1, or 0 if that is past the last option). One command per answer:

```bash
python3 scripts/sherlock.py record --dir ~/study-packages/sherlock-e2e --student e2e-tester --concept concept-1 --mode diagnose --question <question-id> --choice <index>
```

Then:

```bash
python3 scripts/sherlock.py close-round --dir ~/study-packages/sherlock-e2e --student e2e-tester --concept concept-1 --mode diagnose
```

Expected: `"correct": 2`, `"asked": 3`, `"status": "partial"`, `"step": 0`, `"next_review": null`.

- [ ] **Step 8: Teach round: aim for mastered (5 of 5).**

```bash
python3 scripts/sherlock.py next --dir ~/study-packages/sherlock-e2e --student e2e-tester --concept concept-1 --count 5 --mode teach
```

Check that none of the 5 IDs were used in Step 7. Record all 5 correctly (as in Step 7, with `--mode teach`), then:

```bash
python3 scripts/sherlock.py close-round --dir ~/study-packages/sherlock-e2e --student e2e-tester --concept concept-1 --mode teach
```

Expected: `"status": "mastered"`, `"step": 0`, and `"next_review"` equal to tomorrow's date.

- [ ] **Step 9: Review round, dated tomorrow.**

```bash
python3 scripts/sherlock.py due --dir ~/study-packages/sherlock-e2e --student e2e-tester --today <tomorrow>
python3 scripts/sherlock.py next --dir ~/study-packages/sherlock-e2e --student e2e-tester --concept concept-1 --count 5 --mode review --today <tomorrow>
```

Expected: `due` lists `concept-1`, and `next` returns 5 questions (reusing seen ones is expected). Record all 5 correctly with `--mode review --today <tomorrow>`, then:

```bash
python3 scripts/sherlock.py close-round --dir ~/study-packages/sherlock-e2e --student e2e-tester --concept concept-1 --mode review --today <tomorrow>
```

Expected: `"step": 1` and `"next_review"` two days after `<tomorrow>`.

- [ ] **Step 10 (only if the human approved the top-up check): top-up quiz.**

```bash
python3 scripts/sherlock.py status --dir ~/study-packages/sherlock-e2e --student e2e-tester
```

Expected: `unseen_questions` is 0 for `concept-1`. Then repeat Steps 3 (only the `bank request` line, with `--difficulty 4`), 4, 5, and 6 using slot `concept-1-d4-1`, and run `status` again. Expected: `unseen_questions` is greater than 0.

- [ ] **Step 11: Write the run log.** Create `docs/runs/<today YYYY-MM-DD>-e2e.md` with the template below, filled in with real results. **Do not include notebook IDs, artifact IDs, question text, or concept names**; call the concept "concept-1".

````markdown
# Live end-to-end run — <YYYY-MM-DD>

- `nlm` version: <from Step 2>
- Python version: <python3 --version>
- Quiz generations used: <1 or 2>

| Step | Expected | Actual | Pass |
|---|---|---|---|
| Import real quiz | status ready, ~8 questions | <status, count> | <yes/no> |
| Diagnose 2/3 | partial, step 0, no review | <…> | <yes/no> |
| Teach 5/5 | mastered, step 0, review tomorrow | <…> | <yes/no> |
| Teach used only unseen questions | no overlap with diagnose | <…> | <yes/no> |
| Review 5/5 (tomorrow) | step 1, review +2 days | <…> | <yes/no> |
| Top-up (optional) | unseen questions > 0 afterwards | <… or skipped> | <yes/no/skipped> |

## Issues found

<None, or each issue with the exact error text.>
````

- [ ] **Step 12: Validate and commit the log.**

```bash
python3 scripts/validate_skill.py
python3 -m unittest discover -s tests
git add docs/runs/
git commit -m "docs: add live end-to-end run log"
```

Expected: `VALIDATION PASSED` (it fails if a UUID slipped into the log; remove it) and `OK`.

- [ ] **Step 13: Tell the human** where the package directory is (`~/study-packages/sherlock-e2e`). It contains curriculum-derived quiz content and should not be shared. Report any failed rows.

---

### Task 15: Release checkpoint for v2.1.0 (human approval required)

- [ ] **Step 1: Final local check.**

```bash
python3 scripts/validate_skill.py
python3 -m unittest discover -s tests
git status --short
```

Expected: `VALIDATION PASSED`, `OK`, and no output from `git status --short`.

- [ ] **Step 2: STOP and ask the human, word for word:**

> Milestone 2 (v2.1.0 adaptive modes) is complete, the live run is logged in docs/runs/, and everything passes locally. May I push the branch and open a pull request into main?

- [ ] **Step 3: On approval, push and open the pull request.** Before pushing, confirm nobody else has changed `main`:

```bash
git fetch origin
git log --oneline HEAD..origin/main
```

Expected: no output. If it lists commits, stop and tell the human; do not push.

Then push, using the current branch name:

```bash
git push -u origin "$(git branch --show-current)"
gh pr create --base main --title "v2.1.0: adaptive modes with NotebookLM quizzes" --body "Adds diagnose, teach, tutor, and review modes. NotebookLM generates one focused quiz per concept; scripts/sherlock.py owns the quiz bank, student progress, grading, the 1-2-4-8-16-30-60 day review schedule, question selection, and a daily quiz cap. Includes offline tests (79), a docs/commands consistency test, and a live end-to-end run log."
```

- [ ] **Step 4: Wait for CI** with `gh pr checks --watch`. Both Python jobs must pass. Then ask the human to merge.

- [ ] **Step 5: After the merge, with approval, tag the release.**

```bash
git checkout main
git pull
git tag v2.1.0
git push origin v2.1.0
```

- [ ] **Step 6: Update the Hermes copy of the skill (plain copy, as in Task 5 Step 7).** Run from the repository root, on `main` at the `v2.1.0` tag:

```bash
git describe --tags --exact-match
cp -R ~/.hermes/skills/research/sherlock-study-boy ~/sherlock-study-boy-hermes-backup-$(date +%Y%m%d)-v2.1.0
rsync -a --delete --exclude .git --exclude .github --exclude __pycache__ --exclude docs --exclude tests --exclude .gitignore ./ ~/.hermes/skills/research/sherlock-study-boy/
diff -rq --exclude=.git --exclude=.github --exclude=__pycache__ --exclude=docs --exclude=tests --exclude=.gitignore . ~/.hermes/skills/research/sherlock-study-boy && echo identical
head -4 ~/.hermes/skills/research/sherlock-study-boy/SKILL.md
```

Then check the script runs from the installed copy:

```bash
python3 ~/.hermes/skills/research/sherlock-study-boy/scripts/sherlock.py --help
```

Expected: `git describe` prints `v2.1.0`; `diff` prints only `identical`; the `head` output includes `version: 2.1.0`; `--help` prints a usage line starting `usage: sherlock.py`. Tell the human where the backup is and to start a new Hermes session so the skill reloads.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `SyntaxError` or `IndentationError` in `sherlock.py` | A block was pasted inside another function, or indentation changed | Functions go above the `# --- CLI` line at column 0; parser blocks go above `    return parser` with 4-space indentation |
| `NameError: name 'cmd_…' is not defined` | Parser block pasted, function block missing | Do the "Insert the functions" step of that task |
| `invalid choice: '…'` after implementing | Parser block missing or pasted after `return parser` | Move it above `    return parser` |
| A marker line appears twice | A block was pasted twice | Remove the duplicate |
| Validator: `forbidden content found: real UUID in …` | A notebook or artifact ID was pasted into a file | Replace it with a placeholder like `<notebook-id>` |
| Validator: `forbidden content found: machine-specific user path in …` | A path with a real home directory name was written | Use `~` instead |
| `test_version_matches_newest_changelog_entry` fails | `SKILL.md` version and newest `CHANGELOG.md` heading differ | Make them the same version |
| `test_workflow_steps_are_contiguous` fails | A heading like `### 10.` or `### 1 ` was added | Rename it; only the nine procedure steps may start `### <digit>` |
