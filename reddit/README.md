# A2A Project 4: Reddit × Google Docs

## 1. Project Overview

This project builds an **Automated Research & Drafting Pipeline**. It solves the problem of "Research this topic and write a report about it" by using specialized agents to perform the reading and the writing separately.

**Goal:** An intelligent system that takes a user request (e.g., "Write about Marvel's upcoming movies"), assigns a **Reddit Agent** to find the latest community discussions, and then passes those findings to a **Google Docs Agent** which formats and writes the report into a live Google Doc.

---

## 2. Architecture & Communication Flow

This project features a **Research-Review-Revise Loop**.

### The Workflow:

1. **User (via `a2a_client.py`):** Asks: *"Write me content about Marvel's latest upcoming movies."*
2. **Initial Planner:** An Ollama (local LLM) agent analyzes the request and creates a step-by-step strategy: *Research -> Draft -> Review -> Finalize*.
3. **Google Docs Agent (The Lead):**
* Receives the plan.
* Realizes it lacks "knowledge," so it acts as an A2A Client.
* Calls the **Reddit Agent** via A2A (Port 8130) with the research query.


4. **Reddit Agent (The Researcher):**
* Uses its **Reddit MCP Server** to search subreddits like `r/marvelstudios`.
* Returns raw threads and comments to the Lead Agent.


5. **Google Docs Agent (The Writer):**
* Synthesizes the Reddit data into a coherent draft.
* Uses its **Google Docs MCP Server** to `create_doc()` and `write_to_doc()`.
* **Review Loop:** It sends the draft *back* to the Reddit Agent to "fact check" or find more specific details based on the draft's gaps.


6. **Final Output:** A URL to a Google Doc containing the fully researched report.

---

## 3. Google Cloud Platform (GCP) Setup Guide

To allow the Google Docs Agent to create files in your Drive, you need to enable the API.

### Step 1: Create/Select Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Select your project (or create `A2A-Docs-Agent`).

### Step 2: Enable APIs

Enable **two** APIs for this project:

1. **Google Docs API** (for reading/writing text).
2. **Google Drive API** (for creating files and setting permissions so they are publicly viewable).

### Step 3: OAuth Credentials

1. Go to **APIs & Services** -> **Credentials**.
2. Create **OAuth Client ID** (Type: Desktop App).
3. Download the JSON, rename it to `credentials.json`, and place it in the same folder as `google_docs_server.py`.

### Step 4: First Run

When you first run the server, it will open a browser window.

* **Sign in** with your Google Account.
* **Grant Permissions** (See, edit, create, and delete all of your Google Drive files).
* *Note:* The token will be saved locally as `token.json`, so you won't need to log in again.

---

## 4. Code Breakdown

### A. The Servers (MCP)

* **`google_docs_server.py`**:
* **Tools:** `create_doc`, `write_to_doc`, `read_doc`.
* **Permissions:** Specifically sets `role='reader', type='anyone'` on created files so the user can immediately click the link and view the report.


* **Reddit MCP (Config)**:
* Uses the community `mcp-server-reddit` via `uvx`. It provides tools to search subreddits and get conversation threads.



### B. The Agents (A2A)

* **`docs_a2a.py` (Port 8131)**: The Lead Agent. It orchestrates the entire workflow (`agents.workflow.workflow`). It decides when to stop researching and start writing.
* **`reddit_a2a.py` (Port 8130)**: The Research Agent. A specialized interface to Reddit that translates broad questions ("Marvel news") into specific tool calls.

### C. The Logic (`agents/workflow.py`)

This file defines the specific "Business Logic" of the collaboration:

```python
# 1. Research
redditResearch = await agent.invoke(user_input, "reddit")
# 2. Draft
googleDocsResponse = await agent.invoke(redditResearch, "googleDocs")
# 3. Review (Is this good enough?)
revisedResearch = await agent.invoke(revisedText, "reddit")
# 4. Final Polish
finalResponse = await agent.invoke(revisedResearch, "googleDocs")

```

This explicit loop ensures the content isn't just a copy-paste of a Reddit thread, but a curated document.

---

## 5. How to Run

This system requires **3 terminal windows**.

### Prerequisites

* `credentials.json` for Google Cloud in your project root.
* `reddit_config.json` defining the Reddit MCP server.
* Dependencies installed via `uv sync`.

### Step 1: Start Reddit Agent (Terminal 1)

```bash
uv run uvicorn reddit_a2a:app --port 8130

```

### Step 2: Start Google Docs Agent (Terminal 2)

```bash
uv run uvicorn docs_a2a:app --port 8131

```

*(On first run, check this terminal for the Google Login prompt!)*

### Step 3: Run the Client (Terminal 3)

```bash
uv run python a2a_client.py

```

### Expected Output

1. **Planner:** "Strategy: Search r/MarvelStudios for 'upcoming movies'..."
2. **Reddit Agent:** "Found threads about 'Thunderbolts', 'Fantastic Four cast'..."
3. **Google Docs Agent:** "✅ Created new document: Marvel Report. 🔗 Public link: [https://docs.google.com/](https://docs.google.com/)..."
4. **Final:** "Document updated with revised details."

---

## 6. Why is this "Agentic"?

* **Active Collaboration:** The Google Docs agent doesn't just passively receive data; it asks for *clarification*. If the first Reddit search is too vague, the workflow triggers a second, more targeted search (The Review Loop).
* **Persistent Memory:** By writing to a real Google Doc, the agent creates a persistent artifact. It can read what it wrote 5 minutes ago (`read_doc`) to avoid repeating itself.
* **Tool Chaining:** The output of a "Search Tool" (Reddit) becomes the input for a "Creative Tool" (Docs), bridged completely by autonomous agent negotiation.

---
