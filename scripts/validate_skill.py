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
        file_text = read_text_or_none(path)
        if file_text is None:
            continue
        for label, pattern in FORBIDDEN_PATTERNS.items():
            if pattern.search(file_text):
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
