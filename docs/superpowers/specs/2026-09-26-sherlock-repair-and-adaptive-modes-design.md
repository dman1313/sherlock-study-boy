# Sherlock Study Boy — Repair and Adaptive Modes

- **Date:** 2026-09-26
- **Status:** Design approved section by section; awaiting written-spec review
- **Releases:** v2.0.1 (Milestone 1), v2.1.0 (Milestone 2)

## 1. Summary

Finish Sherlock Study Boy as a working agent skill in two milestones:

1. **Repair (v2.0.1):** restore the clean v1 skill that the v2.0.0 commit overwrote, fix the validator bug that has kept CI red since v1, and fold in real-session notes from the locally installed Hermes copy.
2. **Adaptive modes (v2.1.0):** make diagnose, teach, tutor, and review actually work. NotebookLM generates the quiz questions (one focused quiz per concept), a shared per-notebook quiz bank holds them ahead of time, and a small stdlib-only script, `scripts/sherlock.py`, owns all grading, mastery, scheduling, and quota bookkeeping. The host agent (Claude Code or Hermes) does the conversation itself; K3/Nebius is removed.

## 2. Current state (2026-09-26)

- **v2.0.0 regressed `SKILL.md`.** Commit `61bf61d` replaced the v1 `SKILL.md` with the pre-v1 draft (VPS-only instructions, steps numbered 1–7, 9, 8, a real notebook ID, stale download extensions, a link to the missing `references/pipeline-v2-patterns.md`) and appended the adaptive modes. The validator reports 8 errors; 3 of 4 tests fail.
- **CI has never passed.** On v1, the validator scanned `scripts/__pycache__/*.pyc` created by the test run. The bytecode embeds the CI runner's absolute home-directory path, which trips the validator's own machine-specific-path check. On v2.0.0 it also fails for the regression above.
- **Adaptive modes are prose only.** No code exists; `ask_k3` is a stub. The docs contain three different review schedules (CHANGELOG, SKILL.md table, review procedure) and two different progress schemas.
- **The Hermes-installed copy diverged.** `~/.hermes/skills/research/sherlock-study-boy` is not a git checkout. It never received the v1 cleanup, which is the likely source of the regression. It holds richer real-session notes (`nlm-cli-quirks.md`: 152 lines vs 62 in the repo; `pipeline-v2-patterns.md`: 95 lines vs 48 in `pipeline-patterns.md`). Its `web/` directory is empty.
- `nlm` 0.9.14 is installed locally. `nlm quiz create` supports `--count`, `--difficulty 1-5`, `--focus`, `--source-ids`, `--json`. `nlm download quiz` defaults to JSON. No sample quiz JSON exists on disk, so its exact shape is unverified.

## 3. Goals and non-goals

### Goals

- A skill that passes its validator and CI, installs cleanly on Claude Code and Hermes, and documents only behavior that exists.
- A student can talk to the agent directly and run diagnose → teach → review across days, with progress persisted and scheduling done deterministically.
- All grading, mastery, scheduling, question selection, and quota rules live in tested code, not prose.

### Non-goals

- A standalone engine that runs without an agent, or any direct LLM API integration (K3, Nebius, DeepSeek).
- A student web UI. (If wanted later, it gets its own spec and builds on `sherlock.py`.)
- Teacher/class dashboards or multi-student rosters beyond one file per student.
- Tutor-inferred mastery. Only quiz answers change scores.
- Cross-notebook progress, or syncing progress between machines.

## 4. Decisions

| # | Decision | Chosen | Rejected |
|---|---|---|---|
| D1 | Finish line | Working skill; host agent tutors | Standalone K3 engine; web app; repair only |
| D2 | Who is in the chat | One student, directly | Teacher running a class; adult beside student |
| D3 | Question source | NotebookLM native quizzes, one focused quiz per concept | Agent-written questions from package files; instructions only |
| D4 | Bookkeeping | `scripts/sherlock.py` owns all state changes | Agent edits JSON by hand |
| D5 | Mode flows | As in §6.5 | Tutor scoring; 5-question diagnose |
| D6 | Records and schedule | As in §6.3–6.4 | Gentler one-rung-back on review failure |
| D7 | Failures and quota | One approval for first bank fill; daily cap of 20 generations enforced by the script | Approval before every generation |
| D8 | Done | CI green, tests pass, one live end-to-end run with a run log, both releases tagged | Tests only |

