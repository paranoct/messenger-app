from core.models.chat import Chat

class ChatService:
    def __init__(self, repo, message_service):
        self.chat_repo = repo
        self.message_service = message_service        

    def send_message(self, chat_id: int, sender_id: int, text: str):
        chat = self.chat_repo.get_chat_by_id(chat_id)
        if chat is None:
            raise ValueError("Chat with given id not found")
        message = self.message_service.create_message(chat_id, sender_id, text)
        return message
    
    def get_messages(self, chat_id: int):
        chat = self.chat_repo.get_chat_by_id(chat_id)
        if chat is None:
            raise ValueError("Chat with given id not found")
        return self.message_service.get_messages_by_chat_id(chat_id)
    
    def create_chat(self, name: str):
        chat = self.chat_repo.add_chat(name)
        return chat
    
    def get_chat(self, id_or_name):
        id_or_name = str(id_or_name).strip()

        chat = self.chat_repo.get_chat_by_name(id_or_name)
        if chat:
            return chat.id

        if id_or_name.isdigit():
            chat_id = int(id_or_name)
            chat = self.chat_repo.get_chat_by_id(chat_id)
            if chat:
                return chat.id

        raise ValueError("Chat with given id or name was not found")
        
    def list_chats(self):
        return self.chat_repo.list_chats()
