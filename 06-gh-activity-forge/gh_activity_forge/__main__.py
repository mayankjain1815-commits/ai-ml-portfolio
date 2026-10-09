"""Allow ``python -m gh_activity_forge`` to run the CLI."""

import sys

from .cli import main

sys.exit(main())