## 5. Milestone 1 — Repair (v2.0.1)

### Requirements

**R1.1 Restore `SKILL.md` from v1.** Start from `SKILL.md` at commit `c3d3033`. Keep its nine contiguous procedure steps, approval gates, validation table, output structure, pitfalls, and verification checklist. Remove all K3/Nebius content and the v2.0.0 adaptive-mode prose; the adaptive modes return, rewritten, in Milestone 2. Frontmatter:

```yaml
name: sherlock-study-boy
description: Turn curriculum into NotebookLM study media and tutoring.
version: 2.0.1
author: Dwayne Primeau, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
```

The description must stay ≤ 60 characters and end with a period (validator rule). Trigger phrases belong in the body's "When to Use" section.

**R1.2 Fix the validator's file scan.** `validate_skill.py` scans only files tracked by git (`git ls-files -z`). When the directory is not a git checkout (for example, a copy installed by `npx skills add`), fall back to walking the tree while skipping `.git/`, `__pycache__/`, and files that are not valid UTF-8. Add a regression test that creates a `__pycache__` file containing a machine-specific path and asserts the validator still passes.

**R1.3 Make version checks self-maintaining.** Replace the hard-coded `"1.0.0"` assertion with a test that the frontmatter `version` equals the newest version heading in `CHANGELOG.md`.

**R1.4 Merge real-session notes.** Fold the extra material from the Hermes copy's `nlm-cli-quirks.md` and `pipeline-v2-patterns.md` into the repo's `references/nlm-cli-quirks.md` and `references/pipeline-patterns.md`. Do not add a separate `pipeline-v2-patterns.md`. Remove notebook IDs, artifact IDs, machine paths, and anything the validator forbids. Where the Hermes notes conflict with v1's validated 0.9.14 syntax, v1 wins unless `nlm <command> --help` shows otherwise.

**R1.5 Correct the record.** `CHANGELOG.md` gets a 2.0.1 entry stating that 2.0.0's `SKILL.md` regressed to a pre-v1 draft, that the K3 adaptive modes were documented but never implemented and have been withdrawn pending 2.1.0, and that CI now runs green. `references/adaptive-learning.md` is removed in this milestone and rewritten in Milestone 2.

**R1.6 CI upkeep.** Update `actions/checkout` and `actions/setup-python` to current major versions that run on Node 24. Run tests on Python 3.10 and 3.12, matching the README's "Python 3.10+" claim.

**R1.7 Stop the divergence (requires user approval, outside the repo).** Replace the Hermes-installed copy with a git clone of this repository, as the README already instructs, after backing up the existing directory. This prevents a future commit from being made against a stale copy again.

### Acceptance

- `python3 scripts/validate_skill.py` prints `VALIDATION PASSED`.
- `python3 -m unittest discover -s tests -v` passes on Python 3.10 and 3.12.
- CI is green on `main`.
- Tag `v2.0.1`.

## 6. Milestone 2 — Adaptive modes (v2.1.0)

### 6.1 Layout

Everything lives under the study package directory from v1 Step 1 (default `./study-packages/<safe-title>/`, referred to below as `<pkg>`):

```text
<pkg>/
├── manifest.json, curriculum-analysis.md, … (v1 package files)
├── quiz-bank/
│   ├── bank.json                      # shared by every student of this notebook
│   └── <concept>-d<difficulty>-<n>.json   # normalized quiz, one per NotebookLM quiz artifact
└── students/
    └── <student-id>.json              # one progress file per student
```

`quiz-bank/` holds curriculum-derived content only. `students/` holds student progress and is never committed; `.gitignore` gains `students/` and `quiz-bank/` in addition to the existing `study-packages/`.

### 6.2 `scripts/sherlock.py` interface

- Python 3.10+, standard library only, single file.
- Every command takes `--dir <pkg>`. Every command accepts `--today YYYY-MM-DD` (default: local date) so date logic is testable.
- Every command prints one JSON object to stdout. Errors print a one-line message to stderr and exit `1` (bad input or refused action) or `2` (unreadable data or unknown `schema_version`).
- All writes are atomic: write to a temporary file in the same directory, `fsync`, then `os.replace`.

