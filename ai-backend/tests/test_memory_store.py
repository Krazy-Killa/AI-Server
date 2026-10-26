import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

from auth_test_helpers import TEST_ORIGIN, authenticated_client
from memory_store import (
    MAX_CONTEXT_CHARS,
    MAX_CONTEXT_MESSAGES,
    ConversationNotFound,
    ConversationStore,
    SharedInsightLimitReached,
    SharedInsightNotFound,
)
from fastapi.testclient import TestClient


class ConversationStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory(prefix="conversation-store-test-")
        self.addCleanup(self.directory.cleanup)
        self.store = ConversationStore(Path(self.directory.name) / "memory.sqlite3")
        self.owner = "local:alice"

    def test_conversations_and_messages_are_owned_by_account(self):
        conversation = self.store.create_conversation(self.owner)
        conversation_id = conversation["conversation_id"]
        self.store.begin_user_turn(self.owner, conversation_id, "Hello")
        self.store.append_assistant_message(
            self.owner,
            conversation_id,
            "Hi there",
            [{"title": "Example", "url": "https://example.test"}],
        )

        loaded = self.store.get_conversation(self.owner, conversation_id)
        self.assertEqual(loaded["title"], "Hello")
        self.assertEqual([message["role"] for message in loaded["messages"]], ["user", "assistant"])
        self.assertEqual(
            loaded["messages"][1]["sources"],
            [{"title": "Example", "url": "https://example.test"}],
        )
        self.assertEqual(self.store.list_conversations(self.owner)[0]["message_count"], 2)
        reopened = ConversationStore(self.store.path)
        self.assertEqual(
            reopened.get_conversation(self.owner, conversation_id)["messages"],
            loaded["messages"],
        )
        with self.assertRaises(ConversationNotFound):
            self.store.get_conversation("local:bob", conversation_id)

    def test_context_is_bounded_to_recent_messages_and_characters(self):
        conversation_id = self.store.create_conversation(self.owner)["conversation_id"]
        for index in range(MAX_CONTEXT_MESSAGES + 4):
            self.store.begin_user_turn(self.owner, conversation_id, f"User {index}")
            self.store.append_assistant_message(self.owner, conversation_id, f"Reply {index}")

        context = self.store.begin_user_turn(self.owner, conversation_id, "Newest")
        self.assertLessEqual(len(context), MAX_CONTEXT_MESSAGES)
        self.assertLessEqual(sum(len(item["content"]) for item in context), MAX_CONTEXT_CHARS)
        self.assertEqual(context[-1]["content"], f"Reply {MAX_CONTEXT_MESSAGES + 3}")

    def test_context_character_limit_keeps_newest_messages(self):
        conversation_id = self.store.create_conversation(self.owner)["conversation_id"]
        for _ in range(3):
            self.store.begin_user_turn(self.owner, conversation_id, "u" * 5000)
            self.store.append_assistant_message(self.owner, conversation_id, "a" * 5000)

        context = self.store.begin_user_turn(self.owner, conversation_id, "Newest")
        self.assertLessEqual(sum(len(item["content"]) for item in context), MAX_CONTEXT_CHARS)
        self.assertEqual(context[-1]["content"], "a" * 5000)

    def test_existing_conversation_database_migrates_message_authors(self):
        legacy_path = Path(self.directory.name) / "legacy.sqlite3"
        with closing(sqlite3.connect(legacy_path)) as connection:
            connection.executescript(
                """
                CREATE TABLE conversations (
                    conversation_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    updated_at INTEGER NOT NULL
                );
                CREATE TABLE conversation_messages (
                    message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    sources_json TEXT,
                    created_at INTEGER NOT NULL
                );
                INSERT INTO conversations VALUES
                    ('legacy-id', 'local:alice', 'Old chat', 1, 1);
                INSERT INTO conversation_messages
                    (conversation_id, role, content, created_at)
                    VALUES ('legacy-id', 'user', 'Existing message', 1);
                """
            )
            connection.commit()

        migrated = ConversationStore(legacy_path)

        self.assertEqual(
            migrated.get_conversation("local:alice", "legacy-id")["messages"][0]["content"],
            "Existing message",
        )

    def test_delete_removes_only_owned_conversation(self):
        conversation_id = self.store.create_conversation(self.owner)["conversation_id"]
        self.store.begin_user_turn(self.owner, conversation_id, "Private")
        with self.assertRaises(ConversationNotFound):
            self.store.delete_conversation("local:bob", conversation_id)
        self.store.delete_conversation(self.owner, conversation_id)
        with self.assertRaises(ConversationNotFound):
            self.store.get_conversation(self.owner, conversation_id)

    def test_shared_insights_persist_and_can_be_removed(self):
        insight = self.store.add_shared_insight(
            "  The staging service uses port 9000.  ", "local:alice"
        )
        reopened = ConversationStore(self.store.path)
        self.assertEqual(
            reopened.list_shared_insights(),
            [{
                "insight_id": insight["insight_id"],
                "content": "The staging service uses port 9000.",
                "created_by": "local:alice",
                "created_at": insight["created_at"],
            }],
        )
        reopened.delete_shared_insight(insight["insight_id"])
        self.assertEqual(self.store.list_shared_insights(), [])
        with self.assertRaises(SharedInsightNotFound):
            self.store.delete_shared_insight(insight["insight_id"])

    def test_admin_interface_has_one_persistent_shared_conversation(self):
        conversation = self.store.get_admin_interface_conversation()
        self.store.begin_user_turn(
            "system:admin-interface",
            conversation["conversation_id"],
            "Check the backend health.",
            "alice (local)",
        )
        self.store.append_assistant_message(
            "system:admin-interface",
            conversation["conversation_id"],
            "The backend is running.",
        )

        reopened = ConversationStore(self.store.path)
        shared = reopened.get_admin_interface_conversation()
        context = reopened.begin_user_turn(
            "system:admin-interface",
            conversation["conversation_id"],
            "What did Alice ask?",
            "bob (local)",
        )

        self.assertEqual(shared["conversation_id"], conversation["conversation_id"])
        self.assertEqual(shared["messages"][0]["author"], "alice (local)")
        self.assertEqual(
            context,
            [
                {
                    "role": "user",
                    "content": "[Admin alice (local)] Check the backend health.",
                },
                {"role": "assistant", "content": "The backend is running."},
            ],
        )

    def test_shared_insights_have_a_capacity_limit(self):
        with patch("memory_store.MAX_SHARED_INSIGHTS", 1):
            self.store.add_shared_insight("First note", "local:alice")
            with self.assertRaises(SharedInsightLimitReached):
                self.store.add_shared_insight("Second note", "local:alice")


