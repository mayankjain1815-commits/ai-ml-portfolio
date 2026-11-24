"""Refresh the four embedded JSON snapshots used by index.html offline.

Run from anywhere with ``python backend/sync_index.py``. The page still works
without a server; this script keeps its copies identical to the backend modules.
"""

import json
import re
from pathlib import Path

from word_atlas.data import all_words
from word_atlas.repos import all_repos
from word_atlas.solar import solar_payload
from word_atlas.themes import all_themes

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "index.html"

SNAPSHOTS = {
    "word-atlas-data": all_words,
    "repo-atlas-data": all_repos,
    "theme-atlas-data": all_themes,
    "solar-atlas-data": solar_payload,
}


def sync():
    text = PAGE.read_text()
    for script_id, loader in SNAPSHOTS.items():
        blob = json.dumps(loader(), ensure_ascii=False, separators=(",", ":"))
        pattern = re.compile(
            r'(<script type="application/json" id="' + re.escape(script_id) +
            r'">)(.*?)(</script>)', re.S,
        )
        text, count = pattern.subn(lambda m: m.group(1) + blob + m.group(3), text)
        if count != 1:
            raise RuntimeError(f"expected one {script_id} script tag, found {count}")
    PAGE.write_text(text)
    return PAGE


if __name__ == "__main__":
    print(f"Synced embedded snapshots in {sync()}")
