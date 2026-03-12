from pathlib import Path

from langchain.agents import create_agent

from langchain_skills_adapters import SkillsMiddleware

# Create the SkillsMiddleware pointed to your skills directory
skills_dir = str((Path(__file__).parent / "skills").resolve())
skills_middleware = SkillsMiddleware(skills_dir)

# Create the agent
agent = create_agent("openai:gpt-5", middleware=[skills_middleware])
response = agent.invoke(input={"messages": {"role": "user", "content": "What does my-skill do?"}})