import asyncio
import httpx
from typing import Dict, List, Optional

from utils.http_helper import derive_http_base

class SocketListener:
    def __init__(
        self,
        url: str, # ws://localhost:9000/ws
        auto_reconnect: bool = True,
        mapping: Dict[str, str] | None = None,
    ):
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

    # ---------- signals (same lazy pattern) ----------

    @property
    def signals(self) -> Optional[List[str]]:
        if self._signals is None and self._signals_task is None:
            self._signals_task = asyncio.create_task(self._fetch_signals())
        return self._signals

    async def _fetch_signals(self) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self._http_base_url}/signals", timeout=10.0)
            resp.raise_for_status()
            self._signals = resp.json()

    async def wait_for_signals(self) -> List[str]:
        if self._signals is None:
            if self._signals_task is None:
                self._signals_task = asyncio.create_task(self._fetch_signals())
            await self._signals_task
        return self._signals

    # ---------- pub / sub ----------

    async def register(self, signal_name: str, q: asyncio.Queue[dict]) -> None:
        async with self._lock:
            queues = self.queue_handlers.setdefault(signal_name, [])
            if q not in queues:
                queues.append(q)

    async def unregister(self, signal_name: str, q: asyncio.Queue[dict]) -> None:
        async with self._lock:
            queues = self.queue_handlers.get(signal_name)
            if queues and q in queues:
                queues.remove(q)

    # ---------- websocket loop ----------

    async def listen(self) -> None:
        """
        Main websocket receive loop.
        Fan-outs messages to registered queues.
        """
        while not self._stop_event.is_set():
            try:
                async with httpx.AsyncClient() as client:
                    async with client.websocket_connect(
                        f"{self.url}{self.ws_endpoint}"
                    ) as ws:
                        async for message in ws.iter_json():
                            await self._dispatch(message)

            except asyncio.CancelledError:
                raise

            except Exception:
                if not self.auto_reconnect:
                    raise
                await asyncio.sleep(1)  # simple backoff

    async def _dispatch(self, message: dict) -> None:
        """
        Dispatch incoming websocket message to subscribers.
        Expected message shape example:
        {
            "signal": "temperature",
            "data": {...}
        }
        """
        signal_name = message.get("signal")
        payload = message.get("data", message)

        if not signal_name:
            return

        async with self._lock:
            for q in self.queue_handlers.get(signal_name, []):
                await q.put(payload)

    async def stop(self) -> None:
        self._stop_event.set()
