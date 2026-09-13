---
name: sherlock-study-boy
description: "Sherlock Study Boy — adaptive study agent. Generates NotebookLM study packages, diagnoses student knowledge gaps, tutors via K3 reasoning, and loops teach/quiz until mastery. Triggers on 'sherlock study boy', 'study boy', 'tutor me', 'diagnose my knowledge', 'adaptive study'."
---

# Sherlock Study Boy Agent

12-step agent workflow that orchestrates NotebookLM to produce a complete study package from uploaded course materials.

## Prerequisites

- `nlm` CLI installed and authenticated (`nlm login --check`)
- NotebookLM notebook with uploaded sources (tests, quizzes, syllabi, answer keys, teacher notes, review sheets)
- **Direct VPS terminal session** — the workflow requires real shell access. Cron jobs and sandbox sessions may lack the terminal tool. If `nlm` commands fail, switch to a VPS SSH session.

## Execution Notes

This skill needs a session with working terminal access to run `nlm` commands.
- **Preferred:** SSH into the VPS and trigger the skill from there
- **Fallback:** Run the first two commands manually (`nlm login --check`, `nlm notebook get <id>`) and paste the output — the rest of the flow can be orchestrated once the notebook context is confirmed

## Usage

```
Load sherlock-study-boy
Target notebook: <notebook-id>  (e.g., 90d50a5a-a276-409a-9574-936bba1c038e)
```

Output saves to `~/study-packages/<notebook-id>/`.

## Core Rule

**Use NotebookLM's native studio generators** — not text queries that describe study materials. The native generators produce real artifacts (flashcard decks, quizzes, slideshows, videos, audio overviews, reports, infographics, mind maps, data tables). The agent's job is orchestration: kick off native generation, poll for completion, download, organize.

**What is native vs text-query:**
| Artifact | Native command | Do NOT query for |
|----------|---------------|-----------------|
| Flashcards | `nlm flashcards create <id>` | "create flashcards for concept X" |
| Quiz | `nlm quiz create <id>` | "create a quiz for concept X" |
| Slides | `nlm slides create <id>` | "create slideshow content for concept X" |
| Video | `nlm video create <id>` | "create a video script for concept X" |
| Audio/Podcast | `nlm audio create <id>` | N/A |
| Report | `nlm report create <id>` | "write a study guide for concept X" |
| Infographic | `nlm infographic create <id>` | N/A |
| Mind map | `nlm mindmap create <id>` | N/A |
| Data table | `nlm data-table create <id>` | N/A |

**Text queries are only for:** initial concept analysis (Step 2), answer keys (no native generator), and quality checks.

## The 12 Steps

### Step 1 — Read the Notebook Title

```bash
nlm notebook get <notebook-id>
```

Extract the title. It tells you: subject, course, exam type, student level.

Example: `Biology IGCSE Year 1 Test Review` → Biology, IGCSE, Year 1.

**Do not proceed to resource creation yet.** Title first, then move to Step 2.

### Step 2 — Analyze Sources for Top 10 Concepts

Query NotebookLM:

```
Please analyze all uploaded sources in this notebook, including tests, quizzes, answer keys, review sheets, syllabi, teacher notes, and study materials.

Based on the uploaded assessment materials, identify the top 10 concepts that appear most often across the tests.

For each concept, include:
1. The concept name
2. A short student-friendly explanation
3. The percentage of tests or assessment materials where this concept appears
4. Why this concept is important
5. Common question types connected to this concept
6. Any diagrams, vocabulary, or skills students need to know

Rank the concepts from most frequently tested to least frequently tested.
```

Command:
```bash
nlm notebook query <notebook-id> "<prompt>"
```

Save the response as `step2-top10-concepts.md`.

### Step 3 — Store the Top 10 Concepts Table

Parse the NotebookLM response into a structured table:

| Rank | Concept | Percentage | Why it matters |
|------|---------|------------|----------------|
| 1 | Cell structure | 80% | Foundational biology concept |
| 2 | Enzymes | 70% | Common in process and graph questions |

Save as `step3-concepts-table.md`. This is the master plan — every subsequent step references it.

### Step 4 — Generate All Native Artifacts (Notebook-Level)

