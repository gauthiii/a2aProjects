# currency_pair_agent.py
#
# Agent1:
#  - talks to currency_mcp_server.py via MCP
#  - can call Stock Agent (Agent2) over A2A
#
# Expected user input (plain text, but JSON inside is easiest for now):
#   {
#     "amount": 100,
#     "from_currency": "USD",
#     "to_currency": "INR",
#     "symbol": "NVDA",
#     "start_date": "2024-01-01",
#     "end_date": "2024-06-30"
#   }

from __future__ import annotations

import json
import os
from typing import Any
from uuid import uuid4

import httpx
from dotenv import load_dotenv

import aisuite as ai  # 👈 NEW

from langchain_mcp_adapters.client import MultiServerMCPClient

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

load_dotenv()

# Where Stock Agent (Agent2) will run
STOCK_AGENT_URL = os.getenv("STOCK_AGENT_URL", "http://localhost:8082")

# Shared LLM model for this whole currency+stock pair system
DEFAULT_MODEL = os.getenv("CURRENCY_STOCK_MODEL", "openai:gpt-4o-mini")


class CurrencyPairAgent:
    """
    Agent1:

    - Uses currency_mcp_server.py to convert currencies.
    - Optionally calls Stock Agent (Agent2) over A2A
      to fetch stock data for a symbol/date range.

    Input format (JSON inside text):
    {
      "amount": 100,
      "from_currency": "USD",
      "to_currency": "INR",
      "symbol": "NVDA",
      "start_date": "2024-01-01",
      "end_date": "2024-06-30"
    }
    """

    def __init__(self) -> None:
        # One MCP client for the currency server
        self._mcp_client = MultiServerMCPClient(
            {
                "currency": {
                    "command": "python",
                    "args": ["currency_mcp_server.py"],
                    "transport": "stdio",
                }
            }
        )
        self._currency_tool = None

        # 👇 Shared AISuite client + model for reasoning / summarization
        self._llm_client = ai.Client()
        self._model = DEFAULT_MODEL



    async def _get_currency_tool(self):
        if self._currency_tool is None:
            tools = await self._mcp_client.get_tools()

            # Debug: see what tools we actually got
            print("\n[CurrencyPairAgent] MCP tools:")
            for t in tools:
                try:
                    print(" -", t.name)
                except AttributeError:
                    print(" - tool without .name:", t)

            # Try to find the specific tool by (partial) name match
            for t in tools:
                name = getattr(t, "name", "")
                if "convert_currency_with_api" in name or name == "convert_currency_with_api":
                    self._currency_tool = t
                    break

            # Fallback: just pick the first tool if we didn't find by name
            if self._currency_tool is None:
                if not tools:
                    raise RuntimeError("No tools returned from currency MCP server.")
                print("[CurrencyPairAgent] No tool named convert_currency_with_api; using first tool.")
                self._currency_tool = tools[0]

        return self._currency_tool


    async def _convert_currency(
        self, amount: float, from_currency: str, to_currency: str
    ) -> str:
        tool = await self._get_currency_tool()
        # LangChain tools support ainvoke in async contexts
        result = await tool.ainvoke(
            {
                "amount": amount,
                "from_currency": from_currency,
                "to_currency": to_currency,
            }
        )
        # currency_mcp_server returns a string like "100 USD = 82.34 EUR"
        return str(result)

    async def _call_stock_agent(self, payload_dict: dict[str, Any]) -> str:
        """
        Call Stock Agent (Agent2) over A2A using HTTP.
        payload_dict is usually {"symbol": "...", "start_date": "...", "end_date": "..."}.
        """
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            # 1) Discover Stock Agent via its AgentCard
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=STOCK_AGENT_URL,
            )
            agent_card = await resolver.get_agent_card()

            # 2) A2A client
            client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

            message_text = json.dumps(payload_dict)

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
            data = response.model_dump(mode="json", exclude_none=True)

            if "error" in data:
                return f"(Stock Agent error: {data['error'].get('message')})"

            result = data.get("result") or {}
            parts = result.get("parts") or []
            for part in parts:
                if (
                    isinstance(part, dict)
                    and part.get("kind") == "text"
                    and isinstance(part.get("text"), str)
                ):
                    return part["text"]

            return "(Stock Agent did not return a usable text response.)"

    async def invoke(self, user_input: str) -> str:
        """
        Main logic:
        - Parse JSON from user_input
        - Convert currency via currency MCP
        - If symbol/start_date/end_date present, call Stock Agent
        - Then use AISuite OpenAI LLM to summarize the pair analysis
        """
        # 🔍 Debug: see what we actually got
        print("\n[CurrencyPairAgent] raw user_input:", repr(user_input))

        try:
            data = json.loads(user_input)
        except Exception as e:
            return (
                "CurrencyPairAgent expects JSON text with fields: "
                "amount, from_currency, to_currency, and optional "
                "symbol, start_date, end_date.\n"
                f"(JSON decode failed: {e})"
            )

        # 🔧 If the decoded JSON is a list (e.g. [{"amount": ...}]), pick the first dict
        if isinstance(data, list):
            print("[CurrencyPairAgent] decoded data is a list, taking first element")
            if data and isinstance(data[0], dict):
                data = data[0]
            else:
                return (
                    "CurrencyPairAgent received a JSON list but could not find a "
                    "dict with fields like 'amount', 'from_currency', 'to_currency'."
                )

        if not isinstance(data, dict):
            return (
                "CurrencyPairAgent expected a JSON object, but got: "
                f"{type(data).__name__}"
            )

        # Mandatory FX fields
        try:
            amount = float(data["amount"])
            from_ccy = data["from_currency"]
            to_ccy = data["to_currency"]
        except KeyError as e:
            return f"Missing key in JSON: {e}"

        # 1) Convert currency via MCP
        fx_text = await self._convert_currency(amount, from_ccy, to_ccy)

        # 2) Optional: call Stock Agent for pair analysis
        symbol = data.get("symbol")
        start_date = data.get("start_date")
        end_date = data.get("end_date")

        stock_text = ""
        if symbol and start_date and end_date:
            stock_payload = {
                "symbol": symbol,
                "start_date": start_date,
                "end_date": end_date,
            }
            stock_text = await self._call_stock_agent(stock_payload)

        # Combine raw tool outputs
        tools_output = f"[FX via Currency MCP] {fx_text}"
        if stock_text:
            tools_output += f"\n[Stock via Agent2] {stock_text}"

        # 3) Use AISuite OpenAI LLM to create a clean explanation
        system_prompt = (
            "You are a financial assistant that analyzes a currency/stock pair.\n"
            "- The tools have already fetched raw FX and stock information.\n"
            "- Your job is to explain clearly what this means for the user.\n"
            "- Include:\n"
            "  1) A 1–2 sentence overview of the FX conversion.\n"
            "  2) If stock data is present, summarize the stock trend in simple terms.\n"
            "  3) 2–3 short bullet points suggesting how the user might interpret or use this.\n"
            "- Keep it under 200 words and avoid jargon."
        )

        try:
            completion = self._llm_client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {
                        "role": "user",
                        "content": (
                            "User input (JSON or natural language):\n"
                            f"{user_input}\n\n"
                            "Tool outputs (FX + optional stock):\n"
                            f"{tools_output}"
                        ),
                    },
                ],
            )

            content: Any = completion.choices[0].message.content

            if isinstance(content, str):
                return content
            if isinstance(content, list):
                return " ".join(str(part) for part in content)

            # Fallback: if content is weird, at least return the raw tools output
            return tools_output

        except Exception as e:
            # If LLM fails for any reason, fall back to raw tools output
            print("[CurrencyPairAgent] LLM error:", repr(e))
            return tools_output



