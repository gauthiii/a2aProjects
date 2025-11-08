import json
import aisuite as ai
import re

CLIENT = ai.Client()

# ollama:gemma3:latest
# ollama:qwen3:4b
# ollama:gpt-oss:20b-cloud
# openai:gpt-4o-mini


async def client_response_ollama(response: str, model: str = "ollama:gemma3:latest") -> str:
        """
        Use the LLM to plan how to:
        - execute the user's request
        """
        prompt = f"""

                This is the response received from the agent: {response}

                Extract the content from the response.
                
                Carefully draft a response message from this content and give it to me.

                Do not give any additional information.

                Only what is required.


                    """

        completion = CLIENT.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a meticulous data extractor."},
                {"role": "user", "content": prompt},
            ],
        )

        content = completion.choices[0].message.content


                

        return content
