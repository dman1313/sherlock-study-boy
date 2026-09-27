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
AUTO_MARKED_TYPES = ("multiple_choice", "multiple_select", "fill_in_the_blank")
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


# --- Quiz import -------------------------------------------------------------


def question_id(text: str) -> str:
    """Stable ID: first 12 hex chars of SHA-256 of the lowercased, whitespace-collapsed text."""
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:12]



def normalize_answer_text(text: str) -> str:
    """Comparable form of a short answer: drop LaTeX commands, case, and non-alphanumerics."""
    return re.sub(r"[^a-z0-9]", "", re.sub(r"\\[a-zA-Z]+", "", text).lower())


def _clean(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def normalize_question(item: object, number: int) -> dict:
    """Normalize one question; raise SherlockError if it cannot be used."""
    if not isinstance(item, dict):
        raise SherlockError(f"question {number} is not an object")
    text = _clean(item.get("question"))
    if text is None:
        raise SherlockError(f"question {number} has no text")
    kind = item.get("type") or "multiple_choice"
    if item.get("imageUrls"):
        raise SherlockError(f"question {number} needs an image the student cannot see")
    question = {
        "id": question_id(text),
        "type": kind,
        "question": text,
        "options": [],
        "answer_index": None,
        "answer_indexes": [],
        "answers": [],
        "model_answer": None,
        "rationale": _clean(item.get("rationale")),
        "hint": _clean(item.get("hint")),
    }
    if kind in ("multiple_choice", "multiple_select"):
        options = item.get("answerOptions")
        if not isinstance(options, list) or len(options) < 2:
            raise SherlockError(f"question {number} needs at least two answer options")
        correct = []
        for index, option in enumerate(options):
            option_text = _clean(option.get("text")) if isinstance(option, dict) else None
            if option_text is None:
                raise SherlockError(f"question {number} option {index + 1} has no text")
            question["options"].append(option_text)
            if option.get("isCorrect") is True:
                correct.append(index)
        if kind == "multiple_choice" and len(correct) != 1:
            raise SherlockError(
                f"question {number} must have exactly one correct option, found {len(correct)}"
            )
        if kind == "multiple_select" and not correct:
            raise SherlockError(f"question {number} has no correct option")
        question["answer_indexes"] = correct
        if kind == "multiple_choice":
            question["answer_index"] = correct[0]
            question["rationale"] = _clean(options[correct[0]].get("rationale"))
    elif kind == "fill_in_the_blank":
        best = _clean(item.get("bestAnswer"))
        if best is None:
            raise SherlockError(f"question {number} has no best answer")
        extras = item.get("acceptableAnswers") or []
        question["answers"] = [best] + [a for a in (_clean(x) for x in extras) if a]
    elif kind == "short_answer":
        grading = item.get("grading") if isinstance(item.get("grading"), dict) else {}
        question["model_answer"] = _clean(grading.get("modelAnswer"))
        if question["model_answer"] is None:
            raise SherlockError(f"question {number} has no model answer")
    else:
        raise SherlockError(f"question {number} has unsupported type {kind!r}")
    return question


def normalize_quiz(raw: object, slot: str, artifact_id: str) -> dict:
    """Convert `nlm download quiz --format json` output into the bank's format.

    Unusable questions are skipped with a reason. Raises SherlockError when the
    quiz has no question the script can mark automatically.
    """
    if not isinstance(raw, dict) or not isinstance(raw.get("questions"), list):
        raise SherlockError("quiz JSON must be an object with a 'questions' list")
    questions = []
    skipped = []
    seen_ids = set()
    for number, item in enumerate(raw["questions"], start=1):
        try:
            question = normalize_question(item, number)
        except SherlockError as exc:
            skipped.append(str(exc))
            continue
        if question["id"] in seen_ids:
            continue
        seen_ids.add(question["id"])
        questions.append(question)
    if not any(q["type"] in AUTO_MARKED_TYPES for q in questions):
        detail = f" (skipped: {'; '.join(skipped[:3])})" if skipped else ""
        raise SherlockError(f"quiz has no questions that can be marked automatically{detail}")
    return {
        "schema_version": SCHEMA_VERSION,
        "slot": slot,
        "artifact_id": artifact_id,
        "questions": questions,
        "skipped": skipped,
    }



def cmd_bank_import(args: argparse.Namespace) -> dict:
    pkg = package_dir(args)
    bank = load_json(bank_file(pkg))
    quiz = find_quiz(bank, args.quiz)
    retry = quiz["status"] == "failed" and quiz["artifact_id"] is not None
    if quiz["status"] != "pending" and not retry:
        raise SherlockError(
            f"{args.quiz} is {quiz['status']}; only pending quizzes, or failed ones that were "
            "submitted to NotebookLM, can be imported"
        )
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
    gradable = sum(1 for q in normalized["questions"] if q["type"] in AUTO_MARKED_TYPES)
    quiz.update(
        status="ready",
        question_count=len(normalized["questions"]),
        gradable_count=gradable,
        skipped=len(normalized["skipped"]),
        reason=None,
    )
    save_json(bank_file(pkg), bank)
    return {
        "slot": args.quiz,
        "status": "ready",
        "question_count": quiz["question_count"],
        "gradable_count": gradable,
        "skipped": quiz["skipped"],
    }


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


# --- Students and rounds -----------------------------------------------------


def ready_questions(pkg: Path, bank: dict, concept: str) -> list:
    """(difficulty, question) for every question in the concept's ready quizzes, deduplicated by ID."""
    found = {}
    for quiz in bank["quizzes"]:
        if quiz["concept"] != concept or quiz["status"] != "ready":
            continue
        for question in load_json(pkg / quiz["file"])["questions"]:
            if question.get("type", "multiple_choice") in AUTO_MARKED_TYPES:
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
                "type": q.get("type", "multiple_choice"),
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
    correct, given, feedback = grade_answer(match, args)
    times = record["seen"].get(args.question, {}).get("times", 0)
    record["seen"][args.question] = {
        "last_seen": today.isoformat(),
        "times": times + 1,
        "last_correct": correct,
    }
    record["open_answers"].append(
        {"question": args.question, "mode": args.mode, "choice": given, "correct": correct}
    )
    save_json(student_file(pkg, args.student), student)
    return {
        "question": args.question,
        "type": match.get("type", "multiple_choice"),
        "correct": correct,
        **feedback,
        "rationale": match["rationale"],
        "answered_this_round": sum(
            1 for answer in record["open_answers"] if answer["mode"] == args.mode
        ),
    }


def grade_answer(question: dict, args: argparse.Namespace) -> tuple:
    """Return (correct, value_to_store, feedback_fields). Free text is never stored."""
    kind = question.get("type", "multiple_choice")
    options = question["options"]
    if kind == "multiple_choice":
        if args.choice is None:
            raise SherlockError("this is a multiple_choice question; pass --choice <index>")
        if not 0 <= args.choice < len(options):
            raise SherlockError(f"--choice must be 0-{len(options) - 1}")
        index = question["answer_index"]
        return (args.choice == index, args.choice,
                {"correct_index": index, "correct_option": options[index]})
    if kind == "multiple_select":
        if args.choices is None:
            raise SherlockError("this is a multiple_select question; pass --choices <i,j,...>")
        try:
            picked = [int(part) for part in args.choices.split(",")]
        except ValueError as exc:
            raise SherlockError("--choices must be comma-separated option indexes") from exc
        if len(set(picked)) != len(picked) or not all(0 <= i < len(options) for i in picked):
            raise SherlockError(f"--choices must be distinct indexes from 0-{len(options) - 1}")
        wanted = question["answer_indexes"]
        return (sorted(picked) == sorted(wanted), sorted(picked),
                {"correct_indexes": wanted, "correct_options": [options[i] for i in wanted]})
    if args.text is None:
        raise SherlockError("this is a fill_in_the_blank question; pass --text <answer>")
    accepted = {normalize_answer_text(answer) for answer in question["answers"]}
    return (normalize_answer_text(args.text) in accepted, None,
            {"accepted_answers": question["answers"]})



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

    p = actions.add_parser("import", parents=[common], help="import a downloaded quiz")
    p.add_argument("--quiz", required=True)
    p.add_argument("--file", required=True)
    p.set_defaults(handler=cmd_bank_import)

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
    answer = p.add_mutually_exclusive_group(required=True)
    answer.add_argument("--choice", type=int, help="0-based option index (multiple_choice)")
    answer.add_argument("--choices", help="comma-separated 0-based indexes (multiple_select)")
    answer.add_argument("--text", help="the student's answer (fill_in_the_blank); never stored")

    p = student_command("close-round", "score the open round", cmd_close_round)
    p.add_argument("--concept", required=True)
    p.add_argument("--mode", choices=MODES, required=True)

    p = student_command("note", "record a misconception or explanation tag", cmd_note)
    p.add_argument("--concept", required=True)
    group = p.add_mutually_exclusive_group(required=True)
    group.add_argument("--misconception")
    group.add_argument("--explanation")

    student_command("status", "show progress and queues", cmd_status)
    student_command("due", "list concepts due for review", cmd_due)

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
