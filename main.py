from __future__ import annotations

import json
import os
import traceback
from contextlib import asynccontextmanager
from typing import Any
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from dotenv import load_dotenv

from models.a2a import (
    JSONRPCRequest,
    JSONRPCResponse,
    MessageParams,
    ExecuteParams,
    A2AMessage,
    TaskResult,
)
from agents.optimizer_agent import OptimizerAgent

# Load environment variables
load_dotenv()

optimizer_agent: OptimizerAgent | None = None

# --- Initialize OptimizerAgent in lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    global optimizer_agent
    optimizer_agent = OptimizerAgent()
    yield
    # Optional cleanup


app = FastAPI(
    title="Fifth Grade Optimizer API",
    description="An A2A agent that makes text simple for children",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://telex.im", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------
# JSON-RPC endpoint
# -----------------------------
@app.post("/a2a/optimizer")
async def a2a_optimizer(request: Request) -> JSONResponse:
    try:
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Content-Type must be application/json"},
                },
            )

        body_bytes = await request.body()
        if not body_bytes:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Empty request body"},
                },
            )

        try:
            body: dict[str, Any] = json.loads(body_bytes)
        except json.JSONDecodeError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Invalid JSON in request body"},
                },
            )

        if body.get("jsonrpc") != "2.0" or "id" not in body:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {"code": -32600, "message": "Invalid JSON-RPC request"},
                },
            )

        rpc_req = JSONRPCRequest(**body)

        if rpc_req.method == "message/send":
            if not isinstance(rpc_req.params, MessageParams):
                raise ValueError("Invalid params for method 'message/send'")
            messages: list[A2AMessage] = [rpc_req.params.message]
        elif rpc_req.method == "execute":
            if not isinstance(rpc_req.params, ExecuteParams):
                raise ValueError("Invalid params for method 'execute'")
            messages = rpc_req.params.messages
        else:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "error": {"code": -32601, "message": "Method not found"},
                },
            )

        if not optimizer_agent:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "jsonrpc": "2.0",
                    "id": rpc_req.id,
                    "error": {"code": -32603, "message": "Optimizer agent not initialized"},
                },
            )

        result: TaskResult = await optimizer_agent.process_messages(
            messages=messages,
            context_id=getattr(rpc_req.params, "contextId", None),
            task_id=getattr(rpc_req.params, "taskId", None),
            config=getattr(rpc_req.params, "configuration", None),
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=JSONRPCResponse(id=rpc_req.id, result=result).model_dump(),
        )

    except Exception as exc:
        print("FULL TRACEBACK:\n", traceback.format_exc())
        err_id = body.get("id") if "body" in locals() and isinstance(body, dict) else None
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "jsonrpc": "2.0",
                "id": err_id,
                "error": {"code": -32603, "message": "Internal error", "data": {"details": str(exc)}},
            },
        )


# -----------------------------
# Simple optimizer endpoint
# -----------------------------
@app.post("/optimize")
async def optimize_text(request: Request) -> dict[str, Any]:
    try:
        data = await request.json()
    except Exception:
        return {"error": "Invalid JSON"}

    text = data.get("text", "").strip()
    if not text:
        return {"error": "No text provided."}

    if not optimizer_agent:
        return {"error": "Optimizer agent not initialized."}

    dummy_msg = A2AMessage(role="user", parts=[{"kind": "text", "text": text}])
    result = await optimizer_agent.process_messages([dummy_msg])
    simplified = result.artifacts[0].parts[0].text if result.artifacts else "Failed to simplify."

    return {"original": text, "optimized": simplified}


# -----------------------------
# Health check
# -----------------------------
@app.get("/")
async def health() -> dict[str, str]:
    return {"status": "healthy", "agent": "fifth_grade_optimizer"}


# -----------------------------
# Manifest JSON endpoint
# -----------------------------
@app.get("/a2a/manifest")
async def get_manifest() -> dict[str, Any]:
    """Returns the workflow/manifest JSON for Telex-style integrations."""
    return {
        "active": True,
        "category": "utilities",
        "description": "Simplifies any text for 5th-grade kids using Gemini AI",
        "id": "fifth-grade-opt-hng-v1",
        "long_description": (
            "You are a friendly text simplifier for kids. Take any complex sentence and rewrite it "
            "in short, fun, easy words. Use analogies like 'like a superhero' or 'like a magic chef'. "
            "Keep it under 150 words. If no text is given, ask: 'What do you want me to simplify?'\n\n"
            "Example:\nInput: Photosynthesis is the process by which plants convert sunlight into energy.\n"
            "Output: Plants eat sunlight to make food—like magic solar chefs!"
        ),
        "name": "fifth_grade_optimizer",
        "nodes": [
            {
                "id": "optimizer_node",
                "name": "Kid Text Simplifier",
                "parameters": {
                    "method": "POST",
                    "headers": {"Content-Type": "application/json"},
                    "body_template": {
                        "jsonrpc": "2.0",
                        "id": "{{messageId}}",
                        "method": "message/send",
                        "params": {
                            "message": {
                                "role": "user",
                                "parts": [{"kind": "text", "text": "{{input}}"}]
                            },
                            "configuration": {"blocking": True}
                        }
                    }
                },
                "position": [400, 200],
                "type": "http",
                "typeVersion": 1,
                "url": "https://hngbackend3.onrender.com/a2a/optimizer"
            }
        ],
        "pinData": {},
        "settings": {"executionOrder": "v1"},
        "short_description": "Turns hard text into kid-friendly words"
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 5001))
    uvicorn.run("main:app", host="0.0.0.0", port=8000)