class ConversationApiTests(unittest.TestCase):
    def setUp(self):
        import main

        self.main = main
        self.client, self.auth_store = authenticated_client(self, main)
        self.directory = tempfile.TemporaryDirectory(prefix="conversation-api-test-")
        self.addCleanup(self.directory.cleanup)
        self.store = ConversationStore(Path(self.directory.name) / "memory.sqlite3")
        self.store_patch = patch.object(main.runtime, "conversation_store", self.store)
        self.store_patch.start()
        self.addCleanup(self.store_patch.stop)

    def _login_local_user(self, username, role, password="AnotherSafePassword42!"):
        self.auth_store.create_local_user(username, password, role)
        client = TestClient(self.main.app)
        login = client.post(
            "/api/auth/login",
            json={"provider": "local", "username": username, "password": password},
            headers={"origin": TEST_ORIGIN},
        )
        self.assertEqual(login.status_code, 200, login.text)
        client.headers.update(
            {"origin": TEST_ORIGIN, "x-csrf-token": login.json()["csrf_token"]}
        )
        return client

    def test_conversation_routes_create_read_and_delete(self):
        created = self.client.post("/api/memory/conversations")
        self.assertEqual(created.status_code, 201, created.text)
        conversation_id = created.json()["conversation_id"]

        with patch.object(self.main.runtime,
            "run_llm",
            return_value={"reply": "Hello back", "tokens": 2, "latency_ms": 10},
        ) as run_llm:
            first = self.client.post(
                "/api/chat",
                json={"message": "Hello", "conversation_id": conversation_id},
            )
            second = self.client.post(
                "/api/chat",
                json={"message": "Continue", "conversation_id": conversation_id},
            )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(run_llm.call_args.kwargs["history"], [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hello back"},
        ])

        loaded = self.client.get(f"/api/memory/conversations/{conversation_id}")
        self.assertEqual(loaded.status_code, 200, loaded.text)
        self.assertEqual(
            [message["role"] for message in loaded.json()["messages"]],
            ["user", "assistant", "user", "assistant"],
        )
        self.assertEqual(
            self.client.get("/api/memory/conversations").json()["count"],
            1,
        )
        deleted = self.client.delete(f"/api/memory/conversations/{conversation_id}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.json(), {"deleted": True})

    def test_conversation_id_cannot_be_read_by_another_account(self):
        created = self.client.post("/api/memory/conversations")
        conversation_id = created.json()["conversation_id"]
        self.auth_store.create_local_user("other", "AnotherSafePassword42!", "operator")
        other_client = TestClient(self.main.app)
        login = other_client.post(
            "/api/auth/login",
            json={
                "provider": "local",
                "username": "other",
                "password": "AnotherSafePassword42!",
            },
            headers={"origin": TEST_ORIGIN},
        )
        other_client.headers.update(
            {"origin": TEST_ORIGIN, "x-csrf-token": login.json()["csrf_token"]}
        )

        self.assertEqual(
            other_client.get(f"/api/memory/conversations/{conversation_id}").status_code,
            404,
        )
        self.assertEqual(other_client.get("/api/memory/conversations").json()["count"], 0)

    def test_research_turn_and_sources_are_persisted(self):
        conversation_id = self.client.post("/api/memory/conversations").json()["conversation_id"]
        self.store.add_shared_insight("Research uses the staging endpoint.", "local:publisher")
        research_result = {
            "reply": "A cited answer [1].",
            "sources": [
                {
                    "title": "Reference",
                    "url": "https://example.test",
                    "snippet": "Details",
                    "page_status": "fetched",
                }
            ],
            "latency_ms": 20,
            "search_latency_ms": 5,
            "tokens": 8,
        }
        with patch.object(self.main.runtime, "run_research", return_value=research_result
        ) as run_research:
            response = self.client.post(
                "/api/research",
                json={"message": "Find a reference", "conversation_id": conversation_id},
            )

        self.assertEqual(response.status_code, 200, response.text)
        owner_id = f"local:{self.auth_store.list_local_users()[0]['username']}"
        loaded = self.store.get_conversation(owner_id, conversation_id)
        self.assertEqual(loaded["messages"][1]["content"], "A cited answer [1].")
        self.assertEqual(loaded["messages"][1]["sources"], research_result["sources"])
        self.assertIn("test-admin (local)", run_research.call_args.kwargs["system_prompt"])
        self.assertIn(
            "Research uses the staging endpoint.",
            run_research.call_args.kwargs["system_prompt"],
        )

    def test_streaming_research_returns_sources_and_persists_completed_turn(self):
        conversation_id = self.client.post("/api/memory/conversations").json()["conversation_id"]
        self.store.add_shared_insight("Use the current staging API.", "local:publisher")
        prepared = {
            "sources": [
                {
                    "title": "Reference",
                    "url": "https://example.test",
                    "snippet": "Details",
                    "page_status": "fetched",
                }
            ],
            "prompt": "Prepared research prompt",
            "system_prompt": "Safe research context",
            "search_latency_ms": 5,
        }
        with (
            patch.object(self.main.runtime, "prepare_research", return_value=prepared) as prepare,
            patch.object(self.main.runtime, "stream_research", return_value=iter(["A cited ", "answer [1]."])),
        ):
            response = self.client.post(
                "/api/research/stream",
                json={"message": "Find a reference", "conversation_id": conversation_id},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn('event: sources\ndata: {"sources":[{"title":"Reference"', response.text)
        self.assertIn('event: token\ndata: {"content":"A cited "}', response.text)
        self.assertIn('event: done\ndata:', response.text)
        self.assertEqual(
            self.store.get_conversation(
                f"local:{self.auth_store.list_local_users()[0]['username']}",
                conversation_id,
            )["messages"][1]["content"],
            "A cited answer [1].",
        )
        self.assertIn("test-admin (local)", prepare.call_args.args[1])
        self.assertIn("Use the current staging API.", prepare.call_args.args[1])

    def test_published_note_and_current_identity_reach_only_another_admin_chat(self):
        owner_a = f"local:{self.auth_store.list_local_users()[0]['username'].casefold()}"
        private_conversation = self.store.create_conversation(owner_a)["conversation_id"]
        self.store.begin_user_turn(
            owner_a,
            private_conversation,
            "PRIVATE_ADMIN_A_SENTENCE_84a2",
        )
        published = self.client.post(
            "/api/memory/shared-insights",
            json={"content": "The staging API listens on port 9000."},
        )
        self.assertEqual(published.status_code, 201, published.text)

        other_client = self._login_local_user("other-admin", "admin")
        other_conversation = other_client.post("/api/memory/conversations").json()
        with patch.object(self.main.runtime,
            "run_llm",
            return_value={"reply": "Ready.", "tokens": 1, "latency_ms": 10},
        ) as run_llm:
            response = other_client.post(
                "/api/chat",
                json={
                    "message": "What is the staging API port?",
                    "conversation_id": other_conversation["conversation_id"],
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        prompt = run_llm.call_args.args[1]
        self.assertIn("other-admin (local)", prompt)
        self.assertIn("The staging API listens on port 9000.", prompt)
        self.assertNotIn("PRIVATE_ADMIN_A_SENTENCE_84a2", prompt)
        self.assertEqual(other_client.get("/api/memory/conversations").json()["count"], 1)
        shared = other_client.get("/api/memory/shared-insights")
        self.assertEqual(shared.status_code, 200, shared.text)
        self.assertEqual(shared.json()["insights"][0]["content"], "The staging API listens on port 9000.")
        removed = other_client.delete(
            f"/api/memory/shared-insights/{published.json()['insight_id']}"
        )
        self.assertEqual(removed.status_code, 200, removed.text)
        self.assertEqual(other_client.get("/api/memory/shared-insights").json()["count"], 0)

    def test_non_admin_cannot_read_or_publish_shared_notes_or_receive_them_in_chat(self):
        operator = self._login_local_user("operator", "operator")
        self.assertEqual(operator.get("/api/memory/shared-insights").status_code, 403)
        self.assertEqual(
            operator.post(
                "/api/memory/shared-insights",
                json={"content": "Should not be published"},
            ).status_code,
            403,
        )
        with patch.object(self.main.runtime,
            "run_llm",
            return_value={"reply": "Hi.", "tokens": 1, "latency_ms": 10},
        ) as run_llm:
            response = operator.post("/api/chat", json={"message": "Hello"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(run_llm.call_args.args, ("Hello",))
        self.assertEqual(run_llm.call_args.kwargs, {})

    def test_shared_interface_is_admin_only_and_keeps_private_chats_out_of_context(self):
        private_owner = "local:test-admin"
        private_conversation = self.store.create_conversation(private_owner)
        self.store.begin_user_turn(
            private_owner,
            private_conversation["conversation_id"],
            "PRIVATE_CHAT_MESSAGE_47f2",
        )
        first_reply = {"reply": "The backend is healthy.", "latency_ms": 2, "tokens": 4}
        with patch.object(self.main.runtime, "run_llm", return_value=first_reply):
            first = self.client.post(
                "/api/interface/chat",
                json={"message": "Check backend health."},
            )
        self.assertEqual(first.status_code, 200, first.text)

        other_admin = self._login_local_user("other-admin", "admin")
        shared = other_admin.get("/api/interface/conversation")
        self.assertEqual(shared.status_code, 200, shared.text)
        self.assertEqual(shared.json()["messages"][0]["author"], "test-admin (local)")

        next_reply = {"reply": "The previous check succeeded.", "latency_ms": 2, "tokens": 5}
        with patch.object(self.main.runtime, "run_llm", return_value=next_reply) as run_llm:
            second = other_admin.post(
                "/api/interface/chat",
                json={"message": "What was the previous result?"},
            )
        self.assertEqual(second.status_code, 200, second.text)
        self.assertIn(
            "[Admin test-admin (local)] Check backend health.",
            str(run_llm.call_args.kwargs["history"]),
        )
        self.assertNotIn(
            "PRIVATE_CHAT_MESSAGE_47f2",
            str(run_llm.call_args),
        )
        self.assertIn("other-admin (local)", run_llm.call_args.args[1])

        operator = self._login_local_user("operator", "operator")
        self.assertEqual(
            operator.get("/api/interface/conversation").status_code,
            403,
        )
        self.assertEqual(
            operator.post(
                "/api/interface/chat",
                json={"message": "Check the host."},
            ).status_code,
            403,
        )

    def test_admin_chat_context_is_bounded_and_prefers_newest_notes(self):
        for index in range(5):
            label = f"NOTE-{index}-"
            self.store.add_shared_insight(
                label + ("x" * (2000 - len(label))),
                "local:publisher",
            )
        with patch.object(self.main.runtime,
            "run_llm",
            return_value={"reply": "Ready.", "tokens": 1, "latency_ms": 10},
        ) as run_llm:
            response = self.client.post("/api/chat", json={"message": "Hello"})

        self.assertEqual(response.status_code, 200, response.text)
        prompt = run_llm.call_args.args[1]
        self.assertIn("NOTE-4-", prompt)
        self.assertIn("NOTE-2-", prompt)
        self.assertNotIn("NOTE-1-", prompt)
        self.assertNotIn("NOTE-0-", prompt)

    def test_discord_service_chat_does_not_receive_shared_admin_context(self):
        from dataclasses import replace

        self.store.add_shared_insight("Admin-only note", "local:admin")
        settings_patch = patch.object(self.main.runtime,
            "settings",
            replace(self.main.runtime.settings, bot_api_token="test-bot-token"),
        )
        settings_patch.start()
        self.addCleanup(settings_patch.stop)
        with patch.object(self.main.runtime,
            "run_llm",
            return_value={"reply": "Hi.", "tokens": 1, "latency_ms": 10},
        ) as run_llm:
            response = self.client.post(
                "/api/chat",
                json={"message": "Hello"},
                headers={"authorization": "Bearer test-bot-token"},
            )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(run_llm.call_args.args, ("Hello",))
        self.assertEqual(run_llm.call_args.kwargs, {})
