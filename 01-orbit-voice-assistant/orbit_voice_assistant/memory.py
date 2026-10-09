"""Memory: the note store (persistent) and session memory (per conversation).

These are the two "remember" layers of the assistant:

* :class:`NotesStore` — long-term notes that survive restarts, backed by a
  JSON file (``runs/notes.json`` by default, gitignored).
* :class:`SessionMemory` — the last few turns of one conversation, used to
  answer follow-ups like "remind me what I asked" without a database.
"""

from __future__ import annotations

import json
import time
import uuid
from collections import deque
from pathlib import Path


class NotesStore:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path else (
            Path(__file__).resolve().parent.parent / "runs" / "notes.json"
        )
        self._notes: list[dict] = []
        self._load()

    def _load(self) -> None:
        if not self.path.exists():
            return
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            self._notes = [n for n in data if isinstance(n, dict) and "text" in n]
        except (json.JSONDecodeError, OSError):
            self._notes = []

    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(self._notes, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    def add(self, text: str) -> dict:
        note = {
            "id": uuid.uuid4().hex[:8],
            "text": text,
            "created": time.strftime("%Y-%m-%d %H:%M"),
        }
        self._notes.append(note)
        self._save()
        return note

    def list(self) -> list[dict]:
        return list(self._notes)

    def delete(self, key: str) -> bool:
        """Delete by short id, by index (#3), or by substring match."""
        key = key.strip()
        for i, note in enumerate(self._notes):
            if note["id"].startswith(key) or key.lower() in note["text"].lower():
                self._notes.pop(i)
                self._save()
                return True
        if key.startswith("#"):
            try:
                idx = int(key[1:]) - 1
                if 0 <= idx < len(self._notes):
                    self._notes.pop(idx)
                    self._save()
                    return True
            except ValueError:
                pass
        return False

    def __len__(self) -> int:
        return len(self._notes)


class SessionMemory:
    """Ring-buffer of the last ``max_turns`` (user, assistant) pairs."""

    def __init__(self, max_turns: int = 6) -> None:
        self.turns: deque[tuple[str, str]] = deque(maxlen=max_turns)

    def add(self, user: str, assistant: str) -> None:
        self.turns.append((user, assistant))

    def as_text(self) -> str:
        return "\n".join(
            f"user: {u}\nassistant: {a}" for u, a in self.turns
        ) or "(no prior turns)"