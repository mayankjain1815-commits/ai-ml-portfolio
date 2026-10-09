---
name: flashcards
description: Turn Q&A pairs into a printable flashcard deck with a self-test order and progress tracking.
triggers: flashcards, cards, quiz, memorize, recall, revision, deck, test myself
risk: safe
mode: action
version: 1
---

# Flashcards

Build a study deck from plain `question :: answer` pairs.

## Steps

1. Input: `cards` — pairs separated by `;;`, question and answer split on
   `::`. Example: `What is Big-O? :: Upper bound on runtime;;What is a hash map? :: Key-value lookup with O(1) average`
2. Validate every pair has both halves; report malformed pairs by index
   instead of silently dropping them.
3. Render the deck as numbered markdown cards (front, then back) so it can
   be copied into Anki, Notion, or printed.
4. Generate a **self-test order**: deterministic shuffle (seeded by the
   deck's total character count — same deck, same order) so re-running
   gives a stable but non-alphabetical test sequence.
5. Print stats: card count, average question length, and a warning if any
   answer is longer than ~20 words (too long to recall — split it).

## Output format

```
DECK  6 cards
1. Q: ...
   A: ...
...
SELF-TEST ORDER  3, 1, 5, ...
STATS            avg question 8 words | 1 long answer(s) to split
```

## Rules

- Never invent cards — this skill formats, it doesn't generate content
  (unless running with a model, which may propose cards from notes given).
- Duplicate questions get a warning.
