from os import PathLike
from pathlib import Path

import frontmatter

from langchain_skills_adapters.core.base import Skill, SkillCatalog

RESOURCE_DIRS = ["references", "scripts", "assets"]


class SkillsLoader:
    """Load skills from a directory."""

    def __init__(self, skills_path: PathLike):
        """Initialize SkillsLoader."""
        # Save vars
        self.skills_path = skills_path

        # Initialize the skill catalog and map
        self.skill_catalog: SkillCatalog = None
        self.skill_map: dict[str, Skill] = {}

        # Load the skills
        self._load()

    def _load(self):
        """Load skills from the skills_path."""
        # Load skills from the directory
        skills = []
        for path in Path(self.skills_path).glob("**/SKILL.md"):
            # Gather skill info
            meta = frontmatter.load(path)
            content = path.read_text()
            content = content[content.find("---", 4) :].strip()
            resources = []
            for dirname in RESOURCE_DIRS:
                resources.extend(list(path.parent.glob(f"{dirname}/**/*")))

            # Create Skill obj
            try:
                skill = Skill(location=path, content=content, resources=resources, **meta)
            except Exception as e:
                raise ValueError(f"Failed to load skill {path}: {e}")
            skills.append(skill)

        # Save discovered skills
        self.skill_catalog = SkillCatalog(skills=skills)
        self.skill_map = {skill.name: skill for skill in skills}

    def get_catalog(self):
        """Get the skill catalog."""
        return self.skill_catalog.to_str()

    def get_skill(self, name: str) -> Skill:
        """Get a skill by name."""
        try:
            return self.skill_map[name]
        except KeyError:
            raise ValueError(f"Skill {name} not found.")


__all__ = ["SkillsLoader"]
