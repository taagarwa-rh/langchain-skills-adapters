from pathlib import Path
from typing import Any, Optional, Self

import frontmatter
from pydantic import BaseModel, ConfigDict, model_validator


class Skill(BaseModel):
    """Skill."""

    name: str
    description: str
    location: Path
    content: str
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None
    allowed_tools: list[str] = []
    resources: list[Path] = []

    @classmethod
    def from_path(cls, path: Path):
        """Create a Skill object from a file path."""
        # Load frontmattter
        metadata = frontmatter.load(path).to_dict()

        # Check for required fields
        required_fields = ["name", "description"]
        for field in required_fields:
            if field not in metadata:
                raise ValueError(f"Missing required field {field} in frontmatter of {path}")

        # Format fields where needed
        if "allowed-tools" in metadata:
            allowed_tools = metadata.pop("allowed-tools")
            metadata["allowed_tools"] = allowed_tools.split(" ")

        # Read skill resources
        resources = [p for p in path.parent.glob("**/*") if p != path and not p.is_dir()]

        # Create the skill
        return Skill(resources=resources, location=path, **metadata)

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

    model_config = ConfigDict(validate_assignment=True)

    skills: list[Skill] = []

    @model_validator(mode="after")
    def validate_no_matching_names(self) -> Self:
        """Check for duplicate skill names."""
        names = [s.name for s in self.skills]
        if any(names.count(name) > 1 for name in names):
            raise ValueError("Duplicate skill names found.")
        return self

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
