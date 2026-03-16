from os import PathLike
from pathlib import Path
from typing import Callable

from langchain.agents.middleware import AgentMiddleware, ModelRequest, ModelResponse
from langchain_community.tools.file_management.read import ReadFileTool
from langchain_core.messages import SystemMessage

from langchain_skills_adapters.core import SkillsLoader


class SkillsMiddleware(AgentMiddleware):
    """Middleware for importing skills into your agent."""

    def __init__(self, skills_path: PathLike):
        """
        Create a new instance of SkillsMiddleware.

        This middleware appends skills information to your agent's system prompt.
        If there is no system prompt, one will be created.
        It also adds a skills_file_read tool to your agent's tool list.
        This tool allows your agent to read files from the specified skills path.
        If your agent needs to execute scripts from your skill, it's recommended that you add a script execution tool to your agent.

        Args:
            skills_path (PathLike): Path to the directory containing skills.

        """
        # Create system prompt
        self.skills_path = Path(skills_path).resolve()
        self.skills_loader = SkillsLoader(skills_path=skills_path)
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

    def wrap_model_call(self, request: ModelRequest, handler: Callable[[ModelRequest], ModelResponse]):
        """
        Update system messages before model call.

        Args:
            request (ModelRequest): Request object containing the model call.
            handler (Callable[[ModelRequest], ModelResponse]): Handler function to process the model call.

        Returns:
            ModelResponse: Response from the handler.

        """
        if request.system_message is not None:
            new_content = list(request.system_message.content_blocks) + [{"type": "text", "text": self.system_prompt}]
        else:
            new_content = [{"type": "text", "text": self.system_prompt}]
        new_system_message = SystemMessage(content=new_content)
        return handler(request.override(system_message=new_system_message))


__all__ = [
    "SkillsMiddleware",
]
