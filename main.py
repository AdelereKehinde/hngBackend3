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

# Initialize OptimizerAgent in lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    global optimizer_agent
    optimizer_agent = OptimizerAgent()  # Initialize the agent
    yield
    # Optional: Cleanup, e.g., close HTTPX client

app = FastAPI(
    title="Fifth Grade Optimizer API",
    description="An A2A agent that makes text simple for children",
    version="1.0.0",
    lifespan=lifespan,
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://telex.im", "*"],  # Add telex.im as allowed origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/a2a/optimizer")
async def a2a_optimizer(request: Request) -> JSONResponse:
    """JSON-RPC 2.0 endpoint – now bulletproof against bad payloads."""
    try:
        # --------------------------------------------------------------
        # 1. Validate Content-Type
        # --------------------------------------------------------------
        content_type = request.headers.get("content-type", "")
        if not content_type.startswith("application/json"):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32600,
                        "message": "Content-Type must be application/json",
                    },
                },
            )

        # --------------------------------------------------------------
        # 2. Read raw body (prevents JSONDecodeError on empty body)
        # --------------------------------------------------------------
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

        # --------------------------------------------------------------
        # 3. Parse JSON safely
        # --------------------------------------------------------------
        try:
            body: dict[str, Any] = json.loads(body_bytes)
        except json.JSONDecodeError as e:
            print(f"JSON Parse Error: {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32600, "message": "Invalid JSON in request body"},
                },
            )

        # --------------------------------------------------------------
        # 4. Basic JSON-RPC validation
        # --------------------------------------------------------------
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

        # --------------------------------------------------------------
        # 5. Extract messages based on method
        # --------------------------------------------------------------
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

        # --------------------------------------------------------------
        # 6. Run optimizer agent
        # --------------------------------------------------------------
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

    except Exception as exc:  # pylint: disable=broad-except
        print("FULL TRACEBACK:\n", traceback.format_exc())
        err_id = body.get("id") if "body" in locals() and isinstance(body, dict) else None
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "jsonrpc": "2.0",
                "id": err_id,
                "error": {
                    "code": -32603,
                    "message": "Internal error",
                    "data": {"details": str(exc)},
                },
            },
        )


@app.get("/")
async def health() -> dict[str, str]:
    return {"status": "healthy", "agent": "fifth_grade_optimizer"}


@app.post("/optimize")
async def optimize_text(request: Request) -> dict[str, Any]:
    """Simple demo endpoint – uses the real agent now."""
    try:
        data = await request.json()
    except Exception:
        return {"error": "Invalid JSON"}

    text = data.get("text", "").strip()
    if not text:
        return {"error": "No text provided."}

    # Ensure optimizer agent is initialized
    if not optimizer_agent:
        return {"error": "Optimizer agent not initialized."}

    # Reuse the agent for real simplification
    dummy_msg = A2AMessage(
        role="user",
        parts=[{"kind": "text", "text": text}],
    )
    result = await optimizer_agent.process_messages([dummy_msg])
    simplified = result.artifacts[0].parts[0].text if result.artifacts else "Failed to simplify."

    return {"original": text, "optimized": simplified}


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 5001))
    uvicorn.run(app, host="127.0.0.1", port=port)
