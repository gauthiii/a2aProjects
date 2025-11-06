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

import agents.routing, agents.flight_llm

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



        async with httpx.AsyncClient(timeout=120.0) as httpx_client:
            
            # 1) Discover agent card from /.well-known/agent-card.json
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=BASE_URL,
            )
            agent_card = await resolver.get_agent_card()

            airBnbResponse="Airbnb agent wasn't required for this use case. Ignore the Airbnb suggestions."

            if agent_card:


                print("Agents Available:")

                skills_mapping = {
                            "flightAgent": external_skill.model_dump(),
                            "airbnbAgent": [s.model_dump() for s in agent_card.skills],
                        }
                
                print(skills_mapping)

                skills_mapping_str = json.dumps(skills_mapping, indent=2)

                agent_decision = await agents.routing.routing(skills_mapping_str, user_input)
                agent_decision = json.loads(agent_decision)

                print("\nRouting decision:", agent_decision)

                

                if agent_decision.get("airbnbAgent")==True:

                    print("\n******************")

                    print("Orchestrator: Hey I know a friend who can help you with this:")

                    print(agent_card.name)

                    print("******************\n")

                    # If only airbnb agent, then transfer the prompt here
                    airbnbPrompt = user_input

                    # If both agents, split the prompts
                    if agent_decision.get("flightAgent")==True:
                        airbnbPrompt = agent_decision.get("airBnbPrompt")
                        user_input = agent_decision.get("flightPrompt")



                    # Create an A2A client for that airbnb agent
                    client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)


                    send_message_payload: dict[str, Any] = {
                        "message": {
                            "role": "user",
                            "parts": [
                                {"kind": "text", "text": airbnbPrompt},
                            ],
                            "messageId": uuid4().hex,
                        }
                    }

                    request = SendMessageRequest(
                        id=str(uuid4()),
                        params=MessageSendParams(**send_message_payload),
                    )

                    
                    airBnbResponse = await client.send_message(request)


        tools = await self._ensure_tools()

        if tools:

            import tool_def_maker

            tool_def = [tool_def_maker.lc_tool_to_openai_def(t) for t in tools]
            tool_mapping = tool_def_maker.build_tool_mapping(tools,tool_def)


        flightResponse = "Flight agent wasn't required for this use case. Ignore the Flight suggestions."
        flightResponse = await agents.flight_llm.flight_search_openai(user_input,tool_mapping,tool_def)

        return str(flightResponse)+" "+str(airBnbResponse)


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
    name="Flight Agent",
    description="Uses the Google Flights MCP to search for flights.",
    tags=["flight", "flight prices", "flight search", "trips"],
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
