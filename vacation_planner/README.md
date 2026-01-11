# A2A Project 3: Vacation Planner × Airbnb

## 1. Project Overview

This project implements a **Smart Routing Architecture** for travel planning. Unlike the previous projects where the communication chain was fixed, this system uses an **Intelligent Router** to decide which agents need to be involved based on the user's intent.

**Goal:** A "Flight Agent" acts as the primary concierge. If you ask for just flights, it handles it alone. If you ask for "flights and a place to stay," it autonomously routes the accommodation request to a specialized "Airbnb Agent" via A2A, aggregates the results, and presents a complete itinerary.

---

## 2. Architecture & Communication Flow

This project features a **Hub-and-Spoke** model with dynamic routing.

### The Dynamic Flow:

1. **User (via `tester.py`):** Sends a request: *"I need to find some stays in Chennai for Jan 1 2026."* to the **Flight Agent** (Port 8091).
2. **Flight Agent (The Hub):**
* **Routing Logic:** Instead of blindly calling the other agent, it consults a **Router LLM** (`routing.py`).
* **Decision:** The Router analyzes the prompt and returns `{"flightAgent": false, "airbnbAgent": true}`.


3. **Orchestration:**
* Since `airbnbAgent` is True, the Flight Agent acts as an A2A Client.
* It sends the specific accommodation prompt to the **Airbnb Agent** at `http://localhost:8090`.


4. **Airbnb Agent (The Spoke):**
* Receives the request.
* Uses its **Airbnb MCP Server** (Node.js) to search for live listings.
* Returns the listing data to the Flight Agent.


5. **Flight Agent (Finalizer):**
* Since `flightAgent` was False, it skips its own flight search tools.
* It aggregates the Airbnb response and returns the final answer to the user.



---

## 3. Code Breakdown

### A. The Primary Agent: Flight Agent (`flights_a2a.py`)

* **Role:** Manager & Router.
* **MCP:** Connects to `flights_mcp_server.py` (Python FastMCP) to search Google Flights (via RapidAPI).
* **A2A Logic:**
* Discovers the Airbnb Agent via `A2ACardResolver`.
* Uses `agents.routing.routing()` to perform a "Traffic Cop" check on the user input.
* If the user asks for *both* flights and stays, the Router splits the prompt into two distinct tasks (`flightPrompt` and `airBnbPrompt`) to ensure each agent gets clean instructions.



### B. The Secondary Agent: Airbnb Agent (`airbnb_a2a.py`)

* **Role:** Accommodation Specialist.
* **MCP:** Connects to the external `@openbnb/mcp-server-airbnb` using `npx` (Node.js).
* **Logic:** It is a "pure" agent; it doesn't know about flights. It just receives a location/date, searches Airbnb, and returns results.

### C. The Brains: Router & LLMs

* **`agents/routing.py`:** A dedicated prompt that outputs strict JSON (`{"flightAgent": bool, "airbnbAgent": bool}`) to control the flow.
* **`agents/flight_llm.py` & `agents/airbnb_llm.py`:** Specialized logic modules that handle the tool execution loops for their respective domains.

---

## 4. How to Run

This system requires **3 terminal windows**.

### Prerequisites

* **Node.js:** Required for the Airbnb MCP server (`npx`).
* **API Keys:**
* `OPENAI_API_KEY` (or `GROQ_API_KEY`/`OLLAMA` depending on config).
* `RAPID_GOOGLE_FLIGHTS_API` (for the Flight MCP server).


* **Dependencies:** `uv sync` (plus `pip install aisuite` if using the `agents` folder structure).

### Step 1: Start the Airbnb Agent (Terminal 1)

This agent listens on port 8090.

```bash
uv run uvicorn airbnb_a2a:app --port 8090

```

*Note: This will automatically spin up the Airbnb Node.js MCP server in the background.*

### Step 2: Start the Flight Agent (Terminal 2)

This agent listens on port 8091.

```bash
uv run uvicorn flights_a2a:app --port 8091

```

*Note: This acts as the main entry point.*

### Step 3: Run the Tester (Terminal 3)

Send a request to the Flight Agent.

```bash
uv run python tester.py

```

### Expected Output

```text
******************
Orchestrator: Hey I know a friend who can help you with this:
AirBnb Agent
******************

Routing decision: {'flightAgent': False, 'airbnbAgent': True}

... (Airbnb Agent searches MCP) ...

=== Raw A2A response ===
Here are 5 stays in Chennai for Jan 1 2026:
1. Luxury Apt near Marina Beach ($45/night)
2. ...

```

---

## 5. Why is this "Agentic"?

1. **Dynamic Decision Making:** The system isn't hard-coded to always call every agent. It **saves money and time** by using a Router to decide which agents are actually needed for the specific request.
2. **Prompt Separation:** If you ask a single LLM to "Find flights and hotels," it often forgets one or mixes them up. By splitting the prompt (`flightPrompt` vs `airBnbPrompt`) via the Router, each agent gets a focused task, increasing reliability.
3. **Tool Abstraction:** The Flight Agent doesn't need to know *how* to search Airbnb (API keys, endpoints, etc.); it just knows *who* to ask.
