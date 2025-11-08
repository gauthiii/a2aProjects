import json
import aisuite as ai
import re

CLIENT = ai.Client()

# ollama:gemma3:latest
# ollama:qwen3:4b
# ollama:gpt-oss:20b-cloud
# openai:gpt-4o-mini


async def inital_planner_ollama(user_input: str, model: str = "ollama:gemma3:latest") -> str:
        """
        Use the LLM to plan how to:
        - execute the user's request
        """
        prompt = f"""

                This is what the user wants to do: {user_input}

                You are the agent who the A2A client talks to.

                You have access to an A2A reddit agent.
                That agent can research and pull information from reddit.

                The Reddit agent has access to another A2A Google Docs agent.
                That agent can create, write and edit google docs.

                You need to decide a plan. Plan how to execute this request and give me the steps.

                The end goal is to:

                - Research using redit
                - draft the doc on Google Docs
                - Reflect on it and check for alternate on reddit and evaluate the source
                - final draft on Google Docs
                


                Summarize from this and send a response.


                    """

        completion = CLIENT.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are planner for a content research assistant."},
                {"role": "user", "content": prompt},
            ],
        )

        content = completion.choices[0].message.content


                

        return content
