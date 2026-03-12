from pathlib import Path

import pytest


@pytest.fixture
def skills_path():
    return Path(__file__).parent / "static" / "skills"
