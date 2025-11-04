# A2A Projects – Overview

### What is A2A?

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
| Travel Planner × Weather Stylist <br> (A2A + MCP Demo) | talk_to_agent.py → Travel Planner Agent <br> (A2A, port 8081) → Weather Stylist Agent <br> (A2A, port 8080) → Weather MCP Server <br> (MCP over stdio) → OpenWeather API → LLM → outfit recommendation | 1. Start Weather Stylist Agent: <br> `uv run uvicorn weather_stylist_agent:app --port 8080` <br> 2. Start Travel Planner Agent:<br> `uv run uvicorn travel_planner_agent:app --port 8081` <br> 3. Call the chain:<br> `uv run talk_to_agent.py` |


## How to run this project

### 1. Clone the repo

```bash
git clone https://github.com/gauthiii/a2aProjects
cd a2aProjects
```


### 2. Create a .env file

```bash
OPENAI_API_KEY=your_openai_key_here  
OPENWEATHER_API_KEY=your_openweather_key_here  

# Optional
ANTHROPIC_API_KEY=your_anthropic_key_here
```


### 3. Install dependencies with uv

```bash
uv add \
  "a2a-sdk[http-server]>=0.3.10" \
  "aisuite[anthropic]>=0.1.6" \
  "fastmcp>=2.13.0.2" \
  "openai>=2.7.1" \
  "python-dotenv>=1.2.1"
```

This will:
- Set up a2a-sdk with HTTP server support (for both agents)
- Install AISuite with Anthropic and OpenAI
- Install fastmcp for the MCP servers
- Install python-dotenv to load .env



