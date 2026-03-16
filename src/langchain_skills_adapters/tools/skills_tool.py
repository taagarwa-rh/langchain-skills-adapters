from os import PathLike
from pathlib import Path
from typing import Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field

from langchain_skills_adapters.core import SkillsLoader


class SkillsToolArgsSchema(BaseModel):
    """Args schema for skills tool."""

    skill_name: str = Field(description="Name of the skill to activate.")


class SkillsTool(BaseTool):
    """Tool for agents to enable skill usage."""

    skills_path: Path
    skills_loader: SkillsLoader

    def __init__(self, skills_path: PathLike):
        """
        Create a new instance of the SkillsTool.

        This tool enables the agent to activate skills.
        It loads all skills from the skills_path and adds the skill names and descriptions to its tool description.
        The tool takes one argument, `skill_name`, which loads the skill content for the named skill.
        If your skills directory contains resource files (such as scripts, assets, etc.), it's recommended that you
        add another tool (such as a `ReadFileTool`) to enable your agent to read these files.
        If your agent needs to execute scripts from your skill, it's recommended that you add a script execution tool to your agent.

        Args:
            skills_path (PathLike): Path to the directory containing skills.

        """
        # Initialize skill loader
        skills_loader = SkillsLoader(skills_path=skills_path)

        # Generate tool name, description, and args schema
        name = "activate_skill"
        skill_catalog = skills_loader.get_catalog()
        description = (
            "The following skills provide specialized instructions for specific tasks. "
            f"When a task matches a skill's description, call the {name} tool "
            "with the skill's name to load its full instructions.\n"
            f"{skill_catalog}"
        )
        args_schema = SkillsToolArgsSchema

        # Initialize super
        super().__init__(
            name=name,
            description=description,
            args_schema=args_schema,
            skills_path=skills_path,
            skills_loader=skills_loader,
        )

    def _run(self, skill_name: str, run_manager: Optional[CallbackManagerForToolRun] = None) -> str:
        """
        Run the tool.

        Args:
            skill_name (str): Name of the skill to activate.
            run_manager (CallbackManagerForToolRun, optional): Callback manager for the tool run.

        Returns:
            str: Content of the skill in XML format if found, otherwise an error message.

        """
        try:
            skill = self.skills_loader.get_skill(name=skill_name)
            return skill.to_content()
        except ValueError:
            return f"Error: Skill '{skill_name}' does not exist."
        except Exception as e:
            return f"Error: {e}"


__all__ = ["SkillsTool"]
