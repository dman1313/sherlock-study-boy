# NLM CLI Quirks

Validated against `notebooklm-mcp-cli` / `nlm` 0.9.14. NotebookLM uses unofficial endpoints, so verify questionable syntax with `nlm <group> <command> --help`.

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

All specific artifact downloads use `--id <artifact-id>`. Do not pass the artifact ID positionally.

## Difficulty types differ

```text
nlm flashcards create <notebook-id> --difficulty medium --confirm
nlm quiz create <notebook-id> --difficulty 3 --confirm
```

Flashcard difficulty is `easy`, `medium`, or `hard`. Quiz difficulty is an integer from 1 to 5.

## Focus phrases

Use a short topic phrase for focused generations:

```text
--focus "Organ Systems"
```

Long prompts and parenthetical curriculum-objective text have produced empty or failed artifacts. Keep the full concept label in the local manifest and a separate short `focus` value for CLI calls.

## Generation status

- Poll with `nlm studio status <notebook-id> --json --full`.
- Video may temporarily report `unknown`; wait 3–5 minutes before deciding it failed.
- Slides can fail server-side and succeed on one retry.
- Video/slides may return rate-limit error code 8. Stop after three bounded attempts.
- Audio can time out while server-side work continues; check studio status before resubmitting.

## Empty artifacts

A successful download command does not prove useful content.

- Flashcards and quizzes must parse as JSON and contain non-empty collections.
- Markdown study guides should exceed 500 characters and differ from other focused guides.
- Slides should have a PDF signature and exceed 100 KB.
- Videos should have an MP4-compatible `ftyp` box and exceed 1 MB.

## Focused study guides

Use `nlm notebook query` for concept-focused guides. `nlm report create --prompt` controls custom report instructions but is not a dependable topic filter across large notebooks.

## Authentication

Run `nlm login --check` before a batch. If it fails, the user must renew authentication interactively with `nlm login`. Never ask the user to paste cookies into chat or store them in the repository.
