"""Persistent private conversations and the admin-shared console transcript."""

from __future__ import annotations

import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Generator, Literal, TypedDict

MAX_CONTEXT_MESSAGES = 20
MAX_CONTEXT_CHARS = 12_000
MAX_CONVERSATION_LIST = 100
MAX_TITLE_LENGTH = 80
MAX_SHARED_INSIGHTS = 100
MAX_SHARED_INSIGHT_LENGTH = 2_000
ADMIN_INTERFACE_OWNER = "system:admin-interface"
ADMIN_INTERFACE_CONVERSATION_ID = "00000000-0000-4000-8000-000000000001"


class ChatMessage(TypedDict):
    role: Literal["user", "assistant"]
    content: str


class ConversationNotFound(LookupError):
    """The conversation does not exist or does not belong to this account."""


class SharedInsightNotFound(LookupError):
    """The requested shared insight does not exist."""


class SharedInsightLimitReached(RuntimeError):
    """The shared insight store has reached its configured capacity."""


class MemoryStoreError(RuntimeError):
    """Conversation history could not be read or stored safely."""


class ConversationStore:
    """SQLite store for private chats, the shared console, and admin insights."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path).expanduser()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if os.name != "nt":
            self.path.parent.chmod(0o700)
        self._initialize()

    @contextmanager
    def _connect(self) -> Generator[sqlite3.Connection, None, None]:
        connection = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 5000")
        try:
            yield connection
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute("PRAGMA journal_mode = WAL")
                connection.executescript(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        conversation_id TEXT PRIMARY KEY,
                        owner_id TEXT NOT NULL,
                        title TEXT NOT NULL,
                        created_at INTEGER NOT NULL,
                        updated_at INTEGER NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS conversations_owner_updated
                        ON conversations(owner_id, updated_at DESC);
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                        message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        conversation_id TEXT NOT NULL
                            REFERENCES conversations(conversation_id) ON DELETE CASCADE,
                        role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
                        content TEXT NOT NULL,
                        author_id TEXT,
                        sources_json TEXT,
                        created_at INTEGER NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS conversation_messages_order
                        ON conversation_messages(conversation_id, message_id);
                    CREATE TABLE IF NOT EXISTS admin_shared_insights (
                        insight_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        content TEXT NOT NULL,
                        created_by TEXT NOT NULL,
                        created_at INTEGER NOT NULL
                    );
                    CREATE INDEX IF NOT EXISTS admin_shared_insights_created
                        ON admin_shared_insights(created_at DESC, insight_id DESC);
                    """
                )
                message_columns = {
                    row["name"]
                    for row in connection.execute(
                        "PRAGMA table_info(conversation_messages)"
                    )
                }
                if "author_id" not in message_columns:
                    connection.execute(
                        "ALTER TABLE conversation_messages ADD COLUMN author_id TEXT"
                    )
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not initialize the conversation database.") from error
        if os.name != "nt":
            self.path.chmod(0o600)

    @staticmethod
    def _record(row: sqlite3.Row) -> dict[str, object]:
        sources = json.loads(row["sources_json"]) if row["sources_json"] else []
        record = {
            "role": row["role"],
            "content": row["content"],
            "sources": sources,
            "created_at": row["created_at"],
        }
        if row["author_id"] is not None:
            record["author"] = row["author_id"]
        return record

    def get_admin_interface_conversation(self) -> dict[str, object]:
        timestamp = int(time.time())
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT OR IGNORE INTO conversations
                    (conversation_id, owner_id, title, created_at, updated_at)
                    VALUES (?, ?, 'AI Interface Console', ?, ?)""",
                    (
                        ADMIN_INTERFACE_CONVERSATION_ID,
                        ADMIN_INTERFACE_OWNER,
                        timestamp,
                        timestamp,
                    ),
                )
            return self.get_conversation(
                ADMIN_INTERFACE_OWNER, ADMIN_INTERFACE_CONVERSATION_ID
            )
        except sqlite3.Error as error:
            raise MemoryStoreError(
                "Could not load the shared AI Interface conversation."
            ) from error

    def create_conversation(self, owner_id: str) -> dict[str, object]:
        conversation_id = str(uuid.uuid4())
        timestamp = int(time.time())
        try:
            with self._connect() as connection:
                connection.execute(
                    """INSERT INTO conversations
                    (conversation_id, owner_id, title, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?)""",
                    (conversation_id, owner_id, "New conversation", timestamp, timestamp),
                )
            return {
                "conversation_id": conversation_id,
                "title": "New conversation",
                "created_at": timestamp,
                "updated_at": timestamp,
                "message_count": 0,
            }
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not create the conversation.") from error

    def list_conversations(
        self, owner_id: str, limit: int = MAX_CONVERSATION_LIST
    ) -> list[dict[str, object]]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """SELECT c.conversation_id, c.title, c.created_at, c.updated_at,
                       COUNT(m.message_id) AS message_count
                       FROM conversations c
                       LEFT JOIN conversation_messages m
                         ON m.conversation_id = c.conversation_id
                       WHERE c.owner_id = ?
                       GROUP BY c.conversation_id
                       ORDER BY c.updated_at DESC, c.conversation_id
                       LIMIT ?""",
                    (owner_id, limit),
                ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not list conversations.") from error

    def get_conversation(
        self, owner_id: str, conversation_id: str
    ) -> dict[str, object]:
        try:
            with self._connect() as connection:
                conversation = connection.execute(
                    """SELECT conversation_id, title, created_at, updated_at
                       FROM conversations WHERE owner_id = ? AND conversation_id = ?""",
                    (owner_id, conversation_id),
                ).fetchone()
                if conversation is None:
                    raise ConversationNotFound
                rows = connection.execute(
                    """SELECT role, content, author_id, sources_json, created_at
                       FROM conversation_messages WHERE conversation_id = ?
                       ORDER BY message_id""",
                    (conversation_id,),
                ).fetchall()
            return {
                **dict(conversation),
                "messages": [self._record(row) for row in rows],
            }
        except ConversationNotFound:
            raise
        except (sqlite3.Error, json.JSONDecodeError, TypeError) as error:
            raise MemoryStoreError("Could not load the conversation.") from error

    def delete_conversation(self, owner_id: str, conversation_id: str) -> None:
        try:
            with self._connect() as connection:
                result = connection.execute(
                    "DELETE FROM conversations WHERE owner_id = ? AND conversation_id = ?",
                    (owner_id, conversation_id),
                )
                if result.rowcount != 1:
                    raise ConversationNotFound
        except ConversationNotFound:
            raise
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not delete the conversation.") from error

    def begin_user_turn(
        self,
        owner_id: str,
        conversation_id: str,
        content: str,
        author_id: str | None = None,
    ) -> list[ChatMessage]:
        timestamp = int(time.time())
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                conversation = connection.execute(
                    """SELECT 1 FROM conversations
                       WHERE owner_id = ? AND conversation_id = ?""",
                    (owner_id, conversation_id),
                ).fetchone()
                if conversation is None:
                    raise ConversationNotFound
                rows = connection.execute(
                    """SELECT role, content, author_id FROM conversation_messages
                       WHERE conversation_id = ?
                       ORDER BY message_id DESC LIMIT ?""",
                    (conversation_id, MAX_CONTEXT_MESSAGES),
                ).fetchall()
                connection.execute(
                    """INSERT INTO conversation_messages
                       (conversation_id, role, content, author_id, created_at)
                       VALUES (?, 'user', ?, ?, ?)""",
                    (conversation_id, content, author_id, timestamp),
                )
                title = " ".join(content.split())[:MAX_TITLE_LENGTH]
                connection.execute(
                    """UPDATE conversations SET
                       title = CASE WHEN title = 'New conversation' THEN ? ELSE title END,
                       updated_at = ?
                       WHERE owner_id = ? AND conversation_id = ?""",
                    (title or "New conversation", timestamp, owner_id, conversation_id),
                )
                connection.commit()

            history: list[ChatMessage] = []
            total_chars = 0
            for row in rows:
                content = row["content"]
                if row["role"] == "user" and row["author_id"]:
                    content = f"[Admin {row['author_id']}] {content}"
                message_length = len(content)
                if total_chars + message_length > MAX_CONTEXT_CHARS:
                    break
                history.append({"role": row["role"], "content": content})
                total_chars += message_length
            return list(reversed(history))
        except ConversationNotFound:
            raise
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not save the user message.") from error

    def append_assistant_message(
        self,
        owner_id: str,
        conversation_id: str,
        content: str,
        sources: list[dict[str, str]] | None = None,
    ) -> None:
        timestamp = int(time.time())
        sources_json = json.dumps(sources, ensure_ascii=True) if sources else None
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                conversation = connection.execute(
                    """SELECT 1 FROM conversations
                       WHERE owner_id = ? AND conversation_id = ?""",
                    (owner_id, conversation_id),
                ).fetchone()
                if conversation is None:
                    raise ConversationNotFound
                connection.execute(
                    """INSERT INTO conversation_messages
                       (conversation_id, role, content, sources_json, created_at)
                       VALUES (?, 'assistant', ?, ?, ?)""",
                    (conversation_id, content, sources_json, timestamp),
                )
                connection.execute(
                    """UPDATE conversations SET updated_at = ?
                       WHERE owner_id = ? AND conversation_id = ?""",
                    (timestamp, owner_id, conversation_id),
                )
                connection.commit()
        except ConversationNotFound:
            raise
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not save the assistant message.") from error

    def list_shared_insights(
        self, limit: int = MAX_SHARED_INSIGHTS
    ) -> list[dict[str, object]]:
        try:
            with self._connect() as connection:
                rows = connection.execute(
                    """SELECT insight_id, content, created_by, created_at
                       FROM admin_shared_insights
                       ORDER BY created_at DESC, insight_id DESC
                       LIMIT ?""",
                    (min(max(limit, 1), MAX_SHARED_INSIGHTS),),
                ).fetchall()
            return [dict(row) for row in rows]
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not list shared admin insights.") from error

    def add_shared_insight(self, content: str, created_by: str) -> dict[str, object]:
        normalized_content = content.strip()
        if not normalized_content or len(normalized_content) > MAX_SHARED_INSIGHT_LENGTH:
            raise ValueError(
                f"Shared insight must be 1-{MAX_SHARED_INSIGHT_LENGTH} characters."
            )
        timestamp = int(time.time())
        try:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                count = connection.execute(
                    "SELECT COUNT(*) FROM admin_shared_insights"
                ).fetchone()[0]
                if count >= MAX_SHARED_INSIGHTS:
                    raise SharedInsightLimitReached
                cursor = connection.execute(
                    """INSERT INTO admin_shared_insights
                       (content, created_by, created_at)
                       VALUES (?, ?, ?)""",
                    (normalized_content, created_by, timestamp),
                )
                insight_id = cursor.lastrowid
                connection.commit()
            return {
                "insight_id": insight_id,
                "content": normalized_content,
                "created_by": created_by,
                "created_at": timestamp,
            }
        except SharedInsightLimitReached:
            raise
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not publish the shared admin insight.") from error

    def delete_shared_insight(self, insight_id: int) -> None:
        try:
            with self._connect() as connection:
                result = connection.execute(
                    "DELETE FROM admin_shared_insights WHERE insight_id = ?",
                    (insight_id,),
                )
                if result.rowcount != 1:
                    raise SharedInsightNotFound
        except SharedInsightNotFound:
            raise
        except sqlite3.Error as error:
            raise MemoryStoreError("Could not delete the shared admin insight.") from error
