"""Tests for the Blackboard shared-memory model."""

from crew_engine.blackboard import Blackboard


def test_add_fact_and_dedupe():
    board = Blackboard()
    board.add_fact("Neurons pass signals along connections.", "neural-networks", "Aria")
    board.add_fact("Neurons pass signals along connections.", "neural-networks", "Bilal")
    board.add_fact("The first AI winter hit funding hard.", "history-of-ai", "Aria")
    assert len(board.facts) == 2


def test_facts_are_immutable_records():
    board = Blackboard()
    board.add_fact("Facts keep their source.", "history-of-ai", "Aria")
    fact = board.facts[0]
    assert fact.source == "history-of-ai"
    assert fact.by_agent == "Aria"
    assert fact.to_dict()["content"] == "Facts keep their source."


def test_facts_for_relevance_filter():
    board = Blackboard()
    board.add_fact("Gradient descent updates the weights.", "neural-networks", "Aria")
    board.add_fact("The 2012 ImageNet moment changed everything.", "history-of-ai", "Bilal")
    matched = board.facts_for("training weights gradient")
    assert len(matched) == 1
    assert "weights" in matched[0].content


def test_say_and_transcript_ordering():
    board = Blackboard()
    board.say("SYSTEM", "start")
    board.say("Aria", "found something")
    board.say("Bilal", "wrote it down")
    transcript = board.transcript()
    lines = transcript.splitlines()
    assert len(lines) == 3
    assert "SYSTEM" in lines[0]
    assert "Aria" in lines[1]
    assert lines.index(next(l for l in lines if "Aria" in l)) < lines.index(
        next(l for l in lines if "Bilal" in l)
    )


def test_artifacts_roundtrip_and_overwrite():
    board = Blackboard()
    assert board.get_artifact("draft") is None
    board.put_artifact("draft", "v1")
    board.put_artifact("draft", "v2")
    assert board.get_artifact("draft") == "v2"


def test_facts_for_empty_topic_returns_all():
    board = Blackboard()
    board.add_fact("one", "a", "x")
    board.add_fact("two", "b", "y")
    assert len(board.facts_for("")) == 2