Native generators produce **one artifact per notebook**, not per concept. Generate all artifacts sequentially (shell `&` backgrounding breaks in foreground terminal mode). Send each create command in order — the CLI returns immediately after submitting the job.

**Kick off all generations sequentially:**

```bash
# Report — study guide format
nlm report create <notebook-id> --format "Study Guide" --confirm

# Video
nlm video create <notebook-id> --confirm

# Slides
nlm slides create <notebook-id> --confirm

# Flashcards (difficulty is a STRING — pass medium)
nlm flashcards create <notebook-id> --confirm --difficulty medium

# Quiz (difficulty is an INTEGER, not a word — pass 3 for medium)
nlm quiz create <notebook-id> --confirm --count 15 --difficulty 3

# Audio overview (podcast-style) — may timeout on first attempt; retry if so
nlm audio create <notebook-id> --confirm --format deep_dive --length long

# Mind map
nlm mindmap create <notebook-id> --confirm

# Infographic
nlm infographic create <notebook-id> --confirm
```

**NOTE on video and slides:** These are frequently rate-limited by NotebookLM's API (`Rate limited — API error (code 8)`). If they fail, continue with other artifacts and retry after 2-3 minutes. If they fail 3+ times, skip them — they can be generated manually later. Do not loop indefinitely.

**Poll until complete:**
```bash
nlm studio status <notebook-id>
```

Poll every 15-30 seconds. Generation takes 1-5 minutes per artifact. Some may complete before others.

### Step 5 — Download All Artifacts

Once `nlm studio status` shows all artifacts complete, download each one using the `--id` flag (NOT positional — the artifact ID is passed via `--id`):

```bash
# artifact-id is passed via --id flag, NOT as a positional argument
nlm download report <notebook-id> --id <artifact-id> --output report-study-guide.md
nlm download video <notebook-id> --id <artifact-id> --output video.mp4
nlm download slide-deck <notebook-id> --id <artifact-id> --output slides.pdf
nlm download flashcards <notebook-id> --id <artifact-id> --output flashcards.pdf
nlm download quiz <notebook-id> --id <artifact-id> --output quiz.pdf
nlm download audio <notebook-id> --id <artifact-id> --output audio-overview.m4a
nlm download mind-map <notebook-id> --id <artifact-id> --output mindmap.pdf
nlm download infographic <notebook-id> --id <artifact-id> --output infographic.pdf
```

**NOTE:** Reports download as `.md` by default (not `.pdf`). Mind map download uses `mind-map` (hyphenated) as the subcommand. If `nlm studio status` lists a mind map's `type` as `"flashcards"` (a known CLI quirk), try downloading it via the flashcards downloader with `--id <mind-map-artifact-id>`.

**If download fails** with an error, first re-check studio status — the artifact may still be generating. Poll again and retry.

**NOTE on audio:** NotebookLM delivers AAC in an MP4 container — the CLI rejects `.mp3` suffix. Use `.m4a` extension, then transcode with `ffmpeg -i audio.m4a -acodec libmp3lame -q:a 2 audio.mp3` if you need MP3 format. Paid tier may generate two audio overviews — download both.

### Step 6 — Generate Concept-Specific Answer Keys

No native generator exists for answer keys. Query NotebookLM for each concept:

```bash
nlm notebook query <notebook-id> "Create an answer key for the top 10 concepts. For each concept, include: 1. 5 key questions with correct answers 2. Short explanations 3. Common wrong answers 4. What the student should review if they got it wrong. Concepts: [list from step 3]"
```

Save as `answer-keys.md`. One query covers all 10 concepts — don't waste queries doing them individually.

### Step 7 — Quality Check

Verify all downloaded artifacts exist and are non-empty:

```bash
ls -la ~/study-packages/<notebook-id>/
```

Expected artifacts:
1. report-study-guide.pdf (report)
2. video.mp4 (video)
3. slides.pdf (slides)
4. flashcards.pdf (flashcards)
5. quiz.pdf (quiz)
6. audio-overview.m4a (audio)
7. mindmap.pdf (mind map)
8. infographic.pdf (infographic)
9. answer-keys.md (text query)

Re-run any missing generation commands.

### Step 9 — Per-Concept Deep Dive (Optional)

After the notebook-level package is done, you can generate **focused artifacts per concept** using the `--focus` parameter. This filters the notebook's sources (often 95+) to a single topic.

