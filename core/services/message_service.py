from datetime import datetime

class MessageService:
    def __init__(self, msg_repo):
        self.msg_repo = msg_repo
    
    def create_message(self, chat_id: int, sender_id: int, text: str):
        message = self.msg_repo.add_message(chat_id, sender_id, text, datetime.now())
        return message
    
    def delete_message(self, message_id, current_user_id):
        message = self.msg_repo.get_message_by_id(message_id)
        if message.sender_id != current_user_id:
            raise ValueError("Message sender_id and user_id are not the same")
        self.msg_repo.delete_message(message_id=message_id)
        

    def get_messages_by_chat_id(self, chat_id):
        return self.msg_repo.list_messages_for_chat(chat_id=chat_id)