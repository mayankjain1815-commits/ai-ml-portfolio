"""Orbit — a voice-first assistant you talk to in a browser tab.

* **Demo mode (no API key)** — a deterministic, rule-based brain: intent
  classification (time, math, notes, apps, files, search) with slot
  extraction, backed by real tools (safe calculator, JSON note store,
  allowlisted app launcher).
* **LLM mode (GEMINI_API_KEY)** — the same shell runs the Gemini REST API in a
  ReAct loop: think -> call a tool -> observe -> answer, with an honest
  fallback to the demo brain if the model is unreachable.

Same frontend either way: Web Speech API for mic in + speech out, nothing
loaded from a CDN, works with the network off.
"""

__version__ = "1.0.0"