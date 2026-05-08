from datetime import datetime
import sqlite3

from core.models import Chat, Message, User


DEFAULT_DB_PATH = "messenger.db"
CHAT_ROLES = {"owner", "admin", "member"}


def create_connection(db_path=DEFAULT_DB_PATH):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_schema(conn):
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS chat_members (
        chat_id INTEGER NOT NULL,
        user_id INTEGER NOT NULL,
        role TEXT NOT NULL DEFAULT 'member',
        PRIMARY KEY (chat_id, user_id),
        FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        CHECK (role IN ('owner', 'admin', 'member'))
    );

    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id INTEGER NOT NULL,
        sender_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
        FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_chat_members_user_id
        ON chat_members(user_id);

    CREATE INDEX IF NOT EXISTS idx_messages_chat_id_created_at
        ON messages(chat_id, created_at);

    CREATE INDEX IF NOT EXISTS idx_chats_name
        ON chats(name);
    """)
    _add_column_if_missing(conn, "users", "password_hash", "TEXT")
    _add_column_if_missing(conn, "chat_members", "role", "TEXT NOT NULL DEFAULT 'member'")
    _copy_legacy_password_hash(conn)
    _delete_users_without_password_hash(conn)
    _rebuild_chats_if_needed(conn)
    _rebuild_chat_members_if_needed(conn)
    _rebuild_messages_if_needed(conn)
    _normalize_chat_member_roles(conn)
    _delete_empty_chats(conn)
    _create_chat_owner_index(conn)
    conn.commit()


def _add_column_if_missing(conn, table_name, column_name, column_definition):
    columns = _get_columns(conn, table_name)
    if column_name not in columns:
        conn.execute(
            f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
        )


def _get_columns(conn, table_name):
    return {
        row["name"]
        for row in conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    }


def _clean_required_text(value, error_message):
    if value is None:
        raise ValueError(error_message)
    value = str(value).strip()
    if not value or not value.split():
        raise ValueError(error_message)
    return value


def _copy_legacy_password_hash(conn):
    columns = _get_columns(conn, "users")
    if "password" not in columns or "password_hash" not in columns:
        return

    conn.execute("""
        UPDATE users
        SET password_hash = password
        WHERE (password_hash IS NULL OR TRIM(password_hash) = '')
          AND password IS NOT NULL
          AND TRIM(password) != ''
    """)


def _delete_users_without_password_hash(conn):
    conn.execute("""
        DELETE FROM users
        WHERE password_hash IS NULL
           OR TRIM(password_hash) = ''
    """)


def _normalize_chat_member_roles(conn):
    conn.execute("""
        UPDATE chat_members
        SET role = 'member'
        WHERE role IS NULL
           OR role NOT IN ('owner', 'admin', 'member')
    """)

    duplicate_owner_rows = conn.execute("""
        SELECT chat_id, MIN(user_id) AS owner_id
        FROM chat_members
        WHERE role = 'owner'
        GROUP BY chat_id
        HAVING COUNT(*) > 1
    """).fetchall()

    for row in duplicate_owner_rows:
        conn.execute(
            """
            UPDATE chat_members
            SET role = 'admin'
            WHERE chat_id = ?
              AND role = 'owner'
              AND user_id != ?
            """,
            (row["chat_id"], row["owner_id"]),
        )

    rows = conn.execute("""
        SELECT chat_members.chat_id,
               COALESCE(
                   (
                       SELECT MIN(admin_members.user_id)
                       FROM chat_members AS admin_members
                       WHERE admin_members.chat_id = chat_members.chat_id
                         AND admin_members.role = 'admin'
                   ),
                   MIN(chat_members.user_id)
               ) AS owner_id
        FROM chat_members
        GROUP BY chat_members.chat_id
        HAVING SUM(CASE WHEN chat_members.role = 'owner' THEN 1 ELSE 0 END) = 0
    """).fetchall()

    for row in rows:
        conn.execute(
            """
            UPDATE chat_members
            SET role = 'owner'
            WHERE chat_id = ? AND user_id = ?
            """,
            (row["chat_id"], row["owner_id"]),
        )


def _delete_empty_chats(conn):
    conn.execute("""
        DELETE FROM chats
        WHERE NOT EXISTS (
            SELECT 1
            FROM chat_members
            WHERE chat_members.chat_id = chats.id
        )
    """)


def _create_chat_owner_index(conn):
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_one_owner_per_chat
        ON chat_members(chat_id)
        WHERE role = 'owner'
    """)


