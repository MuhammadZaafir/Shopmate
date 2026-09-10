"""
main.py
-------
FastAPI server exposing ShopMate as a REST API.

Endpoints:
  POST /chat        -> send a message, get the agent's reply
  GET  /history/{id} -> fetch conversation history for a customer
  DELETE /history/{id} -> clear a customer's conversation memory
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.agent import run_agent
from app import memory

app = FastAPI(title="ShopMate - AI E-Commerce Customer Support Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    customer_id: str
    message: str


class ChatResponse(BaseModel):
    reply: str


@app.get("/")
def root():
    return {"status": "ShopMate agent is running"}


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")
    try:
        reply = run_agent(req.customer_id, req.message)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    return ChatResponse(reply=reply)


@app.get("/history/{customer_id}")
def get_history(customer_id: str):
    return {"customer_id": customer_id, "history": memory.get_history(customer_id, limit=100)}


@app.delete("/history/{customer_id}")
def clear_history(customer_id: str):
    memory.clear_history(customer_id)
    return {"status": "cleared", "customer_id": customer_id}
