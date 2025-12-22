from plotune_sdk import PlotuneRuntime

from utils import get_config, get_custom_config
from fastapi import FastAPI
from typing import Dict, Optional, List,Union, TypeAlias


from uuid import uuid4

from core.io.http_reader import HTTPPool
from core.io.socket_listener import SocketListener

ListenerType: TypeAlias = Union['HTTPPool', 'SocketListener']

class RelayAgent:
    def __init__(self):
        self.config = get_config()
        self.custom_config = get_custom_config()
        self._runtime: Optional[PlotuneRuntime] = None
        self._api:Optional[FastAPI] = None

        self.http_pools:Dict[str, HTTPPool] = {}
        self.sock_listener:Dict[str, SocketListener] = {}
        self.listeners:List[Dict[str, ListenerType]] = []
        self._last_added: Optional[ListenerType] = None

        self._build_custom_routes()
        self._register_events()

    def _register_events(self):
        """
        Register runtime events AFTER runtime initialization.
        """
        self.runtime.server.on_event("/form")(self._handle_form)
        self.runtime.server.on_event("/fetch-meta")(self.fetch_signals)
        self.runtime.server.on_event("/form", method="POST")(self._new_connection)
    
    async def fetch_signals(self, data: dict):
        if not self._last_added or not hasattr(self._last_added, "signals"):
            return {"headers": []}
        
        return {
            "headers": [
                self._last_added.signals
            ]
        }

    async def _new_connection(self, data:dict):
        from core.io.forms import form_dict_to_input
        form = form_dict_to_input(data)
        connection_id = uuid4().hex[:6]

        listener = None

        if form.source_type == "http_poll":
            listener = HTTPPool(
                form.http_url,
                int(form.poll_interval),
                mapping={"key":form.json_key_field, "time":form.json_time_field, "value":form.json_value_field}
            )
            self.http_pools[connection_id] = listener

        if form.source_type == "websocket":
            listener =SocketListener(
                form.ws_url,
                form.ws_auto_reconnect,
                mapping={"key":form.json_key_field, "time":form.json_time_field, "value":form.json_value_field}
            )
            self.sock_listener[connection_id] = listener
        
        if not listener:
            raise Exception("No available listener type")
        
        self.listeners.append({connection_id:listener})
        self._last_added = listener
        
        print(self._last_added.__class__," added to listeners")



    async def _handle_form(self, data: dict):
        from core.io.forms import dynamic_relay_form
        print("Dynamic Relay Form Requested")
        return dynamic_relay_form()
    
    def _build_custom_routes(self):

        async def help_route():
            return {
                "extension": "Relay",
                "description": ""
                "This extension proxies data from WebSocket or HTTP sources to Plotune Core."
                "HTTP Poolign : Requests /signals to fetch available signals."
                r"Sends pooling to /data/{signal_name}"
                "Websocket : Requests /signals to fetch available signals."
                "Connects /fetch/{signal_name} as a client to collect signals"
                r"{key:str, time:float, value:float} is the default format for all"
            }
        
        self.api.add_api_route("/help", help_route, methods=["GET"])

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
        target = connection.get('target', '127.0.0.1')
        port = connection.get('target_port', '8000')
        _core_url = f"http://{target}:{port}"
        self._runtime = PlotuneRuntime(
            ext_name=self.config.get("id"),
            core_url=_core_url,
            config=self.config,
        )
        return self._runtime

    def start(self):
        self.runtime.start()