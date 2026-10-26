import re
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
QUADLET_ROOT = REPOSITORY_ROOT / "deploy" / "quadlet"
CONTAINERFILE = REPOSITORY_ROOT / "Containerfile"


def read_sections(path: Path) -> dict[str, dict[str, list[str]]]:
    sections: dict[str, dict[str, list[str]]] = {}
    current_section: dict[str, list[str]] | None = None
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        section_match = re.fullmatch(r"\[([^\]]+)\]", line)
        if section_match:
            current_section = sections.setdefault(section_match.group(1), {})
            continue
        if current_section is None or "=" not in line:
            raise AssertionError(f"Invalid Quadlet line in {path.name}: {line}")
        key, value = line.split("=", 1)
        current_section.setdefault(key, []).append(value)
    return sections


class QuadletContractTests(unittest.TestCase):
    def setUp(self):
        self.backend = read_sections(
            QUADLET_ROOT / "ai-server-backend.container"
        )
        self.dashboard = read_sections(
            QUADLET_ROOT / "ai-server-dashboard.container"
        )

    def test_services_share_image_and_container_identity(self):
        for unit in (self.backend, self.dashboard):
            self.assertEqual(unit["Container"]["Image"], ["localhost/ai-server:lab"])
            self.assertEqual(unit["Container"]["User"], ["999:990"])
            self.assertEqual(unit["Container"]["UserNS"], ["keep-id"])
            self.assertNotIn("Install", unit)

        containerfile = CONTAINERFILE.read_text(encoding="utf-8")
        self.assertIn("USER 999:990", containerfile)
        self.assertIn(
            "COPY --chown=999:990 ai-backend/gpu/*.py "
            "/opt/ai-server/ai-backend/gpu/",
            containerfile,
        )
        self.assertRegex(
            containerfile,
            r"(?m)^FROM .+@sha256:[0-9a-f]{64}$",
        )
        self.assertNotRegex(containerfile, r"(?m)^COPY\s+\.\s")

    def test_published_ports_are_loopback_only(self):
        self.assertEqual(
            self.backend["Container"]["PublishPort"], ["127.0.0.1:8000:8000"]
        )
        self.assertEqual(
            self.dashboard["Container"]["PublishPort"], ["127.0.0.1:8001:8001"]
        )

    def test_services_have_health_checks_and_bounded_restart_policy(self):
        for unit, port in ((self.backend, 8000), (self.dashboard, 8001)):
            container = unit["Container"]
            service = unit["Service"]
            self.assertEqual(service["Restart"], ["on-failure"])
            self.assertEqual(service["RestartSec"], ["5s"])
            self.assertEqual(unit["Unit"]["StartLimitIntervalSec"], ["60s"])
            self.assertEqual(unit["Unit"]["StartLimitBurst"], ["3"])
            self.assertEqual(
                container["HealthCmd"],
                ["python /opt/ai-server/ai-backend/container_healthcheck.py"],
            )
            self.assertEqual(
                container["Environment"],
                [
                    "HOME=/var/lib/ai-server",
                    f"AI_SERVER_HEALTH_URL=http://127.0.0.1:{port}/"
                    + ("openapi.json" if port == 8000 else ""),
                ],
            )

    def test_containers_are_hardened_and_application_data_is_persistent(self):
        for unit in (self.backend, self.dashboard):
            container = unit["Container"]
            self.assertEqual(container["ReadOnly"], ["true"])
            self.assertEqual(container["ReadOnlyTmpfs"], ["true"])
            self.assertEqual(container["NoNewPrivileges"], ["true"])
            self.assertEqual(container["DropCapability"], ["all"])

        backend_volumes = self.backend["Container"]["Volume"]
        self.assertIn("/var/lib/ai-server:/var/lib/ai-server:rw", backend_volumes)
        self.assertIn("/opt/ai-server/.env:/opt/ai-server/.env:ro", backend_volumes)
        self.assertIn(
            "/etc/ai-server/proxmox-root-ca.pem:/etc/ai-server/proxmox-root-ca.pem:ro",
            backend_volumes,
        )
        self.assertNotIn("Volume", self.dashboard["Container"])


if __name__ == "__main__":
    unittest.main()
