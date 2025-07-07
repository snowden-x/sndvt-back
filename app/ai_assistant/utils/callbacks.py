"""Custom LangChain callback handler for async streaming."""

import asyncio
from typing import Any, Dict, List
from uuid import UUID
from langchain.callbacks.base import AsyncCallbackHandler

class AsyncStreamCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming LLM responses to an asyncio.Queue."""

    def __init__(self):
        self.queue = asyncio.Queue()

    async def on_llm_new_token(
        self,
        token: str,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Put new tokens in the queue."""
        await self.queue.put(token)

    async def on_llm_end(
        self,
        response,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Signal the end of the stream."""
        await self.queue.put(None) # Sentinel value to indicate end of stream

    async def on_llm_error(
        self,
        error: Exception | KeyboardInterrupt,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        **kwargs: Any,
    ) -> None:
        """Signal an error in the stream."""
        await self.queue.put(None) 