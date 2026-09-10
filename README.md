# ShopMate — AI E-Commerce Customer Support Agent

An agentic AI that handles end-to-end customer support for an online store:
product questions, order tracking, returns, and personalized recommendations —
built with **Tool Calling + Memory** as its core agentic capabilities.

## Use Cases

| Scenario | Example |
|---|---|
| Product queries | "Is the blue running shoes available in size 9?" |
| Order status | "Where's my order #4521?" |
| Returns | "I want to return this jacket, it doesn't fit" |
| Recommendations | "What accessories go with the laptop I bought?" |
| Continuity | Customer returns later and asks "any update on my return?" — agent recalls prior context |

## Architecture

```
Customer message
      │
      ▼
 ┌─────────────┐      loads/saves       ┌───────────────┐
 │   agent.py  │◄──────────────────────►│  memory.py     │
 │ (agent loop)│                         │ (SQLite store) │
 └──────┬──────┘                         └───────────────┘
        │ calls Claude API (tool use)
        ▼
 ┌─────────────┐
 │  Claude API │
 └──────┬──────┘
        │ requests a tool call
        ▼
 ┌─────────────┐
 │  tools.py   │──► products.json / orders.json / customers.json / returns.json
 └─────────────┘
```

**Flow:**
1. Customer sends a message via the API (`/chat`) or Streamlit UI.
2. `agent.py` loads the customer's prior conversation history from SQLite memory.
3. The message + history + tool definitions are sent to Claude.
4. If Claude decides it needs data (stock levels, order status, etc.), it requests
   a tool call. `agent.py` executes the corresponding Python function in `tools.py`
   and feeds the result back to Claude.
5. This repeats until Claude has enough information to give a final answer.
6. The new turn is saved to memory so future messages have context.

## Tech Stack

| Layer | Choice |
|---|---|
| LLM / reasoning | Claude API (`claude-sonnet-4-6`) with tool use |
| Tool layer | Python functions simulating product/order/returns backend |
| Memory | SQLite (conversation history per customer) |
| Backend | FastAPI |
| Frontend | Streamlit chat UI |
| Data | Mock JSON datasets (products, orders, customers) |

## Project Structure

```
shopmate/
├── app/
│   ├── main.py       # FastAPI server (REST API)
│   ├── agent.py       # Core agent loop (Claude + tool calling + memory)
│   ├── tools.py        # Tool functions + schemas
│   └── memory.py      # SQLite-based conversation memory
├── data/
│   ├── products.json  # Mock product catalog
│   ├── orders.json    # Mock orders
│   └── customers.json # Mock customers + purchase history
├── frontend/
│   └── streamlit_app.py  # Chat UI
├── requirements.txt
├── .env.example
└── README.md
```

## Setup

1. **Clone and install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set your Anthropic API key**
   ```bash
   cp .env.example .env
   # edit .env and add your key
   export ANTHROPIC_API_KEY=your_api_key_here   # or use a .env loader
   ```

3. **Run the Streamlit chat UI (recommended for demoing)**
   ```bash
   streamlit run frontend/streamlit_app.py
   ```

4. **Or run the FastAPI backend**
   ```bash
   uvicorn app.main:app --reload
   ```
   Then send requests to `POST http://localhost:8000/chat`:
   ```json
   { "customer_id": "C100", "message": "Where's my order 4521?" }
   ```

## Try These Sample Prompts

- "Is the blue running shoes available in size 9?"
- "Where's my order 4521?"
- "I want to return order 4522, product P007, it's the wrong item"
- "What accessories go with my laptop?"
- Follow up later: "Any update on that return?" — the agent remembers.

## Mock Test Data

- **Customer C100** (Ananya Rao) — has orders `4521` (Denim Jacket, Shipped) and
  `4522` (Laptop, Delivered).
- **Customer C200** (Rahul Mehta) — has order `4530` (Headphones, Out for Delivery).

## 5-Day Build Plan (for course submission)

- **Day 1** — Use case defined, tool schemas designed, mock data created.
- **Day 2** — Core agent loop with Claude tool calling (intent → tool selection).
- **Day 3** — Memory added (conversation + purchase history continuity).
- **Day 4** — Returns workflow + recommendations, multi-turn edge cases handled.
- **Day 5** — Streamlit UI polish, end-to-end testing, demo prep.

## Notes / Limitations

- Data is stored in local JSON/SQLite files to simulate a real backend — swap
  `tools.py` functions for real API calls to go to production.
- The agent escalates to "a human agent" for anything outside its five tools
  (e.g. billing disputes) rather than guessing.
- No authentication is implemented — `customer_id` is passed directly for
  simplicity in this student project.
