import asyncio
import logging
from typing import Dict, List, Optional

import httpx

from utils.http_helper import derive_http_base

logger = logging.getLogger(__name__)


class HTTPPool:
    """
    HTTP polling-based signal listener.

    Periodically polls /data/{signal_name} endpoints and fan-outs
    received payloads to registered asyncio queues.
    """

    def __init__(
        self,
        url: str,
        interval: int,
        mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.interval = interval

        self.mapping = mapping or {
            "key": "key",
            "time": "time",
            "value": "value",
        }

        self._http_base_url = derive_http_base(self.url)
        self._signals: Optional[List[str]] = None
        self._signals_task: Optional[asyncio.Task] = None

        self.queue_handlers: Dict[str, List[asyncio.Queue[dict]]] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Signals discovery (lazy, non-blocking)
    # ------------------------------------------------------------------

    @property
    def signals(self) -> Optional[List[str]]:
        """
        Lazy accessor for available signals.

        Triggers async discovery on first access.
        """
        if self._signals is None and self._signals_task is None:
            self._signals_task = asyncio.create_task(self._fetch_signals())
        return self._signals

    async def _fetch_signals(self) -> None:
        logger.debug("Fetching available signals via HTTP")

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self._http_base_url}/signals",
                timeout=10.0,
            )
            response.raise_for_status()
            self._signals = response.json().get("signals")

        logger.info("Discovered signals: %s", self._signals)

    async def wait_for_signals(self) -> List[str]:
        if self._signals is None:
            if self._signals_task is None:
                self._signals_task = asyncio.create_task(self._fetch_signals())
            await self._signals_task

        return self._signals or []

    # ------------------------------------------------------------------
    # Pub / Sub API
    # ------------------------------------------------------------------

    async def register(self, signal_name: str, queue: asyncio.Queue[dict]) -> None:
        async with self._lock:
            queues = self.queue_handlers.setdefault(signal_name, [])
            if queue not in queues:
                queues.append(queue)
                logger.debug(
                    "Queue registered for signal '%s' (total=%d)",
                    signal_name,
                    len(queues),
                )

    async def unregister(self, signal_name: str, queue: asyncio.Queue[dict]) -> None:
        async with self._lock:
            queues = self.queue_handlers.get(signal_name)
            if queues and queue in queues:
                queues.remove(queue)
                logger.debug(
                    "Queue unregistered for signal '%s' (remaining=%d)",
                    signal_name,
                    len(queues),
                )

    # ------------------------------------------------------------------
    # HTTP polling loop
    # ------------------------------------------------------------------

    async def listen(self, signal_name: str) -> None:
        """
        Main HTTP polling loop.

        Periodically fetches /data/{signal_name} and fan-outs
        payloads to registered queues.
        """
        url = f"{self.url}/{signal_name}"
        logger.info("Starting HTTP polling for '%s'", signal_name)
        logger.debug("Polling URL: %s", url)

        async with httpx.AsyncClient() as client:
            try:
                while True:
                    response = await client.get(url, timeout=10.0)
                    response.raise_for_status()
                    payload = response.json()

                    async with self._lock:
                        for queue in self.queue_handlers.get(signal_name, []):
                            await queue.put(payload)

                    await asyncio.sleep(self.interval / 1000)

            except asyncio.CancelledError:
                logger.info(
                    "HTTP polling cancelled for '%s'",
                    signal_name,
                )
                raise
