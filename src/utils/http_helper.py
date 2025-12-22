from urllib.parse import urlparse, urlunparse


def derive_http_base(url: str) -> str:
    """
    Derive the HTTP base URL from an HTTP or WebSocket URL.

    Examples:
        ws://localhost:9001/ws        -> http://localhost:9001
        wss://example.com/ws/signals  -> https://example.com
        http://localhost:9001/data    -> http://localhost:9001

    The path component is intentionally dropped.
    """
    parsed = urlparse(url)

    if parsed.scheme not in {"ws", "wss", "http", "https"}:
        raise ValueError(f"Unsupported URL scheme: {parsed.scheme}")

    scheme = "https" if parsed.scheme in {"wss", "https"} else "http"

    return urlunparse(
        (
            scheme,
            parsed.netloc,
            "",
            "",
            "",
            "",
        )
    )
