from langchain_core.tools import BaseTool

from langchain_skills_adapters.core import SkillsLoader
from langchain_skills_adapters.tools.skills_tool import SkillsTool, SkillsToolArgsSchema


class TestSkillsToolInit:
    def test_is_base_tool_subclass(self, skills_path):
        tool = SkillsTool(skills_path)
        assert isinstance(tool, BaseTool)

    def test_name_is_activate_skill(self, skills_path):
        tool = SkillsTool(skills_path)
        assert tool.name == "activate_skill"

    def test_description_contains_skill_catalog(self, skills_path):
        tool = SkillsTool(skills_path)
        assert "available_skills" in tool.description
        assert "my-skill" in tool.description

    def test_description_contains_usage_instructions(self, skills_path):
        tool = SkillsTool(skills_path)
        assert "activate_skill" in tool.description
        assert "skill's name" in tool.description

    def test_args_schema_is_set(self, skills_path):
        tool = SkillsTool(skills_path)
        assert tool.args_schema is SkillsToolArgsSchema

    def test_stores_skills_path(self, skills_path):
        tool = SkillsTool(skills_path)
        assert tool.skills_path == skills_path

    def test_initializes_skills_loader(self, skills_path):
        tool = SkillsTool(skills_path)
        assert isinstance(tool.skills_loader, SkillsLoader)

    def test_empty_skills_dir_produces_no_catalog(self, tmp_path):
        tool = SkillsTool(tmp_path)
        assert "available_skills" not in tool.description


class TestSkillsToolRun:
    def test_returns_skill_content_for_valid_name(self, skills_path):
        tool = SkillsTool(skills_path)
        result = tool._run("my-skill")
        assert "summarization assistant" in result
        assert "skill_content" in result

    def test_returns_error_for_nonexistent_skill(self, skills_path):
        tool = SkillsTool(skills_path)
        result = tool._run("nonexistent-skill")
        assert "Error" in result
        assert "nonexistent-skill" in result

    def test_invoke_returns_skill_content(self, skills_path):
        tool = SkillsTool(skills_path)
        result = tool.invoke({"name": "my-skill"})
        assert "summarization assistant" in result
        assert "skill_content" in result

    def test_invoke_with_invalid_name_returns_error(self, skills_path):
        tool = SkillsTool(skills_path)
        result = tool.invoke({"name": "does-not-exist"})
        assert "Error" in result
        assert "does-not-exist" in result

    def test_generic_exception_returns_error(self, skills_path):
        tool = SkillsTool(skills_path)
        # Force a non-ValueError exception by breaking the skill object
        tool.skills_loader.skill_map["my-skill"] = None
        result = tool._run("my-skill")
        assert "Error:" in result
