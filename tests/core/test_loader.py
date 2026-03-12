import pytest

from langchain_skills_adapters.core.base import Skill, SkillCatalog
from langchain_skills_adapters.core.loader import SkillsLoader


class TestSkillsLoaderInit:
    def test_loads_skills_on_init(self, skills_path):
        loader = SkillsLoader(skills_path)
        assert loader.skill_catalog is not None
        assert isinstance(loader.skill_catalog, SkillCatalog)

    def test_stores_skills_path(self, skills_path):
        loader = SkillsLoader(skills_path)
        assert loader.skills_path == skills_path

    def test_populates_skill_map(self, skills_path):
        loader = SkillsLoader(skills_path)
        assert isinstance(loader.skill_map, dict)
        assert len(loader.skill_map) > 0

    def test_invalid_path_yields_no_skills(self, tmp_path):
        loader = SkillsLoader(tmp_path)
        assert loader.skill_catalog.skills == []
        assert loader.skill_map == {}


class TestSkillsLoaderLoad:
    def test_discovers_skill_from_directory(self, skills_path):
        loader = SkillsLoader(skills_path)
        assert "my-skill" in loader.skill_map

    def test_loaded_skill_has_correct_name(self, skills_path):
        loader = SkillsLoader(skills_path)
        skill = loader.skill_map["my-skill"]
        assert skill.name == "my-skill"

    def test_loaded_skill_has_correct_description(self, skills_path):
        loader = SkillsLoader(skills_path)
        skill = loader.skill_map["my-skill"]
        assert skill.description == "A test skill that summarizes text input provided by the user."

    def test_loaded_skill_has_content(self, skills_path):
        loader = SkillsLoader(skills_path)
        skill = loader.skill_map["my-skill"]
        assert "summarization assistant" in skill.content

    def test_loaded_skill_location_points_to_skill_md(self, skills_path):
        loader = SkillsLoader(skills_path)
        skill = loader.skill_map["my-skill"]
        assert skill.location.name == "SKILL.md"
        assert skill.location.exists()

    def test_catalog_contains_all_skills(self, skills_path):
        loader = SkillsLoader(skills_path)
        assert len(loader.skill_catalog.skills) == len(loader.skill_map)

    def test_malformed_skill_raises_value_error(self, tmp_path):
        skill_dir = tmp_path / "bad-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        # Missing required 'name' field in frontmatter
        skill_file.write_text("---\ndescription: no name\n---\nContent here.")
        with pytest.raises(ValueError, match="Failed to load skill"):
            SkillsLoader(tmp_path)


class TestSkillsLoaderGetCatalog:
    def test_returns_string(self, skills_path):
        loader = SkillsLoader(skills_path)
        catalog = loader.get_catalog()
        assert isinstance(catalog, str)

    def test_contains_available_skills_tags(self, skills_path):
        loader = SkillsLoader(skills_path)
        catalog = loader.get_catalog()
        assert "<available_skills>" in catalog
        assert "</available_skills>" in catalog

    def test_contains_loaded_skill(self, skills_path):
        loader = SkillsLoader(skills_path)
        catalog = loader.get_catalog()
        assert "my-skill" in catalog

    def test_empty_when_no_skills(self, tmp_path):
        loader = SkillsLoader(tmp_path)
        assert loader.get_catalog() == ""


class TestSkillsLoaderGetSkill:
    def test_returns_skill_by_name(self, skills_path):
        loader = SkillsLoader(skills_path)
        skill = loader.get_skill("my-skill")
        assert isinstance(skill, Skill)
        assert skill.name == "my-skill"

    def test_raises_for_unknown_skill(self, skills_path):
        loader = SkillsLoader(skills_path)
        with pytest.raises(ValueError, match="not found"):
            loader.get_skill("nonexistent-skill")
