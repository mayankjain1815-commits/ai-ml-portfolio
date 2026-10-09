"""Demo brains — deterministic offline implementations of each agent role.

The design principle that makes demo mode *real* instead of a stub:

    same pipeline, different brain.

With a model, an agent reads its role prompt and produces output. Without
one, the demo brain performs the equivalent computation by hand:

* Researcher -> extracts real sentences from the bundled corpus, scored by
  topic-word overlap, and records them as cited facts on the blackboard.
* Writer     -> assembles those facts into a structured markdown report.
* Critic     -> scores the draft against an explicit rubric and writes
  targeted feedback (the same four axes a model would evaluate).
* Planner    -> splits the corpus into worker assignments.

Every rule here is deliberately simple enough to read in one sitting —
that is the point of a teaching codebase.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .blackboard import Fact
from .tools import _STOP, _sentences, load_corpus


def _content_words(text: str) -> list[str]:
    return [w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP]


def _topic_words(task: str) -> list[str]:
    """The 2-6 most specific words in the task (drops generic ones)."""
    seen: list[str] = []
    for w in _content_words(task):
        if w not in seen:
            seen.append(w)
    return seen[:6]


def _relevant_sentences(topic_words: list[str], k: int = 6) -> list[tuple[str, str, float]]:
    """(sentence, doc_name, score) for the corpus's best-matching sentences."""
    if not topic_words:
        return []
    topic_set = set(topic_words)
    hits: list[tuple[float, str, str]] = []
    for doc_name, text in load_corpus().items():
        for sentence in _sentences(text):
            words = set(_content_words(sentence))
            matched = len(topic_set & words)
            if matched == 0:
                continue
            score = matched / len(topic_set) + min(matched / max(len(words), 1), 1.0) * 0.1
            hits.append((score, sentence, doc_name))
    hits.sort(key=lambda h: (-h[0], h[2]))
    return [(s, d, sc) for sc, s, d in hits[:k]]


def research(agent_name: str, task_text: str, board) -> str:
    """Extract grounded facts from the corpus; record them on the board."""
    topics = _topic_words(task_text)
    lines = [f"Researcher ({agent_name}) looked for: {', '.join(topics) or '(no topic words found)'}"]
    hits = _relevant_sentences(topics, k=6)
    if not hits:
        lines.append("No relevant sentences found in the corpus.")
        return "\n".join(lines)
    for i, (sentence, doc, score) in enumerate(hits, start=1):
        board.add_fact(sentence, source=doc, by_agent=agent_name)
        lines.append(f"{i}. {sentence}  [source: {doc} | score {score:.2f}]")
    return "\n".join(lines)


def _citation(fact: Fact) -> str:
    return f"[{fact.source}]"


def write_draft(agent_name: str, topic: str, facts: list[Fact], fb: str | None = None) -> str:
    """Assemble facts into a markdown draft (optionally addressing feedback)."""
    cited = [f for f in facts if f.source]
    if not cited:
        return f"# {topic}\n\n_(report could not be drafted — the researcher found no facts.)_"

    lines = [f"# {topic}", ""]
    lines.append(f"> A short report assembled by {agent_name} from the offline corpus. ")

    # Feedback-driven improvement: if the critic wanted a mechanism section,
    # this is where it appears on the SECOND pass only — proving the loop.
    want_mechanism = fb and "mechanism" in fb.lower()
    if want_mechanism and len(cited) >= 2:
        lines += ["", "## How it works"]
        mech = next((f for f in cited
                     if any(w in f.content.lower() for w in
                            ("work", "works", "network", "learning", "training"))),
                    cited[1])
        lines.append(f"{mech.content} {_citation(mech)}")

    lines += ["", "## Key findings"]
    for i, fact in enumerate(cited, start=1):
        lines.append(f"- {fact.content} {_citation(fact)}")

    lines += ["", "## What you should remember"]
    recall = 3 if len(cited) >= 1 else 0
    lines.append(
        f"{len(cited)} grounded facts are the basis of this overview. "
        "Every claim cites a corpus source, so nothing here is invented."
    )
    return "\n".join(lines) + "\n"


def critique(agent_name: str, topic: str, draft: str, facts: list[Fact]) -> tuple[dict, str]:
    """Score the draft on a 4-axis rubric; return (scores, feedback_report)."""
    lower = draft.lower()
    # Citations are scored against the draft's OWN bullets (every bullet must
    # carry a [source] tag), never against a board fact count — the critic and
    # writer may legitimately see different subsets of facts for one topic.
    bullets = [line for line in draft.splitlines() if line.startswith("- ")]
    cited_bullets = [b for b in bullets if "[" in b and b.rstrip().endswith("]")]
    citations_ok = bool(bullets) and len(cited_bullets) == len(bullets)
    scores = {
        "coverage": min(10, 2 * len(facts)),
        "citations": 10 if citations_ok else 4,
        "structure": 10 if ("# " in draft and "## key findings" in lower) else 6,
        "relevance": 10 if facts else 0,
    }
    total = round(sum(scores.values()) / len(scores), 1)

    feedback: list[str] = []
    plain = re.sub(r"[^a-z ]", " ", lower)
    # A mechanism-flavoured topic (how/works/learning…) without an explicit
    # "How it works" section must be flagged — this is what triggers the
    # second draft in the ReflectiveCrew demo.
    mechanism_topic = any(
        w in topic.lower() for w in ("how", "works", "mechanism", "learning", "training")
    )
    if "how it works" not in plain and mechanism_topic:
        feedback.append("add a 'How it works' section — the topic is about a mechanism.")
    if not facts:
        feedback.append("the researcher produced no facts; rerun research with clearer wording.")
    if not citations_ok:
        feedback.append("every fact must carry its [source] tag.")
    if len(draft.split()) < 60:
        feedback.append("draft is thin; expand by using more of the gathered facts.")

    report = (
        f"Critic ({agent_name}) — rubric score {total}/10\n"
        + "\n".join(f"  {k:<10} {v:>2}/10" for k, v in scores.items())
        + ("\n  feedback:\n" + "\n".join(f"    - {f}" for f in feedback) if feedback else "\n  feedback: none — draft approved")
    )
    return scores, report


def subtitle_plan(agent_name: str, topic_words: list[str], worker_names: list[str]) -> list[str]:
    """Planner: chop the corpus into one doc per worker (round-robin)."""
    docs = sorted(load_corpus())
    if not docs:
        return []
    assignments = [f"read_doc(name={doc!r}) and extract its key facts" for doc in docs]
    return assignments


def generic_answer(agent_name: str, task_text: str, facts: list[Fact]) -> str:
    """Fallback brain for non-writer roles in demos (e.g. a summarizer)."""
    if not facts:
        return f"{agent_name}: no grounded facts available for {task_text!r}."
    return "\n".join(f"- {f.content} [{f.source}]" for f in facts[:5])