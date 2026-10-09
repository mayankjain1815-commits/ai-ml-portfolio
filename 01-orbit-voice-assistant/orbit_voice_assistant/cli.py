"""CLI entry point: ``python -m orbit_voice_assistant`` serves the app."""

from __future__ import annotations

import argparse
import sys
import webbrowser


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="orbit",
        description="Orbit — a voice-first assistant in your browser. Demo brain "
                    "by default; set GEMINI_API_KEY for real LLM replies.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    parser.add_argument("--port", type=int, default=5101, help="port (default 5101)")
    parser.add_argument("--no-browser", action="store_true",
                        help="do not open a browser tab automatically")
    parser.add_argument("--no-reloader", action="store_true", help="disable the dev reloader")
    args = parser.parse_args(argv)

    from . import llm
    from .app import create_app

    url = f"http://{args.host}:{args.port}"
    print(f"Orbit listening on {url}")
    if llm.have_key():
        print("LLM mode: GEMINI_API_KEY detected — real model replies.")
    else:
        print(llm.demo_note())
    if not args.no_browser:
        webbrowser.open(url)
    create_app().run(
        host=args.host,
        port=args.port,
        debug=not args.no_reloader,
        use_reloader=not args.no_reloader,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())