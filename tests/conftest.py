"""Test configuration shared across the lightweight test suite.

Pytest runs the tests from the repo root, so we add the project folder to
`sys.path` here once instead of repeating import setup in every test file.
"""

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