**Only generate per-concept content when the user explicitly asks.** Do not assume they want this.

**Supported per-concept generators:**

| Artifact | Command with focus | Notes |
|----------|-------------------|-------|
| Video | `nlm video create <id> --confirm --focus "Short Topic"` | Keep focus SHORT (2-5 words max). Long focus strings cause silent failure. |
| Slides | `nlm slides create <id> --confirm --focus "Short Topic"` | Same focus length advice. Slides can fail on first attempt — retry immediately works. |
| Study Guide | `nlm notebook query <id> --json "Focus on [topic] for IGCSE..."` | Use query, NOT report create. Save response `.value.answer` as markdown. |
| Flashcards | `nlm flashcards create <id> --confirm --difficulty medium --focus "Short"` | `--difficulty` takes STRING (easy/medium/hard), NOT integer. Keep focus short. |

**Per-concept workflow:**

1. Create `concepts/` dir + `concept-progress.json` with all 10 concepts and their status
2. Start report (seconds), then slides, then video (3-7 min) — slowest last
3. Poll every 60s (videos/slides filter all sources and take longer than notebook-level)
4. **"Unknown" status fix:** Focused videos may show `status: "unknown"` after processing. **Wait 3-5 minutes and poll again** — the original usually completes in the background. Do NOT immediately retry generation; a new retry often fails while the original succeeds. Only generate a new video if the original shows `failed` after 10+ minutes.
5. Space concept generations 1 hour apart to avoid rate limits and let each batch fully render.
6. **CRITICAL: Use SHORT focus strings (2-5 words max).** Store a separate `focus` field in concept-progress.json. Full concept names like "Human Organ Systems (Coordination & Excretion)" cause silent failures (empty flashcards, unknown videos). Use "Organ Systems" instead.
7. **Use `nlm notebook query` for study guides, NOT `nlm report create --prompt`.** The `--prompt` flag is treated as a style suggestion and produces generic content. Query returns focused, citation-rich content.

**Automation via cron:** For 10-concept pipelines, write a no-agent cron script that reads concept-progress.json, generates the next pending concept, polls for completion, downloads, and updates progress. Deliver output to `concepts/` dir. The script keeps going until all concepts are marked `"done"`. **Tip:** The pipeline script uses a fire-and-forget pattern (Phase 1 submits, Phase 2 checks next run), but you can run Phase 1 and then immediately poll `nlm studio status` + download in the same session — no need to wait for the next cron cycle. Just run the script, wait 3-5 minutes, then manually check status and download completed artifacts.

**Progress tracker format:**
```json
{
  "notebook": "<id>",
  "title": "Subject",
  "current_concept": 1,
  "total_concepts": 10,
  "concepts": [
    {"rank": 1, "name": "Topic", "percentage": "100%", "status": "done"},
    {"rank": 2, "name": "Topic", "percentage": "90%", "status": "pending"}
  ]
}
```

Status values: `"pending"`, `"generating"`, `"done"`, `"failed"`.

### Step 8 — Final Study Package Index

Query NotebookLM for a summary:

```bash
nlm notebook query <notebook-id> "Create a final study package index. List the top 10 concepts by test frequency. For each, include the concept name, percentage of appearance, and a student-friendly summary. At the end, create a suggested 10-day study plan where the student reviews one concept per day."
```

Save as `study-package-index.md`.

## Output Structure

### Notebook-Level Package

```
~/study-packages/<notebook-id>/
├── step1-notebook-title.md
├── step2-top10-concepts.md
├── step3-concepts-table.md
├── report-study-guide.md        # native report (.md, not .pdf)
├── video.mp4                    # native video
├── slides.pdf                   # native slides
├── flashcards.pdf               # native flashcards
├── quiz.pdf                     # native quiz
├── audio-overview.m4a           # native audio/podcast (.m4a, not .mp3)
├── audio-overview-2.m4a         # 2nd audio (paid tier only)
├── mindmap.pdf                  # native mind map
├── infographic.pdf              # native infographic
├── answer-keys.md               # text query (no native equivalent)
├── study-package-index.md
├── progress.json                # notebook-level step tracker
└── concepts/                    # per-concept focused artifacts
    ├── concept-1-<name>-video.mp4
    ├── concept-1-<name>-slides.pdf
    ├── concept-1-<name>.md          # focused study guide
    └── ...concept-10
    
    # Top-level tracker for concept pipeline
    concept-progress.json
```

