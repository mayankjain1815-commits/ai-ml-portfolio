"""One-stop LLM access with an offline demo fallback.

The contract used across this project (and its siblings in the monorepo):

* ``GEMINI_API_KEY`` set  -> real call to Gemini's REST API via ``requests``.
* no key                  -> deterministic offline generator, clearly labeled.

The offline path exists so the CLI is fully usable on a plane, in CI, or
before you've signed up for anything. It is not a stub: for skill *selection*
it does the same job as the model (rank skills by keyword overlap), so the
pipeline shape is identical either way — only the "brain" changes.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except Exception:  # pragma: no cover - dotenv is optional at runtime
    pass

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-2.0-flash:generateContent"
)
TIMEOUT_S = 15
MAX_RETRIES = 2


class LLMUnavailable(RuntimeError):
    """Raised when a real model was requested but no usable key exists."""


def api_key() -> str | None:
    return os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")


def have_key() -> bool:
    return api_key() is not None


def complete(
    prompt: str,
    *,
    system: str | None = None,
    json_mode: bool = False,
    temperature: float = 0.2,
) -> str:
    """Return model output for ``prompt``.

    Raises :class:`LLMUnavailable` only when the caller passes
    ``require_model=True`` semantics — in practice callers check
    :func:`have_key` first and fall back to their own demo logic.
    """
    key = api_key()
    if not key:
        raise LLMUnavailable(
            "No GEMINI_API_KEY/OPENAI_API_KEY set. Run in demo mode instead."
        )

    parts = [{"text": prompt}]
    payload: dict = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": temperature},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if json_mode:
        payload["generationConfig"]["responseMimeType"] = "application/json"

    headers = {"x-goog-api-key": key}
    last_error: Exception | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            import requests

            resp = requests.post(GEMINI_URL, json=payload, headers=headers, timeout=TIMEOUT_S)
            resp.raise_for_status()
            data = resp.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as exc:  # network / rate limit / malformed reply
            last_error = exc
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (2**attempt))
    raise RuntimeError(
        f"Gemini call failed after {MAX_RETRIES + 1} attempts: {last_error}. "
        "The project still works in demo mode (no key needed)."
    )


def demo_note() -> str:
    """One-line banner printed when running without a key."""
    return "[demo mode] no API key found — using offline generator"
