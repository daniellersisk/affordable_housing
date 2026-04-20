"""Contract test shared fixtures and helpers.

This file intentionally stays framework-light so it can be adapted once
the FastAPI app and test client wiring are added.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

SCHEMAS_DIR = Path(__file__).parent / "schemas"


def load_contract_schema(filename: str) -> dict[str, Any]:
    """Load a contract schema fixture from tests/contract/schemas.

    The fixture files are JSON documents committed to version control.
    """
    path = SCHEMAS_DIR / filename
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)