## Notebook-Level vs Per-Concept Generation

### Notebook-Level (Step 4)

Native generators produce **one artifact per notebook** without focus. Generate one complete set covering all content:

```bash
nlm video create <id> --confirm
nlm slides create <id> --confirm
nlm report create <id> --format "Study Guide" --confirm
nlm flashcards create <id> --confirm --difficulty medium
nlm quiz create <id> --confirm --count 15 --difficulty 3
```

### Per-Concept Generation (Step 9 — optional deep-dive)

After the notebook-level package is complete, you can generate **focused artifacts per concept** using the `--focus` parameter. This produces concept-specific video, slides, and report that narrow the notebook's 95+ sources to a single topic.

**Supported per-concept generators:**

| Artifact | Command with focus | Notes |
|----------|-------------------|-------|
| Video | `nlm video create <id> --confirm --focus "Short Topic"` | Keep focus SHORT (2-5 words max). Long focus strings cause silent failure. |
| Slides | `nlm slides create <id> --confirm --focus "Short Topic"` | Same focus length advice. Slides can fail on first attempt — retry immediately works. |
| Study Guide | `nlm notebook query <id> --json "Focus on [topic] for IGCSE..."` | Use query, NOT report create. Save response `.value.answer` as markdown. |
| Flashcards | `nlm flashcards create <id> --confirm --difficulty medium --focus "Short"` | `--difficulty` takes STRING (easy/medium/hard), NOT integer. Keep focus SHORT (2-5 words). |

**Do NOT use `nlm report create` for per-concept study guides.** The `--prompt` parameter is treated as a style suggestion, not a content filter — reports always cover ALL notebook sources generically. Use `nlm notebook query` instead:

```bash
nlm notebook query <notebook-id> --json \
    "Focus on <topic> for IGCSE Biology exam preparation. Give me: 1. Key definitions 2. Core processes 3. Common exam questions 4. Diagrams to memorize 5. Common mistakes."
```

Then extract the answer from the JSON response:
```python
import json
data = json.loads(response)
answer = data.get('response', {}).get('answer', '') or data.get('value', {}).get('answer', '')
```

**Per-concept workflow:**

1. Create `concepts/` directory under the notebook's study-packages folder
2. Generate study guide via `nlm notebook query` (fastest, most reliable)
3. Generate flashcards via `nlm flashcards create --difficulty medium --focus "Short"`
4. Generate slides via `nlm slides create --focus "Short"` (may need retry)
5. Generate video via `nlm video create --focus "Short"` (slowest, 3-7 min)
6. Use a progress tracker (`concept-progress.json`) with status per concept
7. **Validate artifacts on download** — check min file sizes (video >10MB, slides >100KB, study guide >500 chars, flashcards non-empty cards array). Don't trust "file exists" alone.
8. **Known issue:** Focused videos may show `status: "unknown"` after 3-5 minutes of processing. If download fails at this point, retry with a shorter `--focus` string (2-3 words max). The original may complete in the background — check `nlm studio status` periodically.
9. Space concept generation sessions 1 hour apart to avoid rate limits and let each set fully render.

**Automated pipeline:** See `~/.hermes/scripts/concept-pipeline.sh` for a working cron-compatible script that implements this full workflow with validation, retry logic, and timeout handling.

### When to use which

- **Notebook-level:** Student wants a general study package on the full subject.
- **Per-concept:** Student wants deep-dive materials on specific weak topics identified from the top-10 analysis.

## Progress Tracking

### Notebook-Level Progress

Use `progress.json` to survive session restarts for the 12-step notebook-level pipeline:
```json
{
  "notebook_id": "90d50a5a-...",
  "title": "Biology IGCSE Year 1 Test Review",
  "current_step": 5,
  "current_concept": 3,
  "completed_concepts": [1, 2],
  "concepts": [
    {"rank": 1, "name": "Cell structure", "percentage": "80%"},
    ...
  ]
}
```

Read this file before each run to resume where you left off.

### Per-Concept Pipeline Progress

