from core.models import Chat, User, Message
import sqlite3
from datetime import datetime
class SQLiteChatRepository:
    conn = sqlite3.connect('messenger.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chats (
        id INTEGER PRIMARY KEY, 
        name TEXT UNIQUE
    )
    ''')
    conn.commit()

    def add_chat(self, name):
        name = name.strip()
        if not name or not name.split():
            raise ValueError("Chat name cannot be empty")
        try:
            self.cursor.execute("INSERT INTO chats (name) VALUES (?)", (name,))
            self.conn.commit()
        except sqlite3.IntegrityError:
            raise ValueError("Chat with given name already exists")
        chat_id = self.cursor.lastrowid
        return Chat(id=chat_id, name=name)
    
    def delete_chat(self, chat: Chat):
        self.cursor.execute("DELETE FROM chats WHERE id = ?",(chat.id,))
        self.conn.commit()
        if self.cursor.rowcount == 0:
            raise ValueError("Chat with given id was not found")
        self.cursor.execute("DELETE FROM messages WHERE chat_id = ?",(chat.id,))
        self.conn.commit()

       
        
    def get_chat_by_id(self, chat_id: int):
        self.cursor.execute("SELECT id, name FROM chats WHERE id = ?",(chat_id,))
        row = self.cursor.fetchone()
        if row is None:
            return None        
        return Chat(id=row[0],name=row[1])
    
    def get_chat_by_name(self, chat_name: str):
        self.cursor.execute("SELECT id, name FROM chats WHERE name = ?",(chat_name,))
        row = self.cursor.fetchone()
        if row is None:
            return None        
        return Chat(id=row[0],name=row[1])
        
    def list_chats(self):
        self.cursor.execute("SELECT id, name FROM chats")
        rows = self.cursor.fetchall()
        return [
            Chat(id=row[0], name=row[1])
            for row in rows
        ]


class SQLiteUsersRepository:
    conn = sqlite3.connect('messenger.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY, 
        username TEXT UNIQUE,
        email TEXT UNIQUE
    )
    ''')
    conn.commit()

    def add_user(self, username, email):
        try:
            self.cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", (username, email))
            self.conn.commit()
        except sqlite3.IntegrityError as error:
            error_text = str(error)

            if "users.username" in error_text:
                raise ValueError("User with given username already exists")

            if "users.email" in error_text:
                raise ValueError("User with given email already exists")

            raise ValueError("User with given username or email already exists")
        
        user_id = self.cursor.lastrowid
        return User(id=user_id, username=username, email=email)
        
    def delete_user(self, user:User):
        self.cursor.execute("DELETE FROM users WHERE id = ?",(user.id,))
        self.conn.commit()

        if self.cursor.rowcount == 0:
          raise ValueError("User with given id was not found")
    
    def get_user_by_id(self, user_id:int):
        self.cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
        row = self.cursor.fetchone()
        if row is None:
            return None        
        return User(id=row[0], username=row[1], email=row[2])
    
    def get_user_by_name(self, username: str):
        self.cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = self.cursor.fetchone()
        if row is None:
            return None        
        return User(id=row[0], username=row[1], email=row[2])
    
    def list_users(self):
        self.cursor.execute("SELECT id, username, email FROM users")
        rows = self.cursor.fetchall()
        return [
            User(id=row[0], username=row[1], email=row[2])
            for row in rows
        ]



class SQLiteMessagesRepository:
    conn = sqlite3.connect('messenger.db')
    cursor = conn.cursor()

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY,
        chat_id INTEGER,
        sender_id INTEGER,
        text TEXT,
        created_at TEXT
    )
    ''')
    conn.commit()

    def get_message_by_id(self, message_id):
        self.cursor.execute("SELECT * FROM messages WHERE id = ?",(message_id,))
        row = self.cursor.fetchone()
        if row is None:
            raise ValueError("Message with given id was not found")
        return Message(id=row[0],chat_id=row[1],sender_id=row[2],text=row[3],created_at=datetime.fromisoformat(row[4]))

    def add_message(self, chat_id, sender_id, text, created_at):
        text = text.strip()
        if not text or not text.split():
            raise ValueError("Message cannot be empty")
        self.cursor.execute("INSERT INTO messages (chat_id, sender_id, text, created_at) VALUES (?, ?, ?, ?)",(chat_id,sender_id,text,created_at))
        self.conn.commit()
        msg_id = self.cursor.lastrowid
        return Message(msg_id, chat_id, sender_id, text, created_at)

    def list_messages_for_chat(self, chat_id):
        self.cursor.execute("SELECT id, chat_id, sender_id, text, created_at FROM messages WHERE chat_id = ? ORDER BY created_at",(chat_id,))
        rows = self.cursor.fetchall()
        return [
            Message(id=row[0], chat_id=row[1], sender_id=row[2], text=row[3], created_at=datetime.fromisoformat(row[4]))
            for row in rows
        ]
    
    def delete_message(self, message_id):
        self.cursor.execute("DELETE FROM messages WHERE id = ?",(message_id,))
        self.conn.commit()

        if self.cursor.rowcount == 0:
          raise ValueError("Message with given id was not found")
