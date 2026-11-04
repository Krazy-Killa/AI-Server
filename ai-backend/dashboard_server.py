"""Serve the static dashboard with browser security headers.

Replaces ``python -m http.server`` for the dashboard: only the dashboard
entry page and its ``css/`` and ``js/`` assets are served, directory listings
are disabled, and every response carries a restrictive Content-Security-Policy.
"""

from __future__ import annotations

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import posixpath
from pathlib import Path
from urllib.parse import unquote, urlsplit

# Google Fonts are still imported by css/style.css; remove those two origins
# when the fonts are self-hosted. API access is limited to the dashboard origin
# or port 8000 of the host serving the dashboard.
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'none'",
        "script-src 'self'",
        "style-src 'self' https://fonts.googleapis.com",
        "font-src https://fonts.gstatic.com",
        "img-src 'self' data:",
        "connect-src 'self' http://*:8000 https://*:8000 ws://*:8000 wss://*:8000",
        "base-uri 'none'",
        "form-action 'none'",
        "frame-ancestors 'none'",
    )
)

SECURITY_HEADERS = {
    "Content-Security-Policy": CONTENT_SECURITY_POLICY,
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "same-origin",
    "Cache-Control": "no-store",
}

_SERVED_PREFIXES = ("/css/", "/js/")
_SERVED_PAGES = ("/", "/index.html")


class DashboardRequestHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        for name, value in SECURITY_HEADERS.items():
            self.send_header(name, value)
        super().end_headers()

    def send_head(self):
        path = posixpath.normpath(unquote(urlsplit(self.path).path))
        if path not in _SERVED_PAGES and not path.startswith(_SERVED_PREFIXES):
            self.send_error(404)
            return None
        return super().send_head()

    def list_directory(self, path):
        self.send_error(404)
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bind", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    parser.add_argument("--directory", type=Path, default=Path.cwd())
    args = parser.parse_args()

    handler = partial(DashboardRequestHandler, directory=str(args.directory))
    server = ThreadingHTTPServer((args.bind, args.port), handler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
