# Changelog

All notable changes to this project are documented here.

## [2.0.0] - 2026-09-13

### Added
- **Adaptive Learning System** — four new modes powered by K3 (Kimi-K3 via Nebius):
  - **Diagnose**: diagnostic quiz identifies what a student knows/doesn't know
  - **Teach**: adaptive learning loop — explain, quiz, re-teach until mastery
  - **Tutor**: conversational Q&A with K3 reasoning for stuck students
  - **Review**: spaced repetition scheduler with optimal review intervals
- **K3 Integration** — Kimi-K3 (Nebius Token Factory) as reasoning backbone for:
  - Misconception detection from student answers
  - Age-appropriate explanation generation with analogies
  - Adaptive difficulty based on student level
  - Step-by-step reasoning for tutoring conversations
- **Progress Tracking** — persistent `progress.json` schema:
  - Per-concept mastery scores, misconceptions, review schedule
  - Session history with scores and modes used
  - Spaced repetition intervals (1→2→4→8→16→30→60 days)
- **K3 Prompt Templates** — tested prompts for:
  - Answer analysis (correct/partial/wrong + misconception detection)
  - Explanation generation (analogy-based, age-appropriate)
  - Tutoring system prompt (encouraging, adaptive, Socratic)
- `.gitignore` now excludes `progress.json` (student data stays local)

### Changed
- Updated SKILL.md description to include adaptive modes
- Added `references/adaptive-learning.md` with full architecture and data flow
- Privacy section expanded for adaptive modes (no PII in API calls)

### Security
- Student progress stored locally only — never committed
- No real student names — anonymous ID or nickname required
- K3 API calls contain only concept names and anonymized answers

## [1.0.0] - 2026-08-31

### Added

- Portable Claude/Hermes skill for video-only and full study-package workflows.
- Curriculum file ingestion through the `nlm` CLI.
- Explicit privacy, approval, bounded-retry, and artifact-validation gates.
- Current NotebookLM artifact output formats and CLI 0.9.14 guidance.
- Offline repository validator, unit tests, and GitHub Actions validation.

### Changed

- Replaced machine-specific VPS instructions with portable prerequisites.
- Reworked the original out-of-order 12-step draft into nine contiguous, verifiable steps.
- Removed references to a missing local automation script.
- Corrected report, flashcard, quiz, mind-map, infographic, and audio output extensions.
