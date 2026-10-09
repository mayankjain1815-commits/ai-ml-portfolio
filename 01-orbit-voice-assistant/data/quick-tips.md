# Quick tips — reading list for Orbit's demo brain

Orbit can read this file out loud. Ask: "read quick-tips".

- Start small: a voice assistant is just intent detection plus tools.
- Bounded tool loops beat infinite ones: three think->act->observe rounds is plenty.
- Every tool call should land in an audit trail — you can't debug what you can't see.
- Demo mode is not a stub: it is the same pipeline with a rule-based brain.
- An allowlist is more secure than a denylist, and easier to explain.

## What Orbit can do in demo mode

1. Tell the time and date.
2. Evaluate arithmetic safely (AST whitelist — no eval, no imports).
3. Remember notes into a JSON file and list/delete them.
4. Launch allowlisted macOS applications.
5. Read these bundled files.
6. Search the web when online (best-effort, never crashes offline).