def _has_unique_chat_name_index(conn):
    rows = conn.execute("PRAGMA index_list(chats)").fetchall()
    for row in rows:
        if not row["unique"]:
            continue

        index_name = row["name"]
        columns = [
            column["name"]
            for column in conn.execute(f"PRAGMA index_info({index_name})").fetchall()
        ]
        if columns == ["name"]:
            return True
    return False


def _rebuild_chats_if_needed(conn):
    if not _has_unique_chat_name_index(conn):
        return

    conn.commit()
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.executescript("""
            DROP TABLE IF EXISTS chats_new;

            CREATE TABLE chats_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL
            );

            INSERT INTO chats_new (id, name)
            SELECT id, name
            FROM chats
            WHERE name IS NOT NULL
              AND TRIM(name) != '';

            DROP TABLE chats;
            ALTER TABLE chats_new RENAME TO chats;

            CREATE INDEX IF NOT EXISTS idx_chats_name
                ON chats(name);
        """)
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def _has_foreign_keys(conn, table_name, expected_tables):
    rows = conn.execute(f"PRAGMA foreign_key_list({table_name})").fetchall()
    found_tables = {row["table"] for row in rows}
    return expected_tables.issubset(found_tables)


def _rebuild_chat_members_if_needed(conn):
    if _has_foreign_keys(conn, "chat_members", {"chats", "users"}):
        return

    conn.executescript("""
        DROP TABLE IF EXISTS chat_members_new;

        CREATE TABLE chat_members_new (
            chat_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL DEFAULT 'member',
            PRIMARY KEY (chat_id, user_id),
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            CHECK (role IN ('owner', 'admin', 'member'))
        );

        INSERT OR IGNORE INTO chat_members_new (chat_id, user_id, role)
        SELECT chat_members.chat_id,
               chat_members.user_id,
               CASE
                   WHEN chat_members.role IN ('owner', 'admin', 'member')
                   THEN chat_members.role
                   ELSE 'member'
               END
        FROM chat_members
        JOIN chats ON chats.id = chat_members.chat_id
        JOIN users ON users.id = chat_members.user_id;

        DROP TABLE chat_members;
        ALTER TABLE chat_members_new RENAME TO chat_members;

        CREATE INDEX IF NOT EXISTS idx_chat_members_user_id
            ON chat_members(user_id);
    """)
    _normalize_chat_member_roles(conn)


def _rebuild_messages_if_needed(conn):
    if _has_foreign_keys(conn, "messages", {"chats", "users"}):
        return

    conn.executescript("""
        DROP TABLE IF EXISTS messages_new;

        CREATE TABLE messages_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chat_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (chat_id) REFERENCES chats(id) ON DELETE CASCADE,
            FOREIGN KEY (sender_id) REFERENCES users(id) ON DELETE CASCADE
        );

        INSERT INTO messages_new (id, chat_id, sender_id, text, created_at)
        SELECT messages.id,
               messages.chat_id,
               messages.sender_id,
               messages.text,
               messages.created_at
        FROM messages
        JOIN chats ON chats.id = messages.chat_id
        JOIN users ON users.id = messages.sender_id
        WHERE messages.text IS NOT NULL
          AND messages.created_at IS NOT NULL;

        DROP TABLE messages;
        ALTER TABLE messages_new RENAME TO messages;

        CREATE INDEX IF NOT EXISTS idx_messages_chat_id_created_at
            ON messages(chat_id, created_at);
    """)


def _user_from_row(row):
    return User(
        id=row["id"],
        username=row["username"],
        email=row["email"],
        password_hash=row["password_hash"],
    )


def _chat_from_row(row):
    return Chat(id=row["id"], name=row["name"])


def _message_from_row(row):
    created_at = row["created_at"]
    if not isinstance(created_at, datetime):
        created_at = datetime.fromisoformat(created_at)

    return Message(
        id=row["id"],
        chat_id=row["chat_id"],
        sender_id=row["sender_id"],
        text=row["text"],
        created_at=created_at,
    )


