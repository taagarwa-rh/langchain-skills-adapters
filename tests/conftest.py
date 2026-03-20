from pathlib import Path

import pytest

from langchain_skills_adapters.core.base import Skill


@pytest.fixture
def skills_path():
    return Path(__file__).parent / "static" / "skills"


@pytest.fixture
def make_skill():
    """Factory for creating Skill objects with sensible defaults."""

    def _make(**overrides):
        defaults = {
            "name": "test-skill",
            "description": "A test skill.",
            "location": Path("/skills/test-skill/SKILL.md"),
            "content": "Do the thing.",
        }
        defaults.update(overrides)
        return Skill(**defaults)

    return _make
