import warnings
from os import PathLike
from pathlib import Path
from typing import Any, Callable, Union

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse, ToolCallRequest
from langchain_community.tools.file_management.read import ReadFileTool
from langchain_core.messages import SystemMessage
from langchain_core.tools import BaseTool

from langchain_skills_adapters.core import Skill, SkillsLoader


class SkillsMiddleware(AgentMiddleware):
    """Middleware for importing skills into your agent."""

    def __init__(self, skills_path: PathLike, *, dynamic_tools: dict[str, Union[BaseTool, list[BaseTool]]] = None):
        """
        Create a new instance of SkillsMiddleware.

        This middleware appends skills information to your agent's system prompt.
        If there is no system prompt, one will be created.
        It also adds a skills_file_read tool to your agent's tool list.
        This tool allows your agent to read files from the specified skills path.
        If your agent needs to execute scripts from your skill, it's recommended
        that you add a script execution tool to your agent.

        Args:
            skills_path (PathLike):
                Path to the directory containing skills.
            dynamic_tools (dict[str, Union[BaseTool, list[BaseTool]]], optional):
                A dictionary mapping names to tools that can be dynamically
                added to the agent as skills are activated.
                Supports mapping names to single tools or lists of tools.
                When a skill is activated, the tools that are mapped by the names
                listed in the `allowed-tools` field of the skill are added to the
                agent's tools.
                Default is None.

        """
        # Create system prompt
        self.skills_path = Path(skills_path).resolve()
        self.skills_loader = SkillsLoader(skills_path=self.skills_path)
        skill_catalog = self.skills_loader.get_catalog()
        self.system_prompt = (
            "The following skills provide specialized instructions for specific tasks. "
            "When a task matches a skill's description, use your skills_file_read tool to load "
            "the SKILL.md at the listed location before proceeding. "
            "When a skill references relative paths, resolve them against the skill's "
            "directory (the parent of SKILL.md) and use absolute paths in tool calls.\n"
            f"{skill_catalog}"
        )

        # Add skills_file_read tool to agent's tool list
        self.read_file_tool = ReadFileTool(name="skills_file_read", root_dir=str(self.skills_path))
        self.tools = [self.read_file_tool]

        # Register the dynamic tools
        self.dynamic_tools = dynamic_tools or {}
        self.tool_map: dict[str, list[BaseTool]] = {
            key: value if isinstance(value, list) else [value] for key, value in self.dynamic_tools.items()
        }
        all_dynamic_tools = [tool for _, tools in self.tool_map.items() for tool in tools]
        self.name2tool: dict[str, BaseTool] = {tool.name: tool for tool in all_dynamic_tools}

    def _update_system_message(self, request: ModelRequest) -> SystemMessage:
        """Update the system message."""
        if request.system_message is not None:
            new_content = list(request.system_message.content_blocks) + [{"type": "text", "text": self.system_prompt}]
        else:
            new_content = [{"type": "text", "text": self.system_prompt}]
        new_system_message = SystemMessage(content=new_content)
        return new_system_message

    def _get_activated_skills(self, request: ModelRequest) -> list[Skill]:
        """Get a list of activated skills."""
        # Check previous messages for skill activation
        tool_calls = [tc for m in request.messages if (hasattr(m, "tool_calls") and m.tool_calls) for tc in m.tool_calls]
        skills_file_read_calls = [tc for tc in tool_calls if tc.get("name", "") == "skills_file_read"]
        activated_skill_paths = [
            Path(tc["args"]["file_path"].strip()) for tc in skills_file_read_calls if Path(tc["args"]["file_path"]).name == "SKILL.md"
        ]
        # Load the activated skills
        activated_skills = []
        seen = set()
        for path in activated_skill_paths:
            try:
                skill = self.skills_loader.get_skill(path.parent.name)
            except ValueError:
                # Skip hallucinated skills
                continue
            if skill.name not in seen:
                activated_skills.append(skill)
                seen.add(skill.name)
        return activated_skills

    def _update_tools(self, request: ModelRequest) -> list[BaseTool | dict[str, Any]]:
        """Update the tools."""
        # Get existing tools
        tools = request.tools

        # Skip if tool_map is empty
        if not self.tool_map:
            return tools

        # Get activated skills
        activated_skills = self._get_activated_skills(request=request)

        # Get activated tool names
        activated_tool_names = {tool for skill in activated_skills for tool in skill.allowed_tools}

        # Get dynamically activated tools
        activated_tools = []
        for tool in sorted(activated_tool_names):
            if tool not in self.tool_map:
                warnings.warn(f"Tool '{tool}' is not defined in the dynamic_tools. No tool will be added")
                continue
            dynamic_tools = self.tool_map[tool]
            activated_tools.extend(dynamic_tools)

        # Combine existing tools and activated tools and keep only the first tool with a given name
        new_tools = []
        seen = set()
        for tool in tools + activated_tools:
            if isinstance(tool, dict):
                new_tools.append(tool)
            elif tool.name not in seen:
                new_tools.append(tool)
                seen.add(tool.name)

        # Return tools from activated skills
        return new_tools

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse[Any]:
        """
        Update system messages and tools before model call.

        Args:
            request (ModelRequest): Request object containing the model call.
            handler (Callable[[ModelRequest], ModelResponse]): Handler function to process the model call.

        Returns:
            ModelResponse: Response from the handler.

        """
        # Update the system message
        new_system_message = self._update_system_message(request=request)

        # Update tools
        new_tools = self._update_tools(request=request)

        return handler(request.override(system_message=new_system_message, tools=new_tools))

    async def awrap_model_call(self, request, handler):
        """
        Asynchronously update system messages and tools before model call.

        Args:
            request (ModelRequest): Request object containing the model call.
            handler (Callable[[ModelRequest], ModelResponse]): Handler function to process the model call.

        Returns:
            ModelResponse: Response from the handler.

        """
        # Update the system message
        new_system_message = self._update_system_message(request=request)

        # Update tools
        new_tools = self._update_tools(request=request)

        return await handler(request.override(system_message=new_system_message, tools=new_tools))

    def wrap_tool_call(self, request: ToolCallRequest, handler: Callable[[ModelRequest], ModelResponse]) -> ModelResponse[Any]:
        """
        Handle tool calls for dynamic tools.

        Args:
            request (ToolCallRequest): Request object containing the tool call.
            handler (Callable[[ModelRequest], ModelResponse]): Handler function to process the model call.

        Returns:
            ModelResponse: Response from the handler.

        """
        if request.tool_call["name"] in self.name2tool:
            new_tool = self.name2tool[request.tool_call["name"]]
            return handler(request.override(tool=new_tool))
        return handler(request)

    async def awrap_tool_call(self, request, handler) -> ModelResponse[Any]:
        """
        Asynchronously handle tool calls for dynamic tools.

        Args:
            request (ToolCallRequest): Request object containing the tool call.
            handler (Callable[[ModelRequest], ModelResponse]): Handler function to process the model call.

        Returns:
            ModelResponse: Response from the handler.

        """
        if request.tool_call["name"] in self.name2tool:
            new_tool = self.name2tool[request.tool_call["name"]]
            return await handler(request.override(tool=new_tool))
        return await handler(request)


__all__ = [
    "SkillsMiddleware",
]
