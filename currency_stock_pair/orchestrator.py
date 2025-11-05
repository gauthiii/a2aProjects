# orchestrator_google_in_eur.py
import asyncio
import json
from typing import Any
from uuid import uuid4

import httpx
from a2a.client import A2AClient
from a2a.types import (
    GetTaskRequest,
    GetTaskResponse,
    MessageSendParams,
    SendMessageRequest,
    SendMessageResponse,
    SendMessageSuccessResponse,
    Task,
    TaskQueryParams,
)


FOREX_URL = "http://localhost:10001"  # Forex A2A Agent
STOCK_URL = "http://localhost:10002"  # Stocks A2A Agent


def make_payload(text: str, task_id: str | None = None, context_id: str | None = None):
    payload: dict[str, Any] = {
        "message": {
            "role": "user",
            "parts": [{"kind": "text", "text": text}],
            "messageId": uuid4().hex,
        }
    }
    if task_id:
        payload["message"]["taskId"] = task_id
    if context_id:
        payload["message"]["contextId"] = context_id
    return payload


async def send_single_turn(client: A2AClient, text: str) -> str:
    """Send a single-turn request and return final text result."""
    send_payload = make_payload(text)
    request = SendMessageRequest(params=MessageSendParams(**send_payload))
    send_response: SendMessageResponse = await client.send_message(request)

    if not isinstance(send_response.root, SendMessageSuccessResponse):
        raise RuntimeError("Non-success response from agent")

    if not isinstance(send_response.root.result, Task):
        raise RuntimeError("Agent did not return a Task")

    task_id = send_response.root.result.id

    get_req = GetTaskRequest(params=TaskQueryParams(id=task_id))
    get_res: GetTaskResponse = await client.get_task(get_req)

    # NOTE: This assumes your AgentExecutor wrote a text artifact
    # named "current_result" with the final answer as plain text.
    # You can adjust this based on how you structured artifacts.
    task = get_res.root.result
    if not task or not task.artifacts:
        raise RuntimeError("No artifacts in task result")

    text_artifact = task.artifacts[0]
    text_content = text_artifact.serialized.get("text") or text_artifact.serialized.get(
        "data", ""
    )

    if isinstance(text_content, str):
        return text_content
    return json.dumps(text_content)


async def main():
    async with httpx.AsyncClient(timeout=60) as httpx_client:
        # Connect to both agents using their agent cards
        stock_client = await A2AClient.get_client_from_agent_card_url(
            httpx_client, f"{STOCK_URL}/.well-known/agent.json"
        )
        forex_client = await A2AClient.get_client_from_agent_card_url(
            httpx_client, f"{FOREX_URL}/.well-known/agent.json"
        )

        # 1) Ask Market Agent for GOOG price in USD
        stock_question = "What is Google's (GOOG) stock price today in USD? Only give me the numeric price and 'USD'."
        stock_answer = await send_single_turn(stock_client, stock_question)
        print("Stock agent answer:", stock_answer)

        # You can make StockAgent answer JSON, e.g. {"symbol": "GOOG", "price": 123.45, "currency": "USD"}
        # Then parse:
        try:
            data = json.loads(stock_answer)
            price = data["price"]
            currency = data.get("currency", "USD")
        except Exception:
            # fallback: very naive parse
            import re

            m = re.search(r"([0-9]+(\.[0-9]+)?)", stock_answer)
            if not m:
                raise RuntimeError("Could not parse price from stock agent answer")
            price = float(m.group(1))
            currency = "USD"

        # 2) Ask Forex Agent to convert that price from USD to EUR
        forex_question = f"Convert {price} {currency} to EUR. Only return the numeric EUR amount, in JSON {{\"amount_eur\": <value>}}."
        forex_answer = await send_single_turn(forex_client, forex_question)
        print("Forex agent answer:", forex_answer)

        try:
            fx_data = json.loads(forex_answer)
            amount_eur = fx_data["amount_eur"]
        except Exception:
            # fallback naive parse
            import re

            m2 = re.search(r"([0-9]+(\.[0-9]+)?)", forex_answer)
            if not m2:
                raise RuntimeError("Could not parse EUR amount from forex answer")
            amount_eur = float(m2.group(1))

        print(
            f"Final: GOOG is {price} {currency} today, which is approximately {amount_eur} EUR."
        )


if __name__ == "__main__":
    asyncio.run(main())
