# A2A Project 1: Travel Planner × Weather Stylist

## 1. Project Overview

This project demonstrates the **"Power Trio"** architecture: **Agentic AI + A2A + MCP**.
It solves a common problem: "I want to plan a trip, but I also need to know what to pack based on real-time weather."

Instead of building one massive script, we build two specialized micro-agents:

1. **Weather Stylist Agent:** An expert at checking the weather (via MCP) and recommending outfits.
2. **Travel Planner Agent:** An expert at itineraries who "knows" the Weather Stylist exists and calls it for help (via A2A).

**Goal:** Create a distributed system where a Travel Agent autonomously contacts a separate Weather Agent over HTTP to provide a unified response to the user.

---

## 2. Architecture & Communication Flow

This project uses a **Chained Communication Pattern**.

### The Chain of Command:

1. **User (Orchestrator):** Asks the **Travel Planner**: *"I'm going to Chennai."*
2. **Travel Planner (A2A Client):** Realizes it needs weather info. It sends an HTTP POST request to `http://localhost:8080` (The Weather Stylist).
3. **Weather Stylist (MCP Host):** Receives the request. It extracts "Chennai" and calls its local **Weather MCP Server** via stdio.
4. **Weather MCP Server:** Calls the **OpenWeather API**, gets the temp (`30°C`), and returns it.
5. **Weather Stylist:** Reasoning Step: *"30°C means light cotton clothes."* Returns this advice to the Travel Planner.
6. **Travel Planner:** Synthesizes the itinerary + packing list and returns the final answer to the user.

---

## 3. Code Breakdown

### A. The Weather MCP Server (`weather_mcp_server.py`)

* **Role:** The Tool Provider.
* **Tech:** `FastMCP` (Python).
* **Function:** `get_weather(city)` connects to OpenWeatherMap API.
* **Transport:** `stdio` (Standard Input/Output). It doesn't run on a port; it's a subprocess spawned by the Weather Stylist Agent.

### B. The Weather Stylist Agent (`weather_stylist_agent.py`)

* **Role:** The Specialist Service.
* **Tech:** `a2a-sdk` (Starlette/Uvicorn).
* **Key Logic:**
* **MCP Client:** Uses `mcp.client.stdio` to launch the MCP server subprocess and call `get_weather`.
* **LLM Logic:** Takes the raw weather JSON and generates a fashion-focused response ("Wear linen shirts").
* **Server:** Listens on port **8080**.



### C. The Travel Planner Agent (`travel_planner_agent.py`)

* **Role:** The Manager / Primary Interface.
* **Tech:** `a2a-sdk`, `httpx`.
* **Key Logic:**
* **A2A Client:** Uses `A2ACardResolver` to find the Weather Agent at `localhost:8080`.
* **Collaboration:** Sends a structured A2A message: *"User asking about Chennai. Give me outfit advice."*
* **Synthesis:** Merges the Stylist's response with its own travel knowledge.
* **Server:** Listens on port **8081**.



### D. The Client Trigger (`talk_to_agent.py`)

* **Role:** The User Interface.
* **Tech:** Python Script.
* **Action:** It's a simple script that sends the initial "Plan my trip" message to the Travel Planner (Port 8081) to kickstart the chain.

---

## 4. How to Run

This system requires **3 separate terminal windows** because you are running two independent servers and one client script.

### Prerequisites

* Ensure `OPENWEATHER_API_KEY` and `OPENAI_API_KEY` are in your `.env`.
* Install dependencies: `uv sync` (or install `a2a-sdk`, `mcp`, `aisuite`, `uvicorn` manually).

### Step 1: Start the Weather Stylist (Terminal 1)

This agent handles the "Hands" (MCP) part of the system.

```bash
uv run uvicorn weather_stylist_agent:app --port 8080
# Output: Uvicorn running on http://127.0.0.1:8080 (Press CTRL+C to quit)

```

### Step 2: Start the Travel Planner (Terminal 2)

This agent handles the "Brains" and A2A communication.

```bash
uv run uvicorn travel_planner_agent:app --port 8081
# Output: Uvicorn running on http://127.0.0.1:8081

```

### Step 3: Trigger the Conversation (Terminal 3)

This script acts as the user asking the question.

```bash
uv run talk_to_agent.py

```

### Expected Output (in Terminal 3)

```text
******************
Orchestrator: Hey I know a friend who can help you with this:
Travel Planner Agent
******************

=== Raw A2A response ===
{
  ...
  "result": {
    "role": "agent",
    "parts": [
      {
        "kind": "text",
        "text": "Trip to Chennai Summary: A vibrant cultural trip...\n
                 - Suggested Activities: Visit Marina Beach, Kapaleeshwarar Temple.\n
                 - Clothing: The Weather Stylist suggests light cottons as it is 30°C.\n"
      }
    ]
  }
}

```

---

## 5. Why is this "Agentic"?

* **Decoupling:** If the Weather API breaks, only the Stylist Agent needs fixing. The Travel Planner code remains untouched.
* **Scalability:** You could host the Weather Agent on a cloud server and the Travel Agent on your laptop, and they would still work together via HTTP.
* **Specialization:** Each agent uses a different system prompt specialized for its task (Fashion vs. Itinerary), leading to higher quality results than a single generic prompt.
