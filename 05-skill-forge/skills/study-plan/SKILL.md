---
name: study-plan
description: Build a realistic weekly study schedule from subjects, available hours, and priorities.
triggers: study, schedule, plan, revision, exam, timetable, coursework, focus
risk: safe
mode: action
version: 1
---

# Study Plan

Turn "I have N hours and M subjects" into a schedule a real student would
actually follow.

## Steps

1. Inputs: `subjects` (comma-separated, optional `=weight` priorities),
   `hours` (total per week), `days` (study days per week, default 5).
2. Normalize weights — `math=3, history=1` means math gets 3× the hours.
   Equal weights when none are given.
3. Split total hours across subjects by weight, rounding to **whole
   30-minute blocks** (half hours are the smallest unit anyone plans with).
4. Distribute each subject's weekly blocks across study days:
   - spread them out (never two 4-hour blocks back to back),
   - put heavier subjects earlier in the week when focus is fresher,
   - always leave at least one rest day if `days < 7`.
5. Produce the schedule plus the reasoning: total blocks, per-subject hours,
   and a warning if any subject gets less than 1 hour/week (too little to
   stick) or the daily average exceeds 4 hours (unsustainable).

## Output format

```
WEEKLY STUDY PLAN — <hours>h over <days> days
MON  18:00-19:00 math (problem set)   19:30-20:00 history (flashcards)
TUE  ...
TOTALS   math 3.0h | history 1.0h
NOTES    - <warnings / advice>
```

## Rules

- 30-minute granularity always.
- Warn, don't fail, when requests are impossible (0 hours, 0 subjects).
- If a subject has a weight of 0, it's excluded — say so.
