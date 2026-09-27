# Privacy and Safety

NotebookLM is a cloud service. Uploading a source transfers it outside the local machine and may place it under Google's service terms and account controls.

## Do not upload

- Student names or direct identifiers
- Grades tied to individuals
- Individual education plans or accommodations
- Health, disability, safeguarding, or disciplinary records
- Parent communications
- Credentials, authentication cookies, browser profiles, or API tokens
- Copyrighted material the user is not authorized to process

## Before upload

1. List every proposed source.
2. Confirm the user is authorized to upload it.
3. Remove student and staff personal information.
4. Use the least-privilege Google account appropriate for the task.
5. Obtain explicit approval for notebook creation and upload.

## Repository hygiene

Never commit:

- `.env` files
- `storage_state.json` or browser profile directories
- NotebookLM cookie/auth directories
- Real notebook or artifact IDs
- Downloaded curriculum files
- Generated study packages
- School-private names or internal URLs

The repository validator checks several common leak patterns, but it is not a substitute for reviewing `git diff --staged` before a push.

## Adaptive modes

- Identify students by a random ID or a nickname they choose (3–32 lowercase letters, digits, or dashes). Never use a real name.
- Student files in `<pkg>/students/` store option indexes, scores, dates, and one-line misconception notes written by the agent. Never store the student's own free-text words.
- Nothing about students is sent to NotebookLM. Uploads stay curriculum-only.
- `students/` and `quiz-bank/` are ignored by git. Do not commit or share them.
- To delete a student's data, delete their file in `<pkg>/students/`.

## Incident response

If a credential or private document is staged or committed:

1. Stop before pushing.
2. Remove the file from Git history, not only the working tree.
3. Rotate or revoke the exposed credential.
4. Notify the data owner when personal data was involved.
5. Re-run repository validation and inspect the complete staged diff.
