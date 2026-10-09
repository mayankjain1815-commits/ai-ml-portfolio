---
name: debug-helper
description: Structured debugging — reproduce, isolate, hypothesize, fix, verify — for any bug report.
triggers: bug, error, traceback, broken, not working, exception, crash, wrong output, debug
risk: moderate
mode: guided
version: 1
---

# Debug Helper

A repeatable method for fixing bugs without guess-and-hope.

## Steps

1. **Reproduce.** Get the exact error: the full traceback, input, expected
   vs actual output, environment (Python version, OS, package versions).
   If you can't reproduce it, you can't confirm a fix — ask for the missing
   piece instead of guessing.
2. **Read the traceback bottom-up.** The last line names the exception and
   the *first* frame inside the project's own code is usually the crime
   scene. Quote that line back.
3. **Isolate.** Shrink the failing input to the smallest case that still
   fails. Binary-search the problem: comment out halves of the pipeline
   (or write a 10-line script that calls just the suspicious function).
4. **Hypothesize.** Write one sentence: "I think X happens because Y."
   Then name the observation that would *disprove* it. Test that first —
   it's faster than confirming what you already believe.
5. **Fix minimally.** The smallest change that makes the hypothesis false
   and the test pass. No drive-by refactors in the same change.
6. **Verify.** Re-run the original failing case AND the nearest passing
   case (regression check). Add a test that fails before the fix and
   passes after — that's the proof it's really fixed.
7. **Explain.** Three bullets: root cause, the fix, how to avoid it next time.

## Rules

- Never propose a fix before step 1 — "try reinstalling" is not debugging.
- If three hypotheses have failed, stop and gather more data (add logging,
  read the library source) instead of a fourth guess.
- Distinguish clearly: *your* bug (fix the code) vs *someone else's* bug
  (pin version / report upstream / work around, and say which you're doing).