When running the 10-concept deep-dive (Step 9), use a separate `concept-progress.json` in the notebook root:

```json
{
  "notebook": "e621431b-...",
  "title": "IGCSE Biology",
  "current_concept": 1,
  "total_concepts": 10,
  "concepts": [
    {"rank": 1, "name": "Experimental Design (CORMS)", "percentage": "100%", "status": "done"},
    {"rank": 2, "name": "Genetics", "percentage": "90%", "status": "generating"},
    {"rank": 3, "name": "Respiration", "percentage": "85%", "status": "pending"}
  ]
}
```

Status values: `"pending"`, `"generating"`, `"done"`, `"failed"`.

## Pitfalls

- **Per-concept generation:** See `references/pipeline-v2-patterns.md` for the recommended approach. Key: use `nlm notebook query` for study guides (not `nlm report create`), keep focus strings to 2-5 words, and validate artifact content not just file existence.

- **Focused video "unknown" status:** Videos generated with `--focus` may show `status: "unknown"` in studio status after 3-5 minutes. **Do NOT immediately retry with a new generation.** In practice, the original video almost always completes in the background — a retry with shorter focus will often **fail** while the original succeeds. Instead: wait 3-5 minutes and poll `nlm studio status` again. Only retry generation if the original shows `status: "failed"` after 10+ minutes. If the original shows `completed`, download it — even if a retry also exists and failed.
- **Slides can fail on first attempt (non-rate-limit):** Slides sometimes fail with `status: "failed"` for no clear reason. Unlike rate-limited errors, just retry immediately — it usually works on the second attempt.
- **Generation takes 3-7 minutes per artifact for focused videos/slides** (longer than notebook-level because they filter 95+ sources). Report is fastest (~seconds). Poll every 60 seconds for video/slides, not 15-30.
- **Generation takes 1-5 minutes per artifact.** Always poll with `nlm studio status <id>` before trying to download. Don't assume instant availability.
- **Run generation commands SEQUENTIALLY, not with shell `&` backgrounding.** The Hermes terminal foreground mode does not support `&` (background jobs). Each `nlm create` command returns immediately after submitting the job — just run them one after another.
- **Rate limits — paid vs free:** Video and slides are frequently rate-limited by NotebookLM's API (`Rate limited — API error (code 8)`). On free tier, wait 5+ minutes between retries or skip for the session. On paid tier, rate limits ease after ~10-15 minutes. Slides can also fail silently (`status: \"failed\"` in studio status) — just retry immediately, it usually works on the second attempt.
- **Quiz `--difficulty` takes an INTEGER**, not a string like `"medium"`. Use `--difficulty 3` for medium difficulty. Using `"medium"` causes an "invalid value for integer" error.
- **Download artifact IDs are passed via `--id` flag**, NOT as positional arguments. The correct syntax is `nlm download report <notebook-id> --id <artifact-id>` (not `nlm download report <notebook-id> <artifact-id>`).
- **Mind map download uses `mind-map`** (hyphenated subcommand), not `mindmap`. And in `nlm studio status`, mind maps may appear with `type: "flashcards"` (a CLI quirk). If the regular mind-map download fails, try downloading via the flashcards downloader with `nlm download flashcards <notebook-id> --id <mind-map-id>`.
- **Audio creation can timeout with `ReadTimeout` on the first attempt.** Simply retry — it usually works on the second try.
- **Reports download as `.md`** by default, not `.pdf`. This is correct — they're markdown text files.
- **Free tier ~50 queries/day.** Each native generation counts as a query. 8 artifacts + 2-3 text queries = ~11 queries per package. Don't waste queries generating duplicates.
- **Auth expiry:** Sessions last ~20 min. Run `nlm login --check` before every batch. Re-auth via Mac + SCP if expired.
- **Free vs paid tier:** Free tier ~50 queries/day. Paid tier generates faster and allows 2 audio overviews per notebook. Video/slides may still hit per-minute burst limits even on paid tier — wait 10-15 min between retries.

## Adaptive Learning Modes

After generating the study package, Sherlock can switch into adaptive tutoring
modes that use K3 (Kimi-K3 via Nebius) as the reasoning backbone. These modes
turn the one-shot generator into an automatic study tutor.

