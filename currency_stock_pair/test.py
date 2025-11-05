import asyncio
import json
from uuid import uuid4

import httpx
from a2a.client import A2ACardResolver, A2AClient
from a2a.types import MessageSendParams, SendMessageRequest


AGENT1_URL = "http://localhost:8081"  # Currency Pair Agent URL


async def main():
    # 1) Discover Agent1 via its AgentCard
    async with httpx.AsyncClient(timeout=60.0) as httpx_client:
        resolver = A2ACardResolver(
            httpx_client=httpx_client,
            base_url=AGENT1_URL,
        )
        agent_card = await resolver.get_agent_card()

        # 2) Create A2A client
        client = A2AClient(httpx_client=httpx_client, agent_card=agent_card)

        # 3) Build the payload that Agent1 expects (JSON as *text*)
        body = {
            "amount": 100,
            "from_currency": "USD",
            "to_currency": "INR",
            "symbol": "NVDA",
            "start_date": "2024-01-01",
            "end_date": "2024-06-30",
        }

        message_text = json.dumps(body)

        payload = {
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

        # 4) Send the message via A2A
        response = await client.send_message(request)

        # 5) Pretty-print the raw response
        data = response.model_dump(mode="json", exclude_none=True)
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
