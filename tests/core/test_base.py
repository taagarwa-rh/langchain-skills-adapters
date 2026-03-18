from pathlib import Path

import pytest

from langchain_skills_adapters.core.base import Skill, SkillCatalog


def _make_skill(**overrides):
    defaults = {
        "name": "test-skill",
        "description": "A test skill.",
        "location": Path("/skills/test-skill/SKILL.md"),
        "content": "Do the thing.",
    }
    defaults.update(overrides)
    return Skill(**defaults)


class TestSkillModel:
    def test_required_fields(self):
        skill = _make_skill()
        assert skill.name == "test-skill"
        assert skill.description == "A test skill."
        assert skill.location == Path("/skills/test-skill/SKILL.md")
        assert skill.content == "Do the thing."

    def test_optional_fields_default_to_none(self):
        skill = _make_skill()
        assert skill.license is None
        assert skill.compatibility is None
        assert skill.metadata is None

    def test_allowed_tools_defaults_to_empty_list(self):
        skill = _make_skill()
        assert skill.allowed_tools == []

    def test_resources_defaults_to_empty_list(self):
        skill = _make_skill()
        assert skill.resources == []

    def test_optional_fields_can_be_set(self):
        skill = _make_skill(
            license="MIT",
            compatibility=">=1.0",
            metadata={"author": "test"},
            allowed_tools=["tool_a", "tool_b"],
        )
        assert skill.license == "MIT"
        assert skill.compatibility == ">=1.0"
        assert skill.metadata == {"author": "test"}
        assert skill.allowed_tools == ["tool_a", "tool_b"]

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            Skill(name="x", description="y", location=Path("/a"))  # missing content


class TestSkillToCatalog:
    def test_contains_skill_xml_tags(self):
        result = _make_skill().to_catalog()
        assert "<skill>" in result
        assert "</skill>" in result

    def test_contains_name(self):
        result = _make_skill(name="my-skill").to_catalog()
        assert "<name>my-skill</name>" in result

    def test_contains_description(self):
        result = _make_skill(description="Summarize text.").to_catalog()
        assert "<description>Summarize text.</description>" in result

    def test_contains_location(self):
        loc = Path("/skills/my-skill/SKILL.md")
        result = _make_skill(location=loc).to_catalog()
        assert f"<location>{loc}</location>" in result

    def test_does_not_contain_content(self):
        result = _make_skill(content="secret content").to_catalog()
        assert "secret content" not in result


