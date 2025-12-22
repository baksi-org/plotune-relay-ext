import asyncio
import json
import logging
from typing import Dict, List, Optional

import httpx
import websockets

from utils.http_helper import derive_http_base

logger = logging.getLogger(__name__)


class SocketListener:
    """
    WebSocket-based signal listener.

    Listens to ws/{signal_name} endpoints and fan-outs incoming
    payloads to registered asyncio queues.
    """

    def __init__(
        self,
        url: str,
        auto_reconnect: bool = True,
        mapping: Optional[Dict[str, str]] = None,
    ) -> None:
        self.url = url.rstrip("/")
        self.auto_reconnect = auto_reconnect

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
        self._stop_event = asyncio.Event()

    # ------------------------------------------------------------------
    # Signals discovery (lazy, non-blocking)
    # ------------------------------------------------------------------

    @property
    def signals(self) -> Optional[List[str]]:
        if self._signals is None and self._signals_task is None:
            self._signals_task = asyncio.create_task(self._fetch_signals())
        return self._signals

    async def _fetch_signals(self) -> None:
        logger.debug("Fetching available signals")

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
    # WebSocket listen loop (HTTPPool.listen equivalent)
    # ------------------------------------------------------------------

    async def listen(self, signal_name: str) -> None:
        """
        Main WebSocket receive loop.

        Connects to ws/{signal_name}, receives JSON payloads and
        fan-outs them to registered queues.
        """
        ws_url = f"{self.url}/{signal_name}"
        logger.info("Starting WebSocket listener for '%s'", signal_name)
        logger.debug("WebSocket URL: %s", ws_url)

        while not self._stop_event.is_set():
            try:
                logger.debug("Connecting to WebSocket")

                async with websockets.connect(ws_url) as websocket:
                    logger.info(
                        "WebSocket connected for signal '%s'",
                        signal_name,
                    )

                    async for raw_message in websocket:
                        payload = json.loads(raw_message)

                        async with self._lock:
                            queues = self.queue_handlers.get(signal_name, [])
                            for queue in queues:
                                await queue.put(payload)

            except asyncio.CancelledError:
                logger.info(
                    "WebSocket listener cancelled for '%s'",
                    signal_name,
                )
                raise

            except Exception as exc:
                logger.warning(
                    "WebSocket error for '%s': %s",
                    signal_name,
                    exc,
                )

                if not self.auto_reconnect:
                    raise

                logger.info("Reconnecting in 1 second...")
                await asyncio.sleep(1)

        logger.info("WebSocket listener stopped for '%s'", signal_name)

    async def stop(self) -> None:
        logger.info("Stopping WebSocket listener")
        self._stop_event.set()
