import json
import aisuite as ai
import re

CLIENT = ai.Client()

# ollama:gemma3:latest
# ollama:qwen3:4b
# ollama:gpt-oss:20b-cloud
# openai:gpt-4o-mini


async def routing(skills_mapping_str: str, user_input: str, model: str = "ollama:gemma3:latest") -> dict[str, bool]:
        """
        Use the LLM to decide whether to:
        - search flights only
        - search stays (Airbnb) only
        - or both.

        Returns a dict like: {"flights": true/false, "stays": true/false}
        """
        routing_prompt = f"""
                You are a travel orchestration agent.

                You have access to the following agents:

                {skills_mapping_str}

                This is the user request:
                {user_input}

                Your task is to decide which agents to invoke based on the user's request.
                It can be either one of them or both of them.

                Respond with ONLY a compact JSON object like this example:
                {{
                "flightAgent": true/false,
                "airbnbAgent": true/false
                }}

                IMPORTANT:
                But if both of them are true and if the both the agents need to be called, 
                then I want you split the user request into two different requests like this

                {{
                "flightAgent": true,
                "airbnbAgent": true,
                "flightPrompt": <userRequest>,
                "airBnbPrompt": <userRequest>
                }}
"""

        completion = CLIENT.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You decide routing for a travel assistant."},
                {"role": "user", "content": routing_prompt},
            ],
        )

        content = completion.choices[0].message.content

        if content.startswith("```"):
            # Remove first ```...``` wrapper
            content = re.sub(r"^```[a-zA-Z0-9_]*\s*", "", content)  # remove ```json or ``` etc
            if content.endswith("```"):
                content = content[: -3]
            content = content.strip()
                

        return content
        # if not isinstance(content, str):
        #     # Fallback: if something weird happens, default to flights only
        #     return {"flights": True, "stays": False}

        # content = content.strip()

        # # Try to parse the JSON the model returned
        # try:
        #     data = json.loads(content)
        #     flights = bool(data.get("flights", True))
        #     stays = bool(data.get("stays", False))
        #     return {"flights": flights, "stays": stays}
        # except Exception:
        #     # If JSON parse fails, fallback heuristic based on keywords
        #     text_lower = user_input.lower()
        #     flights = any(k in text_lower for k in ["flight", "ticket", "fly", "plane"])
        #     stays = any(k in text_lower for k in ["stay", "hotel", "airbnb", "room", "apartment"])

        #     # sensible defaults
        #     if not flights and not stays:
        #         flights = True  # default to flights for generic queries

        #     return {"flights": flights, "stays": stays}
