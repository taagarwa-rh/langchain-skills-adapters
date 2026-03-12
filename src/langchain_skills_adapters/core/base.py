from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel


class Skill(BaseModel):
    """Skill."""

    name: str
    description: str
    location: Path
    content: str
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    allowed_tools: Optional[list[str]] = None
    resources: list[Path] = []

    def to_catalog(self) -> str:
        """Convert to skill catalog XML format."""
        skill = (
            "<skill>\n"
            f"  <name>{self.name}</name>\n"
            f"  <description>{self.description}</description>\n"
            f"  <location>{self.location}</location>\n"
            "</skill>"
        )
        return skill

    def to_content(self) -> str:
        """Convert to content XML format."""
        # Construct the skill content
        skill = (
            f'<skill_content name="{self.name}">\n'
            f"{self.content}\n\n"
            f"Skill directory: {self.location.parent}\n"
            f"Relative paths in this skill are relative to the skill directory.\n"
        )

        # If resources are present, add a resource section
        if len(self.resources):
            skill_resources = "\n".join([f"  <file>{resource.relative_to(self.location.parent)}</file>" for resource in self.resources])
            skill += f"<skill_resources>\n{skill_resources}\n</skill_resources>\n"

        # Close out the skill content
        skill += "</skill_content>"
        return skill


class SkillCatalog(BaseModel):
    """Skill catalog."""

    skills: list[Skill] = []

    def to_str(self) -> str:
        """Convert to string."""
        # If there are no skills, return an empty string
        if len(self.skills) == 0:
            return ""

        # Fetch skills
        skills = [skill.to_catalog() for skill in self.skills]
        skills = "\n".join(skills)

        # Add two spaces to the start of each line
        skills = "\n".join(["  " + line for line in skills.split("\n")])

        catalog = f"<available_skills>\n{skills}\n</available_skills>"
        return catalog


__all__ = [
    "Skill",
    "SkillCatalog",
]