Read `references/adaptive-learning.md` for the full architecture and data schema.

### Mode 1 — Diagnose (`diagnose`)

Identifies what a student knows and doesn't know.

```text
Use sherlock-study-boy in diagnose mode.
Notebook: <notebook-id>
Student: [anonymous ID or nickname]
```

Procedure:
1. Query NotebookLM for the concept list (use Step 2 output if available).
2. K3 generates a 20-30 question diagnostic quiz covering all concepts,
   calibrated to the audience level from the notebook title.
3. Student answers all questions (interactive or submitted as text/JSON).
4. K3 analyzes each answer:
   - Detects correct/incorrect and **identifies specific misconceptions**.
   - Classifies each concept: `mastered` (≥80%), `partial` (50-79%), `weak` (<50%).
5. Save results to `progress.json` (see schema below).
6. Present the student with a visual summary: green/yellow/red per concept.

**K3 prompt for answer analysis:**
```
You are an expert tutor analyzing a student's quiz answers for the concept
"{concept_name}" in {subject} at {level} level.

Student's answer: "{student_answer}"
Correct answer: "{correct_answer}"
Source material: "{relevant_source_excerpt}"

Analyze:
1. Is the answer correct? (yes/partial/no)
2. What specific misconception does this reveal (if any)?
3. On a scale of 1-5, how deep is the understanding gap?
4. What's the most effective way to explain this concept to this student?
Return as JSON: {"correct": bool, "misconception": str|null,
"gap_depth": int, "explanation_strategy": str}
```

### Mode 2 — Teach (`teach`)

Adaptive learning loop that teaches weak concepts until mastery.

```text
Use sherlock-study-boy in teach mode.
Progress: ~/study-packages/<notebook-id>/progress.json
```

Procedure:
1. Read `progress.json`, sort concepts by gap depth (worst first).
2. For each `weak` or `partial` concept (max 3 per session):
   a. K3 generates a student-friendly explanation (age-appropriate, with analogies).
   b. K3 generates 3-5 practice questions of increasing difficulty.
   c. Present explanation → ask practice questions → collect answers.
   d. K3 evaluates answers (same analysis prompt as diagnose).
   e. If concept reaches `mastered` (≥80% on practice): mark done, schedule review.
   f. If still `partial` or `weak`: generate alternative explanation, try again.
   g. Max 3 attempts per concept per session. If still weak, flag for next session.
3. Update `progress.json` after each concept.
4. End-of-session summary: what improved, what needs more work, next review dates.

**K3 prompt for explanation generation:**
```
Explain "{concept_name}" to a {level} student who finds this concept confusing.
Subject: {subject}
Their specific confusion: {misconception_from_diagnosis}

Requirements:
- Use a real-world analogy they can relate to
- Keep it under 200 words
- Include one simple diagram description (what to draw)
- End with a "check your understanding" question
- Do NOT use jargon without defining it first
```

### Mode 3 — Tutor (`tutor`)

Conversational Q&A for when a student is stuck on something specific.

```text
Use sherlock-study-boy in tutor mode.
Notebook: <notebook-id>
Student: [anonymous ID]
```

Procedure:
1. Student asks a question about any concept in the curriculum.
2. K3 reasons through the question step-by-step:
   - What concept is the student asking about?
   - What level of understanding do they seem to have?
   - Are they revealing a misconception?
3. Generate a clear, encouraging response with:
   - Direct answer or explanation
   - An analogy or example
   - A follow-up question to check understanding
4. If the student's question reveals a misconception, correct it gently.
5. After 3-5 exchanges on a concept, update `progress.json` with the
   inferred mastery level based on conversation quality.

**K3 system prompt for tutoring:**
```
You are Sherlock, a friendly study tutor for {subject} at {level} level.
You're helping a student study for their exam.

Rules:
- Be encouraging but honest
- Use analogies from everyday life
- If you don't know something from the curriculum, say so
- After explaining, always ask a check-understanding question
- If the student seems lost, break it down smaller
- If they're getting it, gradually increase difficulty
- Never give the answer to a practice question — guide them to it
- Track their progress: after each concept covered, note mastery level
```

### Mode 4 — Review (`review`)

Spaced repetition scheduler that brings concepts back at optimal intervals.

