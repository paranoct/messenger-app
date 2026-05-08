import os
import sqlite3
import tempfile
import unittest

from core.repositories.sqlite import SQLiteChatMembersRepository
from core.services import SessionService, create_services
from core.services.user_service import UserService


PUBLIC_ERROR = "Операция не выполнена"
AUTH_ERROR = "Неверные учетные данные"
INVALID_INPUT_ERROR = "Некорректные данные"
PASSWORD = "Pass1!"


class ServiceFlowTests(unittest.TestCase):
    def make_db_path(self):
        fd, path = tempfile.mkstemp(prefix="messenger-test-", suffix=".db")
        os.close(fd)
        os.unlink(path)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return path

    def assert_value_error(self, expected_message, callback):
        with self.assertRaises(ValueError) as ctx:
            callback()
        self.assertEqual(str(ctx.exception), expected_message)

    def test_user_chat_message_roles_and_public_errors(self):
        with create_services(self.make_db_path()) as app:
            users = app.user_service
            chats = app.chat_service
            members_repo = SQLiteChatMembersRepository(conn=app.conn, initialize=False)

            owner = users.register("roma", "roma@example.com", PASSWORD)
            member = users.register("alex", "alex@example.com", PASSWORD)
            admin = users.register("ivan", "ivan@example.com", PASSWORD)

            self.assertFalse(hasattr(owner, "password_hash"))
            self.assertFalse(hasattr(users.login("roma", PASSWORD), "password_hash"))
            self.assertTrue(all("password_hash" not in row for row in users.list_users()))
            self.assertNotIn(
                "password_hash",
                users.get_public_user("roma", include_email=True),
            )

            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: users.register("roma", "other@example.com", PASSWORD),
            )
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: users.register("other", "roma@example.com", PASSWORD),
            )
            self.assert_value_error(
                INVALID_INPUT_ERROR,
                lambda: users.register("x", "bad", "123"),
            )
            self.assert_value_error(AUTH_ERROR, lambda: users.login("none", PASSWORD))
            self.assert_value_error(AUTH_ERROR, lambda: users.login("roma", "wrong"))

            app.conn.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                ("badp", "badp@example.com", "pbkdf2_sha256$200000$not-hex$digest"),
            )
            app.conn.commit()
            self.assert_value_error(AUTH_ERROR, lambda: users.login("badp", PASSWORD))

            chat = chats.create_chat("same", owner.id)
            other_chat = chats.create_chat("same", member.id)
            self.assertNotEqual(chat.id, other_chat.id)
            self.assertEqual(chats.get_chat("same", owner.id), chat.id)
            self.assertEqual(chats.get_chat("same", member.id), other_chat.id)
            self.assertEqual([item.id for item in chats.list_chats(owner.id)], [chat.id])
            self.assertEqual([item.id for item in chats.list_chats(member.id)], [other_chat.id])

            self.assert_value_error(PUBLIC_ERROR, lambda: chats.create_chat("same", owner.id))
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.get_chat(str(chat.id), admin.id),
            )

            chats.add_user_to_chat(owner.id, chat.id, member.id, "member")
            chats.add_user_to_chat(owner.id, chat.id, admin.id, "admin")
            self.assertEqual(members_repo.get_user_role(chat.id, owner.id), "owner")
            self.assertEqual(members_repo.get_user_role(chat.id, member.id), "member")
            self.assertEqual(members_repo.get_user_role(chat.id, admin.id), "admin")

            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.add_user_to_chat(member.id, chat.id, member.id, "member"),
            )
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.add_user_to_chat(admin.id, chat.id, member.id, "admin"),
            )
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.add_user_to_chat(owner.id, chat.id, member.id, "owner"),
            )

            with self.assertRaises(sqlite3.IntegrityError):
                with app.conn:
                    app.conn.execute(
                        "UPDATE chat_members SET role = 'owner' WHERE chat_id = ? AND user_id = ?",
                        (chat.id, member.id),
                    )

            message = chats.send_message(chat.id, "hello", owner.id)
            self.assertEqual(message.text, "hello")
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.send_message(chat.id, "nope", 999),
            )
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.send_message(chat.id, "   ", owner.id),
            )
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.delete_message(member.id, chat.id, message.id),
            )
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.delete_message(owner.id, other_chat.id, message.id),
            )
            self.assert_value_error(
                PUBLIC_ERROR,
                lambda: chats.delete_message(owner.id, chat.id, 999999),
            )
            chats.delete_message(owner.id, chat.id, message.id)
            self.assertEqual(chats.get_messages(chat.id, owner.id), [])

            users.delete_account(owner.id, PASSWORD, owner)
            self.assertEqual(members_repo.get_user_role(chat.id, admin.id), "owner")
            self.assertEqual(members_repo.get_user_role(chat.id, member.id), "member")
            self.assert_value_error(AUTH_ERROR, lambda: users.login("roma", PASSWORD))

    def test_session_service(self):
        sessions = SessionService(ttl_seconds=60)
        token = sessions.create_session(10)

        self.assertEqual(sessions.get_current_user_id(token), 10)
        sessions.delete_session(token)
        self.assert_value_error(PUBLIC_ERROR, lambda: sessions.get_current_user_id(token))

        expired_sessions = SessionService(ttl_seconds=0)
        expired_token = expired_sessions.create_session(11)
        self.assert_value_error(
            PUBLIC_ERROR,
            lambda: expired_sessions.get_current_user_id(expired_token),
        )

    def test_old_schema_migrations(self):
        self.assert_old_schema_without_password_hash_is_cleaned()
        self.assert_legacy_password_column_is_copied()
        self.assert_global_unique_chat_name_index_is_removed()

    def assert_old_schema_without_password_hash_is_cleaned(self):
        path = self.make_db_path()
        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE users (id INTEGER PRIMARY KEY, username TEXT UNIQUE, email TEXT UNIQUE);
            CREATE TABLE chats (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
            CREATE TABLE chat_members (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                sender_id INTEGER,
                text TEXT,
                created_at TEXT
            );
            INSERT INTO users (id, username, email) VALUES (1, 'olduser', 'old@example.com');
            INSERT INTO chats (id, name) VALUES (1, 'oldchat');
            INSERT INTO chat_members (chat_id, user_id) VALUES (1, 1);
            INSERT INTO messages (id, chat_id, sender_id, text, created_at)
                VALUES (1, 1, 1, 'old text', '2026-01-01T00:00:00');
        """)
        conn.commit()
        conn.close()

        with create_services(path) as app:
            self.assertEqual(app.conn.execute("SELECT COUNT(*) FROM users").fetchone()[0], 0)
            self.assertEqual(app.conn.execute("SELECT COUNT(*) FROM chats").fetchone()[0], 0)
            self.assertEqual(app.conn.execute("PRAGMA foreign_key_check").fetchall(), [])
            self.assertEqual(app.conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def assert_legacy_password_column_is_copied(self):
        path = self.make_db_path()
        password_hash = UserService(repo=None).hash_password(PASSWORD)
        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY,
                username TEXT UNIQUE,
                email TEXT UNIQUE,
                password TEXT
            );
            CREATE TABLE chats (id INTEGER PRIMARY KEY, name TEXT UNIQUE);
            CREATE TABLE chat_members (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY,
                chat_id INTEGER,
                sender_id INTEGER,
                text TEXT,
                created_at TEXT
            );
        """)
        conn.execute(
            "INSERT INTO users (id, username, email, password) VALUES (?, ?, ?, ?)",
            (1, "olduser", "old@example.com", password_hash),
        )
        conn.execute("INSERT INTO chats (id, name) VALUES (?, ?)", (1, "oldchat"))
        conn.execute(
            "INSERT INTO chat_members (chat_id, user_id, role) VALUES (?, ?, ?)",
            (1, 1, "owner"),
        )
        conn.commit()
        conn.close()

        with create_services(path) as app:
            self.assertEqual(app.user_service.login("olduser", PASSWORD).username, "olduser")
            self.assertEqual(app.conn.execute("PRAGMA foreign_key_check").fetchall(), [])

    def assert_global_unique_chat_name_index_is_removed(self):
        path = self.make_db_path()
        conn = sqlite3.connect(path)
        conn.executescript("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL
            );
            CREATE TABLE chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE chat_members (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT 'member',
                PRIMARY KEY (chat_id, user_id)
            );
            CREATE TABLE messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                sender_id INTEGER NOT NULL,
                text TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()
        conn.close()

        with create_services(path) as app:
            indexes = app.conn.execute("PRAGMA index_list(chats)").fetchall()
            unique_name_indexes = []
            for row in indexes:
                if row[2]:
                    columns = [
                        col[2]
                        for col in app.conn.execute(f"PRAGMA index_info({row[1]})").fetchall()
                    ]
                    if columns == ["name"]:
                        unique_name_indexes.append(row[1])
            self.assertEqual(unique_name_indexes, [])

            first = app.user_service.register("first", "first@example.com", PASSWORD)
            second = app.user_service.register("secon", "second@example.com", PASSWORD)
            first_chat = app.chat_service.create_chat("shared", first.id)
            second_chat = app.chat_service.create_chat("shared", second.id)
            self.assertNotEqual(first_chat.id, second_chat.id)
            self.assertEqual(app.conn.execute("PRAGMA foreign_key_check").fetchall(), [])


if __name__ == "__main__":
    unittest.main()
