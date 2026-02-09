"""
Entry point for the lib2notebook2lib package.

Allows running the package as an executable module:
    python -m lib2notebook2lib
"""

import sys
from .cli import main

if __name__ == "__main__":
    sys.exit(main())