```text
Use sherlock-study-boy in review mode.
Progress: ~/study-packages/<notebook-id>/progress.json
```

Procedure:
1. Read `progress.json`, find concepts where `next_review ≤ today`.
2. For each concept due:
   - Generate a 5-question review quiz (mix of easy/medium/hard).
   - If the student passes (≥80%): double the review interval (2→4→8→16 days).
   - If they fail: reset interval to 1 day, move concept back to `teach` mode.
3. Update `progress.json` with new scores and next review dates.
4. Show the student what's due today and their overall progress.

**Spaced repetition intervals:**
| Mastery Level | Initial Interval | After Pass | After Fail |
|---|---|---|---|
| New concept | 1 day | 2 days | 1 day |
| Partial (50-79%) | 2 days | 4 days | 1 day |
| Mastered (≥80%) | 7 days | 14 days | 2 days |
| Expert (≥95% 3x) | 30 days | 60 days | 7 days |

## K3 Integration

All adaptive modes use K3 (Kimi-K3) via Nebius Token Factory for reasoning.

**API configuration:**
- Endpoint: `https://api.tokenfactory.nebius.com/v1`
- Model: `moonshotai/Kimi-K3`
- Key env: `NEBIUS_API_KEY`
- Provider plugin: `nebius-token-factory` (built into Hermes)

**Why K3 for tutoring:**
- Strong chain-of-thought reasoning (reasoning tokens are separate)
- Can analyze student misconceptions step-by-step
- Generates age-appropriate explanations with analogies
- Handles multi-turn educational conversations well
- 128K context window — can hold entire curriculum + conversation

**Cost awareness:**
- K3 burns reasoning tokens (85-300+ per exchange)
- Keep practice quizzes short (5 questions max per round)
- Use `tutor` mode for targeted help, not random exploration
- Fallback to `ds` (deepseek-v4-flash) for simple answer checking

## Progress Schema

```json
{
  "student_id": "anon-<hash-or-nickname>",
  "curriculum": "year-8-science",
  "notebook_id": "<notebook-id>",
  "created": "2026-09-13T15:00:00+08:00",
  "last_session": "2026-09-13T16:30:00+08:00",
  "total_sessions": 5,
  "concepts": {
    "photosynthesis": {
      "rank": 1,
      "status": "partial",
      "score": 0.65,
      "attempts": 2,
      "misconceptions": ["thinks CO2 is the main energy source"],
      "explanations_tried": ["analogy-plant-as-factory", "step-by-step-equation"],
      "last_review": "2026-09-13",
      "next_review": "2026-09-15",
      "review_interval_days": 2,
      "history": [
        {"date": "2026-09-12", "mode": "diagnose", "score": 0.4},
        {"date": "2026-09-13", "mode": "teach", "score": 0.65}
      ]
    },
    "cell-division": {
      "rank": 2,
      "status": "mastered",
      "score": 0.85,
      "attempts": 3,
      "misconceptions": [],
      "last_review": "2026-09-13",
      "next_review": "2026-09-20",
      "review_interval_days": 7,
      "history": [
        {"date": "2026-09-11", "mode": "diagnose", "score": 0.3},
        {"date": "2026-09-12", "mode": "teach", "score": 0.6},
        {"date": "2026-09-13", "mode": "review", "score": 0.85}
      ]
    }
  },
  "sessions": [
    {
      "date": "2026-09-13",
      "mode": "diagnose",
      "concepts_tested": ["photosynthesis", "cell-division", "forces"],
      "concepts_mastered": ["forces"],
      "duration_minutes": 25
    }
  ]
}
```

## Privacy (Adaptive Modes)

- Student progress stored locally only — never committed to git.
- No real student names — use anonymous ID or nickname.
- K3 API calls contain only concept names and anonymized answers — no PII.
- Progress file is `.gitignore`d by default.
- NotebookLM uploads remain curriculum-only (no student work).

## Reference Files

- `references/adaptive-learning.md` — Full architecture, data flow, K3 prompts.
- `references/nlm-cli-quirks.md` — Exact error messages, download syntax quirks, rate-limit strategies, and known CLI bugs collected from real sessions. Read this when you hit an unexpected nlm error.
- `references/pipeline-v2-patterns.md` — Per-concept generation patterns and progress tracking.