| Command | Purpose |
|---|---|
| `bank init --notebook-id <id> [--daily-cap 20]` | Create `quiz-bank/bank.json`. |
| `bank concept add --slug <slug> --name <name> --focus <phrase> --rank <n>` | Register a concept. Refuses a focus phrase longer than 5 words or a duplicate slug. |
| `bank quota` | Report `used_today`, `cap`, `remaining`. |
| `bank request --concept <slug> --difficulty <1-5> [--count 8]` | Reserve a quiz slot and count it against today's cap; refuses when the cap is reached. Prints the slot name and the exact `nlm quiz create` command to run, built from the concept's stored focus phrase, so the agent never composes focus or difficulty flags by hand. |
| `bank submitted --quiz <slot> --artifact-id <id>` | Mark the slot `pending` with its NotebookLM artifact ID. |
| `bank pending` | List pending slots with artifact IDs and minutes since submission, for polling. |
| `bank import --quiz <slot> --file <downloaded.json>` | Validate and normalize a downloaded quiz into the bank; mark `ready`, or `failed` if validation fails. |
| `bank fail --quiz <slot> --reason <text>` | Mark a slot `failed` (generation failed, timed out, or submission errored). |
| `student new [--nickname <nick>]` | Create a student file with every bank concept `untested`. Without a nickname, generate `s-` plus 6 random hex characters. Nicknames must match `^[a-z0-9][a-z0-9-]{2,31}$`. |
| `next --student <id> --concept <slug> --count <n> --mode <mode>` | Select questions (§6.4). Prints question IDs, text, and options, plus `unseen_remaining`. Never prints correct answers. |
| `record --student <id> --concept <slug> --mode <mode> --question <qid> --choice <index>` | Grade one answer against the stored answer key; update `seen`. Prints `correct`, the correct option, and the rationale if the quiz has one. |
| `close-round --student <id> --concept <slug> --mode <mode>` | Score the answers recorded since the last round for this concept and mode; apply §6.4 transitions. Prints the new status and next review date. |
| `note --student <id> --concept <slug> (--misconception <text> \| --explanation <tag>)` | Append a one-line misconception (≤ 120 characters) or an explanation-strategy tag. |
| `status --student <id>` | Per concept: status, score, next review, unseen questions available, teach rounds today; plus the teach queue in order. |
| `due --student <id>` | Concepts with `next_review` ≤ today. |

`<mode>` is one of `diagnose`, `teach`, `review`.

### 6.3 Data

**`quiz-bank/bank.json`**

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
      "status": "reserved | pending | ready | failed",
      "artifact_id": "<artifact-id or null>",
      "requested": "2026-09-26T10:02:00+08:00",
      "file": "quiz-bank/photosynthesis-d3-1.json",
      "reason": null
    }
  ]
}
```

Today's quota usage is the count of `quizzes` whose `requested` date is today, in any status. Quota is per Google account, so it is shared across students.

**Normalized quiz file** (`quiz-bank/<slot>.json`), written by `bank import`:

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
      "rationale": "Light energy is captured by chlorophyll…",
      "hint": null
    }
  ]
}
```

A question's `id` is the first 12 hex characters of the SHA-256 of its text, lowercased with whitespace collapsed, so a question repeated across quizzes counts as seen. Import rejects a quiz with no questions, or any question without at least two options and exactly one correct answer.

**`students/<student-id>.json`**

```json
{
  "schema_version": 1,
  "student_id": "s-7f3a2c",
  "notebook_id": "<notebook-id>",
  "created": "2026-09-26",
  "concepts": {
    "photosynthesis": {
      "status": "untested | weak | partial | mastered",
      "score": 0.6,
      "step": 0,
      "next_review": null,
      "misconceptions": ["thinks CO2 is the energy source"],
      "explanations_tried": ["factory-analogy"],
      "rounds": [
        { "date": "2026-09-26", "mode": "diagnose", "correct": 1, "asked": 3 }
      ],
      "open_answers": [
        { "question": "3f9c2a1b7d4e", "mode": "teach", "choice": 0, "correct": false }
      ],
      "seen": {
        "3f9c2a1b7d4e": { "last_seen": "2026-09-26", "times": 1, "last_correct": false }
      }
    }
  }
}
```

`open_answers` holds answers recorded since the last `close-round` for that concept; `close-round` scores and clears them.

### 6.4 Rules

**Mastery thresholds** apply to every closed round: score = correct ÷ asked. `mastered` ≥ 0.80; `partial` 0.50–0.79; `weak` < 0.50. A 3-question diagnose round gives 3/3 mastered, 2/3 partial, 0–1/3 weak. A 5-question round needs 4/5 for mastered.

