# travel_planner_agent.py
#
# A second A2A agent that:
#  - receives high-level travel questions from the user
#  - calls your existing Weather Stylist A2A agent over HTTP
#  - combines that with a small LLM reasoning step to give a travel-oriented answer

from __future__ import annotations

import os
from typing import Any
from uuid import uuid4

import aisuite as ai
import httpx

from a2a.client import A2ACardResolver, A2AClient
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import (
    AgentCapabilities,
    AgentCard,
    AgentSkill,
    MessageSendParams,
    SendMessageRequest,
)
from a2a.utils import new_agent_text_message

from dotenv import load_dotenv

load_dotenv()

# URL of your existing Weather Stylist agent
# You can override this with WEATHER_AGENT_URL env var if needed.
WEATHER_AGENT_URL = os.getenv("WEATHER_AGENT_URL", "http://localhost:8080")

DEFAULT_MODEL = os.getenv("TRAVEL_PLANNER_MODEL", "openai:gpt-4o-mini")


class TravelPlannerAgent:
    """
    High-level travel planner.

    - Takes a user travel question (city, dates, vibe).
    - Calls the Weather Stylist A2A agent to get outfit & weather-style advice.
    - Uses an LLM (AISuite) to combine both into a small travel plan answer.
    """

    def __init__(self) -> None:
        self._client = ai.Client()

    async def _call_weather_stylist(self, user_input: str) -> str:
        """
        Call the Weather Stylist A2A agent over HTTP using the A2A client.

        Returns the *text* produced by the Weather Stylist, or a fallback string.
        """
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            # 1) Discover the remote agent via its agent card
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=WEATHER_AGENT_URL,
            )
            agent_card = await resolver.get_agent_card()

            if agent_card:
                print("\n******************")

                print("Travel Planner: Hey I know an agent who can help you with this:")

                print(agent_card.name)

                print("******************\n")


            # 2) Create an A2A client (yes, A2AClient is deprecated, but fine for now)
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            # 3) Build a simple "user" message for the stylist agent
            message_text = (
                "You are being called by a travel planner agent.\n"
                "User travel question:\n"
                f"{user_input}\n\n"
                "Please respond ONLY with concise weather & outfit advice for the user."
            )

            payload: dict[str, Any] = {
                "message": {
                    "role": "user",
                    "parts": [{"kind": "text", "text": message_text}],
                    "messageId": uuid4().hex,
                }
            }

            request = SendMessageRequest(
                id=str(uuid4()),
                params=MessageSendParams(**payload),
            )

            response = await client.send_message(request)

            # The JSON-RPC response looks like:
            # {'id': '...', 'jsonrpc': '2.0',
            #  'result': {'kind': 'message', 'messageId': '...', 'parts': [
            #       {'kind': 'text', 'text': 'Hello World'}
            #  ], 'role': 'agent'}}
            # 
            data = response.model_dump(mode="json", exclude_none=True)

            if "error" in data:
                return f"(Weather Stylist error: {data['error'].get('message')})"

            result = data.get("result") or {}
            parts = result.get("parts") or []
            for part in parts:
                if (
                    isinstance(part, dict)
                    and part.get("kind") == "text"
                    and isinstance(part.get("text"), str)
                ):
                    return part["text"]

            return "(Weather Stylist did not return a usable text response.)"

    async def invoke(self, user_input: str) -> str:
        """
        Main entry point: combine Weather Stylist output with travel planning.
        """
        if not user_input or not user_input.strip():
            user_input = "Plan a weekend city break somewhere warm and suggest outfits."

        # 1) Call the Weather Stylist agent
        stylist_text = await self._call_weather_stylist(user_input)

        # 2) Use LLM to synthesize a travel-friendly answer
        system_prompt = (
            "You are a travel planner agent.\n"
            "- The user provides a travel question (city, dates, vibe).\n"
            "- Another agent (Weather Stylist) provides weather & outfit advice.\n"
            "- Combine both and answer with:\n"
            "  1) A 1–2 sentence summary of the trip.\n"
            "  2) 3–5 bullet points with:\n"
            "     - suggested activities,\n"
            "     - clothing/outfit guidance,\n"
            "     - packing or timing tips.\n"
            "- Keep the whole answer under 200 words."
        )

        completion = self._client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"User travel question:\n{user_input}\n\n"
                        f"Weather Stylist agent reply:\n{stylist_text}"
                    ),
                },
            ],
        )

        content: Any = completion.choices[0].message.content

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(str(part) for part in content)

        return "I couldn't generate a travel plan right now. Please try rephrasing your question."


class TravelPlannerAgentExecutor(AgentExecutor):
    """
    Adapter that exposes TravelPlannerAgent to A2A via the AgentExecutor interface.
    """

    def __init__(self) -> None:
        self.agent = TravelPlannerAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        # Extract user text from the A2A RequestContext
        user_input: str = context.get_user_input()  # type: ignore[assignment]

        result_text = await self.agent.invoke(user_input)

        # Return a simple text message event to the caller
        await event_queue.enqueue_event(new_agent_text_message(result_text))

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise Exception("Cancellation is not supported for this agent.")


# ---- AgentCard for the Travel Planner agent ---------------------------------------

travel_planner_skill = AgentSkill(
    id="travel_planner",
    name="Travel Planner",
    description=(
        "Plans short trips and gives activity + packing suggestions, "
        "augmenting its answers with a Weather Stylist A2A agent."
    ),
    tags=["travel", "itinerary", "packing", "weather"],
    examples=[
        "I'm going to Chennai for 3 days next week, what should I do and what should I pack?",
        "Weekend in San Francisco in July, give me a mini plan and outfit guidance.",
    ],
)

travel_planner_card = AgentCard(
    name="Travel Planner Agent",
    description=(
        "An A2A agent that plans trips and packing lists, calling a Weather Stylist "
        "A2A agent under the hood for weather-aware outfit suggestions."
    ),
    url="http://localhost:8081/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[travel_planner_skill],
    supportsAuthenticatedExtendedCard=False,
)

# ---- Wire into A2AStarletteApplication --------------------------------------------

request_handler = DefaultRequestHandler(
    agent_executor=TravelPlannerAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

_server_app_builder = A2AStarletteApplication(
    agent_card=travel_planner_card,
    http_handler=request_handler,
)

# This is what uvicorn will run: `uv run uvicorn travel_planner_agent:app --port 8081`
app = _server_app_builder.build()

# uv run uvicorn travel_planner_agent:app --port 8081