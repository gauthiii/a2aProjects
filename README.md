# A2A Projects – Overview

### What is A2A?

A2A (Agent-to-Agent protocol) is a standard way for agents to talk to each other over HTTP using a shared message format (JSON-RPC + structured messages).


### How A2A differs from MCP

MCP (Model Context Protocol) and A2A solve different layers of the stack:

- MCP is about tools  
  It exposes functions/APIs like get_weather(city) or search_docs(query).  
  Agent → MCP server (tools).  

- A2A is about agents  
  It lets full agents (with their own tools, memory, logic) talk to each other.  
  Agent A ↔ Agent B (conversation/requests).  


## Projects

<span style="font-size: 12px;">

| Project Title | The Chain and Run Commands |
| ----- | ------- |
| Travel Planner × Weather Stylist <br> (A2A + MCP Demo) | A2A connects: Travel Planner Agent ↔ Weather Stylist Agent. <br> MCP connects: Weather Stylist Agent → Weather MCP Server → OpenWeather API. <br><br> 1. Start Weather Stylist Agent: <br> `uv run uvicorn weather_stylist_agent:app --port 8080` <br> 2. Start Travel Planner Agent:<br> `uv run uvicorn travel_planner_agent:app --port 8081` <br> 3. Call the chain:<br> `uv run talk_to_agent.py` |
| Currency & Stocks Pair <br> (A2A + MCP Demo) | A2A connects: Currency Pair Agent ↔ Stock Data Agent. <br> MCP connects: <br> • Currency Pair Agent → Currency MCP Server → Exchange Rate API <br> • Stock Data Agent → Stock MCP Server → Yahoo Finance API. <br><br> **Run Order:** <br> 1. Start Currency Pair (A2A) Agent: <br> `uv run uvicorn currency_pair_agent:app --port 8081` <br> 2. Start Stock Data (A2A) Agent: <br> `uv run uvicorn stock_data_agent:app --port 8082` <br> 3. Test or Orchestrate Communication: <br> `uv run python test.py` |
| Vacation Planner × Airbnb <br> (A2A + MCP Demo) | A2A connects: Flight Agent ↔ Airbnb Agent. <br> MCP connects: <br> • Flight Agent → Flights MCP Server → Google Flights API (via RapidAPI) <br> • Airbnb Agent → Airbnb MCP Server → Airbnb Search & Listing Tools. <br><br> **Run Order:** <br> 1. Start Flights MCP Server: <br> `uv run python flights_mcp_server.py` <br> 2. Start Airbnb (A2A) Agent: <br> `uv run uvicorn airbnb_a2a:app --port 8090` <br> 3. Start Flight (A2A) Agent: <br> `uv run uvicorn flights_a2a:app --port 8091` <br> 4. Run the Orchestrator / Tester: <br> `uv run python tester.py` |
| Reddit × Google Docs <br> (A2A + MCP Demo) | A2A connects: Google Docs Agent ↔ Reddit Agent. <br> MCP connects: <br> • Reddit Agent → Reddit MCP Server → Reddit API (hot threads, comments, summaries) <br> • Google Docs Agent → Google Docs MCP Server → Google Docs & Drive API. <br><br> **Run Order:** <br> 1. Start Reddit (A2A) Agent: <br> `uv run uvicorn reddit_a2a:app --port 8130` <br> 2. Start Google Docs (A2A) Agent: <br> `uv run uvicorn docs_a2a:app --port 8131` <br> 3. Run A2A Client / Orchestrator: <br> `uv run python a2a_client.py` <br><br> ✅ *Flow:* User → Planner → Google Docs Agent → Reddit Agent → Reddit MCP → Google Docs MCP → Final Write to Doc |


</span>

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
GROQ_API_KEY=
GEMINI_API_KEY=

GMAIL_CLIENT_ID=
GMAIL_CLIENT_SECRET=

EXCHANGE_RATE_API_KEY=
RAPID_GOOGLE_FLIGHTS_API=


```


### 3. Install dependencies with uv

```bash
uv sync
```



