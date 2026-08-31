# Per-Concept Pipeline Patterns

Use this only after the notebook-level video or full package is complete and the user explicitly requests deep dives.

## Generation order

1. Focused study guide via `nlm notebook query`
2. Flashcards with a short `--focus`
3. Slides with the same short `--focus`
4. Video last because it is slowest and most rate-limit prone

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

Allowed status values: `pending`, `generating`, `completed`, `failed`, `skipped`.

## Bounded retry policy

- Poll every 60 seconds.
- Treat `unknown` as in progress for up to ten minutes.
- Retry slides once after a confirmed `failed` status.
- Retry rate-limited video generation no more than three times with increasing waits.
- Record failure and move on; never use an unbounded loop.

## Validation

- Study guide: >500 characters and not byte-identical to another concept guide.
- Flashcards: valid JSON and at least one card.
- Slides: PDF signature and >100 KB.
- Video: MP4-compatible signature and >1 MB.

A concept is `completed` only when every artifact requested for that concept passes its validation. Partial success remains visible in the artifact map.
