from __future__ import annotations

import os
import re
import json
from typing import Any, Optional

import aisuite as ai


from dotenv import load_dotenv  # type: ignore[import-not-found]

load_dotenv()


# --- MCP client imports ---
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

# --- A2A imports ---
from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.apps import A2AStarletteApplication
from a2a.server.events import EventQueue
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from a2a.utils import new_agent_text_message

DEFAULT_MODEL = os.getenv("WEATHER_STYLIST_MODEL", "openai:gpt-4o-mini")

# If you want to override how we start the MCP server, you can change these:
MCP_COMMAND = os.getenv("WEATHER_MCP_COMMAND", "python")
MCP_ARGS = os.getenv("WEATHER_MCP_ARGS", "weather_mcp_server.py").split()


CITY_PATTERN = re.compile(r"city\s*:\s*([A-Za-z\s]+)", re.IGNORECASE)


class WeatherStylistAgent:
    """
    Weather Stylist that uses:
      - MCP weather server for live weather
      - LLM (via AISuite) for outfit suggestions
    """

    def __init__(self) -> None:
        self._client = ai.Client()

    # ---------- MCP CALL HELPERS ----------

    def _extract_city(self, user_input: str) -> str:
        """
        Very simple heuristic: look for `city: Chennai` pattern in the text.
        If not found, default to "Chennai".
        """
        match = CITY_PATTERN.search(user_input)
        if match:
            return match.group(1).strip()
        # fallback – you can change this default if you like
        return "Chennai"

    async def _get_weather_from_mcp(self, city: str) -> Optional[dict]:
        """
        Call the MCP weather server tool `get_weather` and return a dict:
          {"city": ..., "temp_c": ..., "description": ...}
        or None if something goes wrong.
        """
        server_params = StdioServerParameters(
            command=MCP_COMMAND,
            args=MCP_ARGS,
        )

        try:
            async with stdio_client(server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # Initialize MCP session
                    await session.initialize()

                    # Optional: sanity-check tools
                    # tools_response = await session.list_tools()
                    # print("MCP tools:", [t.name for t in tools_response.tools])

                    result = await session.call_tool(
                        "get_weather", arguments={"city": city}
                    )

                    # Prefer structuredContent (since fastmcp tool returns a dict)
                    if result.structuredContent is not None:
                        if isinstance(result.structuredContent, dict):
                            return result.structuredContent  # type: ignore[return-value]

                    # Fallback: parse first TextContent as JSON if available
                    if result.content:
                        first = result.content[0]
                        if isinstance(first, types.TextContent):
                            try:
                                return json.loads(first.text)
                            except Exception:
                                return {"raw": first.text}

        except Exception as e:
            # Fail gracefully; stylist can still give generic advice
            print(f"[WeatherStylist] MCP weather error for city '{city}': {e}")

        return None

    # ---------- MAIN LLM LOGIC ----------

    async def invoke(self, user_input: str) -> str:
        """
        Entry point for the agent logic.
        1. Extract city from the user input
        2. Call MCP weather tool for that city
        3. Feed weather JSON + user input into LLM
        4. Return outfit suggestion text
        """
        if not user_input or not user_input.strip():
            user_input = "Give a generic outfit recommendation for mild spring weather."

        city = self._extract_city(user_input)
        weather_data = await self._get_weather_from_mcp(city)

        # Build a compact weather summary to give the model
        if weather_data:
            weather_summary = (
                f"Live weather for {weather_data.get('city', city)}: "
                f"{weather_data.get('temp_c', '?')}°C, "
                f"{weather_data.get('description', 'no description')}."
            )
        else:
            weather_summary = (
                f"No live weather data available; assume typical conditions for {city}."
            )

        system_prompt = (
            "You are a friendly 'weather stylist' assistant.\n"
            "- You receive BOTH the user's question and a weather summary.\n"
            "- Use the weather summary as the source of truth for conditions.\n"
            "- Always:\n"
            "  1) Briefly restate the assumed weather (temperature and description).\n"
            "  2) Give 2–3 outfit suggestions (tops, bottoms, shoes, and layers) "
            "     that match that weather.\n"
            "  3) Mention accessories (umbrella, sunglasses, etc.) if needed.\n"
            "- Keep answers under 150 words.\n"
        )

        user_content = (
            f"User question:\n{user_input}\n\n"
            f"Weather summary:\n{weather_summary}\n\n"
            f"Raw weather JSON (if any):\n{json.dumps(weather_data, default=str)}"
            if weather_data
            else f"User question:\n{user_input}\n\nWeather summary:\n{weather_summary}"
        )

        response = self._client.chat.completions.create(
            model=DEFAULT_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
        )

        content: Any = response.choices[0].message.content

        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return " ".join(str(part) for part in content)

        return (
            "I couldn't generate an outfit suggestion just now, "
            "even though I tried to use the live weather data. Please try again."
        )


# ---------- A2A EXECUTOR & APP WIRING ----------


class WeatherStylistAgentExecutor(AgentExecutor):
    """
    Bridges the A2A protocol (RequestContext + EventQueue)
    with our WeatherStylistAgent implementation.
    """

    def __init__(self) -> None:
        self.agent = WeatherStylistAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        user_input: str = context.get_user_input()  # type: ignore[assignment]
        result_text = await self.agent.invoke(user_input)
        await event_queue.enqueue_event(new_agent_text_message(result_text))

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        raise Exception("Cancellation is not supported for this agent.")


# ---- AgentCard & skills definition -------------------------------------------------

weather_stylist_skill = AgentSkill(
    id="weather_stylist",
    name="Weather Stylist",
    description=(
        "Given a free-form question about the weather or an upcoming outing, "
        "fetches live weather via MCP and suggests appropriate outfits."
    ),
    tags=["weather", "clothing", "stylist", "outfit"],
    examples=[
        "I'm visiting San Francisco in July, what should I pack?",
        "It's 35°F and snowing in Chicago, what do I wear to walk to work?",
        "Date night in Phoenix this weekend, probably warm — outfit ideas?",
    ],
)

public_agent_card = AgentCard(
    name="Weather Stylist Agent",
    description=(
        "An A2A agent that fetches live weather via an MCP server and "
        "gives outfit suggestions based on the conditions."
    ),
    url="http://localhost:8080/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[weather_stylist_skill],
    supportsAuthenticatedExtendedCard=False,
)

# ---- Wire into A2AStarletteApplication --------------------------------------------

request_handler = DefaultRequestHandler(
    agent_executor=WeatherStylistAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

_server_app_builder = A2AStarletteApplication(
    agent_card=public_agent_card,
    http_handler=request_handler,
)

# This is what uvicorn will run: `uv run uvicorn weather_stylist_agent:app --port 8080`
app = _server_app_builder.build()

# uv run uvicorn weather_stylist_agent:app --port 8080
