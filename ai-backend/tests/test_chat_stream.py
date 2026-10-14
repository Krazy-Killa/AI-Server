import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

# Keep test runs from writing to the real log directory; set before importing main.
os.environ.setdefault("AI_SERVER_LOG_DIR", tempfile.mkdtemp(prefix="ai-server-test-logs-"))

from gpu import gpu_llm
from gpu.gpu_llm import LLMRuntimeError, stream_llm

try:
    from fastapi.testclient import TestClient
except ImportError:  # httpx is a development-only dependency
    TestClient = None


def sse(*payloads):
    lines = [f"data: {json.dumps(payload)}\n".encode() for payload in payloads]
    return lines + [b"data: [DONE]\n"]


def delta(text):
    return {"choices": [{"delta": {"content": text}}]}


def chunks(*items):
    yield from items


def fake_response(lines):
    response = MagicMock()
    response.__iter__.return_value = iter(lines)
    response.__enter__.return_value = response
    return response


class StreamLlmTests(unittest.TestCase):
    def test_yields_text_chunks_and_skips_empty_deltas(self):
        lines = sse(delta("Hel"), {"choices": [{"delta": {}}]}, delta("lo"))
        with patch.object(gpu_llm, "urlopen", return_value=fake_response(lines)):
            self.assertEqual(list(stream_llm("hi")), ["Hel", "lo"])

    def test_request_asks_for_streaming(self):
        with patch.object(gpu_llm, "urlopen", return_value=fake_response(sse(delta("x")))) as urlopen:
            list(stream_llm("hi"))
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertTrue(body["stream"])

    def test_empty_stream_is_an_error(self):
        with patch.object(gpu_llm, "urlopen", return_value=fake_response(sse())):
            with self.assertRaisesRegex(LLMRuntimeError, "empty"):
                list(stream_llm("hi"))

    def test_invalid_chunk_is_an_error(self):
        with patch.object(gpu_llm, "urlopen", return_value=fake_response([b"data: not-json\n"])):
            with self.assertRaisesRegex(LLMRuntimeError, "invalid streaming chunk"):
                list(stream_llm("hi"))

    def test_unreachable_server_is_an_error(self):
        with patch.object(gpu_llm, "urlopen", side_effect=OSError("refused")):
            with self.assertRaisesRegex(LLMRuntimeError, "Cannot reach llama.cpp"):
                list(stream_llm("hi"))


@unittest.skipIf(TestClient is None, "httpx is required for WebSocket endpoint tests")
class ChatWebSocketTests(unittest.TestCase):
    def setUp(self):
        import main

        self.main = main
        self.client = TestClient(main.app)

    def test_streams_tokens_then_done(self):
        with patch.object(self.main, "stream_llm", side_effect=lambda _m: chunks("Hel", "lo")):
            with self.client.websocket_connect("/ws/chat") as socket:
                socket.send_json({"message": "hi"})
                self.assertEqual(socket.receive_json(), {"type": "token", "content": "Hel"})
                self.assertEqual(socket.receive_json(), {"type": "token", "content": "lo"})
                done = socket.receive_json()
        self.assertEqual(done["type"], "done")
        self.assertIsInstance(done["latency_ms"], int)

    def test_reports_runtime_errors(self):
        def failing_stream(_message):
            raise LLMRuntimeError("llama.cpp is down")
            yield

        with patch.object(self.main, "stream_llm", side_effect=failing_stream):
            with self.client.websocket_connect("/ws/chat") as socket:
                socket.send_json({"message": "hi"})
                self.assertEqual(
                    socket.receive_json(), {"type": "error", "detail": "llama.cpp is down"}
                )

    def test_rejects_invalid_messages_and_keeps_connection_open(self):
        with self.client.websocket_connect("/ws/chat") as socket:
            socket.send_text("not json")
            self.assertEqual(socket.receive_json()["type"], "error")
            socket.send_json({"message": "   "})
            self.assertEqual(socket.receive_json()["type"], "error")
            socket.send_json({"message": "x" * (self.main.settings.max_chat_chars + 1)})
            self.assertIn("exceeds", socket.receive_json()["detail"])

    def test_rejects_disallowed_origin(self):
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/chat", headers={"origin": "http://evil.test"}):
                pass

    def test_allows_dashboard_origin(self):
        with patch.object(self.main, "stream_llm", side_effect=lambda _m: chunks("ok")):
            with self.client.websocket_connect(
                "/ws/chat", headers={"origin": "http://127.0.0.1:8001"}
            ) as socket:
                socket.send_json({"message": "hi"})
                self.assertEqual(socket.receive_json()["type"], "token")


if __name__ == "__main__":
    unittest.main()
