"""Run with: cd backend && python -m word_atlas"""

import os

from .app import create_app, validate_data

app = create_app()

if __name__ == "__main__":
    validate_data()
    port = int(os.environ.get("PORT", "5110"))
    print(f"Word Atlas API on http://127.0.0.1:{port}  ({len(app.url_map._rules)} routes)")
    app.run(host="127.0.0.1", port=port, debug=False)
