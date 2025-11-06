import json
from pathlib import Path
from typing import Any

import asyncio
from uuid import uuid4
import httpx

from langchain_mcp_adapters.client import MultiServerMCPClient

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.server.apps import A2AStarletteApplication
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

from dotenv import load_dotenv
import aisuite as ai

load_dotenv()


def load_mcp_config(config_path: str = "config.json"):
    cfg = json.loads(Path(config_path).read_text())
    servers = cfg.get("mcpServers", {})
    for _, conf in servers.items():
        conf.setdefault("transport", "stdio")
    return servers


class ExternalWebAgent:
    def __init__(self) -> None:
        self._mcp_client = MultiServerMCPClient(load_mcp_config("airbnb_config.json"))
        self._llm_client = ai.Client()
        self._model = "ollama:gemma3:latest"
        self._tools = None

    async def _ensure_tools(self):
        if self._tools is None:
            self._tools = await self._mcp_client.get_tools()
        return self._tools

    async def invoke(self, user_input: str) -> str:
        tools = await self._ensure_tools()

        if tools:

            import tool_def_maker

            tool_def = [tool_def_maker.lc_tool_to_openai_def(t) for t in tools]
            tool_mapping = tool_def_maker.build_tool_mapping(tools,tool_def)


        search_res = await tools[0].ainvoke({"query": user_input})

        prompt = f"""


                    User query: {user_input}
                    
                    Raw search result:
                    
                    {search_res} 
                    
                    
                    Just give the top most result in a concise format


                    """

        # Use LLM to summarise the raw search result
        completion = self._llm_client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": "You are an expert travel assistant."},
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )

        content: Any = completion.choices[0].message.content
        return content if isinstance(content, str) else str(content)


class ExternalWebAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = ExternalWebAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        user_input: str = context.get_user_input()  # type: ignore[assignment]
        result = await self.agent.invoke(user_input)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        raise Exception("Cancellation not supported")    

external_skill = AgentSkill(
    id="external_web",
    name="External Web Agent",
    description="Uses the Airbnb MCP Server and it's search and listing tools to search for hotels, properties, accomodations, and other stays",
    tags=["web", "search", "mcp"],
)

external_card = AgentCard(
    name="External Web Agent",
    description="A2A agent backed by multiple external MCP servers.",
    url="http://localhost:8090/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[external_skill],
    supportsAuthenticatedExtendedCard=False,
)

request_handler = DefaultRequestHandler(
    agent_executor=ExternalWebAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

app_builder = A2AStarletteApplication(
    agent_card=external_card,
    http_handler=request_handler,
)

# uv run uvicorn airbnb_a2a:app --port 8090
app = app_builder.build()
