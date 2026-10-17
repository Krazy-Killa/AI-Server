import os
import unittest
from unittest.mock import MagicMock, patch
from urllib.error import URLError

from container_healthcheck import main


class ContainerHealthCheckTests(unittest.TestCase):
    def test_returns_success_for_healthy_endpoint(self):
        response = MagicMock()
        response.__enter__.return_value.status = 200
        with (
            patch.dict(
                os.environ,
                {"AI_SERVER_HEALTH_URL": "http://127.0.0.1:8000/openapi.json"},
            ),
            patch("container_healthcheck.urlopen", return_value=response) as open_url,
        ):
            result = main()

        self.assertEqual(result, 0)
        open_url.assert_called_once_with(
            "http://127.0.0.1:8000/openapi.json",
            timeout=3,
        )

    def test_reports_non_200_endpoint_as_unhealthy(self):
        response = MagicMock()
        response.__enter__.return_value.status = 503
        with (
            patch.dict(
                os.environ,
                {"AI_SERVER_HEALTH_URL": "http://127.0.0.1:8000/openapi.json"},
            ),
            patch("container_healthcheck.urlopen", return_value=response),
        ):
            result = main()

        self.assertEqual(result, 1)

    def test_reports_unreachable_endpoint_as_unhealthy(self):
        with (
            patch.dict(
                os.environ,
                {"AI_SERVER_HEALTH_URL": "http://127.0.0.1:8000/openapi.json"},
            ),
            patch(
                "container_healthcheck.urlopen",
                side_effect=URLError("connection refused"),
            ),
        ):
            result = main()

        self.assertEqual(result, 1)

    def test_requires_a_health_url(self):
        with patch.dict(os.environ, {}, clear=True):
            result = main()

        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
