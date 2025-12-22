import asyncio
import logging
from time import time
from typing import Any, Dict, List, Optional, TypeAlias, Union
from uuid import uuid4

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from plotune_sdk import PlotuneRuntime

from utils import get_config, get_custom_config
from core.io.http_reader import HTTPPool
from core.io.socket_listener import SocketListener

ListenerType: TypeAlias = Union[HTTPPool, SocketListener]

logger = logging.getLogger(__name__)


class RelayAgent:
    """
    RelayAgent proxies HTTP polling or WebSocket signal sources
    to Plotune Core clients via WebSocket streaming.
    """

    def __init__(self) -> None:
        self.config = get_config()
        self.custom_config = get_custom_config()

        self._runtime: Optional[PlotuneRuntime] = None
        self._api: Optional[FastAPI] = None

        self.http_pools: Dict[str, HTTPPool] = {}
        self.socket_listeners: Dict[str, SocketListener] = {}
        self.listeners: List[Dict[str, ListenerType]] = []

        self.tasks: List[asyncio.Task] = []
        self._last_added: Optional[ListenerType] = None

        self._build_custom_routes()
        self._register_events()

    # ------------------------------------------------------------------
    # Runtime & API wiring
    # ------------------------------------------------------------------

    def _register_events(self) -> None:
        """
        Register runtime events after runtime initialization.
        """
        server = self.runtime.server

        server.on_event("/form")(self._handle_form)
        server.on_event("/fetch-meta")(self.fetch_signals)
        server.on_event("/form", method="POST")(self._new_connection)
        server.on_ws()(self.stream)

        logger.debug("Runtime events registered")

    @property
    def api(self) -> FastAPI:
        if not self._api:
            self._api = self.runtime.server.api
        return self._api

    @property
    def runtime(self) -> PlotuneRuntime:
        if self._runtime:
            return self._runtime

        connection = self.config.get("connection", {})
        target = connection.get("target", "127.0.0.1")
        port = connection.get("target_port", "8000")
        core_url = f"http://{target}:{port}"

        self._runtime = PlotuneRuntime(
            ext_name=self.config.get("id"),
            core_url=core_url,
            config=self.config,
        )

        return self._runtime

    # ------------------------------------------------------------------
    # WebSocket stream handler (client-facing)
    # ------------------------------------------------------------------

    async def stream(
        self,
        signal_name: str,
        websocket: WebSocket,
        data: Any,
    ) -> None:
        logger.info("Client requested signal '%s'", signal_name)

        queue: asyncio.Queue[dict] = asyncio.Queue()
        handler: Optional[ListenerType] = None

        # Find listener that provides this signal
        for entry in self.listeners:
            for listener in entry.values():
                try:
                    signals = listener.signals
                except Exception:
                    signals = None

                if signals and signal_name in signals:
                    handler = listener
                    break
            if handler:
                break

        if not handler:
            logger.warning("No listener found for signal '%s'", signal_name)
            await websocket.send_json({"error": "No listener for signal"})
            await websocket.close()
            return

        await handler.register(signal_name, queue)
        task = asyncio.create_task(handler.listen(signal_name))
        self.tasks.append(task)

        try:
            while True:
                try:
                    payload = await queue.get()
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("Queue get error: %s", exc)
                    continue
                finally:
                    queue.task_done()

                try:
                    await websocket.send_json(
                        {
                            "timestamp": payload.get("time", time()),
                            "value": payload.get("value"),
                        }
                    )
                    await asyncio.sleep(0.03)

                except WebSocketDisconnect:
                    logger.info(
                        "Client disconnected from signal '%s'",
                        signal_name,
                    )
                    break

                except Exception as exc:
                    logger.warning(
                        "WebSocket send error for '%s': %s",
                        signal_name,
                        exc,
                    )
                    break

        finally:
            try:
                await handler.unregister(signal_name, queue)
            except Exception as exc:
                logger.warning("Unregister error: %s", exc)

            if not task.done():
                task.cancel()
                try:
                    await task
                except Exception:
                    pass

            logger.info("Unsubscribed from signal '%s'", signal_name)

    # ------------------------------------------------------------------
    # Metadata & form handling
    # ------------------------------------------------------------------

    async def fetch_signals(self, data: dict) -> Dict[str, List[str]]:
        if not self._last_added:
            logger.warning("No listener available for signal discovery")
            return {"headers": []}

        signals = await self._last_added.wait_for_signals()

        if not signals:
            logger.warning("No signals discovered")
            return {"headers": []}

        logger.debug("Fetched signals: %s", signals)
        return {"headers": signals}

    async def _new_connection(self, data: dict) -> Dict[str, str]:
        from core.io.forms import form_dict_to_input

        form = form_dict_to_input(data)
        connection_id = uuid4().hex[:6]

        listener: Optional[ListenerType] = None

        logger.info(
            "Creating new connection (%s) type=%s",
            connection_id,
            form.source_type,
        )

        if form.source_type == "http_poll":
            listener = HTTPPool(
                form.http_url,
                int(form.poll_interval),
                mapping={
                    "key": form.json_key_field,
                    "time": form.json_time_field,
                    "value": form.json_value_field,
                },
            )
            self.http_pools[connection_id] = listener

        elif form.source_type == "websocket":
            listener = SocketListener(
                form.ws_url,
                form.ws_auto_reconnect,
                mapping={
                    "key": form.json_key_field,
                    "time": form.json_time_field,
                    "value": form.json_value_field,
                },
            )
            self.socket_listeners[connection_id] = listener

        if not listener:
            raise ValueError("Unsupported listener type")

        self.listeners.append({connection_id: listener})
        self._last_added = listener

        logger.info(
            "Listener %s added with id=%s",
            listener.__class__.__name__,
            connection_id,
        )

        return {"status": "success", "message": "Form saved!"}

    async def _handle_form(self, data: dict) -> Any:
        from core.io.forms import dynamic_relay_form

        logger.debug("Dynamic relay form requested")
        return dynamic_relay_form()

    # ------------------------------------------------------------------
    # Custom API routes
    # ------------------------------------------------------------------

    def _build_custom_routes(self) -> None:
        async def help_route() -> Dict[str, str]:
            return {
                "extension": "Relay",
                "description": (
                    "This extension proxies data from WebSocket or HTTP sources "
                    "to Plotune Core. "
                    "HTTP polling fetches /signals and polls /data/{signal_name}. "
                    "WebSocket mode fetches /signals and connects to /ws/{signal_name}. "
                    "Default payload format: {key: str, time: float, value: float}."
                ),
            }

        self.api.add_api_route("/help", help_route, methods=["GET"])

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        logger.info("Starting RelayAgent")
        self.runtime.start()