**Review ladder:** `[1, 2, 4, 8, 16, 30, 60]` days, indexed by `step`.

| Round | Result | New status | `step` | `next_review` |
|---|---|---|---|---|
| diagnose | ≥ 0.80 | mastered | 2 | today + 4 |
| diagnose | < 0.80 | partial or weak | 0 | null |
| teach | ≥ 0.80 | mastered | 0 | today + 1 |
| teach | < 0.80 | partial or weak | 0 | null |
| review | ≥ 0.80 | mastered | min(step + 1, 6) | today + ladder[new step] |
| review | < 0.80 | partial (weak if < 0.50) | 0 | null |

A failed review sends the concept to the teach queue; once it is re-mastered in teach it comes back after 1 day. Concepts that are `weak`, `partial`, or `untested` never have a review date.

**Teach queue order:** `weak` before `partial`, then lower score first, then lower rank first. Teach takes at most 3 concepts per session and at most 3 teach rounds per concept per day (counted from `rounds`).

**Target difficulty** for `bank request` and for selection: untested 3, weak 2, partial 3, mastered 4.

**Question selection (`next`):** among the concept's `ready` quizzes, return unseen questions first, preferring quizzes whose difficulty is closest to the target; then previously seen questions, oldest `last_seen` first. Diagnose and teach take unseen questions only and report a shortfall. Review may reuse seen questions.

**Top-up rule:** teach requests a new quiz when the concept has fewer than 5 unseen questions for this student; diagnose fills the bank with one quiz per concept at difficulty 3, 8 questions each.

### 6.5 Mode procedures (for `SKILL.md`)

Every session begins with `nlm login --check` and `sherlock.py status`. Authentication failure stops the session with an instruction for the student to ask whoever set Sherlock up to run `nlm login`.

**Diagnose**
1. Require `curriculum-analysis.md` (v1 Step 3); run Step 3 first if missing. Register its ten concepts with short focus phrases via `bank concept add`.
2. Show the generation plan (number of quizzes, quota use) and obtain approval. This is the only approval prompt in the adaptive modes.
3. For each concept by rank: `bank request` → run the printed `nlm quiz create` command → `bank submitted`. Submit sequentially; never background with `&`.
4. Rolling start: as soon as a concept's quiz is `completed` in `nlm studio status --artifact-id <id> --json`, download it with `nlm download quiz <id> --id <artifact-id> --format json`, `bank import` it, and quiz that concept. Check pending quizzes between concepts.
5. Per concept: `next --count 3`, ask each question, `record` each answer, give brief feedback using the returned rationale, then `close-round`.
6. Finish with a green/yellow/red summary per concept.

**Teach**
1. Take up to 3 concepts from the teach queue.
2. If `unseen_remaining` < 5, `bank request` a top-up at the target difficulty and submit it before explaining.
3. Explain the concept from the package files on disk (study guide, answer keys), aimed at recorded misconceptions and avoiding strategies in `explanations_tried`. Use `nlm notebook query` only if the package does not cover the concept. Record the strategy with `note --explanation`. End with an unscored check-understanding question.
4. `next --count 5`, ask, `record`, `close-round`. If not mastered and under the 3-round limit, try a different explanation and another round.
5. End with what improved, what needs work, and the next review dates.

**Tutor**
1. Answer the student's question from package files, or with `nlm notebook query` when a cited curriculum answer is needed.
2. Follow up with a check-understanding question. Never reveal the answer to a bank question.
3. Tutor never calls `record` or `close-round`. It may call `note --misconception` and suggest teach mode.

**Review**
1. `due` lists concepts due today.
2. Per concept: `next --count 5 --mode review`, ask, `record`, `close-round`.
3. Show what passed, what returned to teach, and the next review dates.

### 6.6 Failure handling

| Condition | Behavior |
|---|---|
| Quiz still generating when needed | Use remaining unseen questions; otherwise move to another concept and return later. Tell the student what is happening. |
| `unknown` status | Keep polling up to 10 minutes from submission before `bank fail`; never submit a duplicate while one is pending. |
| `failed` status | Retry once immediately with a new `bank request`; on a second failure, skip the concept for today. |
| Rate limited (`code 8`) | Wait 5 minutes; at most 3 submissions per concept per day. |
| Invalid or empty quiz file | `bank import` marks the slot `failed`; its questions are never shown. |
| Daily cap reached | `bank request` refuses; the agent continues with existing bank questions and says so. |
| Unknown `schema_version` | Exit 2; the agent reports the error and does not edit the file. |

