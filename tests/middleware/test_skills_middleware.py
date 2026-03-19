import warnings
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from langchain_community.tools.file_management.read import ReadFileTool
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool

from langchain_skills_adapters.core import Skill, SkillsLoader
from langchain_skills_adapters.middleware.skills_middleware import SkillsMiddleware


@pytest.fixture
def make_model_request():
    """Factory for creating mock ModelRequest objects."""

    def _make(system_message=MagicMock(), messages=None, tools=None):
        request = MagicMock()
        request.system_message = system_message
        request.messages = messages or []
        request.tools = tools or []
        request.override.return_value = request
        return request

    return _make


@pytest.fixture
def make_tool_call_request():
    """Factory for creating mock ToolCallRequest objects."""

    def _make(tool_call, tool=None):
        request = MagicMock()
        request.tool_call = tool_call
        request.tool = tool
        request.override.return_value = request
        return request

    return _make


class TestInit:
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

    def test_dynamic_tools_default_empty_dict(self, skills_path):
        mw = SkillsMiddleware(skills_path)
        assert mw.dynamic_tools == {}

    def test_dynamic_tools_stored(self, skills_path):
        tool = MagicMock(spec=BaseTool)
        tool.name = "my_tool"
        tools = {"my_tool": tool}
        mw = SkillsMiddleware(skills_path, dynamic_tools=tools)
        assert mw.dynamic_tools is tools


