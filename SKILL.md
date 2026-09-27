---
name: sherlock-study-boy
description: Turn curriculum into NotebookLM study media and tutoring.
version: 2.1.0
author: Dwayne Primeau, Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [notebooklm, curriculum, video, study-materials, tutoring]
    related_skills: []
---

# Sherlock Study Boy

Turn authorized curriculum documents into native NotebookLM videos or complete study packages, then tutor a student through them. This skill orchestrates the `nlm` CLI; it does not replace NotebookLM with locally invented artifacts.

## When to Use

- Create a NotebookLM video from curriculum, syllabus, assessment, or lesson files.
- Build a complete study package from an existing NotebookLM notebook.
- Identify frequently assessed concepts, then generate focused learning media.
- Tutor a student: diagnose knowledge gaps, teach weak concepts, answer questions, and schedule reviews ("tutor me", "diagnose my knowledge", "adaptive study").

**Do not use for:** student records, safeguarding material, confidential accommodations, grading data, or content the user is not authorized to upload.

## Prerequisites

- `nlm` from `notebooklm-mcp-cli` is installed.
- The user has a Google account with NotebookLM access.
- A local interactive browser is available when authentication must be renewed.
- Inputs are either an existing notebook ID or a list of authorized local files/URLs.

Use `terminal(command="nlm --version && nlm login --check", timeout=60)` before any work. If authentication fails, stop and ask the user to run `nlm login`; never request or display cookies.

Read `references/privacy-and-safety.md` before uploading curriculum files. Read `references/nlm-cli-quirks.md` when generation or downloads fail.

## Operating Modes

1. **Video-only:** ingest sources if needed, analyze the audience and concepts, generate one native video, download it, and verify the MP4.
2. **Full package:** generate the video plus report, slides, flashcards, quiz, audio, mind map, infographic, answer keys, and package index.
3. **Focused deep dive:** after the notebook-level package, generate explicitly requested concept-specific media using a two-to-five-word focus phrase.
4. **Adaptive tutoring:** diagnose, teach, tutor, and review one student at a time using NotebookLM quizzes. See Adaptive Modes.

Default to **video-only** when the user asks only for a video. Do not expand to the full package without approval.

## Procedure

### 1. Confirm inputs, privacy, and mode

Collect:

- Existing notebook ID **or** notebook title plus source files/URLs.
- Output directory; default to `./study-packages/<safe-notebook-title>/`.
- Audience/grade level, language, video format, and optional visual style.
- `video-only` or `full-package` mode.

Reject or pause on files containing student personal data. List the exact sources and planned remote actions, then obtain user approval before creating a notebook, uploading sources, querying, generating, or downloading.

**Complete when:** mode, audience, source list, output path, and approval are recorded.

### 2. Create or inspect the notebook

For an existing notebook:

```text
terminal(command="nlm notebook get <notebook-id> --json", timeout=60)
```

For curriculum files, create a notebook and capture the returned ID:

```text
terminal(command="nlm notebook create \"<title>\" --json", timeout=60)
terminal(command="nlm source add <notebook-id> --file \"<path>\" --wait --json", timeout=660)
```

Add each approved file separately so a failed upload is attributable. For web sources, use `--url`; for YouTube, use `--youtube`. Do not expose the notebook publicly.

**Complete when:** `nlm notebook get <notebook-id> --json` succeeds and every approved source is processed.

### 3. Analyze the curriculum

Create the output directory, then query the notebook for a source-grounded curriculum map:

```text
terminal(command="nlm notebook query <notebook-id> --json --new-conversation --timeout 180 \"Analyze the uploaded curriculum and assessment sources. Identify the intended learner level, learning objectives, prerequisite knowledge, and the ten most important or frequently assessed concepts. For each concept, give a student-friendly explanation, evidence from the sources, common question types, required vocabulary or diagrams, and likely misconceptions. Do not invent percentages unless the sources support a count.\"", timeout=210)
```

Save the answer as `curriculum-analysis.md`. Create `manifest.json` containing only the notebook ID, title, mode, output directory, and timestamps; never store cookies or tokens.

**Complete when:** the analysis cites or clearly traces claims to notebook sources and the manifest exists.

### 4. Present the generation plan

For video-only mode, propose one command using the requested options:

```text
nlm video create <notebook-id> --format explainer --style auto_select --focus "<audience and learning goal>" --confirm --json
```