### 6.7 Privacy

- Student IDs are random or a student-chosen nickname matching the pattern in §6.2. `SKILL.md` instructs the agent to ask for a nickname and never a real name.
- Student files store option indexes, scores, dates, and the agent's own one-line misconception notes. They never store the student's free-text words.
- Nothing about students is uploaded to NotebookLM. Uploads stay curriculum-only, as in v1.
- `references/privacy-and-safety.md` gains an "Adaptive modes" section covering the above.

### 6.8 File changes

| File | Change |
|---|---|
| `scripts/sherlock.py` | New |
| `SKILL.md` | Add "Adaptive Modes" after the v1 procedure, following §6.5; add the modes to "Operating Modes"; bump version to 2.1.0 |
| `references/adaptive-learning.md` | New: layout, schemas, rules, and failure table from §6.1–6.6 |
| `references/privacy-and-safety.md` | Add adaptive-modes section |
| `scripts/validate_skill.py` | Require `scripts/sherlock.py` and `references/adaptive-learning.md`; require `SKILL.md` to reference both |
| `tests/test_sherlock.py` | New |
| `tests/fixtures/quiz-sample.json`, `tests/fixtures/quiz-broken.json` | New |
| `.gitignore` | Add `students/`, `quiz-bank/` |
| `README.md` | Add adaptive-modes usage |
| `CHANGELOG.md` | 2.1.0 entry |
| `docs/runs/<date>-e2e.md` | Live run log |

## 7. Testing

Offline, standard-library `unittest`, run in CI on Python 3.10 and 3.12. No test contacts Google.

- **Rules:** thresholds at each boundary (0.49, 0.50, 0.79, 0.80); every ladder transition in §6.4, including the cap at step 6; teach-queue ordering; per-day teach-round limit.
- **Selection:** unseen-first, difficulty-closest, oldest-seen fallback; hash dedupe across two quizzes sharing a question; diagnose/teach shortfall reporting.
- **Bank:** focus phrase over 5 words refused; daily cap enforced and reset by `--today`; exact `nlm quiz create` command printed; import accepts the real fixture and rejects the broken one.
- **Students:** nickname validation; generated ID format; `open_answers` cleared by `close-round`.
- **Robustness:** unknown `schema_version` exits 2; a failure between temp-write and replace leaves the original file intact.
- **Validator:** the `__pycache__` regression test from R1.2; frontmatter version matches the CHANGELOG.

**Fixture:** Plan task 1 generates one real NotebookLM quiz (one generation of quota, with the user's approval), downloads it as JSON, removes notebook and artifact IDs, and commits it as `tests/fixtures/quiz-sample.json`. `bank import`'s normalizer is written against this real file.

## 8. Definition of done

1. CI green on `main`.
2. Validator and all tests pass locally on Python 3.10+.
3. One live end-to-end run on a real notebook with a test nickname: diagnose, teach one concept, then review (using `--today` to advance the date). Results are checked by hand against §6.4 and recorded in `docs/runs/<date>-e2e.md` with no notebook IDs, artifact IDs, or curriculum text.
4. README and CHANGELOG updated; tags `v2.0.1` and `v2.1.0` created.

## 9. Assumptions and open items

- **Quiz JSON shape (resolved by plan task 1).** The design assumes NotebookLM's quiz JSON contains, per question, the question text, options, and an identifiable correct answer. If it lacks a machine-readable correct answer, grading falls back to the agent comparing the choice against the quiz's rationale text. That changes `record`, so it would be raised with the user before continuing.
- **Queries also cost quota.** On the free tier (~50/day), `nlm notebook query` calls count too. The daily cap covers generations only; `SKILL.md` tells the agent to prefer package files over queries in teach and tutor.
- **Focused-quiz reliability.** `--focus` has known silent failures for long phrases; the 5-word limit mitigates this. `--source-ids` is available as a later refinement if focus proves unreliable, and is out of scope for v2.1.0.

## 10. Risks

- NotebookLM's private endpoints can change without notice, breaking `nlm`. Mitigation: pin guidance to a tested `nlm` version and keep the offline suite independent of it.
- A student waits while the first bank fills. Mitigation: rolling start (§6.5 Diagnose step 4).
- The Hermes install diverges again. Mitigation: R1.7.
