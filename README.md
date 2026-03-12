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

The `SkillsTool` creates a Langchain tool that can be used by your agent to activate a skill.
The description of the skills tool contains names and descriptions of all available skills from your skill directory.
This way, your agent will always see what skills are available to it before acting, and can use the tool to activate a skill and read its full content.

If your skills directory contains resource files (such as scripts, assets, etc.), you can add a `ReadFileTool` to enable your agent to read these files.

```py
from langchain.agents import create_agent
from langchain_community.tools.file_management.read import ReadFileTool

from langchain_skills_adapters import SkillsTool

# Create the SkillsTool pointed to your skills directory
skills_dir = "/path/to/skills/"
skills_tool = SkillsTool(skills_dir)

# Optional: Add a file reading tool. Recommended if your agent needs to read resources from your skills directory (scripts, assets, etc.)
read_file_tool = ReadFileTool(root_dir=skills_dir)

# Create the agent
tools = [skills_tool, read_file_tool]
agent = create_agent("openai:gpt-5", tools=tools)
response = agent.invoke(input={"messages": {"role": "user", "content": "What skills do you have?"}})
```

### As Middleware

The `SkillsMiddleware` is a Langchain middleware that adds skill info to your agent's system prompt before each model call.
It also adds a `skills_file_read` tool to your agent's tool list, allowing it to read skill files and other resources from your skills directory.
This way, your agent will always see what skills are available to it before acting, and can use the tool to read skill files and other resource files.

```py
from langchain.agents import create_agent

from langchain_skills_adapters import SkillsMiddleware

# Create the SkillsTool pointed to your skills directory
skills_dir = "/path/to/skills/"
skills_middleware = SkillsMiddleware(skills_dir)

# Create the agent
agent = create_agent("openai:gpt-5", middleware=[skills_middleware])
response = agent.invoke(input={"messages": {"role": "user", "content": "What skills do you have?"}})
```
