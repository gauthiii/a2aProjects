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


from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest

BASE_URL = "http://localhost:8090"



class FlightAgent:
    def __init__(self) -> None:
        self._mcp_client = MultiServerMCPClient(
            {
                "flights": {
                    "command": "python",
                    "args": ["flights_mcp_server.py"],
                    "transport": "stdio",
                }
            }
                                                )
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


        search_res = await tools[0].ainvoke({"querystring": user_input})


        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            # 1) Discover agent card from /.well-known/agent-card.json
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=BASE_URL,
            )
            agent_card = await resolver.get_agent_card()

            if agent_card:
                print("\n******************")

                print("Orchestrator: Hey I know a friend who can help you with this:")

                print(agent_card.name)

                print("******************\n")


            # 2) Create an A2A client for that agent
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            # 3) Build the user message (A2A message structure)
            full_message = f"Find me places to stay in Chennai on January 1st, 2026."

            send_message_payload: dict[str, Any] = {
                "message": {
                    "role": "user",
                    "parts": [
                        {"kind": "text", "text": full_message},
                    ],
                    "messageId": uuid4().hex,
                }
            }

            request = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(**send_message_payload),
            )

            # 4) Call the agent via A2A
            response = await client.send_message(request)

        prompt = f"""


                    User query: {user_input}
                    
                    Raw flight search result:
                    
                    {search_res}

                    AirBnb suggestions:

                    {response} 
                    
                    
                    Just give this is in a concise manner.


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


class FlightAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = FlightAgent()

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
    id="flight_agent",
    name="FlightAgent",
    description="Uses the Google Flights MCP to search for flights.",
    tags=["flight", "search", "mcp"],
)

external_card = AgentCard(
    name="Flight Agent",
    description="A2A agent backed by Google Flights MCP server.",
    url="http://localhost:8091/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[external_skill],
    supportsAuthenticatedExtendedCard=False,
)

request_handler = DefaultRequestHandler(
    agent_executor=FlightAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

app_builder = A2AStarletteApplication(
    agent_card=external_card,
    http_handler=request_handler,
)

# uv run uvicorn flights_a2a:app --port 8091
app = app_builder.build()
