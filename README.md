# A2A Projects – Overview

## What is A2A?

A2A (Agent-to-Agent protocol) is a standard way for agents to talk to each other over HTTP using a shared message format (JSON-RPC + structured messages).


### How A2A differs from MCP

MCP (Model Context Protocol) and A2A solve different layers of the stack:

- MCP is about tools  
  It exposes functions/APIs like get_weather(city) or search_docs(query).  
  Typical shape: Agent → MCP server (tools).  
  Think: “LLM or agent calling a toolbox.”

- A2A is about agents  
  It lets full agents (with their own tools, memory, logic) talk to each other.  
  Typical shape: Agent A ↔ Agent B (conversation/requests).  
  Think: “Specialist agents collaborating.”

In this repo:
- A2A connects: Travel Planner Agent ↔ Weather Stylist Agent.
- MCP connects: Weather Stylist Agent → Weather MCP Server → OpenWeather API.


## Projects

| Project Title | The Chain | Run Commands (overview) |
| --- | --- | --- |
| Travel Planner × Weather Stylist (A2A + MCP Demo) | talk_to_agent.py → Travel Planner Agent (A2A, port 8081) → Weather Stylist Agent (A2A, port 8080) → Weather MCP Server (MCP over stdio) → OpenWeather API → back up the chain with an LLM-generated travel + outfit recommendation | 1. Start Weather Stylist Agent: `uv run uvicorn weather_stylist_agent:app --port 8080`  2. Start Travel Planner Agent: `uv run uvicorn travel_planner_agent:app --port 8081`  3. Call the chain: `uv run talk_to_agent.py` |


## How to run this project

### 1. Clone the repo

git clone <your-repo-url>.git
cd <your-repo-folder>

(Replace <your-repo-url> and <your-repo-folder> with your actual repo details.)


### 2. Create a .env file

OPENAI_API_KEY=your_openai_key_here  
OPENWEATHER_API_KEY=your_openweather_key_here  

# Optional
ANTHROPIC_API_KEY=your_anthropic_key_here


### 3. Install dependencies with uv

uv add \
  "a2a-sdk[http-server]>=0.3.10" \
  "aisuite[anthropic]>=0.1.6" \
  "fastmcp>=2.13.0.2" \
  "openai>=2.7.1" \
  "python-dotenv>=1.2.1"

This will:
- Set up a2a-sdk with HTTP server support (for both agents)
- Install AISuite with Anthropic and OpenAI
- Install fastmcp for the Weather MCP server
- Install python-dotenv to load .env


### 4. Start the agents

Terminal 1 – Weather Stylist Agent (A2A + MCP)

uv run uvicorn weather_stylist_agent:app --port 8080

This agent:
- Receives A2A messages
- Extracts the city from the input (e.g., city: Chennai)
- Calls the Weather MCP server (weather_mcp_server.py) via stdio
- Sends live weather summary + JSON to an LLM via AISuite (OpenAI)
- Responds with outfit suggestions


Terminal 2 – Travel Planner Agent (A2A)

uv run uvicorn travel_planner_agent:app --port 8081

This agent:
- Receives high-level travel questions
- Calls the Weather Stylist Agent over A2A as a sub-agent
- Uses AISuite again to combine the stylist’s reply into a short travel plan + packing guidance


### 5. Call the chain via the client

Make sure talk_to_agent.py has:

BASE_URL = "http://localhost:8081"

Then run:

uv run talk_to_agent.py

This will:
- Discover the Travel Planner Agent via its A2A Agent Card
- Send your question (e.g., “I’m visiting Chennai tomorrow evening; do I need an umbrella and what should I wear? (city: Chennai)”)
- Trigger the whole chain:

  Client → Travel Planner (A2A) → Weather Stylist (A2A) → Weather MCP (MCP) → OpenWeather API + LLMs → back to client

You’ll see the final JSON-RPC response printed; you can later refine the client to extract and print just the final text message.
