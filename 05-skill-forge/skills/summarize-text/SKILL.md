---
name: summarize-text
description: Compress any paragraph, article or document into a short extractive summary that keeps the key facts.
triggers: summarize, summary, tldr, condense, shorten, digest, recap
risk: safe
mode: action
version: 1
---

# Summarize Text

Produce a short summary **without inventing anything** — every sentence in
the output must appear verbatim in the source. Extractive summarization is
the honest default: it can't hallucinate.

## Steps

1. Split the text into sentences (handle abbreviations like `e.g.` and
   decimal numbers so they don't split early).
2. Build a word-frequency table:
   - lowercase everything, drop stopwords (`the`, `is`, `and`, ...),
   - keep word stems simple (strip trailing `s`/`ing` only when safe),
   - do **not** count words from the first sentence twice — titles often
     repeat in sentence one, which biases scoring.
3. Score each sentence = sum of its content-word frequencies ÷ its length
   (normalizing by length stops one rambling sentence from winning).
4. Keep the top `N` sentences (default: enough to hit ~25% of the original),
   but **restore original order** — a summary whose sentences jump around
   is unreadable.
5. Return the summary plus: compression ratio, word counts, and the top 3
   keywords of the whole text.

## Output format

```
SUMMARY
<sentences in original order, joined>

KEYWORDS   word1, word2, word3
STATS      <orig> words -> <sum> words (<pct>% of original)
```

## Rules

- Never paraphrase in action mode — verbatim sentences only.
- If the text is already shorter than 3 sentences, say it's too short to
  summarize and return it unchanged.
- Keyword extraction uses the same frequency table as scoring.
