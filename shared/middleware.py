import logging
from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable


class LoggingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable,
        event,
        data: Dict[str, Any]
    ) -> Awaitable[Any]:
        logging.info(f"Update: {event}")
        return await handler(event, data)