class TestUpdateSystemMessage:
    def test_appends_to_existing_system_message(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        existing_block = {"type": "text", "text": "You are helpful."}
        sys_msg = MagicMock()
        sys_msg.content_blocks = [existing_block]
        request = make_model_request(system_message=sys_msg)

        result = mw._update_system_message(request)

        assert isinstance(result, SystemMessage)
        assert len(result.content) == 2
        assert result.content[0] == existing_block
        assert result.content[1]["text"] == mw.system_prompt

    def test_preserves_multiple_existing_blocks(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        blocks = [
            {"type": "text", "text": "Block one"},
            {"type": "text", "text": "Block two"},
        ]
        sys_msg = MagicMock()
        sys_msg.content_blocks = blocks
        request = make_model_request(system_message=sys_msg)

        result = mw._update_system_message(request)

        assert len(result.content) == 3
        assert result.content[0] == blocks[0]
        assert result.content[1] == blocks[1]

    def test_creates_system_message_when_none(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        request = make_model_request(system_message=None)

        result = mw._update_system_message(request)

        assert isinstance(result, SystemMessage)
        assert len(result.content) == 1
        assert result.content[0]["text"] == mw.system_prompt


class TestGetActivatedSkills:
    def test_no_messages_returns_empty(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        request = make_model_request(messages=[])

        result = mw._get_activated_skills(request)

        assert result == []

    def test_no_tool_calls_returns_empty(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        msg = MagicMock()
        msg.tool_calls = []
        request = make_model_request(messages=[msg])

        result = mw._get_activated_skills(request)

        assert result == []

    def test_non_skill_tool_call_returns_empty(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        msg = MagicMock()
        msg.tool_calls = [{"name": "some_other_tool", "args": {"file_path": "foo.txt"}}]
        request = make_model_request(messages=[msg])

        result = mw._get_activated_skills(request)

        assert result == []

    def test_read_skills_file_non_skill_md_returns_empty(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        msg = MagicMock()
        msg.tool_calls = [{"name": "skills_file_read", "args": {"file_path": "some_other_file.txt"}}]
        request = make_model_request(messages=[msg])

        result = mw._get_activated_skills(request)

        assert result == []

    def test_activated_skill_returned(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        skill_md_path = str(skills_path / "my-skill" / "SKILL.md")
        msg = MagicMock()
        msg.tool_calls = [{"name": "skills_file_read", "args": {"file_path": skill_md_path}}]
        request = make_model_request(messages=[msg])

        result = mw._get_activated_skills(request)

        assert len(result) == 1
        assert isinstance(result[0], Skill)
        assert result[0].name == "my-skill"

    def test_multiple_messages_with_skill_calls(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        skill_md_path = str(skills_path / "my-skill" / "SKILL.md")
        msg1 = MagicMock()
        msg1.tool_calls = [{"name": "skills_file_read", "args": {"file_path": skill_md_path}}]
        msg2 = MagicMock()
        msg2.tool_calls = [{"name": "some_other_tool", "args": {"file_path": "foo.txt"}}]
        request = make_model_request(messages=[msg1, msg2])

        result = mw._get_activated_skills(request)

        assert len(result) == 1

    def test_message_without_tool_calls_attr_skipped(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        msg = MagicMock(spec=[])  # no attributes at all
        request = make_model_request(messages=[msg])

        result = mw._get_activated_skills(request)

        assert result == []

    def test_message_with_tool_calls_none_skipped(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        msg = MagicMock()
        msg.tool_calls = None
        request = make_model_request(messages=[msg])

        result = mw._get_activated_skills(request)

        assert result == []

    def test_duplicate_skill_activation_returns_one(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        skill_md_path = str(skills_path / "my-skill" / "SKILL.md")
        msg1 = MagicMock()
        msg1.tool_calls = [{"name": "skills_file_read", "args": {"file_path": skill_md_path}}]
        msg2 = MagicMock()
        msg2.tool_calls = [{"name": "skills_file_read", "args": {"file_path": skill_md_path}}]
        request = make_model_request(messages=[msg1, msg2])

        result = mw._get_activated_skills(request)

        assert len(result) == 1
        assert result[0].name == "my-skill"

    def test_hallucinated_skill_path_skipped(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path)
        msg = MagicMock()
        msg.tool_calls = [{"name": "skills_file_read", "args": {"file_path": "nonexistent-skill/SKILL.md"}}]
        request = make_model_request(messages=[msg])
        result = mw._get_activated_skills(request)
        assert result == []


class TestUpdateTools:
    def test_empty_tool_map_returns_tools_without_checking_activated_skills(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        existing_tools = [MagicMock(spec=BaseTool)]
        request = make_model_request(messages=[], tools=existing_tools)

        with patch.object(mw, "_get_activated_skills") as mock_get:
            result = mw._update_tools(request)

        mock_get.assert_not_called()
        assert result is existing_tools

    def test_no_activated_skills_returns_original_tools(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        existing_tools = [MagicMock(spec=BaseTool)]
        request = make_model_request(messages=[], tools=existing_tools)

        result = mw._update_tools(request)

        assert result == existing_tools

    def test_activated_skill_adds_dynamic_tools(self, skills_path, make_model_request):
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool_impl"
        skill_md_path = str(skills_path / "my-skill" / "SKILL.md")
        msg = MagicMock()
        msg.tool_calls = [{"name": "skills_file_read", "args": {"file_path": skill_md_path}}]

        existing_tool = MagicMock(spec=BaseTool)
        existing_tool.name = "existing"
        existing_tools = [existing_tool]

        mock_skill = MagicMock(spec=Skill)
        mock_skill.allowed_tools = ["my_tool"]

        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool})
        request = make_model_request(messages=[msg], tools=existing_tools)

        with patch.object(mw, "_get_activated_skills", return_value=[mock_skill]):
            result = mw._update_tools(request)

        assert len(result) == 2
        assert result[0] is existing_tools[0]
        assert result[1] is dynamic_tool

    def test_multiple_allowed_tools_from_skill(self, skills_path, make_model_request):
        tool_a = MagicMock(spec=BaseTool)
        tool_a.name = "my_tool_a"
        tool_b = MagicMock(spec=BaseTool)
        tool_b.name = "other_tool_b"
        dynamic_tools = {"my_tool": tool_a, "other_tool": tool_b}

        mock_skill = MagicMock(spec=Skill)
        mock_skill.allowed_tools = ["my_tool", "other_tool"]

        mw = SkillsMiddleware(skills_path, dynamic_tools=dynamic_tools)
        request = make_model_request(messages=[], tools=[])

        with patch.object(mw, "_get_activated_skills", return_value=[mock_skill]):
            result = mw._update_tools(request)

        assert len(result) == 2
        assert tool_a in result
        assert tool_b in result

    def test_multiple_activated_skills(self, skills_path, make_model_request):
        tool_a = MagicMock(spec=BaseTool)
        tool_a.name = "my_tool_a"
        tool_b = MagicMock(spec=BaseTool)
        tool_b.name = "other_tool_b"
        dynamic_tools = {"my_tool": tool_a, "other_tool": tool_b}

        skill1 = MagicMock(spec=Skill)
        skill1.allowed_tools = ["my_tool"]
        skill2 = MagicMock(spec=Skill)
        skill2.allowed_tools = ["other_tool"]

        mw = SkillsMiddleware(skills_path, dynamic_tools=dynamic_tools)
        request = make_model_request(messages=[], tools=[])

        with patch.object(mw, "_get_activated_skills", return_value=[skill1, skill2]):
            result = mw._update_tools(request)

        assert len(result) == 2
        assert tool_a in result
        assert tool_b in result

    def test_list_valued_dynamic_tool(self, skills_path, make_model_request):
        tool_a = MagicMock(spec=BaseTool)
        tool_a.name = "my_tool_a"
        tool_b = MagicMock(spec=BaseTool)
        tool_b.name = "my_tool_b"
        dynamic_tools = {"my_tool": [tool_a, tool_b]}

        mock_skill = MagicMock(spec=Skill)
        mock_skill.allowed_tools = ["my_tool"]

        mw = SkillsMiddleware(skills_path, dynamic_tools=dynamic_tools)
        request = make_model_request(messages=[], tools=[])

        with patch.object(mw, "_get_activated_skills", return_value=[mock_skill]):
            result = mw._update_tools(request)

        assert len(result) == 2
        assert tool_a in result
        assert tool_b in result

    def test_warns_on_undefined_dynamic_tool(self, skills_path, make_model_request):
        # Need a non-empty tool_map so _update_tools doesn't return early
        registered_tool = MagicMock(spec=BaseTool)
        registered_tool.name = "my_tool_impl"

        mock_skill = MagicMock(spec=Skill)
        mock_skill.allowed_tools = ["my_tool", "nonexistent_tool"]

        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": registered_tool})
        request = make_model_request(messages=[], tools=[])

        with patch.object(mw, "_get_activated_skills", return_value=[mock_skill]):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = mw._update_tools(request)

        assert len(w) == 1
        assert "nonexistent_tool" in str(w[0].message)
        assert len(result) == 1

    def test_deduplicates_tools_across_skills(self, skills_path, make_model_request):
        shared_tool = MagicMock(spec=BaseTool)
        shared_tool.name = "my_tool_impl"
        dynamic_tools = {"my_tool": shared_tool}

        skill1 = MagicMock(spec=Skill)
        skill1.allowed_tools = ["my_tool"]
        skill2 = MagicMock(spec=Skill)
        skill2.allowed_tools = ["my_tool"]

        mw = SkillsMiddleware(skills_path, dynamic_tools=dynamic_tools)
        request = make_model_request(messages=[], tools=[])

        with patch.object(mw, "_get_activated_skills", return_value=[skill1, skill2]):
            result = mw._update_tools(request)

        assert result.count(shared_tool) == 1

    def test_activated_skill_with_empty_allowed_tools(self, skills_path, make_model_request):
        mock_skill = MagicMock(spec=Skill)
        mock_skill.allowed_tools = []

        existing_tools = [MagicMock(spec=BaseTool)]
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        request = make_model_request(messages=[], tools=existing_tools)

        with patch.object(mw, "_get_activated_skills", return_value=[mock_skill]):
            result = mw._update_tools(request)

        assert result == existing_tools

    def test_integration_activated_tool_skill(self, skills_path, make_model_request):
        """Integration test using the tool-skill fixture which has allowed-tools in frontmatter."""
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool_impl"
        other_tool = MagicMock(spec=BaseTool)
        other_tool.name = "other_tool_impl"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool, "other_tool": other_tool})

        skill_md_path = str(skills_path / "tool-skill" / "SKILL.md")
        msg = MagicMock()
        msg.tool_calls = [{"name": "skills_file_read", "args": {"file_path": skill_md_path}}]
        request = make_model_request(messages=[msg], tools=[])

        result = mw._update_tools(request)

        tool_names = [t.name for t in result]
        assert dynamic_tool.name in tool_names


class TestWrapModelCall:
    def test_appends_system_prompt_to_system_message(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        original_content = [{"type": "text", "text": "You are a helpful assistant."}]
        sys_msg = MagicMock()
        sys_msg.content_blocks = original_content
        mock_request = make_model_request(system_message=sys_msg)

        mw.wrap_model_call(mock_request, MagicMock())

        mock_request.override.assert_called_once()
        new_system_message = mock_request.override.call_args.kwargs["system_message"]

        assert isinstance(new_system_message, SystemMessage)
        assert len(new_system_message.content) == 2
        assert new_system_message.content[0] == original_content[0]
        assert mw.system_prompt in new_system_message.content[1]["text"]

    def test_calls_handler_with_overridden_request(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "Original"}]
        mock_request = make_model_request(system_message=sys_msg)

        overridden_request = MagicMock()
        mock_request.override.return_value = overridden_request

        mock_handler = MagicMock()
        mock_response = MagicMock()
        mock_handler.return_value = mock_response

        result = mw.wrap_model_call(mock_request, mock_handler)

        mock_handler.assert_called_once_with(overridden_request)
        assert result == mock_response

    def test_preserves_existing_content_blocks(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        original_blocks = [
            {"type": "text", "text": "Block one"},
            {"type": "text", "text": "Block two"},
        ]
        sys_msg = MagicMock()
        sys_msg.content_blocks = original_blocks
        mock_request = make_model_request(system_message=sys_msg)

        mw.wrap_model_call(mock_request, MagicMock())

        new_system_message = mock_request.override.call_args.kwargs["system_message"]
        assert len(new_system_message.content) == 3
        assert new_system_message.content[0] == original_blocks[0]
        assert new_system_message.content[1] == original_blocks[1]

    def test_creates_system_message_when_none(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        mock_request = make_model_request(system_message=None)

        mock_handler = MagicMock()
        mock_handler.return_value = MagicMock()

        mw.wrap_model_call(mock_request, mock_handler)

        mock_request.override.assert_called_once()
        new_system_message = mock_request.override.call_args.kwargs["system_message"]

        assert isinstance(new_system_message, SystemMessage)
        assert len(new_system_message.content) == 1
        assert new_system_message.content[0]["text"] == mw.system_prompt

    def test_handler_called_when_system_message_is_none(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        mock_request = make_model_request(system_message=None)

        overridden = MagicMock()
        mock_request.override.return_value = overridden

        mock_handler = MagicMock()
        mock_response = MagicMock()
        mock_handler.return_value = mock_response

        result = mw.wrap_model_call(mock_request, mock_handler)

        mock_handler.assert_called_once_with(overridden)
        assert result == mock_response

    def test_override_receives_tools(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        existing_tools = [MagicMock(spec=BaseTool)]
        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "Hello"}]
        mock_request = make_model_request(system_message=sys_msg, tools=existing_tools)

        mw.wrap_model_call(mock_request, MagicMock())

        call_kwargs = mock_request.override.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == existing_tools

    def test_override_receives_both_system_message_and_tools(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "Hi"}]
        mock_request = make_model_request(system_message=sys_msg)

        mw.wrap_model_call(mock_request, MagicMock())

        call_kwargs = mock_request.override.call_args.kwargs
        assert "system_message" in call_kwargs
        assert "tools" in call_kwargs

    def test_handler_receives_overridden_request_not_original(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "Original"}]
        mock_request = make_model_request(system_message=sys_msg)

        overridden_request = MagicMock(name="overridden")
        mock_request.override.return_value = overridden_request

        mock_handler = MagicMock()
        mw.wrap_model_call(mock_request, mock_handler)

        mock_handler.assert_called_once_with(overridden_request)
        assert mock_handler.call_args[0][0] is not mock_request


class TestWrapToolCall:
    def test_dynamic_tool_overrides_request(self, skills_path, make_tool_call_request):
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool})

        request = make_tool_call_request(tool_call={"name": "my_tool", "args": {}})
        overridden = MagicMock()
        request.override.return_value = overridden

        mock_handler = MagicMock()
        mock_response = MagicMock()
        mock_handler.return_value = mock_response

        result = mw.wrap_tool_call(request, mock_handler)

        request.override.assert_called_once_with(tool=dynamic_tool)
        mock_handler.assert_called_once_with(overridden)
        assert result == mock_response

    def test_non_dynamic_tool_passes_through(self, skills_path, make_tool_call_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})

        request = make_tool_call_request(tool_call={"name": "some_other_tool", "args": {}})

        mock_handler = MagicMock()
        mock_response = MagicMock()
        mock_handler.return_value = mock_response

        result = mw.wrap_tool_call(request, mock_handler)

        request.override.assert_not_called()
        mock_handler.assert_called_once_with(request)
        assert result == mock_response

    def test_list_dynamic_tool_resolves_by_name(self, skills_path, make_tool_call_request):
        tool_a = MagicMock(spec=BaseTool)
        tool_a.name = "tool_a"
        tool_b = MagicMock(spec=BaseTool)
        tool_b.name = "tool_b"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": [tool_a, tool_b]})

        request = make_tool_call_request(tool_call={"name": "tool_b", "args": {}})
        overridden = MagicMock()
        request.override.return_value = overridden

        mock_handler = MagicMock()
        mw.wrap_tool_call(request, mock_handler)

        request.override.assert_called_once_with(tool=tool_b)
        mock_handler.assert_called_once_with(overridden)


class TestAsyncWrapModelCall:
    @pytest.mark.asyncio
    async def test_appends_system_prompt(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        original_content = [{"type": "text", "text": "You are helpful."}]
        sys_msg = MagicMock()
        sys_msg.content_blocks = original_content
        mock_request = make_model_request(system_message=sys_msg)

        mock_handler = AsyncMock()

        await mw.awrap_model_call(mock_request, mock_handler)

        new_system_message = mock_request.override.call_args.kwargs["system_message"]
        assert isinstance(new_system_message, SystemMessage)
        assert len(new_system_message.content) == 2
        assert new_system_message.content[0] == original_content[0]

    @pytest.mark.asyncio
    async def test_calls_handler_with_overridden_request(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "Original"}]
        mock_request = make_model_request(system_message=sys_msg)

        overridden = MagicMock()
        mock_request.override.return_value = overridden

        mock_handler = AsyncMock()
        mock_response = MagicMock()
        mock_handler.return_value = mock_response

        result = await mw.awrap_model_call(mock_request, mock_handler)

        mock_handler.assert_awaited_once_with(overridden)
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_creates_system_message_when_none(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        mock_request = make_model_request(system_message=None)

        mock_handler = AsyncMock()
        mock_handler.return_value = MagicMock()

        await mw.awrap_model_call(mock_request, mock_handler)

        new_system_message = mock_request.override.call_args.kwargs["system_message"]
        assert isinstance(new_system_message, SystemMessage)
        assert len(new_system_message.content) == 1
        assert new_system_message.content[0]["text"] == mw.system_prompt

    @pytest.mark.asyncio
    async def test_override_receives_tools(self, skills_path, make_model_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})
        existing_tools = [MagicMock(spec=BaseTool)]
        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "Hello"}]
        mock_request = make_model_request(system_message=sys_msg, tools=existing_tools)

        await mw.awrap_model_call(mock_request, AsyncMock())

        call_kwargs = mock_request.override.call_args.kwargs
        assert "tools" in call_kwargs
        assert call_kwargs["tools"] == existing_tools


class TestAsyncWrapToolCall:
    @pytest.mark.asyncio
    async def test_dynamic_tool_overrides_request(self, skills_path, make_tool_call_request):
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool})

        request = make_tool_call_request(tool_call={"name": "my_tool", "args": {}})
        overridden = MagicMock()
        request.override.return_value = overridden

        mock_handler = AsyncMock()
        mock_response = MagicMock()
        mock_handler.return_value = mock_response

        result = await mw.awrap_tool_call(request, mock_handler)

        request.override.assert_called_once_with(tool=dynamic_tool)
        mock_handler.assert_awaited_once_with(overridden)
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_non_dynamic_tool_passes_through(self, skills_path, make_tool_call_request):
        mw = SkillsMiddleware(skills_path, dynamic_tools={})

        request = make_tool_call_request(tool_call={"name": "some_other_tool", "args": {}})

        mock_handler = AsyncMock()
        mock_response = MagicMock()
        mock_handler.return_value = mock_response

        result = await mw.awrap_tool_call(request, mock_handler)

        request.override.assert_not_called()
        mock_handler.assert_awaited_once_with(request)
        assert result == mock_response

    @pytest.mark.asyncio
    async def test_list_dynamic_tool_resolves_by_name(self, skills_path, make_tool_call_request):
        tool_a = MagicMock(spec=BaseTool)
        tool_a.name = "tool_a"
        tool_b = MagicMock(spec=BaseTool)
        tool_b.name = "tool_b"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": [tool_a, tool_b]})

        request = make_tool_call_request(tool_call={"name": "tool_b", "args": {}})
        overridden = MagicMock()
        request.override.return_value = overridden

        mock_handler = AsyncMock()
        await mw.awrap_tool_call(request, mock_handler)

        request.override.assert_called_once_with(tool=tool_b)
        mock_handler.assert_awaited_once_with(overridden)


class TestEndToEnd:
    """End-to-end tests exercising the full middleware flow without mocking internals."""

    def test_full_flow_no_skill_activated(self, skills_path, make_model_request):
        """First model call with no prior skill activation: system prompt injected, no dynamic tools added."""
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool_impl"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool})

        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "You are helpful."}]
        request = make_model_request(system_message=sys_msg, messages=[], tools=[])

        model_response = MagicMock()
        handler = MagicMock(return_value=model_response)

        result = mw.wrap_model_call(request, handler)

        # Handler was called
        assert result == model_response
        call_kwargs = request.override.call_args.kwargs

        # System prompt was appended
        new_sys = call_kwargs["system_message"]
        assert isinstance(new_sys, SystemMessage)
        assert "skills_file_read" in new_sys.content[-1]["text"]

        # No dynamic tools added (skill not activated yet)
        tool_names = [t.name for t in call_kwargs["tools"] if hasattr(t, "name")]
        assert "my_tool_impl" not in tool_names

    def test_full_flow_skill_activated_adds_tools(self, skills_path, make_model_request):
        """After reading a skill's SKILL.md, its dynamic tools appear in the next model call."""
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool_impl"
        other_tool = MagicMock(spec=BaseTool)
        other_tool.name = "other_tool_impl"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool, "other_tool": other_tool})

        # Simulate a previous message where the model read tool-skill's SKILL.md
        skill_md_path = str(skills_path / "tool-skill" / "SKILL.md")
        prior_msg = MagicMock()
        prior_msg.tool_calls = [{"name": "skills_file_read", "args": {"file_path": skill_md_path}}]

        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "You are helpful."}]
        existing_agent_tool = MagicMock(spec=BaseTool)
        existing_agent_tool.name = "existing_tool"
        request = make_model_request(system_message=sys_msg, messages=[prior_msg], tools=[existing_agent_tool])

        handler = MagicMock(return_value=MagicMock())
        mw.wrap_model_call(request, handler)

        call_kwargs = request.override.call_args.kwargs
        tool_names = [t.name for t in call_kwargs["tools"] if hasattr(t, "name")]

        # Both dynamic tools from tool-skill's allowed-tools should be present
        assert "my_tool_impl" in tool_names
        assert "other_tool_impl" in tool_names
        # Original tool is preserved
        assert "existing_tool" in tool_names

    def test_full_flow_wrap_tool_call_resolves_dynamic_tool(self, skills_path, make_tool_call_request):
        """wrap_tool_call correctly resolves a dynamic tool and passes it to the handler."""
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool_impl"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool})

        request = make_tool_call_request(tool_call={"name": "my_tool_impl", "args": {"input": "hello"}})
        overridden = MagicMock()
        request.override.return_value = overridden

        tool_response = MagicMock()
        handler = MagicMock(return_value=tool_response)

        result = mw.wrap_tool_call(request, handler)

        # Tool was resolved and overridden
        request.override.assert_called_once_with(tool=dynamic_tool)
        handler.assert_called_once_with(overridden)
        assert result == tool_response

    def test_full_flow_model_and_tool_call_combined(self, skills_path, make_model_request, make_tool_call_request):
        """Full round-trip: model call activates skill, then tool call resolves the dynamic tool."""
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool_impl"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool})

        # Step 1: wrap_model_call with activated skill
        skill_md_path = str(skills_path / "tool-skill" / "SKILL.md")
        prior_msg = MagicMock()
        prior_msg.tool_calls = [{"name": "skills_file_read", "args": {"file_path": skill_md_path}}]
        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "Base prompt"}]
        model_request = make_model_request(system_message=sys_msg, messages=[prior_msg], tools=[])

        model_handler = MagicMock(return_value=MagicMock())
        mw.wrap_model_call(model_request, model_handler)

        # Verify dynamic tool was injected
        model_tools = model_request.override.call_args.kwargs["tools"]
        assert dynamic_tool in model_tools

        # Step 2: wrap_tool_call for that dynamic tool
        tool_request = make_tool_call_request(tool_call={"name": "my_tool_impl", "args": {"query": "test"}})
        overridden = MagicMock()
        tool_request.override.return_value = overridden

        tool_response = MagicMock()
        tool_handler = MagicMock(return_value=tool_response)

        result = mw.wrap_tool_call(tool_request, tool_handler)

        tool_request.override.assert_called_once_with(tool=dynamic_tool)
        tool_handler.assert_called_once_with(overridden)
        assert result == tool_response

    def test_full_flow_non_skill_read_does_not_activate(self, skills_path, make_model_request):
        """Reading a non-SKILL.md file via skills_file_read does not activate any skill."""
        dynamic_tool = MagicMock(spec=BaseTool)
        dynamic_tool.name = "my_tool_impl"
        mw = SkillsMiddleware(skills_path, dynamic_tools={"my_tool": dynamic_tool})

        prior_msg = MagicMock()
        prior_msg.tool_calls = [{"name": "skills_file_read", "args": {"file_path": "my-skill/references/reference.md"}}]
        sys_msg = MagicMock()
        sys_msg.content_blocks = [{"type": "text", "text": "Prompt"}]
        request = make_model_request(system_message=sys_msg, messages=[prior_msg], tools=[])

        mw.wrap_model_call(request, MagicMock(return_value=MagicMock()))

        tool_names = [t.name for t in request.override.call_args.kwargs["tools"] if hasattr(t, "name")]
        assert "my_tool_impl" not in tool_names
