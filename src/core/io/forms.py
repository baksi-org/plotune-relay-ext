from plotune_sdk import FormLayout

from models import RelayInput
from utils.constant_helper import get_config


def dynamic_relay_form() -> dict:
    """
    Build and return the dynamic relay configuration form schema.
    """
    form = FormLayout()

    # ------------------------------------------------------------------
    # Source
    # ------------------------------------------------------------------
    (
        form.add_tab("Source").add_combobox(
            "source_type",
            "Source Type",
            ["websocket", "http_poll"],
            default="websocket",
            required=True,
        )
    )

    # ------------------------------------------------------------------
    # WebSocket Source
    # ------------------------------------------------------------------
    (
        form.add_tab("WebSocket")
        .add_text(
            "ws_url",
            "WebSocket URL",
            default="ws://localhost:9000/ws",
        )
        .add_checkbox(
            "ws_auto_reconnect",
            "Auto Reconnect",
            default=True,
        )
    )

    # ------------------------------------------------------------------
    # HTTP Poll Source
    # ------------------------------------------------------------------
    (
        form.add_tab("HTTP Poll")
        .add_text(
            "http_url",
            "HTTP Endpoint",
            default="http://localhost:9000/data",
        )
        .add_text(
            "poll_interval",
            "Poll Interval (ms)",
            default="1000",
        )
    )

    # ------------------------------------------------------------------
    # JSON Mapping
    # ------------------------------------------------------------------
    (
        form.add_tab("JSON Mapping")
        .add_text(
            "json_key_field",
            "Signal Key Field",
            default="key",
            required=True,
        )
        .add_text(
            "json_value_field",
            "Value Field",
            default="value",
            required=True,
        )
        .add_text(
            "json_time_field",
            "Timestamp Field",
            default="time",
        )
    )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    connection = get_config().get("connection", {})
    host = connection.get("ip", "127.0.0.1")
    port = connection.get("port", "")
    base_url = f"http://{host}:{port}"

    (
        form.add_group("Actions").add_button(
            "start_relay",
            "Start Relay",
            {
                "method": "POST",
                "url": f"{base_url}/start",
                "payload_fields": [
                    "source_type",
                    "ws_url",
                    "ws_auto_reconnect",
                    "http_url",
                    "poll_interval",
                    "json_key_field",
                    "json_value_field",
                    "json_time_field",
                ],
            },
        )
    )

    return form.to_schema()


def form_dict_to_input(data: dict) -> RelayInput:
    """
    Convert submitted form data into a RelayInput model.
    """

    def safe_int(value, default: int | None = None) -> int | None:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    return RelayInput(
        source_type=data.get("source_type"),
        ws_url=data.get("ws_url"),
        ws_auto_reconnect=bool(data.get("ws_auto_reconnect", True)),
        http_url=data.get("http_url"),
        poll_interval=safe_int(data.get("poll_interval"), 1000),
        json_key_field=data.get("json_key_field", "key"),
        json_value_field=data.get("json_value_field", "value"),
        json_time_field=data.get("json_time_field", "time"),
    )
