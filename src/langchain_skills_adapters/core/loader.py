from os import PathLike
from pathlib import Path

from langchain_skills_adapters.core.base import Skill, SkillCatalog


class SkillsLoader:
    """Load skills from a directory."""

    def __init__(self, skills_path: PathLike):
        """
        Initialize SkillsLoader.

        Args:
            skills_path (PathLike): Path to the directory containing skills.

        """
        # Save vars
        self.skills_path: Path = Path(skills_path).resolve()

        # Initialize the skill catalog and map
        self.skill_catalog: SkillCatalog = None
        self.skill_map: dict[str, Skill] = {}

        # Load the skills
        self._load()

    def _load(self):
        """Load skills from the skills_path."""
        # Load skills from the directory
        skills = []
        for path in self.skills_path.glob("**/SKILL.md"):
            # Create Skill obj
            try:
                skill = Skill.from_path(path=path)
            except Exception as e:
                raise ValueError(f"Failed to load skill {path}: {e}")

            # Check if skill with name already exists
            if any(s.name == skill.name for s in skills):
                raise ValueError(f"Duplicate skill name: {skill.name}")
            skills.append(skill)

        # Save discovered skills
        self.skill_catalog = SkillCatalog(skills=skills)
        self.skill_map = {skill.name: skill for skill in skills}

    def get_catalog(self):
        """Get the skill catalog."""
        return self.skill_catalog.to_str()

    def get_skill(self, name: str) -> Skill:
        """
        Get a skill by name.

        Args:
            name (str): Name of the skill to fetch.

        Returns:
            Skill: Skill object if found.

        Raises:
            ValueError: If the skill is not found.

        """
        try:
            return self.skill_map[name]
        except KeyError:
            raise ValueError(f"Skill {name} not found.")

    def get_all_allowed_tools(self) -> set[str]:
        """Load all allowed tools from all skills."""
        allowed_tools = set()
        for skill in self.skill_catalog.skills:
            allowed_tools.update(skill.allowed_tools)
        return allowed_tools


__all__ = ["SkillsLoader"]
