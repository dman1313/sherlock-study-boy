# Adaptive Learning System

Core engine that turns sherlock-study-boy from a one-shot generator into an
automatic tutor. Uses K3 (Kimi-K3 via Nebius) as the reasoning backbone.

## Architecture

```
curriculum files → NotebookLM (artifacts)
                        ↓
              diagnostic assessment
                        ↓
              identify knowledge gaps
                        ↓
              generate targeted materials (focused deep dives)
                        ↓
              quiz student on weak areas
                        ↓
         ┌── pass ──→ mark mastered, schedule review
         │
         └── fail ──→ generate explanations + more practice
                      → re-quiz
                      → loop (max 3 attempts per concept)
                        ↓
              spaced repetition schedule
                        ↓
              progress.json (persistent)
```

## Modes

### 1. Diagnostic Mode (`diagnose`)
- Generate a diagnostic quiz covering all concepts in the curriculum
- Student answers all questions
- K3 analyzes answers, identifies mastery level per concept:
  - `mastered` (≥80% correct, no misconceptions)
  - `partial` (50-79% correct, some gaps)
  - `weak` (<50% correct or fundamental misconceptions)
- Output: `progress.json` with per-concept scores and gap analysis

### 2. Teach Mode (`teach`)
- Takes progress.json as input
- For each `weak` or `partial` concept:
  - Generate student-friendly explanation via K3
  - Create focused flashcards for that concept
  - Generate practice questions via K3 (not NotebookLM — faster, adaptive)
  - Present material, then quiz immediately
- Loop until concept reaches `mastered` or max attempts hit

### 3. Tutor Mode (`tutor`)
- Conversational Q&A on any concept in the curriculum
- K3 reasons through student questions step-by-step
- Can generate on-the-fly examples, analogies, practice problems
- Detects misconceptions from student questions and corrects them
- Remembers conversation context within session

### 4. Review Mode (`review`)
- Spaced repetition scheduler
- Checks progress.json for concepts due for review
- Generates quick review quiz (5-10 questions)
- Updates mastery scores and next review date

## Student Interaction Flow

```
Student: "I don't understand photosynthesis"
    ↓
Tutor (K3): Analyzes the question, identifies likely confusion point
    ↓
Generates explanation with analogy + diagram description
    ↓
Asks follow-up: "Does that make sense? Try this: if a plant is moved
from sunlight to darkness, what happens to its sugar production?"
    ↓
Student answers
    ↓
K3 evaluates answer, provides feedback, adjusts understanding
    ↓
If misconception persists: generates alternative explanation
If understood: marks partial mastery, schedules review
```

## K3 Integration

All reasoning goes through Nebius Token Factory (Kimi-K3):
- Student answer analysis (misconception detection)
- Explanation generation (age-appropriate, step-by-step)
- Question generation (adaptive difficulty based on student level)
- Study plan creation (prioritize weak areas, sequence concepts)
- Progress evaluation (mastery thresholds, review scheduling)

API pattern:
```python
def ask_k3(prompt: str, system: str = None) -> str:
    """Call K3 via Nebius Token Factory."""
    # Uses NEBIUS_API_KEY from environment
    # Model: moonshotai/Kimi-K3
    # Handles reasoning tokens (separate field in response)
```

## Progress Data Schema

```json
{
  "student_id": "anonymous-hash",
  "curriculum": "year-8-science",
  "created": "2026-09-13T15:00:00+08:00",
  "concepts": {
    "photosynthesis": {
      "rank": 1,
      "status": "partial",
      "score": 0.65,
      "attempts": 2,
      "misconceptions": ["thinks CO2 is the main energy source"],
      "last_review": "2026-09-13",
      "next_review": "2026-09-15",
      "review_interval_days": 2
    }
  },
  "sessions": [
    {
      "date": "2026-09-13",
      "mode": "diagnose",
      "concepts_tested": ["photosynthesis", "cell-division", "forces"],
      "concepts_mastered": ["forces"]
    }
  ]
}
```

## Privacy

- Student progress is stored locally only
- No student names — use anonymous ID or nickname
- No data leaves the machine except NotebookLM uploads (curriculum only)
- K3 API calls contain no PII — only concept names and anonymized answers
- Progress file is gitignored by default
