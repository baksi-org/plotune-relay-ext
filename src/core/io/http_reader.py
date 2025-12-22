import asyncio
import httpx
from typing import Dict, List, Optional


class HTTPPool:
    def __init__(
        self,
        url: str,
        interval: int,
        endpoint: str,
        mapping: Dict[str, str] | None = None,
    ):
        self.url = url.rstrip("/")
        self.interval = interval
        self.endpoint = endpoint if endpoint.startswith("/") else f"/{endpoint}" # to fetch data from eq: "/data"
        self.mapping = mapping or {
            "key": "key",
            "time": "time",
            "value": "value",
        }

        self._signals: Optional[List[str]] = None
        self._signals_task: Optional[asyncio.Task] = None

        self.queue_handlers: Dict[str, List[asyncio.Queue[dict]]] = {}
        self._lock = asyncio.Lock()

    @property
    def signals(self) -> Optional[List[str]]:
        """
        Lazy, non-blocking accessor.
        Triggers async fetch on first access.
        """
        if self._signals is None and self._signals_task is None:
            self._signals_task = asyncio.create_task(self._fetch_signals())
        return self._signals

    async def _fetch_signals(self) -> None:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{self.url}/signals", timeout=10.0)
            resp.raise_for_status()
            self._signals = resp.json().get("signals")

    async def wait_for_signals(self) -> List[str]:
        if self._signals is None:
            if self._signals_task is None:
                self._signals_task = asyncio.create_task(self._fetch_signals())
            await self._signals_task
        return self._signals

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

    async def listen(self, signal_name: str) -> None:
        async with httpx.AsyncClient() as client:
            try:
                while True:
                    resp = await client.get(
                        f"{self.url}{self.endpoint}/{signal_name}",
                        timeout=10.0,
                    )
                    resp.raise_for_status()
                    payload = resp.json()

                    async with self._lock:
                        for q in self.queue_handlers.get(signal_name, []):
                            await q.put(payload)

                    await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                raise
