import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Keep test runs from writing to the real log directory; set before importing main.
os.environ.setdefault("AI_SERVER_LOG_DIR", tempfile.mkdtemp(prefix="ai-server-test-logs-"))

from gpu import gpu_llm
from gpu.gpu_llm import LLMRuntimeError, stream_llm
from auth_test_helpers import TEST_ORIGIN, authenticated_client
from memory_store import ConversationStore
from diagnostics import DiagnosticsMonitor, ResourceSnapshot

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

    def test_request_includes_prior_conversation_turns(self):
        with patch.object(gpu_llm, "urlopen", return_value=fake_response(sse(delta("x")))) as urlopen:
            list(stream_llm(
                "What next?",
                history=[
                    {"role": "user", "content": "I am setting up the server."},
                    {"role": "assistant", "content": "What hardware will you use?"},
                ],
            ))
        body = json.loads(urlopen.call_args.args[0].data)
        self.assertEqual(
            body["messages"],
            [
                {"role": "user", "content": "I am setting up the server."},
                {"role": "assistant", "content": "What hardware will you use?"},
                {"role": "user", "content": "What next?"},
            ],
        )

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
        self.client, self.auth_store = authenticated_client(self, main)
        self.memory_directory = tempfile.TemporaryDirectory(prefix="chat-memory-test-")
        self.addCleanup(self.memory_directory.cleanup)
        self.memory_store = ConversationStore(
            Path(self.memory_directory.name) / "memory.sqlite3"
        )
        memory_patch = patch.object(main.runtime, "conversation_store", self.memory_store)
        memory_patch.start()
        self.addCleanup(memory_patch.stop)

    def test_streams_tokens_then_done(self):
        with patch.object(self.main.runtime,
            "stream_llm",
            side_effect=lambda _message, **_kwargs: chunks("Hel", "lo"),
        ):
            with self.client.websocket_connect(
                "/ws/chat", headers={"origin": TEST_ORIGIN}
            ) as socket:
                socket.send_json({"message": "hi"})
                self.assertEqual(socket.receive_json(), {"type": "token", "content": "Hel"})
                self.assertEqual(socket.receive_json(), {"type": "token", "content": "lo"})
                done = socket.receive_json()
        self.assertEqual(done["type"], "done")
        self.assertIsInstance(done["latency_ms"], int)

    def test_stream_persists_user_and_assistant_turn(self):
        owner_id = f"local:{self.auth_store.list_local_users()[0]['username']}"
        conversation = self.memory_store.create_conversation(owner_id)
        with patch.object(self.main.runtime,
            "stream_llm",
            side_effect=lambda _message, **_kwargs: chunks("Saved", " reply"),
        ):
            with self.client.websocket_connect(
                "/ws/chat", headers={"origin": TEST_ORIGIN}
            ) as socket:
                socket.send_json({
                    "message": "Remember this conversation",
                    "conversation_id": conversation["conversation_id"],
                })
                self.assertEqual(socket.receive_json()["type"], "token")
                self.assertEqual(socket.receive_json()["type"], "token")
                self.assertEqual(socket.receive_json()["type"], "done")

        loaded = self.memory_store.get_conversation(
            owner_id, conversation["conversation_id"]
        )
        self.assertEqual(
            [(item["role"], item["content"]) for item in loaded["messages"]],
            [
                ("user", "Remember this conversation"),
                ("assistant", "Saved reply"),
            ],
        )

    def test_stream_receives_only_published_shared_notes_and_signed_in_identity(self):
        self.memory_store.add_shared_insight(
            "Published operational note.", "local:another-admin"
        )
        with patch.object(self.main.runtime,
            "stream_llm",
            side_effect=lambda _message, **_kwargs: chunks("Context applied."),
        ) as stream_llm:
            with self.client.websocket_connect(
                "/ws/chat", headers={"origin": TEST_ORIGIN}
            ) as socket:
                socket.send_json({"message": "Use the team note."})
                self.assertEqual(socket.receive_json()["type"], "token")
                self.assertEqual(socket.receive_json()["type"], "done")

        prompt = stream_llm.call_args.kwargs["system_prompt"]
        self.assertIn("test-admin (local)", prompt)
        self.assertIn("Published operational note.", prompt)
        self.assertIn("private to their account", prompt)

    def test_explicit_diagnostics_request_streams_with_read_only_evidence(self):
        monitor = DiagnosticsMonitor(
            checks=(("backend.process", lambda: (True, "Backend is running.")),),
            resource_sampler=lambda: ResourceSnapshot(
                cpu_percent=10.0,
                ram_percent=30.0,
                ram_used_bytes=300,
                ram_total_bytes=1000,
                log_disk_free_percent=70.0,
                log_disk_free_bytes=700,
                backend_rss_bytes=100,
            ),
        )
        with (
            patch.object(self.main.runtime, "diagnostics_monitor", monitor),
            patch.object(self.main.runtime,
                "stream_llm",
                side_effect=lambda _message, **_kwargs: chunks("Diagnostics complete."),
            ) as stream_llm,
        ):
            with self.client.websocket_connect(
                "/ws/chat", headers={"origin": TEST_ORIGIN}
            ) as socket:
                socket.send_json({"message": "Please check the diagnostics."})
                token = socket.receive_json()
                done = socket.receive_json()

        self.assertEqual(token, {"type": "token", "content": "Diagnostics complete."})
        self.assertEqual(done["type"], "done")
        self.assertIn("backend.process", stream_llm.call_args.kwargs["system_prompt"])
        self.assertIn("Backend is running.", stream_llm.call_args.kwargs["system_prompt"])

    def test_reports_runtime_errors(self):
        def failing_stream(_message, **_kwargs):
            raise LLMRuntimeError("llama.cpp is down")
            yield

        with patch.object(self.main.runtime, "stream_llm", side_effect=failing_stream):
            with self.client.websocket_connect(
                "/ws/chat", headers={"origin": TEST_ORIGIN}
            ) as socket:
                socket.send_json({"message": "hi"})
                self.assertEqual(
                    socket.receive_json(), {"type": "error", "detail": "llama.cpp is down"}
                )

    def test_rejects_invalid_messages_and_keeps_connection_open(self):
        with self.client.websocket_connect(
            "/ws/chat", headers={"origin": TEST_ORIGIN}
        ) as socket:
            socket.send_text("not json")
            self.assertEqual(socket.receive_json()["type"], "error")
            socket.send_json({"message": "   "})
            self.assertEqual(socket.receive_json()["type"], "error")
            socket.send_json({"message": "x" * (self.main.runtime.settings.max_chat_chars + 1)})
            self.assertIn("exceeds", socket.receive_json()["detail"])

    def test_rejects_disallowed_origin(self):
        with self.assertRaises(Exception):
            with self.client.websocket_connect("/ws/chat", headers={"origin": "http://evil.test"}):
                pass

    def test_rejects_unauthenticated_websocket(self):
        if TestClient is None:
            raise unittest.SkipTest("httpx2 is required for WebSocket endpoint tests")
        unauthenticated_client = TestClient(self.main.app)
        with self.assertRaises(Exception):
            with unauthenticated_client.websocket_connect(
                "/ws/chat", headers={"origin": TEST_ORIGIN}
            ):
                pass

    def test_allows_dashboard_origin(self):
        with patch.object(self.main.runtime,
            "stream_llm",
            side_effect=lambda _message, **_kwargs: chunks("ok"),
        ):
            with self.client.websocket_connect(
                "/ws/chat", headers={"origin": TEST_ORIGIN}
            ) as socket:
                socket.send_json({"message": "hi"})
                self.assertEqual(socket.receive_json()["type"], "token")


if __name__ == "__main__":
    unittest.main()
