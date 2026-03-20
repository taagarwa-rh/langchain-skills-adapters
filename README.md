# Langchain Skills Adapters

[![CI](https://github.com/taagarwa-rh/langchain-skills-adapters/actions/workflows/ci.yml/badge.svg)](https://github.com/taagarwa-rh/langchain-skills-adapters/actions/workflows/ci.yml)
[![coverage](https://taagarwa-rh.github.io/langchain-skills-adapters/badges/coverage.svg)](https://github.com/taagarwa-rh/langchain-skills-adapters/actions)

Langchain adapters to support skills in your agent.

## Features

- Supports the [Anthropic Open Standard for Skills](https://agentskills.io/home)
- Follows the [principle of progressive disclosure](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#three-types-of-skill-content-three-levels-of-loading) 
  - **Dynamic skill activation** - Only loads skills into context if and when they are needed
  - **Dynamic tool registration** - Only loads tools into context if and when they are needed
- Add as middleware or as a tool to your agents

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

The skill directory must be in the following format to be loaded correctly:

```
skills/
├── skill-name/
│   ├── SKILL.md        # Required: instructions + metadata
│   ├── scripts/        # Optional: executable code
│   ├── references/     # Optional: documentation
│   ├── assets/         # Optional: templates, resources
│   └── ...             # Any other additional files or directories        
└── other skills...
```

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

## Usage

### As Middleware

The `SkillsMiddleware` is a Langchain middleware that adds skill info to your agent's system prompt before each model call.
It also adds a `skills_file_read` tool to your agent's tool list, allowing it to read skill files and other resources from your skills directory.
This way, your agent will always see what skills are available to it before acting, and can use the tool to read skill files and other resource files.

```py
from langchain.agents import create_agent

from langchain_skills_adapters import SkillsMiddleware

# Create the SkillsMiddleware pointed to your skills directory
skills_dir = "/path/to/skills/"
skills_middleware = SkillsMiddleware(skills_dir)

# Create the agent
agent = create_agent("openai:gpt-5", middleware=[skills_middleware])
response = agent.invoke(input={"messages": {"role": "user", "content": "What skills do you have?"}})
```

The `SkillsMiddleware` also supports **dynamic tool registration**, adding new tools to your agent as skills get activated.
When a skill is activated by your agent, all the tools listed in the `allowed-tools` field of that skill is added to the agent's tool list.
This allows you to add new tools to your agent on the fly, preventing the agent's context from being overfilled with tools.

For example, if you have a skill with `allowed-tools: say_hello`, you can add that tool to be dynamically registered when the skill is activated like so:

```py
from langchain.agents import create_agent
from langchain_core.tools import tool

from langchain_skills_adapters import SkillsMiddleware

@tool
def say_hello(name: str):
    return "Hello, " + name

# Create the dynamic tools dictionary
# This should map the name of the tool in allowed-tools to a single tool or a list of tools
tools = [say_hello]
dynamic_tools = {tool.name: tool for tool in tools}

# Create the SkillsMiddleware with dynamic tools
skills_dir = "/path/to/skills/"
skills_middleware = SkillsMiddleware(skills_dir, dynamic_tools=dynamic_tools)

# Create the agent
agent = create_agent("openai:gpt-5", middleware=[skills_middleware])
response = agent.invoke(input={"messages": {"role": "user", "content": "What skills do you have?"}})
```

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
