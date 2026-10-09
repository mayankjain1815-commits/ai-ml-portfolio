---
name: regex-builder
description: Write and explain a regular expression from a plain-English description, with test cases.
triggers: regex, regular expression, pattern, match, grep, extract emails, wildcard
risk: moderate
mode: guided
version: 1
---

# Regex Builder

Write a correct regular expression from an English description — and prove
it works before handing it over.

## Steps

1. Restate the requirement as 3–5 concrete positive examples
   (`alice@example.com` ✅) and 2–3 negative examples (`not-an-email` ❌).
2. Build the pattern piece by piece, naming each piece in a comment:
   ```
   [A-Za-z0-9._%+-]   one allowed character in the local part
   @                  literal at-sign
   ...
   ```
3. Anchor deliberately: `^...$` for full-string matches, unanchored for
   search-in-text. Say which one you chose and why — this is the #1 bug.
4. Choose the dialect explicitly (Python `re` by default; note JS/PCRE
   differences if the user mentions a language).
5. **Verify**: write a tiny test block (Python) covering every positive and
   negative example from step 1, and actually reason through each one
   against your pattern. If any fail, fix the pattern and re-check.
6. Deliver: the final pattern, a one-line explanation, the test block, and
   at least one gotcha (catastrophic backtracking, `.` missing newline,
   case sensitivity, unicode).

## Rules

- Never ship an untested pattern.
- Prefer readable patterns over clever ones; add `(?x)` verbose mode with
  comments when the pattern exceeds ~40 characters.
- If the request is ambiguous (partial vs full match, which dialect),
  pick the most common interpretation, state the assumption, and proceed.
