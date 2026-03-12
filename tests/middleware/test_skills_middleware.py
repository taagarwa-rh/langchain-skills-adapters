from unittest.mock import MagicMock

from langchain_community.tools.file_management.read import ReadFileTool
from langchain_core.messages import SystemMessage

from langchain_skills_adapters.core import SkillsLoader
from langchain_skills_adapters.middleware.skills_middleware import SkillsMiddleware


class TestSkillsMiddlewareInit:
    def test_stores_skills_path(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        assert mw.skills_path == skills_path

    def test_initializes_skills_loader(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        assert isinstance(mw.skills_loader, SkillsLoader)

    def test_system_prompt_contains_catalog(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        assert "my-skill" in mw.system_prompt

    def test_system_prompt_contains_instructions(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        assert "skills_file_read" in mw.system_prompt
        assert "SKILL.md" in mw.system_prompt

    def test_tools_contains_read_file_tool(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        assert len(mw.tools) == 1
        assert isinstance(mw.tools[0], ReadFileTool)

    def test_read_file_tool_has_correct_name(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        assert mw.read_file_tool.name == "skills_file_read"

    def test_read_file_tool_has_correct_root_dir(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        assert mw.read_file_tool.root_dir == str(skills_path)

    def test_empty_skills_dir_produces_no_catalog_content(self, tmp_path):
        mw = SkillsMiddleware(tmp_path)
        assert "available_skills" not in mw.system_prompt


class TestSkillsMiddlewareWrapModelCall:
    def _make_mock_request(self, content_blocks):
        mock_request = MagicMock()
        mock_system_message = MagicMock()
        mock_system_message.content_blocks = content_blocks
        mock_request.system_message = mock_system_message
        mock_request.override.return_value = mock_request
        return mock_request

    def test_appends_system_prompt_to_system_message(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        original_content = [{"type": "text", "text": "You are a helpful assistant."}]
        mock_request = self._make_mock_request(original_content)

        mw.wrap_model_call(mock_request, MagicMock())

        mock_request.override.assert_called_once()
        new_system_message = mock_request.override.call_args.kwargs["system_message"]

        assert isinstance(new_system_message, SystemMessage)
        assert len(new_system_message.content) == 2
        assert new_system_message.content[0] == original_content[0]
        assert mw.system_prompt in new_system_message.content[1]["text"]

    def test_calls_handler_with_overridden_request(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        mock_request = self._make_mock_request([{"type": "text", "text": "Original"}])

        overridden_request = MagicMock()
        mock_request.override.return_value = overridden_request

        mock_handler = MagicMock()
        mock_response = MagicMock()
        mock_handler.return_value = mock_response

        result = mw.wrap_model_call(mock_request, mock_handler)

        mock_handler.assert_called_once_with(overridden_request)
        assert result == mock_response

    def test_preserves_existing_content_blocks(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        original_blocks = [
            {"type": "text", "text": "Block one"},
            {"type": "text", "text": "Block two"},
        ]
        mock_request = self._make_mock_request(original_blocks)

        mw.wrap_model_call(mock_request, MagicMock())

        new_system_message = mock_request.override.call_args.kwargs["system_message"]
        assert len(new_system_message.content) == 3
        assert new_system_message.content[0] == original_blocks[0]
        assert new_system_message.content[1] == original_blocks[1]
