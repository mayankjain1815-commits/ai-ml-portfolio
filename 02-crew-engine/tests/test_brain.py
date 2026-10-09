"""Tests for the deterministic demo brains (research / write / critique)."""

from crew_engine import brain
from crew_engine.blackboard import Blackboard


def test_research_posts_cited_facts_to_board():
    board = Blackboard()
    out = brain.research("Aria", "Describe how neural networks learn", board)
    assert out.startswith("Researcher")
    assert len(board.facts) >= 3
    for fact in board.facts:
        assert fact.source, "every recorded fact must cite a source"
        assert fact.by_agent == "Aria"


def test_research_with_no_topic_words():
    board = Blackboard()
    out = brain.research("Aria", "the and of", board)
    assert len(board.facts) == 0
    assert "no topic" in out.lower() or "no relevant" in out.lower()


def test_write_draft_structures_and_cites_facts():
    board = Blackboard()
    board.add_fact("Neurons pass signals along weighted connections.", "neural-networks", "Aria")
    board.add_fact("Training adjusts those weights with gradient descent.", "neural-networks", "Aria")
    draft = brain.write_draft("Bilal", "How do neural networks work?", board.facts)
    assert draft.startswith("# How do neural networks work?")
    assert "## Key findings" in draft
    assert draft.count("[") >= 2, "every fact must carry a [source] citation"
    assert "## What you should remember" in draft


def test_write_draft_adds_mechanism_section_from_feedback():
    board = Blackboard()
    board.add_fact("Neurons pass signals along weighted connections.", "neural-networks", "Aria")
    board.add_fact("Training adjusts weights with gradient descent, layer by layer.", "neural-networks", "Aria")
    board.add_fact("Backpropagation computes how to nudge each weight.", "neural-networks", "Aria")
    feedback = "add a 'How it works' section — the topic is about a mechanism."
    draft = brain.write_draft("Bilal", "How do neural networks work?", board.facts, feedback)
    assert "## How it works" in draft
    assert draft.index("## How it works") < draft.index("## Key findings")


def test_write_draft_without_facts_is_honest_not_broken():
    draft = brain.write_draft("Bilal", "Unknown topic", [], None)
    assert "could not be drafted" in draft


def test_critique_flags_missing_mechanism_section():
    board = Blackboard()
    board.add_fact("Neurons pass signals along weighted connections.", "neural-networks", "Aria")
    draft = brain.write_draft("Bilal", "How do neural networks work?", board.facts, None)
    scores, report = brain.critique("Cleo", "How do neural networks work?", draft, board.facts)
    assert set(scores) == {"coverage", "citations", "structure", "relevance"}
    assert "How it works" in report
    assert "not approved".strip() not in report and "add a 'How it works'" in report


def test_critique_approves_when_mechanism_section_present():
    board = Blackboard()
    for i, text in enumerate(
        [
            "Neurons pass signals along weighted connections.",
            "Training adjusts weights with gradient descent.",
            "Backpropagation computes how to nudge each weight.",
            "Networks learn by example, layer by layer.",
        ]
    ):
        board.add_fact(text, "neural-networks", f"agent{i}")
    draft = brain.write_draft(
        "Bilal", "How do neural networks work?", board.facts,
        "add a 'How it works' section — the topic is about a mechanism.",
    )
    scores, report = brain.critique("Cleo", "How do neural networks work?", draft, board.facts)
    assert "feedback: none — draft approved" in report
    assert scores["citations"] == 10
    assert scores["structure"] == 10


def test_generic_answer_uses_facts_or_says_so():
    board = Blackboard()
    board.add_fact("A fact with a source.", "history-of-ai", "Aria")
    assert "A fact with a source." in brain.generic_answer("Sana", "brief me", board.facts)
    assert "no grounded facts" in brain.generic_answer("Sana", "brief me", [])