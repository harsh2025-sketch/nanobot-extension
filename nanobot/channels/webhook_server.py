"""Minimal webhook server helper for channel integrations."""

from __future__ import annotations

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Optional
from urllib.parse import urlparse, parse_qs


class WebhookServer:
    """HTTP webhook server with a simple JSON POST interface."""

    def __init__(
        self,
        host: str,
        port: int,
        path: str,
        on_event: Callable[[dict[str, Any]], Any],
        verify_token: str | None = None,
        loop: asyncio.AbstractEventLoop | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.path = path
        self.verify_token = verify_token
        self._on_event = on_event
        self._loop = loop
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the webhook server in a background thread."""
        if self._server:
            return

        server = self

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler naming
                if server.path and self.path.split("?")[0] != server.path:
                    self.send_response(404)
                    self.end_headers()
                    return

                if server.verify_token:
                    query = urlparse(self.path).query
                    params = parse_qs(query)
                    token = params.get("token", [None])[0]
                    header_token = self.headers.get("X-Verify-Token")
                    if token != server.verify_token and header_token != server.verify_token:
                        self.send_response(401)
                        self.end_headers()
                        return

                content_length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(content_length or 0)
                try:
                    payload = json.loads(raw.decode("utf-8") or "{}")
                except json.JSONDecodeError:
                    payload = {}

                try:
                    if asyncio.iscoroutinefunction(server._on_event):
                        if server._loop:
                            asyncio.run_coroutine_threadsafe(server._on_event(payload), server._loop)
                        else:
                            asyncio.run(server._on_event(payload))
                    else:
                        server._on_event(payload)
                except Exception:
                    pass

                self.send_response(200)
                self.end_headers()

            def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
                return

        self._server = ThreadingHTTPServer((self.host, self.port), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the webhook server."""
        if not self._server:
            return
        self._server.shutdown()
        self._server.server_close()
        self._server = None
        self._thread = None
