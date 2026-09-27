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
