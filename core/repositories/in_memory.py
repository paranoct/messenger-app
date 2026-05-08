from core.models.chat import Chat
from core.models.user import User
from core.models.message import Message
class InMemoryChatRepository:
    def __init__(self):
        self.chats = {}
        self.chats_by_name = {}

    def add_chat(self, chat: Chat):
        if self.get_chat_by_id(chat.id) or self.get_chat_by_name(chat.name):
            raise ValueError("Чат с таким id или названием уже существует")
        self.chats[chat.id] = chat
        self.chats_by_name[chat.name] = chat
    
    def delete_chat(self, chat: Chat):
        if not self.get_chat_by_id(chat.id) or not self.get_chat_by_name(chat.name):
            raise ValueError("Чат с таким id или названием не найден")
        del self.chats[chat.id]
        del self.chats_by_name[chat.name]
    
    def get_chat_by_id(self, chat_id: int):
        return self.chats.get(chat_id)
    
    def get_chat_by_name(self, chat_name: str):
        return self.chats_by_name.get(chat_name)
        
    def list_chats(self):
        return list(self.chats.values())

class InMemoryUsersRepository:
    def __init__(self):
        self.users = {}
        self.users_by_names = {}

    def get_user_by_id(self, user_id: int):
        return self.users.get(user_id)
    
    def get_user_by_name(self, username: str):
        return self.users_by_names.get(username)

    def add_user(self, user: User):
        if self.get_user_by_id(user.id) or self.get_user_by_name(user.username):
            raise ValueError("Пользователь с таким id или логином уже существует")
        self.users[user.id] = user
        self.users_by_names[user.username] = user

    def delete_user(self, user:User):
        if not self.get_user_by_id(user.id) or not self.get_user_by_name(user.username):
            raise ValueError("Пользователь с таким id или логином не найден")
        del self.users[user.id]
        del self.users_by_names[user.username]

    def list_users(self):
        return list(self.users.values())
    
class InMemoryMessagesRepository:
    def __init__(self):
        self.messages = {}

    def get_msg_by_id(self, msg_id: int):
        return self.messages.get(msg_id)

    def add_message(self, message: Message):
        self.messages[message.id] = message
    
    def list_messages_for_chat(self, chat_id):
        messages = []
        for msg in self.messages.values():
            if msg.chat_id == chat_id:
                messages.append(msg)
        return messages

    def delete_message(self, message: Message):
        if not self.get_msg_by_id(message.id):
            raise ValueError("Сообщение с таким id не найдено")
        del self.messages[message.id]