class SQLiteBaseRepository:
    def __init__(self, db_path=DEFAULT_DB_PATH, conn=None, initialize=True):
        self.conn = conn if conn is not None else create_connection(db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")
        if initialize:
            init_schema(self.conn)


class SQLiteChatRepository(SQLiteBaseRepository):
    def add_chat_with_owner(self, name, owner_id):
        name = _clean_required_text(name, "Название чата не может быть пустым")
        cursor = self.conn.execute("SELECT * FROM users WHERE id = ?",(owner_id,))
        result = cursor.fetchone()
        if result is None:
            raise ValueError("Пользователь с данным id не найден")
        if self.get_chat_by_name_for_user(name, owner_id) is not None:
            raise ValueError("Ошибка в создании чата")

        try:
            with self.conn:
                cursor = self.conn.execute(
                    "INSERT INTO chats (name) VALUES (?)",
                    (name,),
                )
                chat_id = cursor.lastrowid

                self.conn.execute(
                    """
                    INSERT INTO chat_members (chat_id, user_id, role)
                    VALUES (?, ?, ?)
                    """,
                    (chat_id, owner_id, "owner")
                )
        except sqlite3.IntegrityError:
            raise ValueError("Ошибка в создании чата")

        return Chat(id=chat_id, name=name)

    def delete_chat(self, chat: Chat):
        if self.get_chat_by_id(chat.id) is None:
            raise ValueError("Чат с таким id не найден")

        with self.conn:
            self.conn.execute("DELETE FROM messages WHERE chat_id = ?", (chat.id,))
            self.conn.execute("DELETE FROM chat_members WHERE chat_id = ?", (chat.id,))
            self.conn.execute("DELETE FROM chats WHERE id = ?", (chat.id,))

    def get_chat_by_id(self, chat_id: int):
        row = self.conn.execute(
            "SELECT id, name FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone()
        if row is None:
            return None
        return _chat_from_row(row)

    def get_chat_by_name(self, chat_name: str):
        row = self.conn.execute(
            "SELECT id, name FROM chats WHERE name = ?",
            (chat_name,),
        ).fetchone()
        if row is None:
            return None
        return _chat_from_row(row)

    def get_chat_by_name_for_user(self, chat_name: str, user_id: int):
        row = self.conn.execute(
            """
            SELECT chats.id, chats.name
            FROM chats
            JOIN chat_members ON chat_members.chat_id = chats.id
            WHERE chats.name = ?
              AND chat_members.user_id = ?
            ORDER BY chats.id
            LIMIT 1
            """,
            (chat_name, user_id),
        ).fetchone()
        if row is None:
            return None
        return _chat_from_row(row)

    def list_chats(self, user_id):
        rows = self.conn.execute("""
            SELECT chats.id, chats.name
            FROM chats
            JOIN chat_members ON chat_members.chat_id = chats.id
            WHERE chat_members.user_id = ?
            ORDER BY chats.id
        """, (user_id,)).fetchall()

        return [_chat_from_row(row) for row in rows]


class SQLiteUsersRepository(SQLiteBaseRepository):
    def add_user(self, username, email, password_hash):
        username = _clean_required_text(username, "Логин не может быть пустым")
        email = _clean_required_text(email, "Электронная почта не может быть пустой")
        password_hash = _clean_required_text(
            password_hash,
            "Хеш пароля не может быть пустым",
        )

        if self.get_user_by_name(username) is not None:
            raise ValueError("Пользователь с таким логином уже существует")

        if self.get_user_by_email(email) is not None:
            raise ValueError("Пользователь с таким email уже существует")

        try:
            with self.conn:
                cursor = self.conn.execute(
                    """
                    INSERT INTO users (username, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (username, email, password_hash),
                )
        except sqlite3.IntegrityError as error:
            error_text = str(error)

            if "users.username" in error_text:
                raise ValueError("Пользователь с таким логином уже существует")

            elif "users.email" in error_text:
                raise ValueError("Пользователь с таким email уже существует")

            raise ValueError("Пользователь с таким логином или email уже существует")

        return self.get_user_by_id(cursor.lastrowid)

    def delete_user(self, user: User):
        self.get_user_by_id(user.id)

        with self.conn:
            self.conn.execute("DELETE FROM messages WHERE sender_id = ?", (user.id,))
            self.conn.execute("DELETE FROM chat_members WHERE user_id = ?", (user.id,))
            cursor = self.conn.execute("DELETE FROM users WHERE id = ?", (user.id,))
            deleted_count = cursor.rowcount
            _normalize_chat_member_roles(self.conn)
            _delete_empty_chats(self.conn)

        if deleted_count == 0:
            raise ValueError("Пользователь с таким id не найден")

    def get_user_by_username_and_password_hash(self, username, password_hash):
        row = self.conn.execute(
            "SELECT id, username, email, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            raise ValueError("Пользователь с таким логином не найден")

        row = self.conn.execute(
            """
            SELECT id, username, email, password_hash
            FROM users
            WHERE username = ? AND password_hash = ?
            """,
            (username, password_hash),
        ).fetchone()
        if row is None:
            raise ValueError("Неверный хеш пароля")
        return _user_from_row(row)

    def get_user_by_id(self, user_id: int) -> User:
        row = self.conn.execute(
            "SELECT id, username, email, password_hash FROM users WHERE id = ?",
            (user_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Пользователь с таким id не найден")
        return _user_from_row(row)

    def get_user_by_name(self, username: str):
        row = self.conn.execute(
            "SELECT id, username, email, password_hash FROM users WHERE username = ?",
            (username,),
        ).fetchone()
        if row is None:
            return None
        return _user_from_row(row)

    def get_user_by_email(self, email: str):
        row = self.conn.execute(
            "SELECT id, username, email, password_hash FROM users WHERE email = ?",
            (email,),
        ).fetchone()
        if row is None:
            return None
        return _user_from_row(row)

    def list_users(self):
        rows = self.conn.execute(
            "SELECT id, username, email, password_hash FROM users ORDER BY id"
        ).fetchall()
        return [_user_from_row(row) for row in rows]


class SQLiteMessagesRepository(SQLiteBaseRepository):
    def get_message_by_id(self, message_id):
        row = self.conn.execute(
            """
            SELECT id, chat_id, sender_id, text, created_at
            FROM messages
            WHERE id = ?
            """,
            (message_id,),
        ).fetchone()
        if row is None:
            raise ValueError("Сообщение с таким id не найдено")
        return _message_from_row(row)

    def add_message(self, chat_id, sender_id, text, created_at):
        text = _clean_required_text(text, "Сообщение не может быть пустым")
        if chat_id is None:
            raise ValueError("id чата для сообщения не может быть пустым")
        if sender_id is None:
            raise ValueError("id отправителя сообщения не может быть пустым")
        if created_at is None:
            raise ValueError("Дата создания сообщения не может быть пустой")

        if isinstance(created_at, datetime):
            created_at_value = created_at.isoformat()
        else:
            created_at_value = str(created_at)

        if self.conn.execute(
            "SELECT 1 FROM users WHERE id = ?",
            (sender_id,),
        ).fetchone() is None:
            raise ValueError("Сообщение создано от имени несуществующего пользователя")

        if self.conn.execute(
            "SELECT 1 FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone() is None:
            raise ValueError("Сообщение создано в несуществующем чате")

        try:
            with self.conn:
                cursor = self.conn.execute(
                    """
                    INSERT INTO messages (chat_id, sender_id, text, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (chat_id, sender_id, text, created_at_value),
                )
        except sqlite3.IntegrityError:
            raise ValueError("Ошибка при создании сообщения")

        return Message(
            id=cursor.lastrowid,
            chat_id=chat_id,
            sender_id=sender_id,
            text=text,
            created_at=datetime.fromisoformat(created_at_value),
        )

    def list_messages_for_chat(self, chat_id):
        rows = self.conn.execute(
            """
            SELECT id, chat_id, sender_id, text, created_at
            FROM messages
            WHERE chat_id = ?
            ORDER BY created_at, id
            """,
            (chat_id,),
        ).fetchall()
        return [_message_from_row(row) for row in rows]

    def delete_message(self, message_id):
        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM messages WHERE id = ?",
                (message_id,),
            )

        if cursor.rowcount == 0:
            raise ValueError("Сообщение с таким id не найдено")


class SQLiteChatMembersRepository(SQLiteBaseRepository):
    def get_members_by_chat_id(self, chat_id: int):
        rows = self.conn.execute(
            """
            SELECT user_id
            FROM chat_members
            WHERE chat_id = ?
            ORDER BY user_id
            """,
            (chat_id,),
        ).fetchall()
        return [row["user_id"] for row in rows]

    def is_user_in_chat(self, chat_id: int, user_id: int):
        row = self.conn.execute(
            """
            SELECT 1
            FROM chat_members
            WHERE chat_id = ? AND user_id = ?
            LIMIT 1
            """,
            (chat_id, user_id),
        ).fetchone()
        return row is not None

    def add_user_to_chat(self, user_id: int, chat_id: int, role="member"):
        role = _clean_required_text(role, "Роль пользователя в чате не может быть пустой")
        if role not in CHAT_ROLES:
            raise ValueError("Некорректная роль пользователя в чате")
        if role == "owner":
            raise ValueError("Некорректная роль пользователя в чате")

        if self.conn.execute(
            "SELECT 1 FROM users WHERE id = ?",
            (user_id,),
        ).fetchone() is None:
            raise ValueError("Пользователь с таким id не найден")

        if self.conn.execute(
            "SELECT 1 FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone() is None:
            raise ValueError("Чат с таким id не найден")

        try:
            with self.conn:
                self.conn.execute(
                    """
                    INSERT INTO chat_members (user_id, chat_id, role)
                    VALUES (?, ?, ?)
                    """,
                    (user_id, chat_id, role),
                )
        except sqlite3.IntegrityError as error:
            error_text = str(error)
            if "CHECK constraint failed" in error_text:
                raise ValueError("Некорректная роль пользователя в чате")
            raise ValueError("Пользователь уже состоит в этом чате")

    def get_user_role(self, chat_id, user_id):
        row = self.conn.execute(
            "SELECT role FROM chat_members WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id),
        ).fetchone()
        if row is None:
            return None
        return row["role"]

    def is_chat_owner(self, chat_id, user_id):
        return self.get_user_role(chat_id, user_id) == "owner"

    def list_members_by_chat_id(self, chat_id: int) -> list[User]:
        if self.conn.execute(
            "SELECT 1 FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone() is None:
            raise ValueError("Чат с таким id не найден")

        rows = self.conn.execute(
            """
            SELECT users.id, users.username, users.email, users.password_hash
            FROM users
            JOIN chat_members ON chat_members.user_id = users.id
            WHERE chat_members.chat_id = ?
            ORDER BY users.id
            """,
            (chat_id,),
        ).fetchall()
        return [_user_from_row(row) for row in rows]

    def delete_user_from_chat(self, chat_id, user_id):
        if self.conn.execute(
            "SELECT 1 FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone() is None:
            raise ValueError("Чат с таким id не найден")

        if self.conn.execute(
            "SELECT 1 FROM users WHERE id = ?",
            (user_id,),
        ).fetchone() is None:
            raise ValueError("Данный пользователь не существует")

        with self.conn:
            cursor = self.conn.execute(
                "DELETE FROM chat_members WHERE user_id = ? AND chat_id = ?",
                (user_id, chat_id),
            )
            deleted_count = cursor.rowcount
            if deleted_count:
                _normalize_chat_member_roles(self.conn)
                _delete_empty_chats(self.conn)

        if deleted_count == 0:
            raise ValueError("Пользователь не состоит в этом чате")

    def change_user_role(self, chat_id, user_id, role):
        role = _clean_required_text(role, "Роль пользователя в чате не может быть пустой")
        if role not in CHAT_ROLES:
            raise ValueError("Некорректная роль пользователя в чате")
        if role == "owner":
            raise ValueError("Некорректная роль пользователя в чате")

        if self.conn.execute(
            "SELECT 1 FROM chats WHERE id = ?",
            (chat_id,),
        ).fetchone() is None:
            raise ValueError("Чат с таким id не найден")

        if self.conn.execute(
            "SELECT 1 FROM users WHERE id = ?",
            (user_id,),
        ).fetchone() is None:
            raise ValueError("Пользователь с таким id не найден")

        with self.conn:
            cursor = self.conn.execute(
                """
                UPDATE chat_members
                SET role = ?
                WHERE chat_id = ? AND user_id = ?
                """,
                (role, chat_id, user_id),
            )

        if cursor.rowcount == 0:
            raise ValueError("Пользователь не состоит в этом чате")
