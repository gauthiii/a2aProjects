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

import agents.googleDocs_llm




def load_mcp_config(config_path: str = "config.json"):
    cfg = json.loads(Path(config_path).read_text())
    servers = cfg.get("mcpServers", {})
    for _, conf in servers.items():
        conf.setdefault("transport", "stdio")
    return servers


class GoogleDocsAgent:
    def __init__(self) -> None:
        self._mcp_client = MultiServerMCPClient(load_mcp_config("google_docs_config.json"))
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


        googleDocsResponse = await agents.googleDocs_llm.googleDocs_openAI(user_input,tool_mapping,tool_def)
        
        return googleDocsResponse


class GoogleDocsAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = GoogleDocsAgent()

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
    id="google_docs_agent",
    name="Google Docs Agent",
    description="Uses the Google Docs MCP Server and it's reading, writinga and drafting content.",
    tags=["docs", "documents", "google docs", "reading", "writing", "drafting", "creating"],
)

external_card = AgentCard(
    name="Google Docs Agent",
    description="A2A agent backed by a google docs MCP server.",
    url="http://localhost:8131/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[external_skill],
    supportsAuthenticatedExtendedCard=False,
)

request_handler = DefaultRequestHandler(
    agent_executor=GoogleDocsAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

app_builder = A2AStarletteApplication(
    agent_card=external_card,
    http_handler=request_handler,
)

# uv run uvicorn docs_a2a:app --port 8131
app = app_builder.build()
