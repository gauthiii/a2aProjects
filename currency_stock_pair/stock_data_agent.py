# stock_data_agent.py
#
# Agent2:
#  - talks to stock_data_server.py via MCP
#  - can call Currency Agent (Agent1) over A2A
#
# Expected user input:
#   {
#     "symbol": "NVDA",
#     "start_date": "2024-01-01",
#     "end_date": "2024-06-30",
#     "amount": 100,
#     "from_currency": "USD",
#     "to_currency": "INR"
#   }

from __future__ import annotations

import json
import os
from typing import Any
from uuid import uuid4

import httpx
import pandas as pd
from dotenv import load_dotenv

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

import aisuite as ai  # 👈 NEW


# 👇 Shared LLM model – same as CurrencyPairAgent, or override via env
DEFAULT_MODEL = os.getenv("CURRENCY_STOCK_MODEL", "openai:gpt-4o-mini")

# Where Currency Agent (Agent1) will run
CURRENCY_AGENT_URL = os.getenv("CURRENCY_AGENT_URL", "http://localhost:8081")


class StockDataAgent:
    """
    Agent2:

    - Uses stock_data_server.py (MCP) to fetch OHLCV data.
    - Can call Currency Agent (Agent1) via A2A to convert a budget amount.

    Input format:
    {
      "symbol": "NVDA",
      "start_date": "2024-01-01",
      "end_date": "2024-06-30",
      "amount": 100,
      "from_currency": "USD",
      "to_currency": "INR"
    }
    """

    def __init__(self) -> None:
        self._mcp_client = MultiServerMCPClient(
            {
                "stocks": {
                    "command": "python",
                    "args": ["stock_data_server.py"],
                    "transport": "stdio",
                }
            }
        )
        self._stock_tool = None

        # 👇 NEW: AISuite client + model
        self._llm_client = ai.Client()
        self._model = DEFAULT_MODEL


    async def _get_stock_tool(self):
        if self._stock_tool is None:
            tools = await self._mcp_client.get_tools()

            print("\n[StockDataAgent] MCP tools:")
            for t in tools:
                try:
                    print(" -", t.name)
                except AttributeError:
                    print(" - tool without .name:", t)

            for t in tools:
                name = getattr(t, "name", "")
                if "get_stock_data" in name or name == "get_stock_data":
                    self._stock_tool = t
                    break

            if self._stock_tool is None:
                if not tools:
                    raise RuntimeError("No tools returned from stock MCP server.")
                print("[StockDataAgent] No tool named get_stock_data; using first tool.")
                self._stock_tool = tools[0]

        return self._stock_tool


    async def _get_stock_data(self, symbol: str, start_date: str, end_date: str) -> str:
        tool = await self._get_stock_tool()
        df_like = await tool.ainvoke(
            {"symbol": symbol, "start_date": start_date, "end_date": end_date}
        )

        # Your MCP server returns df.astype(str); it may already be a string,
        # but if it's JSON-like / list-of-dicts we can make a small summary.
        if isinstance(df_like, str):
            # Just return first ~500 chars to keep it short
            return f"Raw stock data (truncated):\n{df_like[:500]}..."

        try:
            df = pd.DataFrame(df_like)
            # Simple summary: first and last date, min/max close
            if not df.empty and "Date" in df and "Close" in df:
                first_date = df["Date"].iloc[0]
                last_date = df["Date"].iloc[-1]
                min_close = df["Close"].astype(float).min()
                max_close = df["Close"].astype(float).max()
                return (
                    f"{symbol} from {first_date} to {last_date}: "
                    f"min close={min_close:.2f}, max close={max_close:.2f}."
                )
        except Exception:
            pass

        return f"Stock data for {symbol} from {start_date} to {end_date}: {df_like}"

    async def _call_currency_agent(self, payload_dict: dict[str, Any]) -> str:
        """
        Call Currency Agent (Agent1) over A2A.
        Typically payload_dict has amount/from_currency/to_currency.
        """
        async with httpx.AsyncClient(timeout=60.0) as httpx_client:
            resolver = A2ACardResolver(
                httpx_client=httpx_client,
                base_url=CURRENCY_AGENT_URL,
            )
            agent_card = await resolver.get_agent_card()

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
                return f"(Currency Agent error: {data['error'].get('message')})"

            result = data.get("result") or {}
            parts = result.get("parts") or []
            for part in parts:
                if (
                    isinstance(part, dict)
                    and part.get("kind") == "text"
                    and isinstance(part.get("text"), str)
                ):
                    return part["text"]

            return "(Currency Agent did not return a usable text response.)"

    async def invoke(self, user_input: str) -> str:
        """
        Main logic:
        - Parse symbol + date range
        - Fetch stock data via MCP
        - Optionally call Currency Agent to convert a budget
        - Then use AISuite OpenAI LLM to summarise
        """
        print("\n[StockDataAgent] raw user_input:", repr(user_input))

        try:
            data = json.loads(user_input)
        except Exception as e:
            return (
                "StockDataAgent expects JSON text with fields: "
                "symbol, start_date, end_date, and optional "
                "amount, from_currency, to_currency.\n"
                f"(JSON decode failed: {e})"
            )

        if isinstance(data, list):
            print("[StockDataAgent] decoded data is a list, taking first element")
            if data and isinstance(data[0], dict):
                data = data[0]
            else:
                return (
                    "StockDataAgent received a JSON list but could not find a "
                    "dict with fields like 'symbol', 'start_date', 'end_date'."
                )

        if not isinstance(data, dict):
            return (
                "StockDataAgent expected a JSON object, but got: "
                f"{type(data).__name__}"
            )

        # Required stock fields
        try:
            symbol = data["symbol"]
            start_date = data["start_date"]
            end_date = data["end_date"]
        except KeyError as e:
            return f"Missing key in JSON: {e}"

        # 1) Stock via MCP
        stock_text = await self._get_stock_data(symbol, start_date, end_date)

        # 2) Optional FX via Agent1
        amount = data.get("amount")
        from_ccy = data.get("from_currency")
        to_ccy = data.get("to_currency")

        fx_text = ""
        if amount is not None and from_ccy and to_ccy:
            fx_payload = {
                "amount": amount,
                "from_currency": from_ccy,
                "to_currency": to_ccy,
            }
            fx_text = await self._call_currency_agent(fx_payload)

        # Combine raw tool outputs
        tools_output = f"[Stock via Stock MCP] {stock_text}"
        if fx_text:
            tools_output += f"\n[FX via Agent1] {fx_text}"

        # 3) Use AISuite LLM to turn that into a nice explanation
        system_prompt = (
            "You are a stock analyst agent.\n"
            "- The tools have already fetched raw stock data "
            "and (optionally) an FX conversion.\n"
            "- Your job is to summarise:\n"
            "  1) The basic stock trend over the given period.\n"
            "  2) If FX data is present, how that might affect a budget.\n"
            "  3) 2–3 short bullets with practical takeaways.\n"
            "- Keep it under 200 words and use simple language."
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
                            "Tool outputs (stock + optional FX):\n"
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

            # Fallback: if content structure is weird
            return tools_output

        except Exception as e:
            print("[StockDataAgent] LLM error:", repr(e))
            return tools_output


class StockDataAgentExecutor(AgentExecutor):
    def __init__(self) -> None:
        self.agent = StockDataAgent()

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


stock_data_skill = AgentSkill(
    id="stock_data",
    name="Stock Data Agent",
    description=(
        "Uses a Stock MCP server for OHLCV data and can call Currency Agent over A2A "
        "to convert budgets."
    ),
    tags=["stocks", "forex"],
    examples=[
        '{"symbol": "NVDA", "start_date": "2024-01-01", "end_date": "2024-06-30", '
        '"amount": 100, "from_currency": "USD", "to_currency": "INR"}'
    ],
)

stock_data_card = AgentCard(
    name="Stock Data Agent",
    description=(
        "Agent2: connects to stock_data_server via MCP and talks to Currency Agent via A2A."
    ),
    url="http://localhost:8082/",
    version="1.0.0",
    defaultInputModes=["text"],
    defaultOutputModes=["text"],
    capabilities=AgentCapabilities(streaming=True),
    skills=[stock_data_skill],
    supportsAuthenticatedExtendedCard=False,
)

request_handler = DefaultRequestHandler(
    agent_executor=StockDataAgentExecutor(),
    task_store=InMemoryTaskStore(),
)

_server_app_builder = A2AStarletteApplication(
    agent_card=stock_data_card,
    http_handler=request_handler,
)

# uv run uvicorn stock_data_agent:app --port 8082
app = _server_app_builder.build()
