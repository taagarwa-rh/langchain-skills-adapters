# Contributing

## Contribution Process

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push your changes to your fork.
5. Create a pull request from your branch to the main repository.
6. Wait for the maintainers to review your changes and merge them into the main repository.

## Setting Up the Repository

To set up the repository, run the following commands:

```sh
git clone https://github.com/taagarwa-rh/langchain-skills-adapters.git
cd langchain-skills-adapters

uv venv
uv sync
```

## Developing and Testing

The project is split into three main components:

```
src/langchain_skills_adapters/
├── core/
├── middleware/
└── tools/
```

- `core` contains the main functionality for the project, providing utilities and data models for the skills components. 
  Any common components should be put here.
- `middleware` contains the code supporting `SkillsMiddleware`, a Langchain `AgentMiddleware`.
  Any components supporting the `SkillsMiddleware` should be put here.
- `tools` contains the code supporting the `SkillsTool`, a Langchain `BaseTool`.
  Any components supporting the `SkillsTool` should be put here.

When developing features, please use the appropriate directory.
