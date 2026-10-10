"""CLI-level tests: build → ask → load → eval → demo, all into tmp paths."""

import json

import pytest

from rag_studio.cli import _parse_ks, build_parser, main


@pytest.fixture(autouse=True)
def _no_api_key(monkeypatch):
    """The whole suite must exercise the deterministic offline paths."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


def _docs_dir(tmp_path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "01-packets.md").write_text(
        "The internet splits data into small pieces called packets. "
        "Each packet carries a payload and a header. "
        "Routers forward packets to the next hop.\n",
        encoding="utf-8",
    )
    (docs / "02-dns.md").write_text(
        "DNS turns a domain name into an IP address using a resolver. "
        "The resolver walks from root servers down to the answer.\n",
        encoding="utf-8",
    )
    return docs


def test_build_then_load(tmp_path, capsys):
    docs = _docs_dir(tmp_path)
    index_dir = tmp_path / "index"
    assert main(["build", str(docs), "--index", str(index_dir), "--offline"]) == 0
    assert (index_dir / "meta.json").is_file()
    assert (index_dir / "vectors.npz").is_file()
    meta = json.loads((index_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "tfidf"
    assert meta["settings"]["chunk_count"] == 2  # one chunk per short doc

    assert main(["load", "--index", str(index_dir)]) == 0
    assert "chunks:" in capsys.readouterr().out


def test_build_with_real_key_still_builds_tfidf_when_offline(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("GEMINI_API_KEY", "sk-fake-123")
    docs = _docs_dir(tmp_path)
    index_dir = tmp_path / "index"
    assert main(["build", str(docs), "--index", str(index_dir), "--offline"]) == 0
    meta = json.loads((index_dir / "meta.json").read_text(encoding="utf-8"))
    assert meta["mode"] == "tfidf"  # --offline wins over the fake key


def test_ask_offline(tmp_path, capsys):
    docs = _docs_dir(tmp_path)
    index_dir = tmp_path / "index"
    main(["build", str(docs), "--index", str(index_dir), "--offline"])
    assert (
        main(["ask", "how does dns turn a name into an address", "--index", str(index_dir), "--offline"]) == 0
    )
    out = capsys.readouterr().out
    assert "A:" in out
    assert "02-dns.md" in out  # the gold source is cited
    assert "extractive" in out


def test_eval_rebuild_writes_report(tmp_path, capsys):
    index_dir = tmp_path / "reindex"
    report = tmp_path / "report.json"
    assert (
        main(
            [
                "eval",
                "--index",
                str(index_dir),
                "--rebuild",
                "--report",
                str(report),
                "--offline",
            ]
        )
        == 0
    )
    assert report.is_file()
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert "recall_at_k" in payload["overall"]
    assert len(payload["questions"]) >= 10
    out = capsys.readouterr().out
    assert "recall@1" in out


def test_demo_output_and_artifacts(tmp_path, capsys):
    index_dir = tmp_path / "demo-index"
    report = tmp_path / "demo-report.json"
    assert (
        main(
            [
                "demo",
                "--index",
                str(index_dir),
                "--report",
                str(report),
                "--offline",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "demo complete" in out
    assert (index_dir / "meta.json").is_file()
    assert report.is_file()


def test_parser_exposes_expected_commands():
    help_text = build_parser().format_help()
    for command in ("build", "load", "ask", "chat", "eval", "demo"):
        assert command in help_text


def test_parse_ks_validates():
    assert _parse_ks("1,3,5") == [1, 3, 5]
    assert _parse_ks("5,1,3") == [1, 3, 5]  # dedup + sort
    with pytest.raises(Exception):
        _parse_ks("1,banana")
    with pytest.raises(Exception):
        _parse_ks("0")