Valid video formats are `explainer`, `brief`, `cinematic`, and `short`. Valid built-in styles include `auto_select`, `classic`, `whiteboard`, `kawaii`, `anime`, `watercolor`, `retro_print`, `heritage`, and `paper_craft`.

For full-package mode, include all commands in Step 6. State that generation consumes NotebookLM quota and can be rate-limited. Obtain approval for the final plan.

**Complete when:** the user has approved the exact artifact set.

### 5. Generate and download the video

Submit the approved video command through `terminal`. Do not retry a rate-limited submission more than three times and never loop indefinitely.

Poll without creating new artifacts:

```text
terminal(command="nlm studio status <notebook-id> --json --full", timeout=60)
```

Poll every 30–60 seconds until the video is `completed`, `failed`, or ten minutes have passed. If status is temporarily `unknown`, wait; do not immediately submit a duplicate.

Download the completed artifact using its returned ID:

```text
terminal(command="nlm download video <notebook-id> --id <artifact-id> --output \"<output-dir>/video.mp4\"", timeout=600)
```

Verify the file exists, starts with an MP4-compatible container signature, and is larger than 1 MB. Record the artifact ID and result in `manifest.json`.

**Complete when:** the MP4 passes validation or the manifest records the exact failure.

### 6. Generate the full package when approved

Submit sequentially; NotebookLM performs generation remotely:

```text
nlm report create <notebook-id> --format "Study Guide" --confirm --json
nlm slides create <notebook-id> --confirm --json
nlm flashcards create <notebook-id> --difficulty medium --confirm --json
nlm quiz create <notebook-id> --count 15 --difficulty 3 --confirm --json
nlm audio create <notebook-id> --format deep_dive --length long --confirm --json
nlm mindmap create <notebook-id> --confirm --json
nlm infographic create <notebook-id> --confirm --json
```

The video from Step 5 is part of the package; do not create a duplicate. Poll with `nlm studio status <notebook-id> --json --full` and download completed artifacts:

```text
nlm download report <notebook-id> --id <artifact-id> --output "<output-dir>/study-guide.md"
nlm download slide-deck <notebook-id> --id <artifact-id> --format pdf --output "<output-dir>/slides.pdf"
nlm download flashcards <notebook-id> --id <artifact-id> --format json --output "<output-dir>/flashcards.json"
nlm download quiz <notebook-id> --id <artifact-id> --format json --output "<output-dir>/quiz.json"
nlm download audio <notebook-id> --id <artifact-id> --output "<output-dir>/audio-overview.m4a"
nlm download mind-map <notebook-id> --id <artifact-id> --output "<output-dir>/mind-map.json"
nlm download infographic <notebook-id> --id <artifact-id> --output "<output-dir>/infographic.png"
```

Use one notebook query to create `answer-keys.md`; require the answers to cite the uploaded materials and flag uncertainty. Use a final query to create `study-package-index.md` and a suggested study sequence.

**Complete when:** every approved artifact is either downloaded and validated or recorded as failed in the manifest.

### 7. Validate the package

Check content, not only file existence:

| Artifact | Validation |
|---|---|
| Video | MP4-compatible signature; >1 MB |
| Report | Markdown; >500 characters |
| Slides | PDF signature; >100 KB |
| Flashcards | Valid JSON; non-empty cards collection |
| Quiz | Valid JSON; non-empty questions collection |
| Audio | MP4/M4A-compatible signature; >100 KB |
| Mind map | Valid, non-empty JSON |
| Infographic | PNG signature; >100 KB |
| Answer keys/index | Markdown; >500 characters |

Do not claim success for missing, empty, duplicate, or stub artifacts. Preserve failures in `manifest.json` with the command and returned error, excluding credentials.

**Complete when:** validation results account for every requested artifact.

### 8. Optional focused deep dives

Only run when explicitly requested. Use a short two-to-five-word focus phrase. Generate no more than one concept batch at a time, then verify before continuing.

```text
nlm video create <notebook-id> --focus "Cell Division" --confirm --json
nlm slides create <notebook-id> --focus "Cell Division" --confirm --json
nlm flashcards create <notebook-id> --difficulty medium --focus "Cell Division" --confirm --json
```

For a focused study guide, use `nlm notebook query`; report `--prompt` is a style instruction, not a reliable source filter.

