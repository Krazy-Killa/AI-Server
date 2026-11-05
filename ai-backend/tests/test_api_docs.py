import unittest

try:
    from fastapi.testclient import TestClient
except ImportError:  # pragma: no cover
    TestClient = None


@unittest.skipIf(TestClient is None, "httpx is required for HTTP endpoint tests")
class ApiDocsExposureTests(unittest.TestCase):
    DOC_PATHS = ("/docs", "/redoc", "/openapi.json")

    def setUp(self):
        import main

        self.main = main

    def test_docs_are_not_served_by_default(self):
        client = TestClient(self.main.create_app(enable_api_docs=False))
        for path in self.DOC_PATHS:
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 404)

    def test_docs_are_served_only_when_explicitly_enabled(self):
        client = TestClient(self.main.create_app(enable_api_docs=True))
        for path in self.DOC_PATHS:
            with self.subTest(path=path):
                self.assertEqual(client.get(path).status_code, 200)

    def test_default_application_matches_the_setting(self):
        client = TestClient(self.main.app)
        expected = 200 if self.main.settings.enable_api_docs else 404
        self.assertEqual(client.get("/openapi.json").status_code, expected)


if __name__ == "__main__":
    unittest.main()
