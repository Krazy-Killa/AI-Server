import json
import unittest
from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlsplit

import web_research
from web_research import ResearchRuntimeError, _search_web, run_research


class WebResearchTests(unittest.TestCase):
    def test_search_encodes_query_and_filters_non_http_results(self):
        payload = json.dumps(
            {
                "results": [
                    {
                        "title": "Useful result",
                        "url": "https://example.com/article",
                        "content": "A relevant excerpt.",
                    },
                    {
                        "title": "Unsafe scheme",
                        "url": "javascript:alert(1)",
                        "content": "Not a web source.",
                    },
                ]
            }
        ).encode()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = payload

        with patch("web_research.urlopen", return_value=response) as open_url:
            sources = _search_web("RX 6800 XT & llama")

        request = open_url.call_args.args[0]
        query_parameters = parse_qs(urlsplit(request.full_url).query)
        self.assertEqual(query_parameters["q"], ["RX 6800 XT & llama"])
        self.assertEqual(query_parameters["format"], ["json"])
        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["title"], "Useful result")

    def test_rejects_invalid_search_service_url(self):
        with patch.object(web_research, "SEARXNG_BASE_URL", "file:///private"):
            with self.assertRaisesRegex(ResearchRuntimeError, "HTTP\\(S\\)"):
                _search_web("query")

    def test_research_instructs_model_to_treat_excerpts_as_untrusted(self):
        sources = [
            {
                "title": "Example source",
                "url": "https://example.com/article",
                "snippet": "Example excerpt.",
            }
        ]
        completion = {"reply": "A sourced answer [1].", "tokens": 12, "latency_ms": 25}
        with (
            patch("web_research._search_web", return_value=sources),
            patch("web_research.run_llm", return_value=completion) as run_model,
        ):
            result = run_research("What does the source say?")

        self.assertEqual(result["reply"], completion["reply"])
        self.assertEqual(result["sources"], sources)
        self.assertIn("untrusted", run_model.call_args.kwargs["system_prompt"])
        self.assertIn("[1] Example source", run_model.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
