import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def apify_item() -> dict:
    return json.loads((FIXTURES / "apify_item.json").read_text(encoding="utf-8"))
