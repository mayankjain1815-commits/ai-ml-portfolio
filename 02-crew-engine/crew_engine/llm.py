"""LLM access with the repo-wide convention:

* ``GEMINI_API_KEY`` set  -> real call to Gemini's REST API.
* no key                  -> deterministic offline output.

The demo path is implemented by :mod:`crew_engine.brain`, *not* here —
``llm.chat`` raises :class:`LLMUnavailable` so agents know to hand control
to their demo brain. Keeping the two paths explicit is what makes this
framework explainable: "if a model is available, use it; otherwise use the
rule-based brain that never crashes."
"""

from __future__ import annotations

import os
import time
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:  # pragma: no cover - dotenv is optional
    pass

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)
TIMEOUT_S = 20
MAX_RETRIES = 2


class LLMUnavailable(RuntimeError):
    """The caller must fall back to a demo brain when this is raised."""


def have_key() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def chat(system: str, user_message: str, *, temperature: float = 0.4) -> str:
    """One system + one user turn, returns the model's text reply."""
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not key:
        raise LLMUnavailable("no API key set")

    payload = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": user_message}]}],
        "generationConfig": {"temperature": temperature},
    }
    headers = {"x-goog-api-key": key}
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            import requests

            resp = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=TIMEOUT_S)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"].strip()
        except Exception as exc:  # network, rate limit, malformed reply
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (2**attempt))
    raise RuntimeError(
        f"Gemini call failed after {MAX_RETRIES + 1} attempts: {last_error}. "
        "Demo mode still works without a key."
    )


def demo_note() -> str:
    return "[demo mode] no API key — agents run their deterministic brains"