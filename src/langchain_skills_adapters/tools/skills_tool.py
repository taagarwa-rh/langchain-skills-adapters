from os import PathLike
from pathlib import Path
from typing import Optional

from langchain_core.callbacks import CallbackManagerForToolRun
from langchain_core.tools import BaseTool
from pydantic import BaseModel

from langchain_skills_adapters.core import SkillsLoader


class SkillsToolArgsSchema(BaseModel):
    """Args schema for skills tool."""

    name: str


class SkillsTool(BaseTool):
    """Tool for agents to enable skill usage."""

    skills_path: Path
    skills_loader: SkillsLoader

    def __init__(self, skills_path: PathLike):
        """
        Create a new instance of the SkillsTool.
        
        Args:
            skills_path: Path to the directory containing skills.

        """
        skills_path = Path(skills_path)

        # Initialize skill loader
        skills_loader = SkillsLoader(skills_path=skills_path)

        # Generate tool name, description, and args schema
        name = "activate_skill"
        skill_catalog = skills_loader.skill_catalog.to_str()
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

    def _run(self, name: str, run_manager: Optional[CallbackManagerForToolRun] = None):
        """Run the tool."""
        try:
            skill = self.skills_loader.get_skill(name=name)
            return skill.to_content()
        except ValueError:
            return f"Error: Skill '{name}' does not exist."
        except Exception as e:
            return f"Error: {e}"


__all__ = ["SkillsTool"]
