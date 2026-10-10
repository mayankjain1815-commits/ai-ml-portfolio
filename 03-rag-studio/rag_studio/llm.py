"""Gemini REST access for real mode, with an offline fallback for demo mode.

Everything here talks to the public Gemini REST endpoints with plain `requests`
— no SDK, per the repo's dependency rules. The module reads `GEMINI_API_KEY`
from the environment (via python-dotenv against the project-root `.env`).

Contract, mirroring the shared convention in docs/BUILD_SPEC.md:

* key present  -> real call, 15 s timeout, two retries on transient failures,
  and an error message that tells you demo mode still works;
* key absent   -> log one line and return a deterministic offline response, so
  a missing key can never crash a caller.

Note the RAG pipeline never *needs* the offline branch: demo mode routes around
`complete()` entirely (thesaurus expansion in retriever.py, extractive answers
in generate.py), which is the "parallel implementation" rule from the spec.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path

import requests

from rag_studio.text import content_words, split_sentences
from rag_studio.thesaurus import expansions

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-2.0-flash"
EMBEDDING_MODEL = "text-embedding-004"
API_BASE = "https://generativelanguage.googleapis.com/v1beta"
TIMEOUT_SECONDS = 15
MAX_RETRIES = 2  # retries on top of the first attempt
_RETRY_BACKOFF_SECONDS = 0.5  # 0.5 s, then 1.0 s

_RETRYABLE_STATUS = {429, 500, 502, 503, 504}
_demo_line_logged = False


class LLMError(RuntimeError):
    """A Gemini request failed after retries, or returned something unusable."""


def _load_env_file() -> None:
    """Load the project-root .env exactly once, whatever the working directory."""
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - dotenv is a declared dependency
        return
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")


_load_env_file()


def get_api_key() -> str | None:
    """Return the configured Gemini key, or None in demo mode."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    return key or None


def log_demo_mode_once() -> None:
    """Emit the one-line demo-mode notice, at most once per process."""
    global _demo_line_logged
    if get_api_key() is None and not _demo_line_logged:
        logger.info("[demo mode] no API key found - using offline generator")
        _demo_line_logged = True


def _post_with_retries(url: str, payload: dict, key: str) -> dict:
    """POST JSON to Gemini with a 15 s timeout and two retries on 429/5xx.

    Raises LLMError with a message that keeps demo mode on the table.
    """
    last_problem = "unknown error"
    for attempt in range(1 + MAX_RETRIES):
        if attempt:
            time.sleep(_RETRY_BACKOFF_SECONDS * attempt)
        try:
            response = requests.post(
                url,
                json=payload,
                headers={"Content-Type": "application/json", "x-goog-api-key": key},
                timeout=TIMEOUT_SECONDS,
            )
        except requests.RequestException as exc:
            last_problem = f"network error: {exc}"
            continue
        if response.status_code == 200:
            try:
                return response.json()
            except ValueError:
                last_problem = "response was not valid JSON"
                continue
        if response.status_code in _RETRYABLE_STATUS:
            last_problem = f"HTTP {response.status_code}: {response.text[:200]}"
            continue
        raise LLMError(
            f"Gemini request rejected (HTTP {response.status_code}): {response.text[:300]}. "
            "Demo mode still works - unset GEMINI_API_KEY to run offline."
        )
    raise LLMError(
        f"Gemini request failed after {1 + MAX_RETRIES} attempts ({last_problem}). "
        "Demo mode still works - unset GEMINI_API_KEY to run offline."
    )


def complete(prompt: str, *, system: str | None = None, json_mode: bool = False) -> str:
    """Return a Gemini completion for `prompt`; offline fallback without a key."""
    key = get_api_key()
    if key is None:
        log_demo_mode_once()
        return _offline_complete(prompt, system=system, json_mode=json_mode)

    config: dict = {"temperature": 0.2}
    if json_mode:
        config["responseMimeType"] = "application/json"
    payload: dict = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": config,
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}

    data = _post_with_retries(f"{API_BASE}/models/{GEMINI_MODEL}:generateContent", payload, key)
    try:
        parts = data["candidates"][0]["content"]["parts"]
        text = "".join(part.get("text", "") for part in parts)
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMError(f"unexpected Gemini response shape: {exc}") from exc
    if not text.strip():
        raise LLMError("Gemini returned an empty completion")
    return text.strip()


def embed_texts(texts: list[str], *, api_key: str | None = None) -> list[list[float]]:
    """Embed strings with Gemini's text-embedding-004 (batch endpoint).

    Raises LLMError when no key is available or the request fails; index.py
    decides whether to fall back to TF-IDF.
    """
    key = api_key or get_api_key()
    if not key:
        raise LLMError("embeddings require GEMINI_API_KEY (or build with TF-IDF)")
    if not texts:
        return []

    payload = {
        "model": f"models/{EMBEDDING_MODEL}",
        "requests": [{"content": {"parts": [{"text": text}]}} for text in texts],
    }
    data = _post_with_retries(
        f"{API_BASE}/models/{EMBEDDING_MODEL}:batchEmbedContents", payload, key
    )
    try:
        return [entry["values"] for entry in data["embeddings"]]
    except (KeyError, TypeError) as exc:
        raise LLMError(f"unexpected Gemini embedding response: {exc}") from exc


def _offline_complete(
    prompt: str, *, system: str | None = None, json_mode: bool = False
) -> str:
    """Deterministic stand-in so `complete()` keeps its contract without a key.

    Seeded by the prompt's own content, it answers the only two shapes this
    project ever sends: query rewriting (JSON -> thesaurus-based rewrites) and
    question answering (pull the best sentences out of the sources embedded in
    the prompt). Not a placeholder - just the demo generator, at the wrong layer.
    """
    del system  # shape detection comes from the prompt itself
    if json_mode:
        question = _question_from(prompt) or prompt.strip().splitlines()[0]
        variants = expansions(question)
        return json.dumps({"rewrites": variants[1:] or [question]}, indent=2)

    region = _sources_region(prompt)
    sentences = [
        sentence
        for sentence in split_sentences(region)
        if len(content_words(sentence)) >= 4
    ]
    digest = hashlib.sha256(prompt.encode("utf-8")).digest()
    ranked = sorted(
        range(len(sentences)),
        key=lambda i: (-len(content_words(sentences[i])), int(digest[i % len(digest)])),
    )
    chosen = sorted(ranked[:3])  # keep document order for readability
    if not chosen:
        return "The prompt did not contain any extractable source text."
    return " ".join(sentences[i] for i in chosen)


def _question_from(prompt: str) -> str | None:
    """Pull the 'Question: ...' line out of a prompt, if one is present."""
    for line in prompt.splitlines():
        if line.strip().lower().startswith("question:"):
            return line.split(":", 1)[1].strip()
    return None


def _sources_region(prompt: str) -> str:
    """Isolate the numbered sources block, falling back to the whole prompt."""
    marker = "Sources:"
    if marker in prompt:
        after = prompt.split(marker, 1)[1]
        stop = after.find("\nQuestion:")
        return after[:stop] if stop != -1 else after
    return prompt
