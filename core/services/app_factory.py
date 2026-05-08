from dataclasses import dataclass
import sqlite3

from core.repositories import (
    SQLiteChatMembersRepository,
    SQLiteChatRepository,
    SQLiteMessagesRepository,
    SQLiteUsersRepository,
)
from core.repositories.sqlite import DEFAULT_DB_PATH, create_connection, init_schema
from core.services.chat_service import ChatService
from core.services.message_service import MessageService
from core.services.session_service import SessionService
from core.services.user_service import UserService


@dataclass
class ApplicationServices:
    conn: sqlite3.Connection
    user_service: UserService
    chat_service: ChatService
    message_service: MessageService
    session_service: SessionService

    def close(self):
        self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.close()


def create_services(db_path=DEFAULT_DB_PATH):
    conn = create_connection(db_path)
    init_schema(conn)

    users_repo = SQLiteUsersRepository(conn=conn, initialize=False)
    chat_repo = SQLiteChatRepository(conn=conn, initialize=False)
    msg_repo = SQLiteMessagesRepository(conn=conn, initialize=False)
    members_repo = SQLiteChatMembersRepository(conn=conn, initialize=False)

    message_service = MessageService(msg_repo=msg_repo)
    session_service = SessionService()
    user_service = UserService(repo=users_repo)
    chat_service = ChatService(
        message_service=message_service,
        repo=chat_repo,
        memb_repo=members_repo,
    )

    return ApplicationServices(
        conn=conn,
        user_service=user_service,
        chat_service=chat_service,
        message_service=message_service,
        session_service=session_service,
    )
