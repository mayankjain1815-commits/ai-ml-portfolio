---
name: git-commit-message
description: Turn a diff (or a description of changes) into a clear conventional commit message.
triggers: commit, git, message, conventional commits, changelog, vcs, stage
risk: safe
mode: guided
version: 1
---

# Git Commit Message

Write the message a reviewer is glad to see in `git log`.

## Steps

1. Gather the change: either a pasted diff, `git diff --staged` output, or
   a plain description of what changed.
2. Classify with **conventional commits**:
   `feat` (new user-facing behavior) | `fix` (bug) | `refactor` (no behavior
   change) | `docs` | `test` | `chore` (tooling/build) | `perf` | `style`.
   Use the scope when the change is confined (`feat(auth): ...`).
3. Subject line rules:
   - imperative mood ("add", not "added" / "adds"),
   - ≤ 72 characters,
   - no trailing period,
   - say *what* changed, not *how* (the diff already shows how).
4. Body (only when the change isn't obvious): wrap at 72 chars, explain the
   *why* — the motivation and trade-offs — one blank line after the subject.
5. Check the message against the diff: every claim in the message must be
   backed by an actual change in the diff. Drop anything unsupported.
6. Offer the final message as a copy-pasteable block plus the command
   to use it (`git commit -m "..."` or a heredoc for multi-line).

## Rules

- One commit message, one logical change. If the diff mixes two concerns,
  say so and propose splitting it into two commits.
- Never mention filenames as the whole message ("update utils.py" is banned).
- If the diff is empty, say so instead of inventing a message.
