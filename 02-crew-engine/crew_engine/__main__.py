"""Entry point: ``python -m crew_engine`` routes to the CLI."""

import sys

from .cli import main

if __name__ == "__main__":
    sys.exit(main())