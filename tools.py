"""
tools.py
--------
Backend "tools" that the ShopMate agent can call. In a real system these would
hit live databases / APIs (product catalog service, order management system,
returns service, recommendation engine). Here they read from local JSON files
to simulate that backend for the project.
"""

import json
import os
from datetime import datetime, date

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def _load(filename):
    with open(os.path.join(DATA_DIR, filename), "r") as f:
        return json.load(f)


def _save(filename, data):
    with open(os.path.join(DATA_DIR, filename), "w") as f:
        json.dump(data, f, indent=2)


# ---------------------------------------------------------------------------
# Tool 1: Product info / search
# ---------------------------------------------------------------------------
def get_product_info(query: str):
    """Search the product catalog by name, category, or tag."""
    products = _load("products.json")
    query_lower = query.lower()
    matches = [
        p for p in products
        if query_lower in p["name"].lower()
        or query_lower in p["category"].lower()
        or any(query_lower in t for t in p["tags"])
    ]
    if not matches:
        return {"found": False, "message": f"No products found matching '{query}'."}
    return {"found": True, "products": matches}


# ---------------------------------------------------------------------------
# Tool 2: Order status
# ---------------------------------------------------------------------------
def check_order_status(order_id: str):
    """Look up the live shipping status of an order."""
    orders = _load("orders.json")
    order = next((o for o in orders if o["order_id"] == str(order_id)), None)
    if not order:
        return {"found": False, "message": f"No order found with ID {order_id}."}
    return {"found": True, "order": order}


# ---------------------------------------------------------------------------
# Tool 3: Return eligibility check
# ---------------------------------------------------------------------------
def check_return_eligibility(order_id: str, product_id: str = None):
    """Check whether an item in an order is still eligible for return."""
    orders = _load("orders.json")
    order = next((o for o in orders if o["order_id"] == str(order_id)), None)
    if not order:
        return {"eligible": False, "message": f"No order found with ID {order_id}."}

    order_date = datetime.strptime(order["order_date"], "%Y-%m-%d").date()
    days_since_order = (date.today() - order_date).days
    window = order.get("return_window_days", 30)

    if order["status"] not in ("Delivered", "Shipped", "Out for Delivery"):
        return {"eligible": False, "message": f"Order status is '{order['status']}', not yet eligible for return."}

    if days_since_order > window:
        return {
            "eligible": False,
            "message": f"Return window of {window} days has expired ({days_since_order} days since order)."
        }

    item = None
    if product_id:
        item = next((i for i in order["items"] if i["product_id"] == product_id), None)
        if not item:
            return {"eligible": False, "message": f"Product {product_id} not found in order {order_id}."}

    return {
        "eligible": True,
        "message": f"Order {order_id} is eligible for return ({window - days_since_order} days remaining).",
        "item": item
    }


# ---------------------------------------------------------------------------
# Tool 4: Initiate a return
# ---------------------------------------------------------------------------
def initiate_return(order_id: str, product_id: str, reason: str):
    """File a return request for an item in an order."""
    eligibility = check_return_eligibility(order_id, product_id)
    if not eligibility["eligible"]:
        return {"success": False, "message": eligibility["message"]}

    returns_file = "returns.json"
    path = os.path.join(DATA_DIR, returns_file)
    returns = []
    if os.path.exists(path):
        with open(path, "r") as f:
            returns = json.load(f)

    return_id = f"RTN{len(returns) + 1001}"
    new_return = {
        "return_id": return_id,
        "order_id": order_id,
        "product_id": product_id,
        "reason": reason,
        "status": "Requested",
        "requested_date": date.today().isoformat()
    }
    returns.append(new_return)
    with open(path, "w") as f:
        json.dump(returns, f, indent=2)

    return {
        "success": True,
        "return_id": return_id,
        "message": f"Return {return_id} has been initiated for product {product_id} in order {order_id}. "
                   f"Reason logged: '{reason}'. You'll receive pickup/refund instructions by email."
    }


# ---------------------------------------------------------------------------
# Tool 5: Recommendations
# ---------------------------------------------------------------------------
def get_recommendations(customer_id: str = None, context: str = None):
    """Recommend products based on purchase history and/or a text context (e.g. 'laptop accessories')."""
    products = _load("products.json")
    customers = _load("customers.json")

    candidate_tags = set()

    if customer_id:
        customer = next((c for c in customers if c["customer_id"] == customer_id), None)
        if customer:
            purchased_ids = customer["purchase_history"]
            purchased_products = [p for p in products if p["product_id"] in purchased_ids]
            for p in purchased_products:
                candidate_tags.update(p["tags"])

    if context:
        candidate_tags.update(context.lower().split())

    if not candidate_tags:
        # fallback: just return top 3 products
        return {"recommendations": products[:3]}

    scored = []
    for p in products:
        score = len(candidate_tags.intersection(set(p["tags"])))
        if score > 0:
            scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    recs = [p for _, p in scored[:4]]

    if not recs:
        recs = products[:3]

    return {"recommendations": recs}


# ---------------------------------------------------------------------------
# Tool schema definitions (for Claude tool-calling / function calling)
# ---------------------------------------------------------------------------
TOOL_DEFINITIONS = [
    {
        "name": "get_product_info",
        "description": "Search the product catalog by name, category, or tag (e.g. 'shoes', 'laptop', 'headphones'). Returns matching products with price and stock info.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term for the product"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "check_order_status",
        "description": "Check the live shipping/delivery status of a customer's order by order ID.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID, e.g. '4521'"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "check_return_eligibility",
        "description": "Check if an order (or a specific item within it) is still eligible for return based on the return window.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "The order ID"},
                "product_id": {"type": "string", "description": "Optional specific product ID within the order"}
            },
            "required": ["order_id"]
        }
    },
    {
        "name": "initiate_return",
        "description": "File a return request for a specific product within an order. Only call this after confirming eligibility and getting the customer's reason.",
        "input_schema": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string"},
                "product_id": {"type": "string"},
                "reason": {"type": "string", "description": "Customer's stated reason for the return"}
            },
            "required": ["order_id", "product_id", "reason"]
        }
    },
    {
        "name": "get_recommendations",
        "description": "Get personalized product recommendations based on the customer's purchase history and/or a text context like 'laptop accessories'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "customer_id": {"type": "string", "description": "Optional customer ID to base recommendations on purchase history"},
                "context": {"type": "string", "description": "Optional text describing what kind of products the customer wants recommendations for"}
            },
            "required": []
        }
    }
]

TOOL_FUNCTIONS = {
    "get_product_info": get_product_info,
    "check_order_status": check_order_status,
    "check_return_eligibility": check_return_eligibility,
    "initiate_return": initiate_return,
    "get_recommendations": get_recommendations,
}
