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
