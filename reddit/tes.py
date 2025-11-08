import reddit_a2a
from langchain_mcp_adapters.client import MultiServerMCPClient
import asyncio

async def main():
    mcp_client = MultiServerMCPClient(reddit_a2a.load_mcp_config("reddit_config.json"))

    tools = await mcp_client.get_tools()

    for tool in tools:
        print(f"{tool.name} - {tool.description}")

if __name__ == "__main__":
    asyncio.run(main())