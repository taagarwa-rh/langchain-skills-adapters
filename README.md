# Langchain Skills Adapters

Langchain adapters to support skills in your agent.

## Features

- Supports the [Anthropic Open Standard for Skills](https://agentskills.io/home)
- Follows the [principle of progressive disclosure](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#three-types-of-skill-content-three-levels-of-loading) - Only loads skills if they are needed
- Loads skills from anywhere on your system
- Use as a tool or add as middleware to your agents

## Installation

**uv:**

```sh
uv add langchain-skills-adapters
```

**pip:**

```sh
pip install langchain-skills-adapters
```

## Skills Format

Skills must follow the [Anthropic Open Standard for Skills](https://agentskills.io/home).
This includes having frontmatter with at minimum the name and skill description.

```md
---
name: My Skill
description: This is my skill
---

# My Skill

Skill content

```

The skill directory must be in the following format to be loaded correctly:

```
skills
├── my-skill
│   ├── assets          # Required: instructions + metadata
│   ├── references      # Optional: executable code
│   ├── scripts         # Optional: documentation
│   └── SKILL.md        # Optional: templates, resources
└── other skills...
```

## Usage

### As a Tool

```py
from langchain.agents import create_agent
from langchain_community.tools.file_management.read import ReadFileTool

from langchain_skills_adapters import SkillsTool

# Create the SkillsTool pointed to your skills directory
skills_dir = "/path/to/skills/"
skills_tool = SkillsTool(skills_dir)
print(skills_tool.description)

# Optional: Add a file reading tool. Recommended if your agent needs to read resources from your skill directory (scripts, assets, etc.)
read_file_tool = ReadFileTool(root_dir=skills_dir)

# Create the agent
tools = [skills_tool, read_file_tool]
agent = create_agent("openai:gpt-5", tools=tools)
response = agent.invoke(input={"messages": {"role": "user", "content": "What skills do you have?"}})
print(response)
```

### As Middleware

COMING SOON
