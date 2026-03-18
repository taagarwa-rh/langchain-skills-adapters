from langchain.agents import create_agent
from langchain_community.agent_toolkits import PlayWrightBrowserToolkit
from langchain_community.tools.playwright.utils import create_async_playwright_browser
import nest_asyncio

from langchain_skills_adapters import SkillsMiddleware

nest_asyncio.apply()

async def main():
    # Get playwright tools
    async_browser = create_async_playwright_browser()
    toolkit = PlayWrightBrowserToolkit.from_browser(async_browser=async_browser)
    tools = toolkit.get_tools()

    # Create dynamic tools
    dynamic_tools = {tool.name: tool for tool in tools}

    # Create the SkillsTool pointed to your skills directory
    skills_dir = "examples/browser-skills"
    skills_middleware = SkillsMiddleware(skills_dir, dynamic_tools=dynamic_tools)

    # Create the agent
    agent = create_agent(model="openai:gpt-5", middleware=[skills_middleware])
    response = await agent.ainvoke(input={"messages": {"role": "user", "content": "First summarize the webpage https://en.wikipedia.org/wiki/Appellate_Division_Courthouse_of_New_York_State, then list what tools you have access to"}})
    print(response)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
