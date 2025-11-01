# agents/optimizer_agent.py
from __future__ import annotations

import os
from typing import List, Optional
from uuid import uuid4

import httpx
from dotenv import load_dotenv

from models.a2a import (
    A2AMessage,
    Artifact,
    MessageConfiguration,
    MessagePart,
    TaskResult,
    TaskStatus,
)

load_dotenv()


class OptimizerAgent:
    """Simplifies text using Gemini 2.0 Flash with retry & fallback."""

    def __init__(self) -> None:
        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing in .env")

        # CORRECT MODEL (2025): gemini-2.0-flash
        self.model_name = "gemini-2.0-flash"
        self.endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent"
        )

        # Optional: List models on startup (uncomment to debug)
        # import asyncio
        # asyncio.create_task(self._log_available_models())

    async def _log_available_models(self) -> None:
        """Debug helper – prints all available models."""
        url = "https://generativelanguage.googleapis.com/v1beta/models"
        params = {"key": self.api_key}
        async with httpx.AsyncClient(timeout=10) as client:
            try:
                res = await client.get(url, params=params)
                if res.status_code == 200:
                    models = [m["name"] for m in res.json().get("models", [])]
                    print("Available Gemini models:", models)
                else:
                    print("Failed to list models:", res.text)
            except Exception as e:
                print("Error listing models:", e)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    async def process_messages(
        self,
        messages: List[A2AMessage],
        context_id: Optional[str] = None,
        task_id: Optional[str] = None,
        config: Optional[MessageConfiguration] = None,
    ) -> TaskResult:
        context_id = context_id or str(uuid4())
        task_id = task_id or str(uuid4())

        if not messages:
            raise ValueError("No messages provided")

        user_msg = messages[-1]
        input_text = next(
            (p.text.strip() for p in user_msg.parts if p.kind == "text" and p.text),
            "",
        )
        if not input_text:
            raise ValueError("No text content in message")

        simplified = await self._call_gemini_with_retry(input_text)

        # Build response
        response_msg = A2AMessage(
            role="agent",
            parts=[MessagePart(kind="text", text=simplified)],
            taskId=task_id,
        )

        artifact = Artifact(
            name="simplified_text",
            parts=[MessagePart(kind="text", text=simplified)],
        )

        history = messages + [response_msg]

        return TaskResult(
            id=task_id,
            contextId=context_id,
            status=TaskStatus(state="completed", message=response_msg),
            artifacts=[artifact],
            history=history,
        )

    # ------------------------------------------------------------------
    # Gemini Call with Retry (handles 429, 500, etc.)
    # ------------------------------------------------------------------
    async def _call_gemini_with_retry(self, text: str, max_retries: int = 3) -> str:
        prompt = (
            "Rewrite the following text in very simple language for a 5th-grade child. "
            "Use short sentences. Keep the meaning the same.\n\n"
            f"{text}"
        )

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}
        payload = {"contents": [{"parts": [{"text": prompt}]}]}

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(max_retries):
                try:
                    resp = await client.post(
                        self.endpoint, headers=headers, params=params, json=payload
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        return data["candidates"][0]["content"]["parts"][0]["text"]

                    if resp.status_code == 429:  # Rate limit
                        wait = 2 ** attempt
                        print(f"Rate limited. Retrying in {wait}s...")
                        await httpx._utils.sleep(wait)
                        continue

                    print(f"Gemini API error {resp.status_code}: {resp.text}")
                    if attempt == max_retries - 1:
                        return "Sorry, I couldn’t simplify the text right now."

                except httpx.RequestError as e:
                    print(f"Network error (attempt {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        return "Sorry, I couldn’t reach the simplification service."
                    await httpx._utils.sleep(2 ** attempt)

        return "Sorry, something went wrong while simplifying."