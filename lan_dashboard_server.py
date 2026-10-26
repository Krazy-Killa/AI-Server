"""Serve only the dashboard's public assets over HTTPS on the LAN."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ssl
from urllib.parse import unquote, urlsplit

from lan_test_config import PROJECT_ROOT, load_lan_test_config

ASSETS = {
    "/": (PROJECT_ROOT / "index.html", "text/html; charset=utf-8"),
    "/index.html": (PROJECT_ROOT / "index.html", "text/html; charset=utf-8"),
    "/css/style.css": (PROJECT_ROOT / "css" / "style.css", "text/css; charset=utf-8"),
    "/js/app.js": (PROJECT_ROOT / "js" / "app.js", "text/javascript; charset=utf-8"),
    "/js/backend-logs.js": (
        PROJECT_ROOT / "js" / "backend-logs.js",
        "text/javascript; charset=utf-8",
    ),
    "/js/operations.js": (
        PROJECT_ROOT / "js" / "operations.js",
        "text/javascript; charset=utf-8",
    ),
    "/js/system-monitor.js": (
        PROJECT_ROOT / "js" / "system-monitor.js",
        "text/javascript; charset=utf-8",
    ),
    "/js/ui-preferences.js": (
        PROJECT_ROOT / "js" / "ui-preferences.js",
        "text/javascript; charset=utf-8",
    ),
}


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        self._send_asset()

    def do_HEAD(self) -> None:
        self._send_asset(include_body=False)

    def _send_asset(self, include_body: bool = True) -> None:
        asset_path = unquote(urlsplit(self.path).path)
        asset = ASSETS.get(asset_path)
        if asset is None:
            self.send_error(404)
            return

        file_path, content_type = asset
        try:
            content = file_path.read_bytes()
        except OSError:
            self.send_error(500, "Dashboard asset could not be read.")
            return

        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.end_headers()
        if include_body:
            self.wfile.write(content)


def main() -> None:
    config = load_lan_test_config()
    server = ThreadingHTTPServer((config.host, 8001), DashboardHandler)
    tls_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    tls_context.load_cert_chain(
        certfile=str(config.certificate),
        keyfile=str(config.private_key),
    )
    server.socket = tls_context.wrap_socket(server.socket, server_side=True)
    print(f"Dashboard available at {config.dashboard_origin}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping LAN dashboard.", flush=True)
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
