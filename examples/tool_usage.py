from pathlib import Path

from langchain.agents import create_agent
from langchain_community.tools.file_management.read import ReadFileTool

from langchain_skills_adapters import SkillsTool

# Create the SkillsTool pointed to your skills directory
skills_dir = str((Path(__file__).parent / "skills").resolve())
skills_tool = SkillsTool(skills_dir)
print(skills_tool.description)

# Optional: Add a file reading tool. Recommended if your agent needs to read resources from your skill directory (scripts, assets, etc.)
read_file_tool = ReadFileTool(root_dir=skills_dir)

# Create the agent with the SkillsTool
tools = [skills_tool, read_file_tool]
agent = create_agent("openai:gpt-5", tools=tools)
response = agent.invoke(input={"messages": {"role": "user", "content": "What skills do you have?"}})
print(response)
