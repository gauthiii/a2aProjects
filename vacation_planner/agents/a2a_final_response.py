import json
import aisuite as ai
import re

CLIENT = ai.Client()

# ollama:gemma3:latest
# ollama:qwen3:4b
# ollama:gpt-oss:20b-cloud
# openai:gpt-4o-mini


async def final_response(user_input: str, response: str, model: str = "ollama:gemma3:latest") -> str:
        """
        Use the LLM to decide whether to:
        - search flights only
        - search stays (Airbnb) only
        - or both.

        Returns a dict like: {"flights": true/false, "stays": true/false}
        """
        routing_prompt = f"""

                This was the user query: {user_input}

                With the final response you have receieved here: {response}

                Summarize from this and send a response.


                    """

        completion = CLIENT.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You decide routing for a travel assistant."},
                {"role": "user", "content": routing_prompt},
            ],
        )

        content = completion.choices[0].message.content


                

        return content
