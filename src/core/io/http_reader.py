import asyncio
import httpx
from typing import Dict, List, Optional


from utils.http_helper import derive_http_base

class HTTPPool:
    def __init__(
        self,
        url: str,
        interval: int,
        mapping: Dict[str, str] | None = None,
    ):
        self.url = url.rstrip("/")
        
        self._http_base_url = derive_http_base(self.url)
        self.interval = interval
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
            resp = await client.get(f"{self._http_base_url}/signals", timeout=10.0)
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
        print("Listenning",signal_name)
        async with httpx.AsyncClient() as client:
            try:
                while True:
                    print("await response")
                    resp = await client.get(
                        f"{self.url}/{signal_name}",
                        timeout=10.0,
                    )
                    
                    resp.raise_for_status()
                    payload = resp.json()

                    print("Payload : ",payload)

                    async with self._lock:
                        print("handler put queue")
                        for q in self.queue_handlers.get(signal_name, []):
                            print(signal_name,"handler",q)
                            await q.put(payload)
                            print("Putted")

                    await asyncio.sleep(self.interval/1000)

            except asyncio.CancelledError:
                raise
