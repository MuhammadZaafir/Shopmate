"""
agent.py
--------
The ShopMate agent loop:
  1. Load conversation memory for the customer
  2. Send the conversation + tool definitions to Claude
  3. If Claude requests a tool call, execute it and feed the result back
  4. Repeat until Claude produces a final text answer
  5. Save the new turns to memory
"""

import os
import anthropic
from app.tools import TOOL_DEFINITIONS, TOOL_FUNCTIONS
from app import memory

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """You are ShopMate, an AI customer support agent for an online store.

You can help customers with:
- Product questions (availability, price, sizes) via get_product_info
- Order status / tracking via check_order_status
- Return eligibility and filing returns via check_return_eligibility and initiate_return
- Personalized recommendations via get_recommendations

Guidelines:
- Always use the tools to get real data — never guess prices, stock, or order status.
- Before calling initiate_return, first call check_return_eligibility, and make sure you have
  the customer's reason for the return.
- If a request is outside what your tools can do (e.g. billing disputes, complaints about
  a human agent, legal issues), say clearly that you'll escalate this to a human support
  agent, and do not attempt to resolve it yourself.
- Be concise, friendly, and precise. Confirm details (order IDs, product names) back to the
  customer when taking an action like initiating a return.
- If you're missing information needed to call a tool (like an order ID), ask the customer
  for it rather than guessing.
"""


def get_client():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("ANTHROPIC_API_KEY environment variable is not set.")
    return anthropic.Anthropic(api_key=api_key)


def run_agent(customer_id: str, user_message: str, max_tool_iterations: int = 5):
    """
    Run one full turn of the agent: takes a new user message, returns the
    agent's final text reply. Handles multi-step tool calling internally.
    """
    client = get_client()

    # 1. Load prior memory and append the new user message
    history = memory.get_history(customer_id)
    messages = history + [{"role": "user", "content": user_message}]
    memory.save_message(customer_id, "user", user_message)

    # 2. Agent loop: call Claude, execute tools, repeat until done
    for _ in range(max_tool_iterations):
        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        if response.stop_reason != "tool_use":
            # Final answer reached
            final_text = "".join(
                block.text for block in response.content if block.type == "text"
            )
            memory.save_message(customer_id, "assistant", final_text)
            return final_text

        # Model wants to call one or more tools
        tool_use_blocks = [b for b in response.content if b.type == "tool_use"]
        assistant_content = [b.model_dump() for b in response.content]
        messages.append({"role": "assistant", "content": assistant_content})

        tool_results = []
        for block in tool_use_blocks:
            func = TOOL_FUNCTIONS.get(block.name)
            if not func:
                result = {"error": f"Unknown tool: {block.name}"}
            else:
                try:
                    result = func(**block.input)
                except Exception as e:
                    result = {"error": str(e)}

            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": str(result)
            })

        messages.append({"role": "user", "content": tool_results})

    # If we hit the iteration cap without a final answer
    fallback = "I'm having trouble completing that request right now — let me connect you with a human agent."
    memory.save_message(customer_id, "assistant", fallback)
    return fallback
