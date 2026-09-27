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

`nlm download quiz <notebook-id> --id <artifact-id> --format json` writes `{"title": ..., "questions": [...]}`. A live run on 2026-09-27 (NotebookLM via `nlm` 0.9.14) showed four question `type`s in one quiz, and more questions than `--count` asked for (12 for `--count 8`):

| `type` | Fields | Correct answer |
|---|---|---|
| `multiple_choice` | `answerOptions[]` (`text`, `isCorrect`, `rationale`) | exactly one `isCorrect: true` |
| `multiple_select` | `answerOptions[]`, `hasAllOfTheAbove`, `hasNoneOfTheAbove` | several `isCorrect: true` |
| `fill_in_the_blank` | `bestAnswer`, `acceptableAnswers[]`, `rationale` | any accepted string; may contain LaTeX such as `$O_2$` |
| `short_answer` | `grading.modelAnswer` | free text; needs a judge |

Every question can also carry `question`, `hint`, and `imageUrls`. A question with `imageUrls` refers to a diagram a text-only student cannot see. `nlm` 0.9.14's own `core/download.py` only formats `question`, `answerOptions`, and `hint`, so older notes that list only those fields are incomplete. `nlm quiz create ... --json` prints `{"artifact_type": "quiz", "artifact_id": "...", "status": "unknown" | "in_progress", ...}`; the first status is often `unknown`.

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
