from dataclasses import dataclass
from typing import Optional, Literal


@dataclass
class RelayInput:
    source_type: Literal["websocket", "http_poll"]
    ws_url: Optional[str] = None
    ws_auto_reconnect: bool = True

    http_url: Optional[str] = None
    poll_interval: int = 1000  # ms

    json_key_field: str = "key"
    json_value_field: str = "value"
    json_time_field: Optional[str] = "time"
