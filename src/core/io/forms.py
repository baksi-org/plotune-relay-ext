from plotune_sdk import FormLayout


def dynamic_relay_form():
    form = FormLayout()

    # =========================
    # Source
    # =========================
    form.add_tab("Source") \
        .add_combobox(
            "source_type",
            "Source Type",
            [
                "websocket",
                "http_poll"
            ],
            default="websocket",
            required=True
        )

    # =========================
    # WebSocket Source
    # =========================
    form.add_tab("WebSocket") \
        .add_text(
            "ws_url",
            "WebSocket URL",
            default="ws://localhost:9000/ws"
        ) \
        .add_checkbox(
            "ws_auto_reconnect",
            "Auto Reconnect",
            default=True
        )

    # =========================
    # HTTP Poll Source
    # =========================
    form.add_tab("HTTP Poll") \
        .add_text(
            "http_url",
            "HTTP Endpoint",
            default="http://localhost:9000/data"
        ) \
        .add_text(
            "poll_interval",
            "Poll Interval (ms)",
            default="1000"
        )

    # =========================
    # JSON Mapping
    # =========================
    form.add_tab("JSON Mapping") \
        .add_text(
            "json_key_field",
            "Signal Key Field",
            default="key",
            required=True
        ) \
        .add_text(
            "json_value_field",
            "Value Field",
            default="value",
            required=True
        ) \
        .add_text(
            "json_time_field",
            "Timestamp Field",
            default="time"
        )

    # =========================
    # Actions
    # =========================
    from utils.constant_helper import get_config
    conf = get_config().get("connection", {})
    url = f"http://{conf.get('ip','127.0.0.1')}:{conf.get('port','')}"

    form.add_group("Actions") \
        .add_button(
            "start_relay",
            "Start Relay",
            {
                "method": "POST",
                "url": f"{url}/start",
                "payload_fields": [
                    "source_type",
                    "ws_url",
                    "ws_auto_reconnect",
                    "http_url",
                    "poll_interval",
                    "json_key_field",
                    "json_value_field",
                    "json_time_field"
                ],
            },
        )

    return form.to_schema()

from models import RelayInput


def form_dict_to_input(data: dict) -> RelayInput:
    def safe_int(val, default=None):
        try:
            return int(val)
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