**Complete when:** each requested concept artifact passes the Step 7 checks.

### 9. Deliver the result

Report:

- Mode and notebook title.
- Output directory.
- Validated artifacts with sizes.
- Failed or skipped artifacts with exact non-secret errors.
- Rate-limit or unofficial-API warnings.
- Confirmation that no credentials or student personal data were written.

Never include authentication cookies or session state in the report.

## Adaptive Modes

After a notebook has a curriculum analysis (Step 3), Sherlock can tutor one student at a time in four modes: diagnose, teach, tutor, and review. NotebookLM generates the quiz questions (one focused quiz per concept). The bundled script `scripts/sherlock.py` does all grading and record keeping. Read `references/adaptive-learning.md` for the data files, rules, and full command reference.

Below, `sherlock` means `python3 <skill-dir>/scripts/sherlock.py` (the script next to this file) and `<pkg>` is the study package directory from Step 1. Every `sherlock` command takes `--dir <pkg>` and prints one JSON object. Never edit files in `<pkg>/quiz-bank/` or `<pkg>/students/` by hand.

### Adaptive rules

- The person in the chat is the student. Ask for a nickname (3–32 lowercase letters, digits, or dashes), never a real name, then run `sherlock student new --dir <pkg> --nickname <nickname>`. Without a nickname, `sherlock student new --dir <pkg>` generates an ID.
- Start every session with `nlm login --check` and `sherlock status --dir <pkg> --student <id>`. If login fails, tell the student to ask whoever set Sherlock up to run `nlm login`, and stop.
- Only quiz answers change mastery. Record each answer with `sherlock record` and end each round with `sherlock close-round`.
- `sherlock next` never includes correct answers. Do not reveal an answer before the student chooses; `sherlock record` returns the correct option afterwards for feedback.
- Answer by question `type`: `--choice <index>` for `multiple_choice`, `--choices <i,j,...>` for `multiple_select` (every correct option, nothing else), and `--text "<answer>"` for `fill_in_the_blank`. Indexes are 0-based. Typed answers are marked but never stored.
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
5. For each ready concept: `sherlock next --dir <pkg> --student <id> --concept <slug> --count 3 --mode diagnose`. Ask each question with its options, run `sherlock record --dir <pkg> --student <id> --concept <slug> --mode diagnose --question <question-id>` plus `--choice`, `--choices`, or `--text` for that question's type, give brief feedback, then `sherlock close-round --dir <pkg> --student <id> --concept <slug> --mode diagnose`.
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
| `bank import` fails validation | The quiz is marked failed and its questions are never shown. If the download was incomplete, download again and re-run `bank import`; no new generation is needed. Otherwise request another. |
| `bank request` reports the daily cap | Continue with questions already in the bank and tell the student. |

## Output Structure

```text
study-packages/<safe-title>/
├── curriculum-analysis.md
├── manifest.json
├── video.mp4
├── study-guide.md
├── slides.pdf
├── flashcards.json
├── quiz.json
├── audio-overview.m4a
├── mind-map.json
├── infographic.png
├── answer-keys.md
├── study-package-index.md
├── quiz-bank/              # adaptive modes: shared quiz bank (bank.json + normalized quizzes)
└── students/               # adaptive modes: one progress file per student; never commit
```

Only approved artifacts need to exist.

## Pitfalls

- NotebookLM and `nlm` use unofficial endpoints; run `nlm --version` and command `--help` checks when syntax appears stale.
- `flashcards --difficulty` uses `easy|medium|hard`; quiz difficulty uses integer `1–5`.
- Downloads require `--id`; artifact IDs are not positional arguments.
- Reports are Markdown, flashcards/quizzes/mind maps are JSON, slides are PDF/PPTX, infographics are PNG, and audio is M4A.
- A focused video may show `unknown` while still processing. Wait before retrying.
- Short focus phrases are more reliable than full curriculum-objective sentences.
- Never automate public notebook sharing.

## Verification

A run is complete only when:

- Authentication and notebook access were checked.
- The approved source list and artifact set match the manifest.
- Every requested artifact has a validation result.
- No browser profile, cookie, secret, student record, or unapproved source appears in the output.
- The final report distinguishes completed, failed, and skipped artifacts.
- Adaptive sessions changed quiz-bank and student files only through `scripts/sherlock.py`.
