"""Erzeugt docs/code-doku/index.html (Aufruf: `python3 docs/code-doku/generate.py [--check]`)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from tools.code_doku.cli import main

if __name__ == "__main__":
    sys.exit(main())
