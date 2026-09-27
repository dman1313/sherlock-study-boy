# Sherlock Study Boy

A portable agent skill that turns curriculum documents into native NotebookLM learning artifacts: video overviews, study guides, slides, flashcards, quizzes, audio overviews, mind maps, infographics, and answer keys.

The skill can start from local curriculum files or from an existing NotebookLM notebook. It directs the agent to use NotebookLM's native Studio generators instead of inventing local substitutes.

> [!IMPORTANT]
> This project automates an unofficial NotebookLM CLI. Google can change NotebookLM's private endpoints without notice. Do not use it for confidential student records or safeguarding data.

## What it produces

**Video-only mode**

- One native NotebookLM video overview
- A local MP4 download
- A small manifest recording the notebook and artifact IDs

**Full study-package mode**

- Study guide (`.md`)
- Video (`.mp4`)
- Slides (`.pdf`)
- Flashcards (`.json`)
- Quiz (`.json`)
- Audio overview (`.m4a`)
- Mind map (`.json`)
- Infographic (`.png`)
- Concept analysis, answer keys, and package index (`.md`)

## Requirements

- Python 3.10+
- [`uv`](https://docs.astral.sh/uv/) recommended
- Google account with NotebookLM access
- Chrome or another supported browser for initial authentication

Install the CLI:

```bash
uv tool install "notebooklm-mcp-cli[browser]"
nlm --version
nlm login
nlm login --check
```

The skill was validated against `nlm` 0.9.14.

## Install the skill

### Claude Code

```bash
mkdir -p ~/.claude/skills
git clone https://github.com/dman1313/sherlock-study-boy.git \
  ~/.claude/skills/sherlock-study-boy
```

Start a new Claude session, then ask:

```text
Use sherlock-study-boy to make a video from these curriculum files:
/path/to/unit-plan.pdf
/path/to/assessment.docx
```

### Hermes Agent

```bash
mkdir -p ~/.hermes/skills/research
git clone https://github.com/dman1313/sherlock-study-boy.git \
  ~/.hermes/skills/research/sherlock-study-boy
```

Start a new Hermes session so the skill catalog reloads.

### Other skill-compatible agents

```bash
npx skills add dman1313/sherlock-study-boy
```

If the agent does not discover root-level skills, copy this repository into its user skill directory while retaining `SKILL.md` and `references/` together.

## Use it

From curriculum files:

```text
Use sherlock-study-boy in video-only mode.
Create a new notebook titled "Year 8 Forces Review".
Sources:
- /path/to/forces-unit.pdf
- /path/to/forces-assessment.pdf
Audience: Year 8 students
Video format: explainer
```

From an existing notebook:

```text
Use sherlock-study-boy in full-package mode.
Notebook: <notebook-id>
Output directory: ./study-packages/forces-review
```

The agent will inspect sources and show the generation plan before issuing commands that create remote artifacts or consume NotebookLM quota.

## Adaptive study modes

Once a notebook has a curriculum analysis, Sherlock can tutor one student at a time:

- **Diagnose:** a short quiz on every concept finds what the student already knows.
- **Teach:** explains weak concepts, then quizzes until they are mastered.
- **Tutor:** answers the student's own questions from the curriculum.
- **Review:** brings mastered concepts back after 1, 2, 4, 8, 16, 30, then 60 days.

NotebookLM writes the quiz questions, one focused quiz per concept. The bundled `scripts/sherlock.py` grades answers and keeps records in the study package directory.

```text
Use sherlock-study-boy in diagnose mode.
Study package: ./study-packages/forces-review
```

The first diagnose on a notebook generates about ten quizzes and asks before doing so. After that, the script allows at most 20 quiz generations per day (set with `bank init --daily-cap`). Student progress stays in `students/` inside the study package directory; it is never uploaded or committed.

## Privacy and authentication

- Keep curriculum files limited to material you are authorized to upload.
- Do not upload student names, grades, accommodations, health data, safeguarding records, or disciplinary records.
- Never commit NotebookLM browser profiles, cookies, session state, downloaded school content, notebook IDs, or generated packages.
- Authenticate locally with `nlm login`; this repository contains no credentials.
- Use a dedicated least-privilege Google account for testing.

See [`references/privacy-and-safety.md`](references/privacy-and-safety.md).

## Validate the repository

```bash
python3 scripts/validate_skill.py
python3 -m unittest discover -s tests -v
```

These are offline tests. They do not contact Google, create notebooks, upload files, or consume quota.

## Known limits

- Video, slides, and audio can take several minutes.
- NotebookLM can rate-limit artifact generation.
- Focused artifacts work best with short focus phrases.
- Authentication can expire and require `nlm login` again.
- Native artifact output formats differ by type; the skill documents current formats.

## License

MIT — see [`LICENSE`](LICENSE).
