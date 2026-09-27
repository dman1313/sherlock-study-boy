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
