# A2A Project 2: Currency & Stocks Pair

## 1. Project Overview

This project demonstrates a **collaborative Financial Mesh**. It consists of two independent agents that can act as both "Server" and "Client" to each other, depending on the user's entry point.

1. **Currency Pair Agent:** Specializes in Forex conversion (via ExchangeRate-API).
2. **Stock Data Agent:** Specializes in Equity data (via Yahoo Finance).

**Goal:** Provide a comprehensive financial analysis by combining data from two distinct domains. If you ask for a stock analysis in a foreign currency, the agents collaborate to fetch the stock data *and* calculate the exchange impact.

---

## 2. Architecture & Communication Flow

Unlike the linear "Chain" in Project 1, this project represents a **Bi-Directional Mesh**.

### The Collaborative Flow:

1. **User (via `test.py`):** Sends a complex request to the **Currency Agent**:
* *"I have 100 USD, want to convert to INR, and I want to analyze NVDA stock from Jan-Jun 2024."*


2. **Currency Agent (Agent 1):**
* **Local Action:** Calls its own **Currency MCP Server** to convert 100 USD  8,300 INR.
* **A2A Action:** Recognizes stock parameters (`symbol`, `dates`) in the input. It calls the **Stock Agent** via HTTP (Port 8082).


3. **Stock Agent (Agent 2):**
* **Local Action:** Receives the request, calls its **Stock MCP Server** (yfinance) to get OHLCV data.
* **Return:** Sends a summary of the stock movement back to Agent 1.


4. **Currency Agent (Final Synthesis):**
* Uses its internal LLM (AISuite) to combine the FX data and the Stock data into a cohesive financial report.



---

## 3. Code Breakdown

### A. The Tool Servers (MCP)

* **`currency_mcp_server.py`**:
* **Tool:** `convert_currency_with_api`.
* **Tech:** `FastMCP` + `requests`.
* **Logic:** Hits `v6.exchangerate-api.com` to get real-time rates.


* **`stock_data_server.py`**:
* **Tool:** `get_stock_data`.
* **Tech:** `FastMCP` + `yfinance` + `pandas`.
* **Logic:** Downloads historical data, cleans column names (flattening MultiIndex headers), and returns a stringified DataFrame.



### B. The Agents (A2A)

* **`currency_pair_agent.py` (Port 8081)**:
* **Role:** The Forex Expert.
* **MCP Logic:** Uses `MultiServerMCPClient` to talk to the local python script `currency_mcp_server.py`.
* **A2A Logic:** Has a method `_call_stock_agent` that sends JSON payloads to `localhost:8082`.
* **Brain:** Uses `aisuite` (OpenAI/GPT-4o) to write the final summary.


* **`stock_data_agent.py` (Port 8082)**:
* **Role:** The Market Analyst.
* **MCP Logic:** Connects to `stock_data_server.py`.
* **A2A Logic:** Uniquely, this agent *also* has code to call the Currency Agent (`_call_currency_agent`). This means if the user started here, the flow would work in reverse!



### C. The Orchestrator (`test.py`)

* Sends a structured JSON payload disguised as a text message. This is a common pattern in A2A: structuring the natural language channel to pass strict data types.

---

## 4. How to Run

This requires **3 terminal windows**.

### Prerequisites

* Get a free key from [ExchangeRate-API](https://www.exchangerate-api.com/) and add `EXCHANGE_RATE_API_KEY` to your `.env`.
* Ensure `OPENAI_API_KEY` is set.
* Install: `uv sync` (includes `yfinance`, `pandas`, `requests`).

### Step 1: Start Currency Agent (Terminal 1)

```bash
uv run uvicorn currency_pair_agent:app --port 8081
# Listens on 8081 for A2A requests

```

### Step 2: Start Stock Agent (Terminal 2)

```bash
uv run uvicorn stock_data_agent:app --port 8082
# Listens on 8082 for A2A requests

```

### Step 3: Run the Test Client (Terminal 3)

```bash
uv run python test.py

```

### Expected Output

The output will be a JSON object containing the final synthesized response from Agent 1:

```json
{
  "result": {
    "role": "agent",
    "parts": [
      {
        "kind": "text",
        "text": "Financial Analysis:\n\n1. FX Overview: 100 USD converts to approx 8,350 INR.\n\n2. Stock Trend: NVDA showed significant growth from Jan to June 2024, starting at $48 and peaking around $130.\n\n3. Takeaway: The strong dollar combined with NVDA's growth makes this a high-value entry point for INR-based investors."
      }
    ]
  }
}

```

---

## 5. Why is this "Agentic"?

1. **Modular Intelligence:** The Stock Agent doesn't know how to convert currency, and the Currency Agent doesn't know how to query Yahoo Finance. They rely on each other's expertise.
2. **Structured Protocol:** Even though they "speak" HTTP, they pass structured JSON payloads (`symbol`, `amount`) embedded in the messages, simulating how software APIs talk but with the flexibility of LLM parsing.
3. **Redundancy & Resilience:** Since both agents use `aisuite` for reasoning, either one can act as the "Lead Agent" to summarize the data, depending on which one the user contacts first.