class TestSkillToContent:
    def test_contains_skill_content_tag_with_name(self):
        result = _make_skill(name="my-skill").to_content()
        assert '<skill_content name="my-skill">' in result
        assert "</skill_content>" in result

    def test_contains_content_body(self):
        result = _make_skill(content="Do the thing.").to_content()
        assert "Do the thing." in result

    def test_contains_skill_directory(self):
        skill = _make_skill(location=Path("/skills/test-skill/SKILL.md"))
        result = skill.to_content()
        assert f"Skill directory: {Path('/skills/test-skill')}" in result

    def test_no_resources_omits_skill_resources_section(self):
        result = _make_skill().to_content()
        assert "<skill_resources>" not in result
        assert "</skill_resources>" not in result

    def test_contains_skill_resources_section_when_resources_present(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        location = skill_dir / "SKILL.md"
        resource = skill_dir / "data" / "ref.txt"

        skill = _make_skill(location=location, resources=[resource])
        result = skill.to_content()
        assert "<skill_resources>" in result
        assert "</skill_resources>" in result

    def test_lists_resource_files_relative_to_skill_dir(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        location = skill_dir / "SKILL.md"
        resource = skill_dir / "data" / "ref.txt"

        skill = _make_skill(location=location, resources=[resource])
        result = skill.to_content()
        assert "<file>data/ref.txt</file>" in result

    def test_multiple_resources_listed(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        location = skill_dir / "SKILL.md"
        resources = [skill_dir / "a.txt", skill_dir / "b.txt"]

        skill = _make_skill(location=location, resources=resources)
        result = skill.to_content()
        assert "<file>a.txt</file>" in result
        assert "<file>b.txt</file>" in result


class TestSkillFromPath:
    def test_loads_skill_from_valid_file(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: my-skill\ndescription: A cool skill.\n---\nDo the thing.\n")
        skill = Skill.from_path(skill_file)
        assert skill.name == "my-skill"
        assert skill.description == "A cool skill."
        assert skill.content == "Do the thing."
        assert skill.location == skill_file

    def test_parses_allowed_tools(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: my-skill\ndescription: A skill.\nallowed-tools: tool_a tool_b\n---\nContent here.\n")
        skill = Skill.from_path(skill_file)
        assert skill.allowed_tools == ["tool_a", "tool_b"]

    def test_optional_frontmatter_fields(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: my-skill\ndescription: A skill.\nlicense: MIT\ncompatibility: '>=1.0'\n---\nContent.\n")
        skill = Skill.from_path(skill_file)
        assert skill.license == "MIT"
        assert skill.compatibility == ">=1.0"

    def test_missing_name_raises(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\ndescription: A skill.\n---\nContent.\n")
        with pytest.raises(ValueError, match="Missing required field name"):
            Skill.from_path(skill_file)

    def test_missing_description_raises(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: my-skill\n---\nContent.\n")
        with pytest.raises(ValueError, match="Missing required field description"):
            Skill.from_path(skill_file)

    def test_discovers_resource_files(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: my-skill\ndescription: A skill.\n---\nContent.\n")
        resource = skill_dir / "data.txt"
        resource.write_text("some data")

        skill = Skill.from_path(skill_file)
        assert resource in skill.resources

    def test_excludes_skill_file_from_resources(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        skill_file = skill_dir / "SKILL.md"
        skill_file.write_text("---\nname: my-skill\ndescription: A skill.\n---\nContent.\n")
        skill = Skill.from_path(skill_file)
        assert skill_file not in skill.resources

    def test_multiline_content(self, tmp_path):
        skill_file = tmp_path / "SKILL.md"
        skill_file.write_text("---\nname: my-skill\ndescription: A skill.\n---\nLine one.\n\nLine two.\n")
        skill = Skill.from_path(skill_file)
        assert "Line one." in skill.content
        assert "Line two." in skill.content


class TestSkillCatalogModel:
    def test_skills_defaults_to_empty_list(self):
        catalog = SkillCatalog()
        assert catalog.skills == []

    def test_accepts_list_of_skills(self):
        skills = [_make_skill(name="a"), _make_skill(name="b")]
        catalog = SkillCatalog(skills=skills)
        assert len(catalog.skills) == 2


class TestSkillCatalogToStr:
    def test_empty_catalog_returns_empty_string(self):
        catalog = SkillCatalog()
        assert catalog.to_str() == ""

    def test_contains_available_skills_tags(self):
        catalog = SkillCatalog(skills=[_make_skill()])
        result = catalog.to_str()
        assert "<available_skills>" in result
        assert "</available_skills>" in result

    def test_contains_skill_entries(self):
        catalog = SkillCatalog(skills=[_make_skill(name="my-skill")])
        result = catalog.to_str()
        assert "<name>my-skill</name>" in result

    def test_multiple_skills_all_appear(self):
        skills = [_make_skill(name="alpha"), _make_skill(name="beta")]
        catalog = SkillCatalog(skills=skills)
        result = catalog.to_str()
        assert "<name>alpha</name>" in result
        assert "<name>beta</name>" in result

    def test_entries_are_indented(self):
        catalog = SkillCatalog(skills=[_make_skill()])
        result = catalog.to_str()
        # Each line inside <available_skills> should start with two spaces
        inner_lines = result.split("\n")[1:-1]
        for line in inner_lines:
            assert line.startswith("  ")
