from typing import Dict, List, Callable, Any
import asyncio
from concurrent.futures import ThreadPoolExecutor
import logging

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._handlers: Dict[str, List[Callable]] = {}
        self._executor = ThreadPoolExecutor(max_workers=4)

    def subscribe(self, event_type: str, handler: Callable):
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable):
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    async def publish(self, event_type: str, data: Dict[str, Any]):
        if event_type not in self._handlers:
            return

        tasks = []
        for handler in self._handlers[event_type]:
            if asyncio.iscoroutinefunction(handler):
                tasks.append(asyncio.create_task(handler(data)))
            else:
                task = asyncio.get_event_loop().run_in_executor(
                    self._executor, self._run_sync_handler, handler, data
                )
                tasks.append(task)

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    handler_name = self._handlers[event_type][i].__name__
                    logger.error(f"Error in event handler {handler_name}: {result}")

    def _run_sync_handler(self, handler: Callable, data: Dict[str, Any]):
        try:
            handler(data)
        except Exception as e:
            logger.error(f"Error in sync event handler {handler.__name__}: {e}")
            raise

event_bus = EventBus()