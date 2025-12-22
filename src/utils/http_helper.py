from urllib.parse import urlparse, urlunparse

def derive_http_base(ws_url: str) -> str:
    parsed = urlparse(ws_url)

    if parsed.scheme not in ("ws", "wss", "http", "https"):
        raise ValueError(f"Unsupported scheme: {parsed.scheme}")

    scheme = "https" if parsed.scheme == "wss" else "http"

    # WebSocket path intentionally dropped
    return urlunparse((
        scheme,
        parsed.netloc,
        "",
        "",
        "",
        "",
    ))