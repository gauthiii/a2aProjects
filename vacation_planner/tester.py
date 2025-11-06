import asyncio
from uuid import uuid4
from typing import Any

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest

from dotenv import load_dotenv

load_dotenv()

BASE_URL = "http://localhost:8091"


async def ask_agent(message: str) -> None:
    """
    Send a simple A2A message to the Flight agent and print the response.
    """
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
        full_message = f"{message}"

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

        # 5) Print raw JSON for now
        print("=== Raw A2A response ===")
        print(response.model_dump(mode="json", exclude_none=True))


async def main() -> None:
    await ask_agent(
        "Find me flights from New York to Chennai on January 1, 2026",
      
    )


if __name__ == "__main__":
    asyncio.run(main())