class CurrencyPairAgentExecutor(AgentExecutor):
    """
    Adapter to expose CurrencyPairAgent via A2A.
    """

    def __init__(self) -> None:
        self.agent = CurrencyPairAgent()

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


# ---- AgentCard for CurrencyPairAgent ----------------------------------------------

currency_pair_skill = AgentSkill(
    id="currency_pair",
    name="Currency Pair Analyzer",
    description=(
        "Uses a Currency MCP server for FX conversion and can call a Stock Agent "
        "over A2A to get stock data for pair analysis."
    ),
    tags=["forex", "stocks", "pair"],
    examples=[
        '{"amount": 100, "from_currency": "USD", "to_currency": "INR", '
        '"symbol": "NVDA", "start_date": "2024-01-01", "end_date": "2024-06-30"}'
    ],
)

currency_pair_card = AgentCard(
    name="Currency Pair Agent",
    description=(
        "Agent1: connects to currency_mcp_server via MCP and talks to Stock Agent via A2A."
    ),
    url="http://localhost:8081/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[currency_pair_skill],
    supportsAuthenticatedExtendedCard=False,
)

request_handler = DefaultRequestHandler(
    agent_executor=CurrencyPairAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

_server_app_builder = A2AStarletteApplication(
    agent_card=currency_pair_card,
    http_handler=request_handler,
)

# uv run uvicorn currency_pair_agent:app --port 8081
app = _server_app_builder.build()
