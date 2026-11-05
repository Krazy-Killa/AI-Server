import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
NGINX_CONF = REPOSITORY_ROOT / "deploy" / "nginx" / "ai-server.conf"
CERT_SCRIPT = REPOSITORY_ROOT / "scripts" / "proxmox" / "make-lan-cert.sh"


def location_block(config: str, selector: str) -> str:
    match = re.search(
        rf"location {re.escape(selector)} \{{(.*?)\n    \}}", config, re.DOTALL
    )
    if match is None:
        raise AssertionError(f"Missing location {selector}")
    return match.group(1)


class LanProxyContractTests(unittest.TestCase):
    def setUp(self):
        self.config = NGINX_CONF.read_text(encoding="utf-8")

    def test_only_loopback_upstreams_are_used(self):
        upstreams = re.findall(r"proxy_pass\s+(\S+);", self.config)
        self.assertTrue(upstreams)
        for upstream in upstreams:
            self.assertRegex(upstream, r"^http://127\.0\.0\.1:(8000|8001)$")
        self.assertNotIn("11434", self.config)
        self.assertNotIn("8080", self.config)

    def test_routes_map_to_the_right_services(self):
        self.assertIn("http://127.0.0.1:8000", location_block(self.config, "/api/"))
        self.assertIn("http://127.0.0.1:8000", location_block(self.config, "/ws/"))
        self.assertIn("http://127.0.0.1:8001", location_block(self.config, "/"))
        login = location_block(self.config, "= /api/auth/login")
        self.assertIn("limit_req zone=ai_server_login", login)
        self.assertIn("http://127.0.0.1:8000", login)

    def test_websocket_upgrade_is_forwarded(self):
        websocket = location_block(self.config, "/ws/")
        self.assertIn("proxy_set_header Upgrade $http_upgrade;", websocket)
        self.assertIn("proxy_set_header Connection", websocket)

    def test_tls_is_modern_and_http_redirects_to_https(self):
        self.assertIn("listen 443 ssl;", self.config)
        self.assertIn("ssl_protocols       TLSv1.2 TLSv1.3;", self.config)
        self.assertIn("ssl_session_tickets off;", self.config)
        self.assertIn("return 301 https://$host$request_uri;", self.config)
        self.assertRegex(self.config, r"Strict-Transport-Security")
        self.assertNotIn("TLSv1 ", self.config)
        self.assertNotIn("TLSv1.1", self.config)

    def test_proxy_does_not_leak_or_widen_access(self):
        self.assertIn("server_tokens off;", self.config)
        self.assertIn("client_max_body_size", self.config)
        self.assertNotIn("autoindex on", self.config)
        self.assertNotIn("add_header Access-Control-Allow-Origin", self.config)
        self.assertNotIn("proxy_set_header Origin", self.config)
        self.assertNotRegex(self.config, r"listen\s+(8000|8001|8080|11434)\b")

    def test_certificate_script_is_conservative(self):
        script = CERT_SCRIPT.read_text(encoding="utf-8")
        self.assertIn("set -euo pipefail", script)
        self.assertIn("umask 077", script)
        self.assertIn("refusing to overwrite", script)
        self.assertIn("nameConstraints=critical", script)
        self.assertIn("CA:FALSE", script)
        self.assertIn("extendedKeyUsage=serverAuth", script)
        self.assertNotIn("-nodes", script)
        self.assertNotIn("-passout", script)
        self.assertNotIn("cat \"$OUT/server.key\"", script)

    def test_lab_bundle_includes_proxy_files(self):
        builder = (
            REPOSITORY_ROOT / "scripts" / "proxmox" / "build-lab-bundle.py"
        ).read_text(encoding="utf-8")
        self.assertIn('"deploy/nginx/ai-server.conf"', builder)
        self.assertIn('"scripts/proxmox/make-lan-cert.sh"', builder)


if __name__ == "__main__":
    unittest.main()
