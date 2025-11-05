import os
import json
import asyncio
from dotenv import load_dotenv
# import agents.planner, agents.task_executor, agents.reflector, agents.final_eval


# MCP + LangChain imports
from langchain_mcp_adapters.client import MultiServerMCPClient
import tool_def_maker

# Load environment variables
load_dotenv()




# ------------------------------------------------------------------
# Read MCP config dynamically from config.json
# ------------------------------------------------------------------
def load_mcp_config(config_path: str = "currency_config.json"):
    with open(config_path, "r") as f:
        cfg = json.load(f)
    return cfg.get("mcpServers", {})

# ------------------------------------------------------------------
# AGENTS
# ------------------------------------------------------------------

# groq:llama-3.1-8b-instant
# openai:gpt-4o-mini
# anthropic:claude-haiku-4-5
# ollama:gemma3:latest

# MIGRATED TO THE AGENTS FOLDER

import aisuite as ai
CLIENT = ai.Client()

import json


async def task_executor_groq(task,tool_mapping, tool_defs, model: str = "groq:llama-3.1-8b-instant") -> str:
    """
    Groq-specific agent loop that uses MCP tools to compare LG vs Sony TV prices.
    Differs from the OpenAI version only in how it formats `role: "tool"` messages
    (no `tool_name` field, which Groq rejects).
    """

    prompt = f"""
    You have a task: {task}

    Execute all the necessary steps required to accomplish the user's goal.
    Use tools if necessary.



    """

    max_turns = 2

    messages = [
        {"role": "system", "content": "You are an amazing shopping assistant who is also a smart webscraper and data analyst."},
        {"role": "user", "content": prompt},
    ]

    final_text = ""

    for i in range(max_turns):
        # print(f"\n**********************************************************************************\n")
        print(f"Attempt : {i+1}")

        # Call Groq chat completions
        response = CLIENT.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_defs,
            temperature=1.0,
        )

        msg = response.choices[0].message

        # Build assistant message we send back next turn
        assistant_msg = {
            "role": msg.role,
            "content": msg.content or "",
        }

        # Keep tool_calls so Groq knows why tool messages follow
        if getattr(msg, "tool_calls", None):
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]

        messages.append(assistant_msg)

        # If no tool calls, this is the final answer
        if not getattr(msg, "tool_calls", None):
            final_text = msg.content
            print("✅ Final answer:")
            print(final_text)
            break

        # print("Tool Calls Detected:")
        # print(msg.tool_calls)

        # Execute each requested tool
        for tool_call in msg.tool_calls:
            tool_id = tool_call.id
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments

            args = json.loads(tool_args or "{}")

            print(f"Calling tool: {tool_name} with args: {tool_args}")

            tool = tool_mapping[tool_name]
            tool_response = await tool.coroutine(**args)

            # print(f"Tool response: {tool_response}")

            # 🔴 IMPORTANT for Groq:
            # - No `tool_name` field (Groq rejects it)
            # - Just role, tool_call_id, content
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "content": str(tool_response),
                }
            )

    return final_text


async def task_executor_openai(task,tool_mapping, tool_defs, model: str = "openai:gpt-4o-mini") -> str: 

    ### START CODE HERE ###

    # Define your prompt here. A multi-line f-string is typically used for this.
    prompt = f"""
    You have a task: {task}

    Execute all the necessary steps required to accomplish the user's goal.
    Use tools if necessary.



    """

    ### END CODE HERE ###

    max_turns = 3

    messages = [

                {"role": "system", "content": "You are a smart webscraper and data analyst."},
                {"role": "user", "content": prompt}
                ]

    for i in range(max_turns):

        print(f"\n**********************************************************************************\n")

        print(f"Attempt : {i+1}")
    
        # Get a response from the LLM by creating a chat with the client.
        response = CLIENT.chat.completions.create(
            model=model,
            messages=messages,
            tools = tool_defs,
            temperature=1.0,
        )

        msg = response.choices[0].message

        assistant_msg = {
            "role": msg.role,
            "content": msg.content or ""
        }

        # IMPORTANT: keep tool_calls if present
        if getattr(msg, "tool_calls", None):
            assistant_msg["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": tc.type,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in msg.tool_calls
            ]

        messages.append(assistant_msg)



        if not msg.tool_calls:      
            final_text = msg.content
            print("✅ Final answer:")
            print(final_text)
            break

        else:
            print("Tool Calls Detected:")
            print(msg.tool_calls)


        for tool_call in msg.tool_calls:

            tool_id = tool_call.id
            tool_name = tool_call.function.name
            tool_args = tool_call.function.arguments

            args = json.loads(tool_args or "{}")  


            print(f'Calling tool: {tool_name} with args: {tool_args}')

            # tool_response = tool_mapping[tool_name](**args)

            tool = tool_mapping[tool_name]

            # 🔄 ASYNC EXECUTION
            # if hasattr(tool, "ainvoke"):
            #     tool_response = await tool.ainvoke(args)
            # else:
            #     tool_response = tool.invoke(args)

            tool_response = await tool.coroutine(**args)

            print(f'Tool response: {tool_response}')

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "tool_name": tool_name,         
                    "content": str(tool_response)    
                }
            )



    return final_text


# ------------------------------------------------------------------
# Main async routine
# ------------------------------------------------------------------
async def main():
    # 1️⃣ Load MCP servers from config.json
    mcp_servers = load_mcp_config()

    # 2️⃣ Initialize MCP client
    client = MultiServerMCPClient(mcp_servers)

    # 3️⃣ Ensure OpenAI key is available
    os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    if not os.environ.get("OPENAI_API_KEY"):
        raise ValueError("❌ OPENAI_API_KEY not found in .env file!")

    # 4️⃣ Collect tools exposed by the MCP servers
    tools = await client.get_tools()

    if tools:
        tool_defs = [tool_def_maker.lc_tool_to_openai_def(t) for t in tools]
        tool_mapping = tool_def_maker.build_tool_mapping(tools, tool_defs)

    answer = await task_executor_openai("What's 1 crore rupees in US dollars?",tool_mapping, tool_defs)

    print(answer)

    



    
    # x= await agents.compare_products.compare_products_groq(tool_mapping,tool_defs)
    # print(x)



# ------------------------------------------------------------------
# Entry point
# ------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(main())
